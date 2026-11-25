"""Check replay mode (task 6.1): one investigation, run with whatever REPLAY is set to. Prints hits, misses, time.

    REPLAY=record uv run python scripts/check_replay.py   # live, fills results/llm_cache.sqlite
    REPLAY=1      uv run python scripts/check_replay.py   # should be all hits, no live calls
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import replay  # noqa: E402

cache = replay.enable()

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.store.memory import InMemoryStore  # noqa: E402

from agents import build_agent  # noqa: E402
from tools.precedents import load_seed_precedents  # noqa: E402
from utils import db  # noqa: E402
from utils.state import MyAgentContext  # noqa: E402
from utils.stream import process_stream  # noqa: E402

store = InMemoryStore()
load_seed_precedents(store)
agent = build_agent(checkpointer=InMemorySaver(), store=store)
tx = db.get("transactions", transaction_id="TX-000167")
run = process_stream(agent, MyAgentContext(), [tx])
replay.note_recorded_runs([i["trace_run_id"] for i in run["investigations"]])
d = run["decisions"][0]
print(f"decision {d['final_decision']} by {d['decided_by']} · {run['counters']['seconds']}s · "
      f"model calls {run['counters']['model_calls']} · cache hits {cache.hits if cache else '-'} "
      f"misses {cache.misses if cache else '-'}")
print(replay.replay_banner())
