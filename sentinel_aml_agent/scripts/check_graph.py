"""Check ring detection timing (task 2.2): in world 0 the ring is not confirmed at the 4th mule forward and is
confirmed at the 5th. Observes the data only (DEC-004).

    uv run python scripts/check_graph.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import db  # noqa: E402
from utils.graph import build_graph, fan_in_summary  # noqa: E402

results = []
mules = ["ACC-0040", "ACC-0041", "ACC-0042", "ACC-0043", "ACC-0044"]
forwards = sorted((t for t in db.table("transactions")
                   if t["account_id"] in mules and t["direction"] == "out" and t["counterparty_id"] == "ACC-0050"),
                  key=lambda t: t["timestamp"])
fourth, fifth = forwards[3], forwards[4]

s4 = fan_in_summary(fourth["account_id"], fourth["timestamp"])
s5 = fan_in_summary(fifth["account_id"], fifth["timestamp"])
liam_later = fan_in_summary("ACC-0040", fifth["timestamp"])
northgate = fan_in_summary("ACC-0050", fifth["timestamp"])
before_any = fan_in_summary("ACC-0040", "2026-11-01T00:00")

results += [
    (not s4["ring_confirmed"], f"not confirmed at the 4th forward ({fourth['transaction_id']} {fourth['timestamp']})"),
    (s5["ring_confirmed"], f"confirmed at the 5th forward ({fifth['transaction_id']} {fifth['timestamp']})"),
    (s5.get("collector_account") == "ACC-0050" and set(s5["feeder_accounts"]) == set(mules), "ring = 5 mules → Northgate"),
    (liam_later["ring_confirmed"] and liam_later["role"] == "feeder", "Liam is a feeder once the ring is confirmed"),
    (northgate["role"] == "collector", "Northgate is the collector"),
    (not before_any["ring_confirmed"] and not before_any["forwards"], "nothing visible before the ring starts"),
    (all(k not in str(s5) for k in ("name", "occupation", "date_of_birth", "risk_rating")), "summary has no profile fields"),
]
g = build_graph(fifth["timestamp"])
results.append((g.has_edge("ACC-0044", "ACC-0050") or g.has_edge(fifth["account_id"], "ACC-0050"), "graph has the 5th edge"))
results.append((not build_graph(fourth["timestamp"]).has_edge(fifth["account_id"], "ACC-0050"), "graph at the 4th has no future edge"))

for ok, name in results:
    print(("PASS " if ok else "FAIL ") + name)
sys.exit(0 if all(ok for ok, _ in results) else 1)
