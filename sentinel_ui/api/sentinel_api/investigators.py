"""How one transaction gets investigated: live (the real agents), replayed from a recording, or offline.

Every investigator has the same shape, so the session doesn't care which one runs:

    run(tx, rule_score, reasons, on_step, ask_human) -> Outcome

- `on_step(key, state, finding=None, tool=None)` reports agent progress (EX-1).
- `ask_human(question) -> answer` blocks until the analyst decides (EX-4). `question` is the payload the agents'
  `record_decision` passes to `interrupt()`; `answer` is `{"decision", "note", "analyst"}`.
"""

import ast
import json
import threading
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Callable, Protocol

from langchain_core.callbacks import BaseCallbackHandler
from langgraph.types import Command

from tools.decisions import apply_review, hard_flags_for  # sentinel_aml_agent
from utils import db
from utils.state import MyAgentContext
from utils.stream import UsageCounter, _new_tool_calls, _sar_from, investigation_message

OnStep = Callable[..., None]
AskHuman = Callable[[dict], dict]


@dataclass
class Outcome:
    record: dict
    seconds: float
    model_calls: int = 0
    tokens: int = 0
    sar: dict | None = None
    tool_calls: list[dict] = field(default_factory=list)
    trace_run_id: str | None = None
    human: dict | None = None
    replayed: bool = False


class Investigator(Protocol):
    def run(self, tx: dict, rule_score: int, reasons: list[str], on_step: OnStep, ask_human: AskHuman) -> Outcome: ...


#
# Turning sub-agent output into one line (EX-1.2)
#
def _text_of(output) -> str:
    if isinstance(output, str):
        return output
    update = getattr(output, "update", None)
    if isinstance(update, dict) and update.get("messages"):
        output = update["messages"][-1]
    content = getattr(output, "content", output)
    if isinstance(content, list):
        return " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return str(content)


def summarise_finding(subagent: str, text: str) -> str:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return (text or "").strip().replace("\n", " ")[:160]
    if subagent == "pattern-analyst":
        evidence = (data.get("evidence") or [""])[0]
        return f"{str(data.get('pattern', 'none')).replace('_', ' ')} · risk {data.get('risk_score')} · {evidence}"[:200]
    if subagent == "kyc-precedent":
        parts = [f"KYC {data.get('risk_rating', '?')}"]
        if data.get("hard_flags"):
            parts.append("hard flags: " + "; ".join(data["hard_flags"]))
        parts.append(f"{len(data.get('precedents_applicable') or [])} valid precedent(s)")
        if data.get("precedents_expired"):
            parts.append(f"{len(data['precedents_expired'])} expired/out of scope")
        return " · ".join(parts)[:200]
    if subagent == "fund-flow":
        if data.get("ring_confirmed"):
            return (f"Ring confirmed: {len(data.get('accounts') or [])} accounts → {data.get('collector_account')}, "
                    f"pass-through {float(data.get('pass_through_ratio') or 0):.0%}")
        return "No confirmed ring"
    if subagent == "sar-writer":
        return f"SAR draft written for {data.get('subject', 'the customer')}"
    return text[:160]


class StepTracker(BaseCallbackHandler):
    """Watches the supervisor's `task` calls (one per specialist) and the tools each specialist calls."""

    def __init__(self, on_step: OnStep):
        self.on_step = on_step
        self.parents: dict = {}
        self.task_runs: dict = {}
        self.lock = threading.Lock()

    def _remember(self, run_id, parent_run_id):
        with self.lock:
            self.parents[run_id] = parent_run_id

    def _owner(self, run_id) -> str | None:
        seen = 0
        while run_id is not None and seen < 200:
            if run_id in self.task_runs:
                return self.task_runs[run_id]
            run_id = self.parents.get(run_id)
            seen += 1
        return None

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, **kwargs):
        self._remember(run_id, parent_run_id)

    def on_chat_model_start(self, serialized, messages, *, run_id, parent_run_id=None, **kwargs):
        self._remember(run_id, parent_run_id)

    def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, inputs=None, **kwargs):
        self._remember(run_id, parent_run_id)
        name = (serialized or {}).get("name") or kwargs.get("name")
        if name == "task":
            args = inputs if isinstance(inputs, dict) else _parse_args(input_str)
            sub = args.get("subagent_type") or "specialist"
            with self.lock:
                self.task_runs[run_id] = sub
            self.on_step("supervisor", "done", finding=None, tool=f"task → {sub}")
            self.on_step(sub, "working")
        elif name == "record_decision":
            self.on_step("verdict", "working", tool=name)
        else:
            owner = self._owner(parent_run_id)
            self.on_step(owner or "supervisor", None, tool=name)

    def on_tool_end(self, output, *, run_id, **kwargs):
        sub = self.task_runs.get(run_id)
        if sub:
            self.on_step(sub, "done", finding=summarise_finding(sub, _text_of(output)))


def _parse_args(input_str) -> dict:
    try:
        value = ast.literal_eval(input_str) if isinstance(input_str, str) else input_str
        return value if isinstance(value, dict) else {}
    except (ValueError, SyntaxError):
        return {}


