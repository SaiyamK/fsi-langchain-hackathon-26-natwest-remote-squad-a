"""A tiny read-only database over the JSONL files in `data/`.

Each `.jsonl` file is a table and each line in it is one row, so `data/transactions.jsonl` is the `transactions`
table. Every query reads the file again, so changes show up straight away.

Extended from the organiser starter for Sentinel's eval worlds (design.md D1): world 0, the demo, lives in `data/`;
eval worlds live in `data/worlds/world_<N>/`. `with use_world(n):` switches the folder for the current context.
It's a ContextVar, so parallel eval runs each read their own world. Reference tables (watchlists) are shared and
always read from `data/`.
"""

import json
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from utils import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data"
SHARED_TABLES = {"sanctions_list", "pep_list"}

_active_dir: ContextVar[Path] = ContextVar("sentinel_data_dir", default=DATA_DIR)


def world_dir(world: int) -> Path:
    """The folder that holds a world's tables. World 0 is `data/` itself."""
    return DATA_DIR if world == 0 else DATA_DIR / "worlds" / f"world_{world}"


@contextmanager
def use_world(world: int):
    """Read tables from `world`'s folder inside this block."""
    token = _active_dir.set(world_dir(world))
    try:
        yield
    finally:
        _active_dir.reset(token)


def table(name: str, /) -> list[dict]:
    """Every row in a table, in file order."""
    folder = DATA_DIR if name in SHARED_TABLES else _active_dir.get()
    path = folder / f"{name}.jsonl"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def query(name: str, /, **where) -> list[dict]:
    """The rows whose fields equal the given values, for example `query("transactions", user_id="CUS-0100")`.

    The table name is positional-only, so a column called `name` can be filtered on (`get("pep_list", name=...)`).
    """
    return [row for row in table(name) if all(row.get(field) == value for field, value in where.items())]


def get(name: str, /, **where) -> dict | None:
    """The first row that matches, or None if there isn't one."""
    rows = query(name, **where)
    return rows[0] if rows else None
