"""Scenario check (task 3.3): run Sentinel live on world 0's scripted cases and compare with the analyst labels.

Observes behaviour only; nothing here steers the agents (DEC-004). Expectations come from `analyst_labels.jsonl`:
- the final decision matches the label's `decision`;
- a human was asked if and only if the label says `expect_human` (scripted answers from `reviewer_answers.jsonl`);
- a precedent was relied on when `expect_precedent_use`, and overridden when `expect_override`.

    uv run python scripts/check_scenarios.py               # core scenarios (about 2 minutes, parallel customers)
    uv run python scripts/check_scenarios.py --with-mule   # also the mule ring and Liam's override (phase 4)
    uv run python scripts/check_scenarios.py --save        # also write results/scenario_run.json

Every run is traced to LangSmith project LANGSMITH_PROJECT.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.tracers.langchain import wait_for_all_tracers  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.store.memory import InMemoryStore  # noqa: E402

from agents import build_agent  # noqa: E402
from evals.sar_checks import sar_grounded  # noqa: E402
from rules.scorer import goes_to_agents, score_all  # noqa: E402
from tools.precedents import load_seed_precedents  # noqa: E402
from utils import PROJECT_ROOT, db  # noqa: E402
from utils.state import MyAgentContext  # noqa: E402
from utils.stream import process_stream  # noqa: E402


def txs_where(user_id, pred):
    return [t for t in sorted(db.query("transactions", user_id=user_id), key=lambda t: t["timestamp"]) if pred(t)]


def scenarios(with_mule: bool) -> dict[str, list[dict]]:
    s = {
        "structuring (Daniel, deposits 3 and 4)": txs_where("CUS-0001", lambda t: t["amount"] == 9500)[2:4],
        "anomalous credit -> analyst -> precedent (Sophie)": txs_where("CUS-0002", lambda t: t["reference"] == "Annual bonus"),
        "expired precedent is not relied on (Grace)": txs_where("CUS-0004", lambda t: t["amount"] == 15000),
        "out-of-scope precedent is ignored (Tom)": txs_where("CUS-0005", lambda t: t["amount"] == 20000),
    }
    if with_mule:
        mules = ["CUS-0040", "CUS-0041", "CUS-0042", "CUS-0043", "CUS-0044"]
        forwards = sorted((t for u in mules for t in txs_where(u, lambda t: t["counterparty_id"] == "ACC-0050")),
                          key=lambda t: t["timestamp"])
        liam_flat = txs_where("CUS-0040", lambda t: t["counterparty_id"] == "EXT-FLAT-0040" and t["timestamp"] > "2026-11-12")
        s["mule ring: 4th forward (not yet confirmed) and 5th (confirmed)"] = forwards[3:5]
        s["Liam's old precedent is overridden by ring membership"] = liam_flat
    return s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-mule", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    labels = {l["transaction_id"]: l for l in db.table("analyst_labels")}
    answers = {a["transaction_id"]: a for a in db.table("reviewer_answers")}
    cases = scenarios(args.with_mule)
    txs = [t for rows in cases.values() for t in rows]

    store = InMemoryStore()
    load_seed_precedents(store)
    agent = build_agent(checkpointer=InMemorySaver(), store=store)
    run = process_stream(agent, MyAgentContext(), txs, reviewer_answers=answers, parallel_customers=True,
                         extra_tags=["scenario-check"])
    by_tx = {d["transaction_id"]: d for d in run["decisions"]}
    inv = {i["transaction_id"]: i for i in run["investigations"]}

    results = []
    for name, rows in cases.items():
        for t in rows:
            tid, lab, d = t["transaction_id"], labels[t["transaction_id"]], by_tx[t["transaction_id"]]
            checks = {
                f"decision {d['final_decision']} (label {lab['decision']})": d["final_decision"] == lab["decision"],
                f"human asked: {d['decided_by'] == 'human'} (expected {lab['expect_human']})":
                    (d["decided_by"] == "human") == lab["expect_human"],
            }
            if lab["expect_precedent_use"]:
                checks["precedent relied on"] = bool(d.get("precedents_relied_on"))
            if lab["expect_override"]:
                checks["precedent overridden"] = bool(d.get("precedents_overridden"))
            if d["final_decision"] == "escalate" and d["decided_by"] != "rules":
                checks["SAR draft saved"] = bool(d.get("sar_id"))
                sar = (inv.get(tid) or {}).get("sar") or {}
                grounded, problems = sar_grounded(sar, t["timestamp"])
                checks[f"SAR grounded ({grounded}{': ' + '; '.join(problems) if problems else ''})"] = grounded == 1.0
            ok = all(checks.values())
            results.append({"scenario": name, "transaction_id": tid, "ok": ok, "checks": checks,
                            "seconds": inv.get(tid, {}).get("seconds"), "model_calls": inv.get(tid, {}).get("model_calls"),
                            "trace_run_id": d.get("trace_run_id"), "decided_by": d["decided_by"],
                            "final_decision": d["final_decision"], "reason": d.get("reason"),
                            "precedents_relied_on": d.get("precedents_relied_on"),
                            "precedents_overridden": d.get("precedents_overridden"),
                            "tool_calls": [c["subagent"] or c["name"] for c in inv.get(tid, {}).get("tool_calls", [])],
                            "sar": (inv.get(tid) or {}).get("sar")})

    # Rules-tier share on all of world 0 (no LLM)
    all_txs = db.table("transactions")
    profiles = {p["user_id"]: p for p in db.table("customer_profiles")}
    share = 1 - sum(goes_to_agents(s) for s, _ in score_all(all_txs, profiles).values()) / len(all_txs)

    for r in results:
        print(("PASS " if r["ok"] else "FAIL ") + f"{r['scenario']} · {r['transaction_id']} · {r['seconds']}s, "
              f"{r['model_calls']} model calls")
        for k, v in r["checks"].items():
            print(f"     {'ok ' if v else 'NO '} {k}")
        if not r["ok"]:
            print(f"     reason: {r['reason']}")
    print(("PASS " if share >= 0.9 else "FAIL ") + f"rules tier clears {share:.1%} of world 0 (target ≥ 90%)")
    c = run["counters"]
    print(f"\n{sum(r['ok'] for r in results)}/{len(results)} scenario transactions passed · "
          f"{c['model_calls']} model calls · {c['input_tokens'] + c['output_tokens']:,} tokens · "
          f"seconds per investigation {c['seconds']}")

    if args.save:
        out = PROJECT_ROOT / "results" / "scenario_run.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({"results": results, "rules_tier_share": share, "counters": c}, indent=1, default=str))
        print(f"saved {out}")
    wait_for_all_tracers()
    sys.exit(0 if all(r["ok"] for r in results) and share >= 0.9 else 1)


if __name__ == "__main__":
    main()