#
# Live
#
class LiveInvestigator:
    """Runs the real supervisor, the same way `utils/stream.py` does, with progress callbacks added."""

    def __init__(self, agent, ctx: MyAgentContext):
        self.agent = agent
        self.store = agent.store
        self.ctx = ctx

    def run(self, tx, rule_score, reasons, on_step, ask_human) -> Outcome:
        user = tx["user_id"]
        run_id = str(uuid.uuid4())
        run_ctx = replace(self.ctx, user_id=user, as_of=tx["timestamp"], rule_score=rule_score,
                          rule_reasons=tuple(reasons), trace_run_id=run_id)
        usage = UsageCounter()
        config = {"configurable": {"thread_id": user}, "run_id": run_id, "recursion_limit": 80,
                  "callbacks": [usage, StepTracker(on_step)], "run_name": "sentinel-investigation",
                  "tags": ["sentinel", "investigation", "ui"],
                  "metadata": {"transaction_id": tx["transaction_id"], "user_id": user, "rule_score": rule_score}}
        state = self.agent.get_state({"configurable": {"thread_id": user}})
        start_index = len((state.values or {}).get("messages", [])) if state else 0

        started = time.perf_counter()
        on_step("supervisor", "working")
        result = self.agent.invoke(investigation_message(tx, rule_score, reasons), config, context=run_ctx)
        human = None
        while "__interrupt__" in result:
            question = result["__interrupt__"][0].value
            on_step("verdict", "working", finding="Waiting for the analyst")
            answer = ask_human(question)
            human = {"question": question, "answer": answer}
            result = self.agent.invoke(Command(resume=answer), config | {"run_id": str(uuid.uuid4())}, context=run_ctx)
        seconds = time.perf_counter() - started
        messages = result["messages"]

        item = self.store.get(("decisions", user), tx["transaction_id"])
        record = dict(item.value) if item else {
            "transaction_id": tx["transaction_id"], "final_decision": "escalate", "decided_by": "agent",
            "agent_decision": None, "risk_score": rule_score, "rule_score": rule_score, "rule_reasons": reasons,
            "reason": "record_decision was not called; escalated by default", "pattern": "none",
            "confidence_checks": ["record_decision missing"], "hard_flags": [], "precedents_overridden": []}
        sar = _sar_from(messages, start_index)
        if sar is not None:
            record["sar_id"] = f"SAR-{tx['transaction_id']}"
            self.store.put(("sars", user), record["sar_id"], sar | {"transaction_id": tx["transaction_id"]})
        record["trace_run_id"] = run_id
        self.store.put(("decisions", user), tx["transaction_id"], record)
        return Outcome(record=record, seconds=round(seconds, 1), model_calls=usage.calls,
                       tokens=usage.input_tokens + usage.output_tokens, sar=sar,
                       tool_calls=_new_tool_calls(messages, start_index), trace_run_id=run_id, human=human)


#
# Offline: no model configured
#
class OfflineInvestigator:
    """No model is configured, so nothing can investigate. Every flagged transaction goes to the analyst, with the
    rule reasons as the only evidence. Labelled on screen; never presented as an agent verdict."""

    def __init__(self, store, ctx: MyAgentContext):
        self.store = store
        self.ctx = ctx

    def run(self, tx, rule_score, reasons, on_step, ask_human) -> Outcome:
        on_step("supervisor", "done", finding="Agents offline: no model configured, so the analyst decides")
        run_ctx = replace(self.ctx, user_id=tx["user_id"], as_of=tx["timestamp"])
        profile = db.get("customer_profiles", user_id=tx["user_id"]) or {}
        flags = hard_flags_for(profile, tx["timestamp"]) if profile else []
        question = {"transaction_id": tx["transaction_id"], "risk_score": rule_score, "model_confidence": None,
                    "confidence": None, "agent_decision": "escalate", "pattern": "none",
                    "reason": "; ".join(reasons), "why_review": ["agents offline"], "hard_flags": flags,
                    "precedents": {}, "rule_score": rule_score, "rule_reasons": reasons}
        answer = ask_human(question)
        decision = apply_review(self.store, run_ctx, tx["transaction_id"], tx.get("counterparty_id"), "none", answer)
        record = {"transaction_id": tx["transaction_id"], "risk_score": rule_score, "final_decision": decision,
                  "agent_decision": None, "decided_by": "human", "rule_score": rule_score, "rule_reasons": reasons,
                  "reason": "; ".join(reasons), "pattern": "none", "confidence": None, "confidence_checks": ["agents offline"],
                  "hard_flags": flags, "precedents_cited": [], "precedents_overridden": [], "analyst_note": answer.get("note", ""),
                  "as_of": tx["timestamp"]}
        self.store.put(("decisions", tx["user_id"]), tx["transaction_id"], record)
        on_step("verdict", "done", finding=f"Analyst: {decision}")
        return Outcome(record=record, seconds=0.0, human={"question": question, "answer": answer})
