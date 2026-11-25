"""The stream runner: tier 1 rules, then the agents, then a human when needed (PLAN.md 5.5, task 2.6).

Extends the organiser starter's `process_transactions`:
- every transaction is scored by `rules.scorer.score_with_network` first; below the threshold it's auto-cleared and
  recorded with `decided_by="rules"`, with no LLM call;
- otherwise the supervisor is invoked on the customer's thread, with `as_of`, the rule score and a LangSmith run ID
  in the context;
- interrupts are answered by `on_interrupt` (the notebook's analyst panel) or by scripted `reviewer_answers`
  (evals); with neither, the agents' own decision is accepted, as in the starter;
- model calls, tokens, seconds and each investigation's tool calls are counted, for the efficiency and trajectory evals.

The notebook runs one global, timestamp-ordered stream (it tells the story). Evals may run customers in parallel
(`parallel_customers=True`, DEC-007): no verdict depends on the order, because the graph and history reads are
filtered by `as_of` and precedents are stored per customer.
"""

import contextvars
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Lock

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command

from rules.scorer import goes_to_agents, score_with_network
from utils import db
from utils.state import MyAgentContext


class UsageCounter(BaseCallbackHandler):
    """Counts chat-model calls and tokens across the supervisor and all sub-agents."""

    def __init__(self):
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self._lock = Lock()

    def on_chat_model_start(self, serialized, messages, **kwargs):
        with self._lock:
            self.calls += 1

    def on_llm_end(self, response, **kwargs):
        for gens in response.generations:
            for g in gens:
                usage = getattr(getattr(g, "message", None), "usage_metadata", None) or {}
                with self._lock:
                    self.input_tokens += usage.get("input_tokens", 0)
                    self.output_tokens += usage.get("output_tokens", 0)


def global_stream(start: str | None = None, end: str | None = None, user_ids: set[str] | None = None) -> list[dict]:
    """All customers' transactions in the active world, in timestamp order, from `start` up to (not including) `end`."""
    rows = [t for t in db.table("transactions")
            if (start is None or t["timestamp"] >= start) and (end is None or t["timestamp"] < end)
            and (user_ids is None or t["user_id"] in user_ids)]
    return sorted(rows, key=lambda t: (t["timestamp"], t["transaction_id"]))


def investigation_message(tx: dict, rule_score: int, reasons: list[str]) -> dict:
    """The supervisor's input: the transaction ID and why the rules flagged it. The agents look up the rest."""
    why = "; ".join(reasons) if reasons else "no specific rule"
    return {"messages": [{"role": "user", "content": f"New transaction: {tx['transaction_id']} "
                                                     f"(rule score {rule_score}: {why})"}]}


def _new_tool_calls(messages: list, start: int) -> list[dict]:
    calls = []
    for m in messages[start:]:
        if isinstance(m, AIMessage):
            for c in m.tool_calls or []:
                args = c.get("args", {})
                calls.append({"name": c["name"], "subagent": args.get("subagent_type") if c["name"] == "task" else None,
                              "id": c.get("id")})
    return calls


def _sar_from(messages: list, start: int) -> dict | None:
    """The SAR draft returned by the sar-writer sub-agent in this investigation, if any."""
    sar_call_ids = {c["id"] for c in _new_tool_calls(messages, start) if c["subagent"] == "sar-writer"}
    for m in messages[start:]:
        if isinstance(m, ToolMessage) and m.tool_call_id in sar_call_ids:
            try:
                return json.loads(m.text)
            except (json.JSONDecodeError, TypeError):
                return {"raw": m.text}
    return None


