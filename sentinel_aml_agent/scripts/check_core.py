"""Check tasks 2.3-2.6 without an LLM: tools, the network tool, record_decision's safeguards and the stream runner.

The safeguard cases call the same `assess` / `apply_review` functions `record_decision` uses. The stream runner is
run over all of world 0 with a stub agent. Observes behaviour only (DEC-004).

    uv run python scripts/check_core.py
"""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain.tools import ToolRuntime  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langgraph.store.memory import InMemoryStore  # noqa: E402

from rules.scorer import goes_to_agents, score_all  # noqa: E402
from tools import customers, decisions, network, precedents, screening, transactions  # noqa: E402
from tools.decisions import apply_review, assess  # noqa: E402
from tools.precedents import load_seed_precedents  # noqa: E402
from utils import db  # noqa: E402
from utils.state import MyAgentContext  # noqa: E402
from utils.stream import global_stream, process_stream  # noqa: E402

results = []


def check(ok, name):
    results.append((bool(ok), name))


def rt(ctx, store):
    return ToolRuntime(state={}, context=ctx, config={}, stream_writer=None, tool_call_id=None, store=store)


def tx_of(user_id, pred):
    return next(t for t in sorted(db.query("transactions", user_id=user_id), key=lambda t: t["timestamp"]) if pred(t))


store = InMemoryStore()
check(load_seed_precedents(store) == 3, "3 seed precedents loaded into the store")

# ---------- 2.3 customer-scoped tools ----------
daniel4 = [t for t in sorted(db.query("transactions", user_id="CUS-0001"), key=lambda t: t["timestamp"])
           if t["amount"] == 9500][3]
ctx = MyAgentContext(user_id="CUS-0001", as_of=daniel4["timestamp"])
r = rt(ctx, store)
check(transactions.get_transaction.func(daniel4["transaction_id"], r)["amount"] == 9500, "get_transaction finds Daniel's 4th deposit")
check(isinstance(transactions.get_transaction.func("TX-000770", r), str), "get_transaction refuses another customer's transaction")
recent = transactions.get_recent_transactions.func(r, days=30)
check(recent["totals"]["cash_deposits"] >= 38000 and all(t["timestamp"] <= ctx.as_of for t in recent["transactions"]),
      "get_recent_transactions sees all 4 deposits and nothing after as_of")
check(customers.get_customer_profile.func(r)["name"] == "Daniel Hughes", "get_customer_profile returns the run's customer")
check(screening.screen_customer.func(r)["hits"] == [], "screen_customer: Daniel has no hits")
marcus_ctx = MyAgentContext(user_id="CUS-0003", as_of="2026-11-20T15:30")
check(any(h["list"] == "pep" for h in screening.screen_customer.func(rt(marcus_ctx, store))["hits"]), "screen_customer: Marcus is a PEP")
liam_ctx = MyAgentContext(user_id="CUS-0040", as_of="2026-11-01T00:00")
found = precedents.find_precedents.func("EXT-FLAT-0040", "mule_fan_in", rt(liam_ctx, store))
check(len(found["valid"]) == 1, "find_precedents: Liam's flatmate precedent is valid and in scope")
check(len(precedents.find_precedents.func("EXT-OTHER", "mule_fan_in", rt(liam_ctx, store))["valid"]) == 0,
      "find_precedents: a different counterparty is out of scope")
grace_ctx = MyAgentContext(user_id="CUS-0004", as_of="2026-11-05T12:00")
check(len(precedents.find_precedents.func("EXT-0401", "anomalous_credit", rt(grace_ctx, store))["expired"]) == 1,
      "find_precedents: Grace's precedent is expired")
tool_objs = [transactions.get_transaction, transactions.get_recent_transactions, customers.get_customer_profile,
             screening.screen_customer, precedents.find_precedents, network.trace_fund_flows, decisions.record_decision]
check(all("user_id" not in t.args for t in tool_objs), "no tool exposes a user_id argument to the model")

# ---------- 2.4 privileged network tool ----------
fifth = sorted((t for t in db.table("transactions") if t["counterparty_id"] == "ACC-0050" and t["direction"] == "out"
                and t["account_id"] in {f"ACC-00{n}" for n in range(40, 45)}), key=lambda t: t["timestamp"])[4]
net_ctx = MyAgentContext(user_id="CUS-0040", as_of=fifth["timestamp"], trace_run_id="check")
summary = network.trace_fund_flows.func(rt(net_ctx, store))
check(summary["ring_confirmed"] and len(summary["feeder_accounts"]) == 5 and summary["collector_account"] == "ACC-0050",
      "trace_fund_flows: Liam at the 5th forward sees all 5 feeders and Northgate")
check(not any(k in str(summary) for k in ("Liam", "Walsh", "date_of_birth", "occupation")), "trace_fund_flows returns no profile fields")
check(len(store.search(("network_audit",))) == 1, "trace_fund_flows wrote one audit record")

