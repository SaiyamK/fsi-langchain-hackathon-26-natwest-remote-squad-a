"""World 0 loaded once, with the lookups the UI needs (names, profiles, per-account history).

The agent's `utils.db` re-reads files on every query, which suits the agents but not a UI that asks the same
questions many times a second. This is a read-only, in-memory view of the same tables.
"""

from dataclasses import dataclass, field
from datetime import datetime

from utils import db  # sentinel_aml_agent

from sentinel_api.models import Party

NON_FLOW_TYPES = {"card"}  # card spend is not a money movement of interest on the graph


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def is_flow(tx: dict) -> bool:
    return tx["txn_type"] not in NON_FLOW_TYPES


def cash_node_id(tx: dict) -> str:
    return f"CASH:{tx.get('branch') or 'unknown'}"


@dataclass
class World:
    transactions: list[dict]
    profiles_by_user: dict[str, dict]
    profiles_by_account: dict[str, dict]
    labels: dict[str, dict]
    by_account: dict[str, list[dict]] = field(default_factory=dict)
    external_names: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "World":
        txs = sorted(db.table("transactions"), key=lambda t: (t["timestamp"], t["transaction_id"]))
        profiles = db.table("customer_profiles")
        world = cls(
            transactions=txs,
            profiles_by_user={p["user_id"]: p for p in profiles},
            profiles_by_account={p["account_id"]: p for p in profiles},
            labels={row["transaction_id"]: row for row in db.table("analyst_labels")},
        )
        for t in txs:
            world.by_account.setdefault(t["account_id"], []).append(t)
            cp = t.get("counterparty_id")
            if cp and cp not in world.profiles_by_account and t.get("counterparty_name"):
                world.external_names.setdefault(cp, t["counterparty_name"])
        return world

    def tx(self, transaction_id: str) -> dict | None:
        return next((t for t in self.transactions if t["transaction_id"] == transaction_id), None)

    def is_ours(self, node_id: str) -> bool:
        return node_id in self.profiles_by_account

    def name(self, node_id: str) -> str:
        if node_id in self.profiles_by_account:
            return self.profiles_by_account[node_id]["name"]
        if node_id.startswith("CASH:"):
            return f"Cash · {node_id[5:]}"
        return self.external_names.get(node_id, node_id)

    def counterparty_node(self, tx: dict) -> str:
        """The graph node on the other side of a transaction: an account ID, an external ID, or a cash branch."""
        return tx.get("counterparty_id") or cash_node_id(tx)

    def parties(self, tx: dict) -> tuple[Party, Party]:
        """(sender, receiver) as the stream shows them."""
        me = Party(account=tx["account_id"], name=self.profiles_by_user[tx["user_id"]]["name"])
        cp_id = tx.get("counterparty_id")
        if cp_id:
            other = Party(account=cp_id, name=tx.get("counterparty_name") or self.name(cp_id))
        elif tx["txn_type"].startswith("cash"):
            other = Party(account=None, name=f"Cash · {tx.get('branch') or 'branch'}")
        else:
            other = Party(account=None, name=tx.get("counterparty_name") or "—")
        return (me, other) if tx["direction"] == "out" else (other, me)

    def flows(self, account_id: str, start: str, end: str) -> list[dict]:
        """An account's non-card transactions with start <= timestamp <= end."""
        return [t for t in self.by_account.get(account_id, []) if is_flow(t) and start <= t["timestamp"] <= end]
