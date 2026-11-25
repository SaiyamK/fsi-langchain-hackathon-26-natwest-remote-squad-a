"""Tier 1: the deterministic rule scorer, and the rules-only baseline (PLAN.md 5.1).

Every transaction is scored 0-100 from the customer's own history up to that transaction and their KYC profile.
No LLM, no other customers' data. Below `ctx.rules_clear_below` the transaction is auto-cleared; otherwise it goes
to the agents. The same scorer, with a plain threshold, is the rules-only baseline, so the comparison is fair.

Thresholds come from standard AML typology definitions, not from the demo data (DEC-004):
- near-threshold cash: £9,000-£9,999 (just under a £10,000 cash-monitoring threshold);
- structuring: 3 or more near-threshold deposits within 72 hours;
- cash velocity: more than twice the customer's expected monthly cash within 48 hours;
- large one-off movement: at least 3× the customer's expected monthly credits;
- pass-through: an outbound payment worth at least 90% of what came in over the previous 24 hours;
- round trip: money back within 30 days, from a different counterparty, worth at least 85% of a large outbound;
- fan-in to a new account: 5 or more distinct internal senders within 72 hours, account under 90 days old
  (the same 5-account definition the network check uses to confirm a ring);
- high-risk or PEP customers: scores × 1.3.
"""

from datetime import datetime, timedelta

from utils.state import MyAgentContext

CASH_THRESHOLD = 10_000
NEAR_THRESHOLD_LOW = 9_000
STRUCTURING_COUNT = 3
STRUCTURING_WINDOW = timedelta(hours=72)
CASH_VELOCITY_WINDOW = timedelta(hours=48)
LARGE_MULTIPLE = 3
PASS_THROUGH_WINDOW = timedelta(hours=24)
PASS_THROUGH_RATIO = 0.9
ROUND_TRIP_WINDOW = timedelta(days=30)
ROUND_TRIP_RATIO = 0.85
FAN_IN_SENDERS = 5
FAN_IN_WINDOW = timedelta(hours=72)
NEW_ACCOUNT_DAYS = 90
NEW_COUNTERPARTY_MIN = 1_000
HIGH_RISK_MULTIPLIER = 1.3

POINTS = {
    "near_threshold_cash": 20,
    "structuring": 40,
    "cash_velocity": 25,
    "large_credit": 35,
    "large_debit": 30,
    "new_counterparty": 10,
    "pass_through": 30,
    "round_trip": 45,
    "fan_in_new_account": 35,
}


def _t(tx: dict) -> datetime:
    return datetime.fromisoformat(tx["timestamp"])


def score(tx: dict, history: list[dict], profile: dict, ctx: MyAgentContext | None = None) -> tuple[int, list[str]]:
    """Score one transaction. `history` is this customer's earlier transactions (any order), before `tx`."""
    now = _t(tx)
    earlier = [h for h in history if h["timestamp"] < tx["timestamp"] or (h["timestamp"] == tx["timestamp"]
               and h["transaction_id"] < tx["transaction_id"])]
    monthly_credits = max(float(profile.get("expected_monthly_credits") or 0), 1.0)
    monthly_cash = float(profile.get("expected_monthly_cash") or 0)
    amount = float(tx["amount"])
    points: dict[str, int] = {}
    reasons: list[str] = []

    def hit(key: str, why: str):
        points[key] = POINTS[key]
        reasons.append(why)

    is_cash_in = tx["txn_type"] == "cash_deposit"
    if is_cash_in and NEAR_THRESHOLD_LOW <= amount < CASH_THRESHOLD:
        hit("near_threshold_cash", f"cash deposit £{amount:,.0f} just under the £{CASH_THRESHOLD:,} threshold")
        near = [h for h in earlier if h["txn_type"] == "cash_deposit" and NEAR_THRESHOLD_LOW <= h["amount"] < CASH_THRESHOLD
                and now - _t(h) <= STRUCTURING_WINDOW]
        if len(near) + 1 >= STRUCTURING_COUNT:
            branches = {h["branch"] for h in near} | {tx["branch"]}
            hit("structuring", f"{len(near) + 1} near-threshold cash deposits in 72h at {len(branches)} branches")

    if is_cash_in:
        cash_48h = amount + sum(h["amount"] for h in earlier if h["txn_type"] == "cash_deposit"
                                and now - _t(h) <= CASH_VELOCITY_WINDOW)
        if cash_48h > 2 * max(monthly_cash, 1.0):
            hit("cash_velocity", f"£{cash_48h:,.0f} cash in 48h vs £{monthly_cash:,.0f} expected per month")

    if tx["direction"] == "in" and not is_cash_in and amount >= LARGE_MULTIPLE * monthly_credits:
        hit("large_credit", f"credit £{amount:,.0f} is {amount / monthly_credits:.1f}× expected monthly credits")
    if tx["direction"] == "out" and amount >= LARGE_MULTIPLE * monthly_credits:
        hit("large_debit", f"payment £{amount:,.0f} is {amount / monthly_credits:.1f}× expected monthly credits")

    cp = tx.get("counterparty_id")
    if cp and amount >= NEW_COUNTERPARTY_MIN and not any(h.get("counterparty_id") == cp for h in earlier):
        hit("new_counterparty", f"first payment with counterparty {cp}")

    if tx["direction"] == "out" and tx["txn_type"] != "card":
        received = sum(h["amount"] for h in earlier if h["direction"] == "in" and now - _t(h) <= PASS_THROUGH_WINDOW)
        if received > 0 and amount >= PASS_THROUGH_RATIO * received:
            hit("pass_through", f"sends on £{amount:,.0f} of £{received:,.0f} received in the last 24h")

    if tx["direction"] == "in" and cp:
        for h in earlier:
            if (h["direction"] == "out" and h.get("counterparty_id") not in (None, cp)
                    and h["amount"] >= LARGE_MULTIPLE * monthly_credits and now - _t(h) <= ROUND_TRIP_WINDOW
                    and ROUND_TRIP_RATIO * h["amount"] <= amount <= h["amount"]):
                hit("round_trip", f"£{amount:,.0f} back from a different counterparty {(now - _t(h)).days} days "
                                  f"after £{h['amount']:,.0f} went out ({h['transaction_id']})")
                break

    if tx["direction"] == "in" and tx["txn_type"] == "internal_transfer":
        opened = datetime.fromisoformat(profile.get("account_opened", "1900-01-01"))
        if (now - opened).days < NEW_ACCOUNT_DAYS:
            senders = {h["counterparty_id"] for h in earlier if h["direction"] == "in"
                       and h["txn_type"] == "internal_transfer" and now - _t(h) <= FAN_IN_WINDOW} | {cp}
            if len(senders) >= FAN_IN_SENDERS:
                hit("fan_in_new_account", f"{len(senders)} internal senders in 72h into an account opened "
                                          f"{(now - opened).days} days ago")

    total = sum(points.values())
    if profile.get("risk_rating") == "high" or profile.get("pep"):
        if total:
            reasons.append("high-risk or PEP customer (score × 1.3)")
        total = int(round(total * HIGH_RISK_MULTIPLIER))
    return min(total, 100), reasons


