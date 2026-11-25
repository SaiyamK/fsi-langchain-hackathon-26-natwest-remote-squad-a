"""Replay mode for the stage demo (PLAN.md 5.7, DEC-003).

    REPLAY=record  run live and save every model response to results/llm_cache.sqlite
    REPLAY=1       serve model responses from that file; anything not in it is called live and saved

The cache is keyed on the exact prompt and model settings, so a replay returns what the model really said in the
recorded run. `replay_banner()` says so on screen, with when the recording was made, how many calls were replayed
versus live, and a link to the recorded run's traces in LangSmith. Nothing is invented.
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from threading import Lock

from langchain_core.caches import BaseCache
from langchain_core.globals import set_llm_cache
from langchain_core.load import dumps, loads

from dotenv import load_dotenv

from utils import PROJECT_ROOT

load_dotenv(PROJECT_ROOT.parent / ".env")

CACHE_FILE = PROJECT_ROOT / "results" / "llm_cache.sqlite"
META_FILE = PROJECT_ROOT / "results" / "replay_meta.json"


class SqliteLLMCache(BaseCache):
    """A small SQLite cache of model responses, safe to use from several threads."""

    def __init__(self, path):
        path.parent.mkdir(exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)")
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _normalise(prompt: str) -> str:
        """Drop per-run message IDs (random UUIDs) from the serialised prompt; keep everything the model saw."""
        try:
            data = json.loads(prompt)
        except (json.JSONDecodeError, TypeError):
            return prompt

        def walk(x):
            if isinstance(x, dict):
                if "lc" in x and isinstance(x.get("kwargs"), dict):
                    for field in ("id", "usage_metadata", "response_metadata"):  # bookkeeping, not prompt content
                        x["kwargs"].pop(field, None)
                return {k: walk(v) for k, v in x.items()}
            if isinstance(x, list):
                return [walk(v) for v in x]
            return x

        return json.dumps(walk(data), sort_keys=True)

    @classmethod
    def _key(cls, prompt: str, llm_string: str) -> str:
        return hashlib.sha256((llm_string + "\x00" + cls._normalise(prompt)).encode()).hexdigest()

    def lookup(self, prompt, llm_string):
        if os.environ.get("REPLAY_DEBUG"):
            with open(CACHE_FILE.with_suffix(f".{mode()}.prompts.txt"), "a") as f:
                f.write(json.dumps({"llm": llm_string, "prompt": self._normalise(prompt)}) + "\n")
        with self._lock:
            row = self._db.execute("SELECT v FROM cache WHERE k = ?", (self._key(prompt, llm_string),)).fetchone()
            if row:
                self.hits += 1
                return loads(row[0])
            self.misses += 1
            return None

    def update(self, prompt, llm_string, return_val):
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)",
                             (self._key(prompt, llm_string), dumps(return_val)))
            self._db.commit()

    def clear(self, **kwargs):
        with self._lock:
            self._db.execute("DELETE FROM cache")
            self._db.commit()


_cache: SqliteLLMCache | None = None


def mode() -> str:
    return os.environ.get("REPLAY", "").strip().lower()


def enable() -> SqliteLLMCache | None:
    """Turn on recording or replay according to REPLAY. Live (no cache) when REPLAY is unset."""
    global _cache
    m = mode()
    if m not in ("record", "1", "true", "yes"):
        return None
    if m == "record" and CACHE_FILE.exists():
        CACHE_FILE.unlink()
    _cache = SqliteLLMCache(CACHE_FILE)
    set_llm_cache(_cache)
    if m == "record":
        META_FILE.write_text(json.dumps({"recorded_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                                         "project": os.environ.get("LANGSMITH_PROJECT"), "trace_run_ids": []}, indent=1))
    return _cache


def note_recorded_runs(run_ids: list[str]):
    """Remember which LangSmith runs the recording came from (shown in the banner)."""
    if mode() != "record" or not META_FILE.exists():
        return
    meta = json.loads(META_FILE.read_text())
    meta["trace_run_ids"] = sorted(set(meta["trace_run_ids"]) | {r for r in run_ids if r})
    META_FILE.write_text(json.dumps(meta, indent=1))


def replay_banner() -> str:
    m = mode()
    if m in ("1", "true", "yes"):
        meta = json.loads(META_FILE.read_text()) if META_FILE.exists() else {}
        counts = f"{_cache.hits} model calls replayed, {_cache.misses} called live" if _cache else ""
        return (f"REPLAY: model responses recorded from the live run at {meta.get('recorded_at', 'unknown time')} "
                f"(LangSmith project {meta.get('project')}, {len(meta.get('trace_run_ids', []))} recorded "
                f"investigations). {counts}. Rules, safeguards and memory still run for real.")
    if m == "record":
        return "LIVE, recording model responses for replay."
    return "LIVE: every model call goes to the LangSmith LLM Gateway now."