# ---------- 2.5 record_decision safeguards (cases a-d) ----------
sophie1 = tx_of("CUS-0002", lambda t: t["reference"] == "Annual bonus")
s_ctx = MyAgentContext(user_id="CUS-0002", as_of=sophie1["timestamp"])
a = assess(store, s_ctx, sophie1, 50, 0.8, "clear", "anomalous_credit", [])
check(a["needs_human"] and a["confidence_checks"], "(a) grey zone, no precedent: goes to a human")

key = apply_review(store, s_ctx, sophie1["transaction_id"], sophie1["counterparty_id"], "anomalous_credit",
                   {"decision": "clear", "note": "Annual bonus — employer verified via payslip"})
p = store.get(("precedents", "CUS-0002"), "EXT-0102:anomalous_credit").value
check(key == "clear" and p["created_at"] == "2026-10-14" and p["expires_at"] == "2027-10-14",
      "(d) the analyst's note became a precedent valid to 2027-10-14")

sophie2 = tx_of("CUS-0002", lambda t: t["amount"] == 19200)
b = assess(store, MyAgentContext(user_id="CUS-0002", as_of=sophie2["timestamp"]), sophie2, 45, 0.8, "clear",
           "anomalous_credit", ["EXT-0102:anomalous_credit"])
check(not b["needs_human"] and b["precedents_relied_on"] == ["EXT-0102:anomalous_credit"],
      "(b) grey zone with a valid precedent: no human needed, precedent relied on")
b2 = assess(store, MyAgentContext(user_id="CUS-0002", as_of="2027-10-20T10:00"), sophie2, 45, 0.8, "clear",
            "anomalous_credit", ["EXT-0102:anomalous_credit"])
check(b2["needs_human"] and b2["precedents_dropped"], "expired precedent is not relied on, and the citation is dropped")

liam_flat = tx_of("CUS-0040", lambda t: t["counterparty_id"] == "EXT-FLAT-0040" and t["timestamp"] > fifth["timestamp"])
l_ctx = MyAgentContext(user_id="CUS-0040", as_of=liam_flat["timestamp"])
c = assess(store, l_ctx, liam_flat, 40, 0.9, "clear", "mule_fan_in", ["EXT-FLAT-0040:mule_fan_in"])
check(c["hard_flags"] and c["precedents_overridden"] and c["needs_human"],
      "(c) Liam: ring hard flag overrides his precedent, and a 'clear' goes to a human")
c2 = assess(store, l_ctx, liam_flat, 85, 0.9, "escalate", "mule_fan_in", [])
check(c2["precedents_overridden"] and not c2["needs_human"], "(c) override is recorded even if the model didn't cite it")
try:
    apply_review(store, s_ctx, "x", None, "none", {"decision": "approve"})
    check(False, "a bad analyst answer is rejected")
except ValueError:
    check(True, "a bad analyst answer is rejected")

# ---------- 2.6 stream runner over world 0 with a stub agent ----------
class StubAgent:
    """Stands in for the supervisor: records an 'escalate' and returns, with no LLM."""

    def __init__(self, store):
        self.store = store
        self.calls = 0

    def invoke(self, inputs, config, context):
        self.calls += 1
        tx_id = inputs["messages"][0]["content"].split()[2]
        self.store.put(("decisions", context.user_id), tx_id, {
            "transaction_id": tx_id, "final_decision": "escalate", "decided_by": "agent", "agent_decision": "escalate",
            "risk_score": context.rule_score, "rule_score": context.rule_score, "pattern": "none"})
        return {"messages": [AIMessage(content="stub")]}


stub_store = InMemoryStore()
load_seed_precedents(stub_store)
stub = StubAgent(stub_store)
txs = global_stream()
run = process_stream(stub, MyAgentContext(), txs)
profiles = {p["user_id"]: p for p in db.table("customer_profiles")}
expected = sum(goes_to_agents(s) for s, _ in score_all(txs, profiles).values())
check(len(run["decisions"]) == len(txs), f"a decision for every transaction ({len(txs)})")
check(stub.calls == expected == run["counters"]["investigations"], f"investigations = rule scores ≥ 30 ({expected})")
check(abs(run["counters"]["llm_share"] - expected / len(txs)) < 1e-4, f"llm_share = {run['counters']['llm_share']:.1%}")
check(all(d.get("trace_run_id") for d in run["decisions"] if d["decided_by"] != "rules"), "every investigation has a trace_run_id")
par = process_stream(StubAgent(InMemoryStore()), MyAgentContext(), txs, parallel_customers=True)
check(sorted(d["final_decision"] for d in par["decisions"]) == sorted(d["final_decision"] for d in run["decisions"]),
      "parallel customers give the same decisions (DEC-007)")

for ok, name in results:
    print(("PASS " if ok else "FAIL ") + name)
print(f"\n{sum(ok for ok, _ in results)}/{len(results)} checks passed")
sys.exit(0 if all(ok for ok, _ in results) else 1)
