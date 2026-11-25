"""Check the generated data (tasks 1.3 and 1.4). Observes the data only; it never changes it (DEC-004).

Run from sentinel_aml_agent/ after `uv run python data/generate.py`:

    uv run python scripts/check_data.py
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import db  # noqa: E402

PATTERNS = {"structuring", "anomalous_credit", "round_tripping", "mule_fan_in"}
results: list[tuple[bool, str]] = []


def check(ok: bool, name: str):
    results.append((bool(ok), name))


def txs_of(user_id: str) -> list[dict]:
    return sorted(db.query("transactions", user_id=user_id), key=lambda t: t["timestamp"])


def common_checks(world: int):
    profiles = db.table("customer_profiles")
    txs = db.table("transactions")
    labels = {row["transaction_id"]: row for row in db.table("analyst_labels")}
    ids = [t["transaction_id"] for t in txs]
    check(len(ids) == len(set(ids)), f"w{world}: transaction IDs are unique")
    check(set(ids) == set(labels), f"w{world}: every transaction has exactly one label")
    users = {p["user_id"] for p in profiles}
    check(all(t["user_id"] in users for t in txs), f"w{world}: every transaction belongs to a known customer")
    accounts = {p["account_id"] for p in profiles}
    internal = [t for t in txs if t["txn_type"] == "internal_transfer"]
    check(all(t["counterparty_id"] in accounts for t in internal), f"w{world}: internal transfers point at our accounts")
    check(30 <= len(profiles) <= 60, f"w{world}: about 40 customers (DEC-006), got {len(profiles)}")
    alerts = Counter(l["pattern"] for l in labels.values() if l["decision"] == "escalate")
    for pattern in PATTERNS - {"anomalous_credit"}:
        check(alerts[pattern] >= 1, f"w{world}: at least one planted '{pattern}' alert")
    check(any(l["pattern"] == "anomalous_credit" and l["decision"] == "clear" and l["ambiguous"]
              for l in labels.values()), f"w{world}: benign-but-ambiguous credits exist (should go to a human)")
    check(any(l["expect_override"] for l in labels.values()), f"w{world}: a precedent-override case exists")
    check(any(l["ambiguous"] and l["pattern"] == "mule_fan_in" and l["decision"] == "escalate"
              for l in labels.values()), f"w{world}: early mule forwards are ambiguous + escalate (agreed rule)")
    answers = db.table("reviewer_answers")
    check(all(a["transaction_id"] in labels for a in answers), f"w{world}: reviewer answers refer to real transactions")
    check(all(labels[a["transaction_id"]]["ambiguous"] for a in answers), f"w{world}: answers exist only for ambiguous cases")
    share_alert = sum(l["decision"] == "escalate" for l in labels.values()) / len(labels)
    check(share_alert < 0.05, f"w{world}: alerts are rare ({share_alert:.1%} of transactions)")
    return profiles, txs, labels


def world_0_cast():
    p = {row["user_id"]: row for row in db.table("customer_profiles")}
    names = {"CUS-0001": "Daniel Hughes", "CUS-0002": "Sophie Clarke", "CUS-0003": "Marcus Reid",
             "CUS-0040": "Liam Walsh", "CUS-0041": "Chloe Evans", "CUS-0042": "Ben Taylor", "CUS-0043": "Amira Khan",
             "CUS-0044": "Josh Patel", "CUS-0050": "Northgate Trading Ltd"}
    check(all(p.get(uid, {}).get("name") == name for uid, name in names.items()), "w0: demo cast has the D4 IDs")

    cash = [t for t in txs_of("CUS-0001") if t["txn_type"] == "cash_deposit" and "2026-10-02" <= t["timestamp"] < "2026-10-11"]
    check([t["amount"] for t in cash] == [9500.0] * 4, "w0: Daniel has exactly 4 × £9,500 cash deposits that week")
    check(cash and cash[0]["timestamp"] >= "2026-10-06" and cash[-1]["timestamp"] < "2026-10-09",
          "w0: Daniel's deposits fall on 6-8 Oct")
    check(len({t["branch"] for t in cash}) == 3, "w0: Daniel used 3 branches")

    sophie = [t for t in txs_of("CUS-0002") if t["reference"] == "Annual bonus"]
    check([(t["timestamp"][:10], t["amount"]) for t in sophie] == [("2026-10-14", 18000.0), ("2027-08-14", 19200.0)],
          "w0: Sophie's credits are £18,000 on 14 Oct 2026 and £19,200 on 14 Aug 2027")
    check(len({t["counterparty_id"] for t in sophie}) == 1, "w0: both of Sophie's credits come from the same counterparty")

    marcus = txs_of("CUS-0003")
    check(any(t["amount"] == 250000 and t["direction"] == "out" and t["timestamp"].startswith("2026-11-03") for t in marcus)
          and any(t["amount"] == 240000 and t["direction"] == "in" and t["timestamp"].startswith("2026-11-20") for t in marcus),
          "w0: Marcus sends £250k on 3 Nov and gets £240k back on 20 Nov")
    check(p["CUS-0003"]["pep"] and db.get("pep_list", name="Marcus Reid") is not None, "w0: Marcus is on the PEP list")

    forwards = [t for uid in ("CUS-0040", "CUS-0041", "CUS-0042", "CUS-0043", "CUS-0044") for t in txs_of(uid)
                if t["direction"] == "out" and t["counterparty_id"] == "ACC-0050"]
    check({t["user_id"] for t in forwards} == {"CUS-0040", "CUS-0041", "CUS-0042", "CUS-0043", "CUS-0044"},
          "w0: all five mules forward to Northgate")
    check(all("2026-11-09" <= t["timestamp"] < "2026-11-14" for t in forwards), "w0: mule forwards fall on 9-13 Nov")
    check(p["CUS-0050"]["account_opened"] == "2026-10-25", "w0: Northgate opened on 25 Oct 2026")

    liam = db.get("seed_precedents", user_id="CUS-0040")
    check(liam and liam["created_at"] == "2026-03-10" and liam["expires_at"] == "2027-03-10",
          "w0: Liam's precedent runs 10 Mar 2026 to 10 Mar 2027 (still valid, so it must be overridden)")
    check(db.get("seed_precedents", user_id="CUS-0004")["expires_at"] < "2026-11-05", "w0: Grace's precedent has expired")
    tom_p = db.get("seed_precedents", user_id="CUS-0005")
    tom_cps = {t["counterparty_id"] for t in txs_of("CUS-0005") if t["amount"] >= 10000}
    check(tom_p["counterparty_id"] not in tom_cps, "w0: Tom's precedent is for a different counterparty (out of scope)")


def main():
    for world in (0, 1, 2):
        with db.use_world(world):
            if not db.table("transactions"):
                check(False, f"w{world}: data exists (run data/generate.py)")
                continue
            common_checks(world)
            if world == 0:
                world_0_cast()
    for ok, name in results:
        print(("PASS " if ok else "FAIL ") + name)
    failed = sum(not ok for ok, _ in results)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
