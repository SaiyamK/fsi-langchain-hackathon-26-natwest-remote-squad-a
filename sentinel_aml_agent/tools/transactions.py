"""Customer-scoped transaction lookups (`data/transactions.jsonl`).

The customer comes from the run context, never from the model (R4.6), and only transactions up to `as_of` are
visible, so no tool can see the future.
"""

from datetime import datetime, timedelta

from langchain.tools import ToolRuntime, tool

from utils import db
from utils.state import MyAgentContext

FIELDS = ("transaction_id", "timestamp", "direction", "txn_type", "amount", "currency", "counterparty_id",
          "counterparty_name", "branch", "country", "reference", "channel")


def _visible(row: dict, as_of: str) -> bool:
    return not as_of or row["timestamp"] <= as_of


def _slim(row: dict) -> dict:
    return {k: row.get(k) for k in FIELDS}


@tool(parse_docstring=True)
def get_transaction(transaction_id: str, runtime: ToolRuntime[MyAgentContext]) -> dict | str:
    """Look up one of this customer's transactions: amount, direction, type, counterparty, branch, time.

    Args:
        transaction_id: The ID of the transaction, for example "TX-000167".
    """
    ctx = runtime.context
    row = db.get("transactions", transaction_id=transaction_id, user_id=ctx.user_id)
    if row is None or not _visible(row, ctx.as_of):
        return f"There is no transaction {transaction_id} for this customer."
    return _slim(row)


@tool(parse_docstring=True)
def get_recent_transactions(runtime: ToolRuntime[MyAgentContext], days: int = 30) -> dict:
    """This customer's transactions over the last `days` days, up to now, oldest first, plus simple totals.

    Card spending is summarised rather than listed, to keep the result short.

    Args:
        days: How many days back to look (default 30, at most 90).
    """
    ctx = runtime.context
    days = max(1, min(int(days), 90))
    now = datetime.fromisoformat(ctx.as_of) if ctx.as_of else None
    rows = sorted(db.query("transactions", user_id=ctx.user_id), key=lambda r: r["timestamp"])
    if now:
        start = (now - timedelta(days=days)).isoformat(timespec="minutes")
        rows = [r for r in rows if start <= r["timestamp"] <= ctx.as_of]
    cards = [r for r in rows if r["txn_type"] == "card"]
    listed = [_slim(r) for r in rows if r["txn_type"] != "card"]
    return {
        "window_days": days,
        "as_of": ctx.as_of,
        "transactions": listed,
        "card_spend": {"count": len(cards), "total": round(sum(r["amount"] for r in cards), 2)},
        "totals": {
            "credits_in": round(sum(r["amount"] for r in rows if r["direction"] == "in"), 2),
            "debits_out": round(sum(r["amount"] for r in rows if r["direction"] == "out"), 2),
            "cash_deposits": round(sum(r["amount"] for r in rows if r["txn_type"] == "cash_deposit"), 2),
        },
    }