def process_stream(agent, ctx: MyAgentContext, transactions: list[dict], reviewer_answers: dict | None = None,
                   on_interrupt=None, on_event=None, parallel_customers: bool = False, max_workers: int = 4,
                   extra_tags: list[str] | None = None) -> dict:
    """Run transactions through tier 1, the agents and human review. Returns decisions and counters.

    `on_interrupt(question) -> answer` resolves pauses (notebook); otherwise `reviewer_answers[transaction_id]`.
    `on_event(event)` is called after each transaction (live counters in the notebook).
    """
    store = agent.store
    counter = UsageCounter()
    lock = Lock()
    out = {"decisions": [], "investigations": [], "transactions": 0, "rules_cleared": 0}
    msg_index: dict[str, int] = {}

    def run_one(tx: dict):
        profile = db.get("customer_profiles", user_id=tx["user_id"])
        history = [h for h in db.query("transactions", user_id=tx["user_id"])
                   if (h["timestamp"], h["transaction_id"]) < (tx["timestamp"], tx["transaction_id"])]
        rule_score, reasons = score_with_network(tx, history, profile, ctx)

        if not goes_to_agents(rule_score, ctx):
            record = {"transaction_id": tx["transaction_id"], "risk_score": rule_score, "final_decision": "clear",
                      "agent_decision": None, "decided_by": "rules", "rule_score": rule_score,
                      "rule_reasons": reasons, "pattern": "none", "reason": "cleared by rules",
                      "confidence": None, "model_confidence": None, "confidence_checks": [], "hard_flags": [],
                      "precedents_cited": [], "precedents_overridden": [], "trace_run_id": None, "as_of": tx["timestamp"]}
            store.put(("decisions", tx["user_id"]), tx["transaction_id"], record)
            with lock:
                out["transactions"] += 1
                out["rules_cleared"] += 1
                out["decisions"].append(record)
            if on_event:
                on_event({"tx": tx, "record": record, "tier": "rules"})
            return

        run_id = str(uuid.uuid4())
        run_ctx = replace(ctx, user_id=tx["user_id"], as_of=tx["timestamp"], rule_score=rule_score,
                          rule_reasons=tuple(reasons), trace_run_id=run_id)
        own = UsageCounter()  # this investigation only (the shared counter is updated by several threads)
        config = {"configurable": {"thread_id": tx["user_id"]}, "run_id": run_id, "recursion_limit": 80,
                  "callbacks": [counter, own], "run_name": "sentinel-investigation",
                  "tags": ["sentinel", "investigation", *(extra_tags or [])],
                  "metadata": {"transaction_id": tx["transaction_id"], "user_id": tx["user_id"],
                               "rule_score": rule_score}}
        started = time.perf_counter()
        start_index = msg_index.get(tx["user_id"], 0)
        result = agent.invoke(investigation_message(tx, rule_score, reasons), config, context=run_ctx)
        human = None
        while "__interrupt__" in result:
            question = result["__interrupt__"][0].value
            if on_interrupt:
                answer = on_interrupt(question)
            elif reviewer_answers and question["transaction_id"] in reviewer_answers:
                row = reviewer_answers[question["transaction_id"]]
                answer = {"decision": row["decision"], "note": row.get("note", ""), "analyst": "scripted"}
            else:
                answer = {"decision": question["agent_decision"], "note": ""}
            human = {"question": question, "answer": answer}
            resume_config = config | {"run_id": str(uuid.uuid4())}
            result = agent.invoke(Command(resume=answer), resume_config, context=run_ctx)
        seconds = time.perf_counter() - started
        messages = result["messages"]
        msg_index[tx["user_id"]] = len(messages)

        item = store.get(("decisions", tx["user_id"]), tx["transaction_id"])
        record = dict(item.value) if item else {
            "transaction_id": tx["transaction_id"], "final_decision": "escalate", "decided_by": "agent",
            "agent_decision": None, "risk_score": rule_score, "rule_score": rule_score, "rule_reasons": reasons,
            "reason": "record_decision was not called; escalated by default", "pattern": "none",
            "confidence_checks": ["record_decision missing"], "hard_flags": [], "precedents_overridden": []}
        sar = _sar_from(messages, start_index)
        if sar is not None:
            sar_id = f"SAR-{tx['transaction_id']}"
            store.put(("sars", tx["user_id"]), sar_id, sar | {"transaction_id": tx["transaction_id"]})
            record["sar_id"] = sar_id
        record["trace_run_id"] = run_id
        store.put(("decisions", tx["user_id"]), tx["transaction_id"], record)

        investigation = {"transaction_id": tx["transaction_id"], "user_id": tx["user_id"], "seconds": round(seconds, 1),
                         "model_calls": own.calls, "tokens": own.input_tokens + own.output_tokens,
                         "tool_calls": _new_tool_calls(messages, start_index),
                         "human": human, "reply": messages[-1].text if messages else "", "trace_run_id": run_id,
                         "sar": sar}
        with lock:
            out["transactions"] += 1
            out["decisions"].append(record)
            out["investigations"].append(investigation)
        if on_event:
            on_event({"tx": tx, "record": record, "tier": "agents", "investigation": investigation})

    if parallel_customers:
        by_user: dict[str, list[dict]] = {}
        for tx in sorted(transactions, key=lambda t: (t["timestamp"], t["transaction_id"])):
            by_user.setdefault(tx["user_id"], []).append(tx)

        def run_customer(rows):
            for tx in rows:
                run_one(tx)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(contextvars.copy_context().run, run_customer, rows) for rows in by_user.values()]
            for f in futures:
                f.result()
    else:
        for tx in sorted(transactions, key=lambda t: (t["timestamp"], t["transaction_id"])):
            run_one(tx)

    n = max(out["transactions"], 1)
    out["decisions"].sort(key=lambda d: d["transaction_id"])
    out["counters"] = {
        "transactions": out["transactions"],
        "investigations": len(out["investigations"]),
        "llm_share": round(len(out["investigations"]) / n, 4),
        "model_calls": counter.calls,
        "input_tokens": counter.input_tokens,
        "output_tokens": counter.output_tokens,
        "seconds": [i["seconds"] for i in out["investigations"]],
    }
    return out


def decision_log(store, user_id: str) -> list[dict]:
    """Every decision recorded for a customer, in transaction order (from the starter)."""
    items = store.search(("decisions", user_id), limit=10000)
    return sorted((item.value for item in items), key=lambda d: d["transaction_id"])