#
# Network watchlist (DEC-013): a deterministic graph check, shared by Sentinel and the rules-only baseline
#
RING_TRIGGER_TYPES = {"faster_payment", "internal_transfer"}
RING_TRIGGER_SCORE = 60


def network_trigger(tx: dict) -> str | None:
    """If this money movement is by an account in a ring confirmed by the graph check (as of this transaction),
    return the reason; else None. Card spending and salaries are not money movements of interest here."""
    if tx["txn_type"] not in RING_TRIGGER_TYPES:
        return None
    from utils.graph import ring_membership  # local import: the scorer itself stays free of graph code

    ring = ring_membership(tx["account_id"], tx["timestamp"])
    if not ring:
        return None
    role = "collector" if tx["account_id"] == ring["collector_account"] else "feeder"
    return (f"account is a {role} in a fan-in ring into {ring['collector_account']} confirmed at "
            f"{ring['confirmed_at']} (network check)")


def score_with_network(tx: dict, history: list[dict], profile: dict, ctx: MyAgentContext | None = None) -> tuple[int, list[str]]:
    """Tier 1 as used by Sentinel and the baseline: the rule score, raised to at least 60 by the network watchlist."""
    rule_score, reasons = score(tx, history, profile, ctx)
    why = network_trigger(tx)
    if why:
        reasons = reasons + [why]
        rule_score = max(rule_score, RING_TRIGGER_SCORE)
    return rule_score, reasons


def baseline_decision(rule_score: int, ctx: MyAgentContext | None = None) -> str:
    """The rules-only baseline: escalate at or above the threshold, otherwise clear. No LLM."""
    ctx = ctx or MyAgentContext()
    return "escalate" if rule_score >= ctx.rules_escalate_at else "clear"


def goes_to_agents(rule_score: int, ctx: MyAgentContext | None = None) -> bool:
    """Tier 1 routing: below the threshold, auto-clear with no LLM call."""
    ctx = ctx or MyAgentContext()
    return rule_score >= ctx.rules_clear_below


def score_all(transactions: list[dict], profiles: dict[str, dict], ctx: MyAgentContext | None = None,
              network: bool = True) -> dict[str, tuple[int, list[str]]]:
    """Score many transactions: {transaction_id: (score, reasons)}. Reads the active world's data for the network
    check, so call it inside `db.use_world(n)` for eval worlds."""
    by_user: dict[str, list[dict]] = {}
    for t in transactions:
        by_user.setdefault(t["user_id"], []).append(t)
    scorer = score_with_network if network else score
    out = {}
    for user_id, rows in by_user.items():
        rows.sort(key=lambda r: (r["timestamp"], r["transaction_id"]))
        for i, t in enumerate(rows):
            out[t["transaction_id"]] = scorer(t, rows[:i], profiles[user_id], ctx)
    return out
