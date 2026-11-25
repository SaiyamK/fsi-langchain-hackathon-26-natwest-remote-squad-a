"""Analyst precedents: past human decisions, stored in the LangGraph store under ("precedents", user_id).

A precedent applies only when the customer, the counterparty and the pattern all match and it hasn't expired at
`as_of` (R6.3). The classification here is plain code, and `record_decision` uses the same function, so the
safeguards never depend on what the model says (R6.6).
"""

from langchain.tools import ToolRuntime, tool

from utils import db
from utils.state import MyAgentContext

NO_COUNTERPARTY = "*"


def precedent_key(counterparty_id: str | None, pattern: str) -> str:
    return f"{counterparty_id or NO_COUNTERPARTY}:{pattern}"


def classify_precedents(store, user_id: str, counterparty_id: str | None, pattern: str | None, as_of: str) -> dict:
    """Sort this customer's precedents into valid (in scope and unexpired), expired and out of scope."""
    out = {"valid": [], "expired": [], "out_of_scope": []}
    if store is None:
        return out
    today = (as_of or "9999-12-31")[:10]
    for item in store.search(("precedents", user_id), limit=200):
        p = dict(item.value) | {"key": item.key}
        same_scope = p["counterparty_id"] == (counterparty_id or NO_COUNTERPARTY) and (pattern is None or p["pattern"] == pattern)
        if not same_scope:
            out["out_of_scope"].append(p)
        elif today >= p["expires_at"]:
            out["expired"].append(p)
        else:
            out["valid"].append(p)
    return out


def load_seed_precedents(store) -> int:
    """Put the active world's `seed_precedents.jsonl` into the store (R6.7). Returns how many were loaded."""
    rows = db.table("seed_precedents")
    for p in rows:
        store.put(("precedents", p["user_id"]), precedent_key(p["counterparty_id"], p["pattern"]), p)
    return len(rows)


@tool(parse_docstring=True)
def find_precedents(counterparty_id: str | None, pattern: str, runtime: ToolRuntime[MyAgentContext]) -> dict:
    """Find analysts' past decisions about this customer, sorted into valid, expired and out-of-scope.

    A precedent is valid only for the same counterparty and pattern, and only until its expiry date.

    Args:
        counterparty_id: The counterparty of the transaction under review (null for cash).
        pattern: The pattern being considered: none, structuring, anomalous_credit, round_tripping or mule_fan_in.
    """
    ctx = runtime.context
    found = classify_precedents(runtime.store, ctx.user_id, counterparty_id, pattern, ctx.as_of)
    found["scope_checked"] = {"counterparty_id": counterparty_id or NO_COUNTERPARTY, "pattern": pattern, "as_of": ctx.as_of}
    return found
