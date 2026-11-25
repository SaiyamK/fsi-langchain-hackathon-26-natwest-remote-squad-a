"""Run Sentinel on chosen transactions of world 0 and print what happened: tier, tools, verdict, timing, SAR.

    uv run python scripts/run_case.py TX-000167            # one or more transaction IDs
    uv run python scripts/run_case.py TX-000167 --show-tools

Interrupts are answered from `data/reviewer_answers.jsonl` if there's a scripted answer, otherwise the agents'
own decision is accepted (as in the starter). Seed precedents are loaded first. Every run is traced to LangSmith.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from langchain_core.tracers.langchain import wait_for_all_tracers  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.store.memory import InMemoryStore  # noqa: E402

from agents import build_agent  # noqa: E402
from tools.precedents import load_seed_precedents  # noqa: E402
from utils import db  # noqa: E402
from utils.state import MyAgentContext  # noqa: E402
from utils.stream import process_stream  # noqa: E402


class ToolsOffered(BaseCallbackHandler):
    """Records the tool names offered to each model call (checks the harness profile's exclusions)."""

    def __init__(self):
        self.seen: list[list[str]] = []

    def on_chat_model_start(self, serialized, messages, **kwargs):
        tools = (kwargs.get("invocation_params") or {}).get("tools") or []
        self.seen.append(sorted(t.get("function", t).get("name", "?") for t in tools))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("transaction_ids", nargs="+")
    parser.add_argument("--show-tools", action="store_true")
    args = parser.parse_args()

    store = InMemoryStore()
    load_seed_precedents(store)
    agent = build_agent(checkpointer=InMemorySaver(), store=store)
    answers = {row["transaction_id"]: row for row in db.table("reviewer_answers")}
    txs = [db.get("transactions", transaction_id=t) for t in args.transaction_ids]
    offered = ToolsOffered()

    def on_event(e):
        rec = e["record"]
        print(f"\n=== {e['tx']['transaction_id']} {e['tx']['user_id']} £{e['tx']['amount']:,.0f} -> tier {e['tier']}")
        print(f"rule score {rec.get('rule_score')}: {rec.get('rule_reasons')}")
        if e["tier"] == "agents":
            inv = e["investigation"]
            print(f"time {inv['seconds']}s, model calls {inv['model_calls']}")
            print("tool calls:", [c["subagent"] or c["name"] for c in inv["tool_calls"]])
            if inv["human"]:
                print("HUMAN asked:", inv["human"]["question"]["why_review"], "->", inv["human"]["answer"])
            print("reply:", inv["reply"])
        keep = ("final_decision", "decided_by", "agent_decision", "risk_score", "confidence", "pattern", "hard_flags",
                "precedents_relied_on", "precedents_overridden", "precedents_dropped", "reason", "sar_id")
        print(json.dumps({k: rec.get(k) for k in keep}, indent=1, default=str))
        if e["tier"] == "agents" and e["investigation"]["sar"]:
            print("SAR:", json.dumps(e["investigation"]["sar"], indent=1)[:2500])

    from dataclasses import replace  # noqa: E402
    import utils.stream as stream  # noqa: E402

    original = stream.UsageCounter

    class Counter(original):
        def on_chat_model_start(self, serialized, messages, **kwargs):
            super().on_chat_model_start(serialized, messages, **kwargs)
            offered.on_chat_model_start(serialized, messages, **kwargs)

    stream.UsageCounter = Counter
    result = process_stream(agent, replace(MyAgentContext()), txs, reviewer_answers=answers, on_event=on_event)
    print("\ncounters:", json.dumps({k: v for k, v in result["counters"].items()}, default=str))
    if args.show_tools:
        print("tools offered per model call:")
        for names in offered.seen:
            print("  ", names)
    wait_for_all_tracers()


if __name__ == "__main__":
    main()
