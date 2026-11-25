"""Check the rule scorer (task 2.1). Prints stats for world 0 (demo) and world 1 (dev) only.

The test world (2) is deliberately not scored here: it's for the reported eval only (R9.5, DEC-004).

    uv run python scripts/check_rules.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rules.scorer import baseline_decision, goes_to_agents, score_all  # noqa: E402
from utils import db  # noqa: E402

results = []


def stats(world: int) -> dict:
    with db.use_world(world):
        txs = db.table("transactions")
        profiles = {p["user_id"]: p for p in db.table("customer_profiles")}
        labels = {l["transaction_id"]: l for l in db.table("analyst_labels")}
        scores = score_all(txs, profiles)
    flagged = [t for t in txs if goes_to_agents(scores[t["transaction_id"]][0])]
    alerts = [tid for tid, l in labels.items() if l["decision"] == "escalate" and l["pattern"] != "none"]
    caught = [tid for tid in alerts if baseline_decision(scores[tid][0]) == "escalate"]
    clears = [tid for tid, l in labels.items() if l["decision"] == "clear"]
    fps = [tid for tid in clears if baseline_decision(scores[tid][0]) == "escalate"]
    s = {"world": world, "transactions": len(txs), "rules_tier_share": 1 - len(flagged) / len(txs),
         "to_agents": len(flagged), "baseline_recall": len(caught) / len(alerts), "baseline_false_positives": len(fps),
         "baseline_fp_rate": len(fps) / len(clears), "alerts": len(alerts)}
    missed = [tid for tid in alerts if tid not in caught]
    return s | {"missed": missed, "scores": scores, "txs": {t["transaction_id"]: t for t in txs}, "labels": labels}


def check(ok, name):
    results.append((bool(ok), name))


w0 = stats(0)
w1 = stats(1)
for s in (w0, w1):
    print(f"world {s['world']}: {s['transactions']} tx, rules tier clears {s['rules_tier_share']:.1%}, "
          f"{s['to_agents']} go to agents; rules-only baseline: recall {s['baseline_recall']:.0%} of {s['alerts']} "
          f"alerts, {s['baseline_false_positives']} false positives (FP rate {s['baseline_fp_rate']:.1%})")
    for tid in s["missed"]:
        t, l = s["txs"][tid], s["labels"][tid]
        print(f"   missed {tid} {t['user_id']} {t['txn_type']} £{t['amount']:,.0f} ({l['pattern']}) score {s['scores'][tid][0]}")

# Task 2.1 done-when (observing world 0, not steering it)
sc, txs = w0["scores"], w0["txs"]
def ids(**where):
    with db.use_world(0):
        return [t["transaction_id"] for t in sorted(db.query("transactions", **where), key=lambda t: t["timestamp"])]

daniel = [tid for tid in ids(user_id="CUS-0001", txn_type="cash_deposit") if txs[tid]["amount"] == 9500]
check(sc[daniel[3]][0] >= 30 and sc[daniel[2]][0] >= 30, "w0: Daniel's 3rd and 4th deposits go to the agents")
check(sc[daniel[0]][0] < 30, "w0: Daniel's 1st deposit is cleared by rules")
sophie = [tid for tid in ids(user_id="CUS-0002") if txs[tid]["reference"] == "Annual bonus"]
check(all(sc[tid][0] >= 30 for tid in sophie), "w0: both of Sophie's credits go to the agents")
forwards = [tid for uid in ("CUS-0040", "CUS-0041", "CUS-0042", "CUS-0043", "CUS-0044")
            for tid in ids(user_id=uid, direction="out") if txs[tid]["counterparty_id"] == "ACC-0050"]
check(forwards and all(sc[tid][0] >= 30 for tid in forwards), f"w0: all {len(forwards)} mule forwards go to the agents")
check(w0["rules_tier_share"] >= 0.90, f"w0: at least 90% cleared by rules ({w0['rules_tier_share']:.1%})")
check(w1["rules_tier_share"] >= 0.90, f"w1 (dev): at least 90% cleared by rules ({w1['rules_tier_share']:.1%})")
check(w1["baseline_recall"] >= 0.9, f"w1 (dev): rules-only catches at least 90% of planted alerts ({w1['baseline_recall']:.0%})")

print()
for ok, name in results:
    print(("PASS " if ok else "FAIL ") + name)
sys.exit(0 if all(ok for ok, _ in results) else 1)
