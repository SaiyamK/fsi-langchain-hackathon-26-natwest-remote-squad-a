"""Record a live run; replay it later (design.md U2, DEC-003).

A recording keeps, per transaction, every progress step and pause with its time offset, plus the final decision
record, SAR draft and LangSmith run ID. Replay plays the steps back at `speed`× and is labelled on screen.

A recorded pause still waits for the real analyst, and their answer goes through the agents' own `apply_review`,
so the precedent saved to memory is real in replay too. The final decision is the analyst's, not the recording's.
"""

import json
import threading
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from tools.decisions import apply_review  # sentinel_aml_agent
from utils.state import MyAgentContext

from sentinel_api import UI_ROOT
from sentinel_api.investigators import AskHuman, Investigator, OnStep, Outcome

DEFAULT_PATH = UI_ROOT / "recordings" / "world0.json"


def load(path: Path = DEFAULT_PATH) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class RecordingInvestigator:
    """Wraps a live investigator and saves what happened after every investigation."""

    def __init__(self, inner: Investigator, model: str, path: Path = DEFAULT_PATH):
        self.inner = inner
        self.path = path
        self.lock = threading.Lock()
        self.data = {"recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": model,
                     "investigations": {}}

    def run(self, tx, rule_score, reasons, on_step: OnStep, ask_human: AskHuman) -> Outcome:
        started = time.perf_counter()
        events: list[dict] = []

        def step(key, state=None, finding=None, tool=None):
            events.append({"t": round(time.perf_counter() - started, 2), "kind": "step", "key": key, "state": state,
                           "finding": finding, "tool": tool})
            on_step(key, state, finding=finding, tool=tool)

        def ask(question):
            events.append({"t": round(time.perf_counter() - started, 2), "kind": "interrupt", "question": question})
            return ask_human(question)

        outcome = self.inner.run(tx, rule_score, reasons, step, ask)
        entry = {"events": events, "record": outcome.record, "seconds": outcome.seconds, "sar": outcome.sar,
                 "model_calls": outcome.model_calls, "tokens": outcome.tokens, "tool_calls": outcome.tool_calls,
                 "trace_run_id": outcome.trace_run_id}
        with self.lock:
            self.data["investigations"][tx["transaction_id"]] = entry
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=1, default=str), encoding="utf-8")
            tmp.replace(self.path)
        return outcome


class ReplayInvestigator:
    """Plays recorded investigations back. Transactions with no recording fall back to `fallback`."""

    def __init__(self, recording: dict, store, ctx: MyAgentContext, fallback: Investigator, speed: float = 3.0):
        self.recording = recording
        self.store = store
        self.ctx = ctx
        self.fallback = fallback
        self.speed = max(speed, 0.1)

    def has(self, transaction_id: str) -> bool:
        return transaction_id in self.recording["investigations"]

    def run(self, tx, rule_score, reasons, on_step, ask_human) -> Outcome:
        entry = self.recording["investigations"].get(tx["transaction_id"])
        if entry is None:
            return self.fallback.run(tx, rule_score, reasons, on_step, ask_human)
        record = dict(entry["record"])
        sar = entry.get("sar")
        human = None
        last = 0.0
        for event in entry["events"]:
            time.sleep(max(event["t"] - last, 0) / self.speed)
            last = event["t"]
            if event["kind"] == "step":
                if event["key"] == "sar-writer" and record.get("final_decision") == "clear":
                    continue  # the analyst cleared it in this session, so no SAR
                on_step(event["key"], event.get("state"), finding=event.get("finding"), tool=event.get("tool"))
            elif event["kind"] == "interrupt":
                question = event["question"]
                answer = ask_human(question)
                run_ctx = replace(self.ctx, user_id=tx["user_id"], as_of=tx["timestamp"])
                decision = apply_review(self.store, run_ctx, tx["transaction_id"], tx.get("counterparty_id"),
                                        question.get("pattern", "none"), answer)
                record.update(final_decision=decision, decided_by="human", analyst_note=answer.get("note", ""))
                human = {"question": question, "answer": answer}
        if record.get("final_decision") != "escalate":
            sar, record["sar_id"] = None, None
        elif sar is not None:
            self.store.put(("sars", tx["user_id"]), record.get("sar_id") or f"SAR-{tx['transaction_id']}",
                           sar | {"transaction_id": tx["transaction_id"]})
        self.store.put(("decisions", tx["user_id"]), tx["transaction_id"], record)
        return Outcome(record=record, seconds=entry.get("seconds", 0.0), model_calls=entry.get("model_calls", 0),
                       tokens=entry.get("tokens", 0), sar=sar, tool_calls=entry.get("tool_calls", []),
                       trace_run_id=entry.get("trace_run_id"), human=human, replayed=True)
