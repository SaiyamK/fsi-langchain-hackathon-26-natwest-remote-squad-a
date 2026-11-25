"""Session: rules tier, agent queue, human review, precedents, cases and counters. No LLM: a scripted investigator."""

import threading
import time

import pytest
from langgraph.store.memory import InMemoryStore

from sentinel_api.investigators import Outcome
from sentinel_api.session import Config, Session
from sentinel_api.world import World


class ScriptedInvestigator:
    """Escalates everything, except transactions listed in `ask`, which pause for the analyst."""

    def __init__(self, ask=()):
        self.ask = set(ask)

    def run(self, tx, rule_score, reasons, on_step, ask_human):
        on_step("supervisor", "working")
        on_step("kyc-precedent", "working")
        on_step("kyc-precedent", "done", finding="KYC low")
        record = {"transaction_id": tx["transaction_id"], "final_decision": "escalate", "agent_decision": "escalate",
                  "decided_by": "agent", "pattern": "structuring", "reason": "scripted", "risk_score": rule_score,
                  "confidence": 0.9, "hard_flags": [], "precedents_overridden": []}
        if tx["transaction_id"] in self.ask:
            answer = ask_human({"transaction_id": tx["transaction_id"], "agent_decision": "clear", "confidence": 0.5,
                                "pattern": "anomalous_credit", "reason": "unsure", "why_review": ["grey zone"],
                                "hard_flags": []})
            record.update(final_decision=answer["decision"], decided_by="human", pattern="anomalous_credit",
                          analyst_note=answer["note"])
        return Outcome(record=record, seconds=0.0, model_calls=3, tokens=100)


@pytest.fixture(scope="module")
def world():
    return World.load()


def make(world, investigator, n=None):
    events = []
    lock = threading.Lock()

    def publish(kind, data):
        with lock:
            events.append((kind, data))

    if n:
        world = World(world.transactions[:n], world.profiles_by_user, world.profiles_by_account, world.labels,
                      world.by_account, world.external_names)
    s = Session(world, InMemoryStore(), investigator, Config(mode="offline", workers=2), publish)
    return s, events


def wait_for(cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_rules_tier_clears_most_without_agents(world):
    s, _ = make(world, ScriptedInvestigator(), n=200)
    for _ in range(200):
        s.release_next(publish_counters=False)
    c = s.counters()
    assert c.received == 200
    assert c.cleared_rules / c.received > 0.9
    assert wait_for(lambda: s.counters().under_review == 0)
    s.close()


def test_flagged_transactions_become_cases(world):
    s, events = make(world, ScriptedInvestigator(), n=170)
    while s.release_next(publish_counters=False):
        pass
    assert wait_for(lambda: s.counters().under_review == 0)
    assert "CASE-CUS-0001-structuring" in s.cases
    case = s.cases["CASE-CUS-0001-structuring"]
    assert case.status == "new" and case.verdict == "escalate"
    assert any(kind == "case" for kind, _ in events)
    s.close()


def test_human_review_pauses_then_resumes(world):
    s, events = make(world, ScriptedInvestigator(ask={"TX-000254"}), n=260)
    while s.release_next(publish_counters=False):
        pass
    assert wait_for(lambda: "TX-000254" in s.alerts)
    assert s.rows["TX-000254"].status == "needs_analyst"
    assert s.cases[s.rows["TX-000254"].case_id].status == "awaiting_analyst"
    assert s.decide("TX-000254", "clear", "Annual bonus, payslip seen")
    assert wait_for(lambda: s.rows["TX-000254"].status == "cleared")
    assert "TX-000254" not in s.alerts
    assert any(kind == "alert_removed" for kind, _ in events)
    s.close()


def test_value_ticker_is_computed(world):
    s, _ = make(world, ScriptedInvestigator(), n=300)
    while s.release_next(publish_counters=False):
        pass
    assert wait_for(lambda: s.counters().under_review == 0)
    c = s.counters()
    assert c.rules_alerts >= c.sentinel_alerts
    assert c.investigations == c.cleared + c.flagged + c.needs_analyst
    assert c.avg_tokens_per_investigation == 100
    s.close()


def test_reviewing_an_agent_flag_saves_a_precedent(world):
    s, _ = make(world, ScriptedInvestigator(), n=170)
    while s.release_next(publish_counters=False):
        pass
    assert wait_for(lambda: s.counters().under_review == 0)
    assert s.decide("TX-000167", "clear", "Market takings, till receipts seen")
    row = s.rows["TX-000167"]
    assert row.decided_by == "human" and row.status == "cleared"
    assert [m.kind for m in row.memory] == ["saved"]
    s.close()
