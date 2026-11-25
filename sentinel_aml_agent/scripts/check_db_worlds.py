"""Check that `db.use_world` switches folders, including inside LangChain's worker threads (task 1.2).

Run from sentinel_aml_agent/:  uv run python scripts/check_db_worlds.py
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.runnables import RunnableLambda  # noqa: E402

from utils import db  # noqa: E402

TEST_WORLD = 99
folder = db.world_dir(TEST_WORLD)
folder.mkdir(parents=True, exist_ok=True)
(folder / "probe.jsonl").write_text(json.dumps({"where": "world_99"}) + "\n")
(db.DATA_DIR / "probe.jsonl").write_text(json.dumps({"where": "data"}) + "\n")

try:
    outside = db.table("probe")[0]["where"]
    with db.use_world(TEST_WORLD):
        inside = db.table("probe")[0]["where"]
        # .batch runs each input in a LangChain worker thread, as tool calls are run
        threaded = RunnableLambda(lambda _: db.table("probe")[0]["where"]).batch([1, 2, 3])
        shared = len(db.table("pep_list"))
    after = db.table("probe")[0]["where"]

    checks = {
        "outside reads data/": outside == "data",
        "inside reads world_99": inside == "world_99",
        "worker threads read world_99": threaded == ["world_99"] * 3,
        "watchlists stay shared": shared > 0,
        "switch is undone after the block": after == "data",
    }
    for name, ok in checks.items():
        print(("PASS " if ok else "FAIL ") + name)
    sys.exit(0 if all(checks.values()) else 1)
finally:
    shutil.rmtree(folder)
    (db.DATA_DIR / "probe.jsonl").unlink()
    worlds = db.DATA_DIR / "worlds"
    if worlds.exists() and not any(worlds.iterdir()):
        worlds.rmdir()
