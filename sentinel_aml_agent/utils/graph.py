"""Cross-account fund-flow graph and fan-in ring detection (PLAN.md 4.3, task 2.2). Deterministic, no LLM.

"Now" is `as_of`: only transactions at or before it are visible, so nothing can see the future (PLAN.md section 1).

Ring definition, shared with the data generator's labels and the rule scorer (DEC-012, DEC-013):
a collector account receives forwards from at least RING_MIN_FEEDERS distinct accounts within RING_WINDOW, where
each forward is an internal transfer worth at least PASS_THROUGH_RATIO of what the feeder received in the previous
PASS_THROUGH_WINDOW. The ring is "confirmed" once that holds.
"""

from datetime import datetime, timedelta

import networkx as nx

from utils import db

RING_MIN_FEEDERS = 5
RING_WINDOW = timedelta(hours=72)
PASS_THROUGH_RATIO = 0.9
PASS_THROUGH_WINDOW = timedelta(hours=24)


def _t(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _visible(as_of: str) -> list[dict]:
    return [t for t in db.table("transactions") if t["timestamp"] <= as_of]


def build_graph(as_of: str) -> nx.MultiDiGraph:
    """Accounts as nodes; one edge per money movement between two of our accounts (internal transfers, out legs),
    plus edges to external counterparties for inbound and outbound payments. Only transactions up to `as_of`."""
    g = nx.MultiDiGraph()
    for t in _visible(as_of):
        cp = t.get("counterparty_id")
        if not cp or t["txn_type"] == "card":
            continue
        if t["txn_type"] == "internal_transfer" and t["direction"] == "in":
            continue  # the out leg already records this movement
        src, dst = (t["account_id"], cp) if t["direction"] == "out" else (cp, t["account_id"])
        g.add_edge(src, dst, transaction_id=t["transaction_id"], amount=t["amount"], timestamp=t["timestamp"])
    return g


def _qualifying_forwards(txs: list[dict]) -> list[dict]:
    """Internal forwards that pass on at least 90% of what the sender received in the previous 24 hours."""
    by_account: dict[str, list[dict]] = {}
    for t in txs:
        by_account.setdefault(t["account_id"], []).append(t)
    out = []
    for t in txs:
        if t["txn_type"] != "internal_transfer" or t["direction"] != "out":
            continue
        now = _t(t["timestamp"])
        received = sum(h["amount"] for h in by_account[t["account_id"]]
                       if h["direction"] == "in" and h["timestamp"] < t["timestamp"]
                       and now - _t(h["timestamp"]) <= PASS_THROUGH_WINDOW)
        if received > 0 and t["amount"] >= PASS_THROUGH_RATIO * received:
            out.append(t | {"pass_through_ratio": round(t["amount"] / received, 3)})
    return out


def confirmed_rings(as_of: str) -> dict[str, dict]:
    """{collector_account: ring} for every ring confirmed by `as_of`."""
    forwards = _qualifying_forwards(_visible(as_of))
    by_collector: dict[str, list[dict]] = {}
    for f in forwards:
        by_collector.setdefault(f["counterparty_id"], []).append(f)
    rings = {}
    for collector, fs in by_collector.items():
        fs.sort(key=lambda f: f["timestamp"])
        for i, first in enumerate(fs):
            window = [f for f in fs[i:] if _t(f["timestamp"]) - _t(first["timestamp"]) <= RING_WINDOW]
            feeders = {f["account_id"] for f in window}
            if len(feeders) >= RING_MIN_FEEDERS:
                confirmed_at = sorted(window, key=lambda f: f["timestamp"])
                # the moment the Nth distinct feeder appeared
                seen, at = set(), None
                for f in confirmed_at:
                    seen.add(f["account_id"])
                    if len(seen) == RING_MIN_FEEDERS:
                        at = f["timestamp"]
                        break
                all_feeders = sorted({f["account_id"] for f in fs})
                rings[collector] = {
                    "collector_account": collector,
                    "feeder_accounts": all_feeders,
                    "confirmed_at": at,
                    "forwards": [{"transaction_id": f["transaction_id"], "from": f["account_id"],
                                  "amount": f["amount"], "timestamp": f["timestamp"],
                                  "pass_through_ratio": f["pass_through_ratio"]} for f in fs],
                }
                break
    return rings


def ring_membership(account_id: str, as_of: str) -> dict | None:
    """The confirmed ring this account belongs to (as collector or feeder) at `as_of`, or None."""
    for ring in confirmed_rings(as_of).values():
        if account_id == ring["collector_account"] or account_id in ring["feeder_accounts"]:
            return ring
    return None


def fan_in_summary(account_id: str, as_of: str) -> dict:
    """Graph summary for one account: accounts, amounts and timings only, never customer profiles (R7.2)."""
    ring = ring_membership(account_id, as_of)
    if ring:
        role = "collector" if account_id == ring["collector_account"] else "feeder"
        ratios = [f["pass_through_ratio"] for f in ring["forwards"]]
        return {"account_id": account_id, "as_of": as_of, "ring_confirmed": True, "role": role,
                "collector_account": ring["collector_account"], "feeder_accounts": ring["feeder_accounts"],
                "confirmed_at": ring["confirmed_at"], "forwards": ring["forwards"],
                "pass_through_ratio": round(sum(ratios) / len(ratios), 3)}
    # Not in a confirmed ring: report what's visible around the account, so the agent can still reason about it
    forwards = [f for f in _qualifying_forwards(_visible(as_of))
                if f["account_id"] == account_id or f["counterparty_id"] == account_id]
    collectors = {f["counterparty_id"] for f in forwards}
    return {"account_id": account_id, "as_of": as_of, "ring_confirmed": False, "role": None,
            "collector_account": next(iter(collectors)) if len(collectors) == 1 else None,
            "feeder_accounts": sorted({f["account_id"] for f in forwards}),
            "confirmed_at": None,
            "forwards": [{"transaction_id": f["transaction_id"], "from": f["account_id"], "to": f["counterparty_id"],
                          "amount": f["amount"], "timestamp": f["timestamp"],
                          "pass_through_ratio": f["pass_through_ratio"]} for f in forwards],
            "pass_through_ratio": round(sum(f["pass_through_ratio"] for f in forwards) / len(forwards), 3) if forwards else 0.0}
