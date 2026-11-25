"""The stream session: clock, rules tier, agent queue, human review, cases and counters (design.md U2, U5).

Threads:
- the producer releases transactions at `speed` per second (pause stops it; fast-forward skips ahead);
- a small pool investigates flagged transactions, one customer at a time in order (the agents keep a thread per
  customer), several customers in parallel (DEC-007), so one paused case never blocks the rest.

State here is authoritative. Every change is published as an event carrying the whole updated entity.
"""

import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import Callable

from rules.scorer import baseline_decision, goes_to_agents, score_all  # sentinel_aml_agent
from tools.decisions import apply_review
from tools.precedents import precedent_key
from utils.state import MyAgentContext

from sentinel_api import cases as C
from sentinel_api.investigators import Investigator, Outcome
from sentinel_api.models import (
    Activity,
    Alert,
    AuditEntry,
    CaseSummary,
    Counters,
    MemoryCard,
    ReplayInfo,
    SessionInfo,
    Snapshot,
    Step,
    TxRow,
)
from sentinel_api.world import World, ts

Publish = Callable[[str, dict], None]

STEP_LABELS = {"supervisor": "Supervisor", "pattern-analyst": "Pattern analyst", "kyc-precedent": "KYC & precedent",
               "fund-flow": "Fund-flow", "verdict": "Verdict", "sar-writer": "SAR writer"}
STEP_ORDER = list(STEP_LABELS)
ACTIVITY_KEEP = 40


class SessionClosed(Exception):
    """Raised in a worker waiting for an analyst when the session is reset."""


@dataclass
class Config:
    mode: str                       # live | record | replay | offline
    speed: float = 8.0              # transactions released per second
    minutes_per_alert: int = 20     # assumption for "analyst hours saved" (EX-3), shown on request
    workers: int = 4
    model: str | None = None
    replay: ReplayInfo | None = None
    live_transactions: tuple[str, ...] = ()
    agents_available: bool = False


class Session:
    def __init__(self, world: World, store, investigator: Investigator, config: Config, publish: Publish,
                 ctx: MyAgentContext | None = None):
        self.world = world
        self.store = store
        self.investigator = investigator
        self.config = config
        self._publish = publish
        self.ctx = ctx or MyAgentContext()
        self.scores = score_all(list(world.transactions), world.profiles_by_user, self.ctx)

        self.lock = threading.RLock()
        self.state = "idle"
        self.speed = config.speed
        self.cursor = 0
        self.seq = 0
        self.rows: dict[str, TxRow] = {}
        self.order: list[str] = []
        self.records: dict[str, dict] = {}
        self.activity: dict[str, Activity] = {}
        self.alerts: dict[str, Alert] = {}
        self.cases: dict[str, CaseSummary] = {}
        self.audit: list[tuple[str | None, AuditEntry]] = []
        self.usage = {"investigations": 0, "model_calls": 0, "tokens": 0}
        self._changed_cases: list[CaseSummary] = []
        self._removed_cases: list[str] = []

        self._waiting: dict[str, Future] = {}
        self._queues: dict[str, deque] = {}
        self._active_users: set[str] = set()
        self._pool = ThreadPoolExecutor(max_workers=config.workers, thread_name_prefix="investigate")
        self._ff_until: str | None = None
        self._alive = True
        self._wake = threading.Event()
        self._producer = threading.Thread(target=self._produce, name="stream", daemon=True)
        self._producer.start()

    # ------------------------------------------------------------------ publishing
    def publish(self, kind: str, data: dict):
        if self._alive:
            self._publish(kind, data)

    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq

    # ------------------------------------------------------------------ controls
    def start(self):
        with self.lock:
            if self.state in ("idle", "paused"):
                self.state = "running"
        self._wake.set()
        self._publish_session()

    def pause(self):
        with self.lock:
            if self.state == "running":
                self.state = "paused"
        self._publish_session()

    def set_speed(self, tx_per_second: float):
        with self.lock:
            self.speed = tx_per_second
        self._wake.set()
        self._publish_session()

    def fast_forward(self, days: int):
        with self.lock:
            base = self.clock() or (self.world.transactions[0]["timestamp"] if self.world.transactions else None)
            if base is None:
                return
            self._ff_until = (ts(base) + timedelta(days=days)).isoformat(timespec="minutes")
            if self.state == "idle":
                self.state = "paused"
        self._wake.set()
        self._audit(None, "stream", f"Fast-forwarded {days} days")

    def close(self):
        self._alive = False
        self._wake.set()
        with self.lock:
            for fut in self._waiting.values():
                if not fut.done():
                    fut.set_exception(SessionClosed())
        self._pool.shutdown(wait=False, cancel_futures=True)

    def clock(self) -> str | None:
        return self.rows[self.order[-1]].timestamp if self.order else None

    # ------------------------------------------------------------------ producer
    def _produce(self):
        while self._alive:
            with self.lock:
                done = self.cursor >= len(self.world.transactions)
                ff = self._ff_until
                running = self.state == "running"
                speed = self.speed
            if done:
                with self.lock:
                    if self.state != "finished":
                        self.state = "finished"
                        finished = True
                    else:
                        finished = False
                if finished:
                    self._publish_session()
                self._wake.wait(1.0)
                self._wake.clear()
                continue
            if ff:
                self._release_until(ff)
                continue
            if not running:
                self._wake.wait(0.5)
                self._wake.clear()
                continue
            self.release_next()
            self._wake.wait(1.0 / max(speed, 0.1))
            self._wake.clear()

    def _release_until(self, until: str):
        while self._alive:
            with self.lock:
                if self.cursor >= len(self.world.transactions) or self.world.transactions[self.cursor]["timestamp"] >= until:
                    self._ff_until = None
                    break
            self.release_next(publish_counters=False)
        self._publish_counters()
        self._publish_session()

    def release_next(self, publish_counters: bool = True) -> TxRow | None:
        """Release one transaction into the stream and run the rules tier on it."""
        with self.lock:
            if self.cursor >= len(self.world.transactions):
                return None
            tx = self.world.transactions[self.cursor]
            self.cursor += 1
            score, reasons = self.scores[tx["transaction_id"]]
            sender, receiver = self.world.parties(tx)
            to_agents = goes_to_agents(score, self.ctx)
            row = TxRow(
                transaction_id=tx["transaction_id"], user_id=tx["user_id"], account_id=tx["account_id"],
                customer_name=self.world.profiles_by_user[tx["user_id"]]["name"], timestamp=tx["timestamp"],
                direction=tx["direction"], txn_type=tx["txn_type"], amount=tx["amount"], currency=tx["currency"],
                country=tx.get("country"), branch=tx.get("branch"), sender=sender, receiver=receiver,
                rule_score=score, rule_reasons=reasons, baseline=baseline_decision(score, self.ctx),
                status="under_review" if to_agents else "cleared_rules",
                decided_by=None if to_agents else "rules", final_decision=None if to_agents else "clear",
                seq=self._next_seq(),
            )
            self.rows[row.transaction_id] = row
            self.order.append(row.transaction_id)
        self.publish("tx", row.model_dump(mode="json"))
        if to_agents:
            self._enqueue(tx, score, reasons)
        if publish_counters:
            self._publish_counters()
        return row

    # ------------------------------------------------------------------ agents
    def _enqueue(self, tx: dict, score: int, reasons: list[str]):
        user = tx["user_id"]
        with self.lock:
            self._queues.setdefault(user, deque()).append((tx, score, reasons))
            if user in self._active_users:
                return
            self._active_users.add(user)
        try:
            self._pool.submit(self._drain, user)
        except RuntimeError:  # pool shut down by a reset
            pass

    def _drain(self, user: str):
        while self._alive:
            with self.lock:
                queue = self._queues.get(user)
                if not queue:
                    self._active_users.discard(user)
                    return
                tx, score, reasons = queue.popleft()
            try:
                self._investigate(tx, score, reasons)
            except SessionClosed:
                return
            except Exception as exc:  # keep the stream alive; show the failure on the row
                self._fail(tx, exc)

    def _investigate(self, tx: dict, score: int, reasons: list[str]):
        tx_id = tx["transaction_id"]
        activity = Activity(transaction_id=tx_id, customer_name=self.rows[tx_id].customer_name, amount=tx["amount"],
                            steps=[Step(key="supervisor", label=STEP_LABELS["supervisor"], state="waiting")])
        with self.lock:
            self.activity[tx_id] = activity
            self._trim_activity()
        self.publish("activity", activity.model_dump(mode="json"))

        def on_step(key, state=None, finding=None, tool=None):
            self._on_step(tx_id, key, state, finding, tool)

        def ask_human(question: dict) -> dict:
            return self._ask_human(tx, question)

        outcome = self.investigator.run(tx, score, reasons, on_step, ask_human)
        self._complete(tx, outcome)

    def _on_step(self, tx_id: str, key: str, state, finding, tool):
        with self.lock:
            activity = self.activity.get(tx_id)
            if activity is None:
                return
            step = next((s for s in activity.steps if s.key == key), None)
            if step is None:
                step = Step(key=key, label=STEP_LABELS.get(key, key), state="waiting")
                activity.steps.append(step)
                activity.steps.sort(key=lambda s: STEP_ORDER.index(s.key) if s.key in STEP_ORDER else 99)
            if state:
                step.state = state
            if finding:
                step.finding = finding
            if tool and tool not in step.tools:
                step.tools.append(tool)
            data = activity.model_dump(mode="json")
        self.publish("activity", data)

    def _ask_human(self, tx: dict, question: dict) -> dict:
        tx_id = tx["transaction_id"]
        fut: Future = Future()
        leaning = question.get("agent_decision") or "unsure"
        confidence = question.get("confidence")
        why = question.get("why_review") or []
        alert = Alert(
            transaction_id=tx_id, case_id=None, customer_name=self.rows[tx_id].customer_name, amount=tx["amount"],
            currency=tx["currency"], pattern=question.get("pattern") or "none",
            question="Clear or escalate this transaction?",
            leaning=f"leaning {leaning}" + (f", confidence {confidence:.2f}" if isinstance(confidence, (int, float)) else ""),
            main_reason=(why[0] if why else question.get("reason") or ""), why_review=why,
            hard_flags=question.get("hard_flags") or [],
        )
        with self.lock:
            self._waiting[tx_id] = fut
            row = self.rows[tx_id]
            row.status = "needs_analyst"
            row.pattern = question.get("pattern") or row.pattern
            row.reason = question.get("reason") or row.reason
            row.confidence = confidence
            row.seq = self._next_seq()
            self.records[tx_id] = {**question, "final_decision": None, "decided_by": None}
            self._recompute_cases()
            alert.case_id = row.case_id
            self.alerts[tx_id] = alert
            act = self.activity.get(tx_id)
            if act:
                act.route, act.route_reason = "sent_to_analyst", "; ".join(why)
            row_data = row.model_dump(mode="json")
        self.publish("tx", row_data)
        self.publish("alert", alert.model_dump(mode="json"))
        if act:
            self.publish("activity", act.model_dump(mode="json"))
        self._publish_cases()
        self._publish_counters()
        self._audit(row.case_id, "review_requested", f"{tx_id} sent to the analyst: {'; '.join(why)}")
        return fut.result()

    def decide(self, tx_id: str, decision: str, note: str, analyst: str = "analyst") -> bool:
        """The analyst's decision (FR-9.1/9.3). Resumes a paused investigation, or records a review of a flag."""
        answer = {"decision": decision, "note": note.strip(), "analyst": analyst}
        with self.lock:
            fut = self._waiting.pop(tx_id, None)
            row = self.rows.get(tx_id)
            if row is None:
                return False
            self.alerts.pop(tx_id, None)
        self.publish("alert_removed", {"transaction_id": tx_id})
        self._audit(row.case_id, "analyst_decision", f"{analyst} chose {decision} on {tx_id}: {note.strip()}")
        if fut is not None:
            fut.set_result(answer)  # the investigation resumes and completes as usual
            return True
        # Not paused: the analyst is reviewing an agent's flag. Same code path the agents use to save the note.
        tx = self.world.tx(tx_id)
        record = self.records.get(tx_id, {})
        ctx = replace(self.ctx, user_id=tx["user_id"], as_of=tx["timestamp"])
        apply_review(self.store, ctx, tx_id, tx.get("counterparty_id"), record.get("pattern") or "none", answer)
        record.update(final_decision=decision, decided_by="human", analyst_note=answer["note"])
        self.records[tx_id] = record
        with self.lock:
            row.final_decision, row.decided_by = decision, "human"
            row.status = "flagged" if decision == "escalate" else "cleared"
            row.memory = [m for m in row.memory if m.kind != "saved"] + self._saved_card(tx, record)
            row.seq = self._next_seq()
            self._recompute_cases()
            data = row.model_dump(mode="json")
        self.publish("tx", data)
        self._publish_cases()
        self._publish_counters()
        return True

    def _complete(self, tx: dict, outcome: Outcome):
        tx_id = tx["transaction_id"]
        record = outcome.record
        decision = record.get("final_decision")
        with self.lock:
            self.records[tx_id] = record
            self.usage["investigations"] += 1
            self.usage["model_calls"] += outcome.model_calls
            self.usage["tokens"] += outcome.tokens
            row = self.rows[tx_id]
            row.status = "flagged" if decision == "escalate" else "cleared"
            row.final_decision = decision
            row.decided_by = record.get("decided_by")
            row.pattern = record.get("pattern")
            row.reason = record.get("reason")
            row.confidence = record.get("confidence")
            row.sar_id = record.get("sar_id")
            row.trace_run_id = outcome.trace_run_id
            row.replayed = outcome.replayed
            row.memory = self._memory_cards(tx, record)
            row.seq = self._next_seq()
            self.alerts.pop(tx_id, None)
            act = self.activity.get(tx_id)
            if act:
                act.done, act.replayed, act.seconds = True, outcome.replayed, outcome.seconds
                act.trace_run_id = outcome.trace_run_id
                act.verdict, act.confidence = decision, record.get("confidence")
                act.memory = row.memory
                if record.get("decided_by") == "human":
                    act.route = "sent_to_analyst"
                    act.route_reason = "; ".join(record.get("confidence_checks") or []) or act.route_reason
                else:
                    act.route = "escalated" if decision == "escalate" else "auto_cleared"
                    act.route_reason = record.get("reason")
                for step in act.steps:
                    if step.key == "verdict" or step.state == "working":
                        step.state = "done"
                if not any(s.key == "verdict" for s in act.steps):
                    act.steps.append(Step(key="verdict", label="Verdict", state="done"))
                verdict = next(s for s in act.steps if s.key == "verdict")
                verdict.finding = (f"{decision} · decided by {record.get('decided_by')}"
                                   + (f" · confidence {record['confidence']:.2f}" if isinstance(record.get("confidence"), (int, float)) else ""))
            self._recompute_cases()
            data = row.model_dump(mode="json")
        self.publish("tx", data)
        self.publish("alert_removed", {"transaction_id": tx_id})
        if act:
            self.publish("activity", act.model_dump(mode="json"))
        self._publish_cases()
        self._publish_counters()
        if record.get("precedents_overridden"):
            self._audit(row.case_id, "precedent_overridden",
                        "; ".join(f"{p.get('key')}: {p.get('reason')}" for p in record["precedents_overridden"]))

    def _fail(self, tx: dict, exc: Exception):
        tx_id = tx["transaction_id"]
        with self.lock:
            row = self.rows[tx_id]
            row.status = "needs_analyst"
            row.reason = f"Investigation failed ({type(exc).__name__}): an analyst must decide"
            row.seq = self._next_seq()
            data = row.model_dump(mode="json")
        self.publish("tx", data)
        self._audit(None, "error", f"{tx_id}: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ memory (EX-2)
    def _precedent(self, user_id: str, key: str) -> dict | None:
        item = self.store.get(("precedents", user_id), key)
        return dict(item.value) if item else None

    def _memory_cards(self, tx: dict, record: dict) -> list[MemoryCard]:
        cards = []
        for key in record.get("precedents_relied_on") or []:
            p = self._precedent(tx["user_id"], key) or {}
            cards.append(MemoryCard(kind="cited", key=key, note=p.get("note", ""), analyst=p.get("analyst", ""),
                                    created_at=p.get("created_at"), expires_at=p.get("expires_at"),
                                    scope=_scope(p)))
        for o in record.get("precedents_overridden") or []:
            p = self._precedent(tx["user_id"], o.get("key", "")) or {}
            cards.append(MemoryCard(kind="overridden", key=o.get("key", ""), note=o.get("note") or p.get("note", ""),
                                    analyst=p.get("analyst", ""), created_at=p.get("created_at"),
                                    expires_at=p.get("expires_at"), reason=o.get("reason", ""), scope=_scope(p)))
        return cards + self._saved_card(tx, record)

    def _saved_card(self, tx: dict, record: dict) -> list[MemoryCard]:
        if record.get("decided_by") != "human" or not record.get("analyst_note"):
            return []
        key = precedent_key(tx.get("counterparty_id"), record.get("pattern") or "none")
        p = self._precedent(tx["user_id"], key)
        if not p:
            return []
        return [MemoryCard(kind="saved", key=key, note=p["note"], analyst=p.get("analyst", ""),
                           created_at=p.get("created_at"), expires_at=p.get("expires_at"), scope=_scope(p))]

    # ------------------------------------------------------------------ cases
    def _recompute_cases(self):
        """Regroup every flagged transaction into cases. Call with the lock held."""
        rings = C.ring_index(self.clock())
        members: dict[str, list[TxRow]] = {}
        for tx_id, record in self.records.items():
            row = self.rows[tx_id]
            if not (row.status in ("flagged", "needs_analyst") or row.decided_by == "human"):
                continue
            tx = self.world.tx(tx_id)
            case_id = C.case_id_for(tx, row.pattern, rings)
            row.case_id = case_id
            members.setdefault(case_id, []).append(row)
        changed = {}
        for case_id, rows in members.items():
            summary = self._summarise(case_id, rows, rings)
            old = self.cases.get(case_id)
            if old is None or old.model_dump(exclude={"updated_seq"}) != summary.model_dump(exclude={"updated_seq"}):
                summary.updated_seq = self._next_seq()
                changed[case_id] = summary
        self.cases.update(changed)
        for case_id in [c for c in self.cases if c not in members]:
            del self.cases[case_id]
            self._removed_cases.append(case_id)
        self._changed_cases.extend(changed.values())
        related = {}
        for summary in self.cases.values():
            for tx_id in summary.related_transaction_ids:
                related[tx_id] = summary.case_id
        for tx_id, case_id in related.items():
            row = self.rows.get(tx_id)
            if row and row.case_id != case_id and row.status not in ("flagged", "needs_analyst"):
                row.case_id = case_id

    def case_graph(self, case_id: str, rows: list[TxRow] | None = None) -> C.CaseGraph:
        as_of = self.clock() or ""
        if case_id.startswith("CASE-RING-"):
            return C.ring_graph(self.world, case_id.removeprefix("CASE-RING-"), as_of)
        rows = rows if rows is not None else [r for r in self.rows.values() if r.case_id == case_id and r.transaction_id in self.records]
        txs = [self.world.tx(r.transaction_id) for r in rows]
        return C.single_graph(self.world, rows[0].account_id, txs) if rows else C.CaseGraph()

    def _summarise(self, case_id: str, rows: list[TxRow], rings) -> CaseSummary:
        rows = sorted(rows, key=lambda r: (r.timestamp, r.transaction_id))
        g = self.case_graph(case_id, rows)
        network = case_id.startswith("CASE-RING-")
        lead = g.hub or rows[0].account_id
        pattern = "mule_fan_in" if network else (rows[-1].pattern or "none")
        if any(r.status == "needs_analyst" for r in rows):
            status = "awaiting_analyst"
        elif any(r.decided_by == "human" for r in rows):
            status = "escalated" if any(r.decided_by == "human" and r.final_decision == "escalate" for r in rows) else "cleared"
        else:
            status = "new"
        escalate = any((self.records[r.transaction_id].get("agent_decision") or r.final_decision) == "escalate" for r in rows)
        confidences = [r.confidence for r in rows if isinstance(r.confidence, (int, float))]
        risk = max([int(self.records[r.transaction_id].get("risk_score") or r.rule_score) for r in rows])
        hard = any(self.records[r.transaction_id].get("hard_flags") for r in rows)
        transfers = g.sorted_transfers()
        nodes, edges = C.shape(g)
        return CaseSummary(
            case_id=case_id, kind="network" if network else "single", pattern=pattern, layout=g.layout,
            lead_account=lead, lead_name=self.world.name(lead), accounts=len([n for n in g.nodes if self.world.is_ours(n)]) or 1,
            transaction_ids=[r.transaction_id for r in rows],
            flagged_transaction_ids=[r.transaction_id for r in rows if r.status in ("flagged", "needs_analyst")],
            related_transaction_ids=[t["transaction_id"] for _, _, t in transfers],
            total_amount=round(sum(t["amount"] for _, _, t in transfers) if transfers else sum(r.amount for r in rows), 2),
            first_ts=transfers[0][2]["timestamp"] if transfers else rows[0].timestamp,
            last_ts=rows[-1].timestamp,
            verdict="escalate" if escalate else "clear",
            confidence=min(confidences) if confidences else None,
            why=rows[-1].reason or "; ".join(rows[-1].rule_reasons),
            status=status, severity=min(100, risk + (15 if hard else 0) + (10 if network else 0)),
            shape_nodes=nodes, shape_edges=edges,
        )

    # ------------------------------------------------------------------ counters (EX-3)
    def counters(self) -> Counters:
        with self.lock:
            rows = [self.rows[t] for t in self.order]
            c = Counters(received=len(rows), total=len(self.world.transactions),
                         minutes_per_alert=self.config.minutes_per_alert, **self.usage)
            for r in rows:
                if r.status == "cleared_rules":
                    c.cleared_rules += 1
                elif r.status == "under_review":
                    c.under_review += 1
                elif r.status == "needs_analyst":
                    c.needs_analyst += 1
                elif r.status == "flagged":
                    c.flagged += 1
                elif r.status == "cleared":
                    c.cleared += 1
                if r.baseline == "escalate":
                    c.rules_alerts += 1
                analyst_saw = r.status in ("flagged", "needs_analyst") or r.decided_by == "human"
                if analyst_saw:
                    c.sentinel_alerts += 1
                label = self.world.labels.get(r.transaction_id, {})
                if r.baseline == "escalate" and label.get("decision") == "clear" and r.final_decision == "clear" and not analyst_saw:
                    c.false_positives_avoided += 1
            c.analyst_touches = c.sentinel_alerts
            avoided = max(c.rules_alerts - c.sentinel_alerts - c.under_review, 0)  # pending ones aren't saved yet
            c.analyst_hours_saved = round(avoided * c.minutes_per_alert / 60, 1)
            if c.investigations:
                c.avg_tokens_per_investigation = round(c.tokens / c.investigations, 1)
                c.tokens_if_all_to_agents = int(c.avg_tokens_per_investigation * c.total)
            return c

    # ------------------------------------------------------------------ snapshot & events
    def info(self) -> SessionInfo:
        return SessionInfo(mode=self.config.mode, state=self.state, clock=self.clock(), speed=self.speed,
                           replay=self.config.replay, live_transactions=list(self.config.live_transactions),
                           agents_available=self.config.agents_available, model=self.config.model)

    def snapshot(self) -> Snapshot:
        with self.lock:
            return Snapshot(
                session=self.info(),
                transactions=[self.rows[t] for t in self.order],
                cases=list(self.cases.values()),
                counters=self.counters(),
                alerts=list(self.alerts.values()),
                activity=list(self.activity.values()),
            )

    def audit_for(self, case_id: str) -> list[AuditEntry]:
        with self.lock:
            return [entry for cid, entry in self.audit if cid == case_id]

    def _audit(self, case_id: str | None, kind: str, detail: str):
        with self.lock:
            self.audit.append((case_id, AuditEntry(at=self.clock() or "", kind=kind, detail=detail)))

    def _trim_activity(self):
        if len(self.activity) > ACTIVITY_KEEP:
            for tx_id in list(self.activity)[: len(self.activity) - ACTIVITY_KEEP]:
                if self.activity[tx_id].done:
                    del self.activity[tx_id]

    def _publish_session(self):
        self.publish("session", self.info().model_dump(mode="json"))

    def _publish_counters(self):
        self.publish("counters", self.counters().model_dump(mode="json"))

    def _publish_cases(self):
        with self.lock:
            changed, self._changed_cases = self._changed_cases, []
            removed, self._removed_cases = self._removed_cases, []
        for summary in changed:
            self.publish("case", summary.model_dump(mode="json"))
        for case_id in removed:
            self.publish("case_removed", {"case_id": case_id})


def _scope(p: dict) -> str:
    if not p:
        return ""
    return f"{p.get('user_id')} + {p.get('counterparty_id')} + {str(p.get('pattern', '')).replace('_', ' ')}"
