"""LangSmith datasets and experiments: rules-only vs Sentinel (task 5.3, PLAN.md section 7, DEC-010).

Two datasets, linked to the agent's "Agent" tag as in the organiser starter:
- `<LANGSMITH_PROJECT>-sentinel-benchmark`: one example per eval world. World 1 has split "dev", world 2 "test".
  Headline numbers (detection, calibration, routing, efficiency) are reported on "test" only (R9.5).
- `<LANGSMITH_PROJECT>-sentinel-scenarios`: world 0's scripted scenarios, one example per scenario. Behaviour and
  safeguard checks (memory, trajectory, SAR, network scope).

Experiments: `rules-only` (tier 1 alone, including the network check, DEC-013) and `sentinel` (tier 1 + agents +
scripted human answers). Results are averaged and saved to `results/eval_summary.json`, which the notebook loads.

Run from sentinel_aml_agent/:

    uv run python scripts/run_experiments.py --datasets-only       # create or update the datasets
    uv run python scripts/run_experiments.py --split dev           # tuning run on world 1 (not reported)
    uv run python scripts/run_experiments.py                       # the reported run: test split + scenarios
    uv run python scripts/run_experiments.py --recreate            # rebuild the datasets first
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.store.memory import InMemoryStore  # noqa: E402
from langsmith import Client, evaluate  # noqa: E402

from agents import build_agent  # noqa: E402
from evals.behaviour_evals import BEHAVIOUR_EVALUATORS, memory_safeguards  # noqa: E402
from evals.scoring_evals import BENCHMARK_EVALUATORS  # noqa: E402
from rules.scorer import baseline_decision, score_all  # noqa: E402
from scripts.check_scenarios import scenarios  # noqa: E402
from tools.precedents import load_seed_precedents  # noqa: E402
from utils import PROJECT_ROOT, db  # noqa: E402
from utils.models import model  # noqa: E402
from utils.state import MyAgentContext  # noqa: E402
from utils.stream import global_stream, process_stream  # noqa: E402

if not os.environ.get("LANGSMITH_PROJECT"):
    raise SystemExit("LANGSMITH_PROJECT is not set: copy .env.example to .env in the repo root and fill it in")
PROJECT = os.environ["LANGSMITH_PROJECT"]
BENCHMARK = f"{PROJECT}-sentinel-benchmark"
SCENARIOS = f"{PROJECT}-sentinel-scenarios"
SUMMARY = PROJECT_ROOT / "results" / "eval_summary.json"


#
# Datasets
#
def _get_agent_tag(client: Client, agent_name: str) -> dict:
    """The workspace's "Agent" tag value for this project (from the starter); exists once the agent is traced."""
    response = requests.get(f"{client.api_url}/api/v1/workspaces/current/tags",
                            headers={"X-API-Key": client.api_key or ""}, timeout=30)
    response.raise_for_status()
    for tag in response.json():
        if tag["key"] == "Agent":
            for value in tag["values"]:
                if value["value"] == agent_name:
                    return value
    raise SystemExit(f"No 'Agent' tag value named '{agent_name}'. Run the agent once so it's traced, then retry.")


def _labels(world: int, ids: list[str] | None = None) -> dict:
    with db.use_world(world):
        rows = {l["transaction_id"]: l for l in db.table("analyst_labels")}
    return rows if ids is None else {i: rows[i] for i in ids}


def benchmark_examples() -> list[dict]:
    return [{"inputs": {"world": w}, "outputs": {"labels": _labels(w)}, "split": split,
             "metadata": {"world": w}} for w, split in ((1, "dev"), (2, "test"))]


def scenario_examples() -> list[dict]:
    out = []
    for name, rows in scenarios(with_mule=True).items():
        ids = [t["transaction_id"] for t in rows]
        out.append({"inputs": {"world": 0, "scenario": name, "transaction_ids": ids},
                    "outputs": {"labels": _labels(0, ids)}, "metadata": {"scenario": name}})
    return out


def ensure_dataset(client: Client, name: str, description: str, examples: list[dict], recreate: bool, tag: dict):
    if client.has_dataset(dataset_name=name):
        if not recreate:
            print(f"Using existing dataset '{name}' (pass --recreate to rebuild it)")
            return client.read_dataset(dataset_name=name)
        client.delete_dataset(dataset_name=name)
    dataset = client.create_dataset(name, description=description, tag_value_ids=[tag["id"]])
    client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"Created dataset '{name}' with {len(examples)} examples")
    return dataset


#
# Targets
#
def _slim(d: dict) -> dict:
    keep = ("transaction_id", "risk_score", "agent_decision", "final_decision", "decided_by", "pattern", "hard_flags",
            "precedents_relied_on", "precedents_overridden", "precedents_dropped", "confidence", "sar_id", "trace_run_id")
    return {k: d.get(k) for k in keep}


def _transactions(inputs: dict) -> list[dict]:
    txs = global_stream()
    if inputs.get("transaction_ids"):
        wanted = set(inputs["transaction_ids"])
        txs = [t for t in txs if t["transaction_id"] in wanted]
    return txs


def rules_only_target(inputs: dict) -> dict:
    """Tier 1 alone, including the network check. No LLM."""
    with db.use_world(inputs["world"]):
        txs = _transactions(inputs)
        profiles = {p["user_id"]: p for p in db.table("customer_profiles")}
        # Score the whole world, then pick: each transaction needs its full history, not just the selected ones
        scores = score_all(global_stream(), profiles)
    decisions = [{"transaction_id": t["transaction_id"], "risk_score": scores[t["transaction_id"]][0],
                  "agent_decision": baseline_decision(scores[t["transaction_id"]][0]),
                  "final_decision": baseline_decision(scores[t["transaction_id"]][0]), "decided_by": "rules",
                  "pattern": "none", "hard_flags": [], "precedents_relied_on": [], "precedents_overridden": []}
                 for t in txs]
    return {"world": inputs["world"], "decisions": decisions, "investigations": [], "network_audit": [],
            "counters": {"transactions": len(txs), "investigations": 0, "llm_share": 0.0, "model_calls": 0,
                         "input_tokens": 0, "output_tokens": 0, "seconds": []}}


def sentinel_target(inputs: dict) -> dict:
    """Tier 1 + agents + scripted human answers, on a fresh agent with fresh memory."""
    with db.use_world(inputs["world"]):
        store = InMemoryStore()
        load_seed_precedents(store)
        agent = build_agent(checkpointer=InMemorySaver(), store=store)
        answers = {a["transaction_id"]: a for a in db.table("reviewer_answers")}
        run = process_stream(agent, MyAgentContext(), _transactions(inputs), reviewer_answers=answers,
                             parallel_customers=True, max_workers=4, extra_tags=["eval"])
        audit = [i.value for i in store.search(("network_audit",), limit=1000)]
    investigations = [{k: i.get(k) for k in ("transaction_id", "seconds", "model_calls", "tokens", "tool_calls",
                                             "rule_reasons", "as_of", "final_decision", "decided_by", "sar",
                                             "trace_run_id")} for i in run["investigations"]]
    return {"world": inputs["world"], "decisions": [_slim(d) for d in run["decisions"]],
            "investigations": investigations, "network_audit": audit, "counters": run["counters"]}


#
# Experiments
#
def average(results) -> dict:
    scores: dict[str, list[float]] = {}
    for row in results:
        for r in row["evaluation_results"]["results"]:
            if r.score is not None:
                scores.setdefault(r.key, []).append(float(r.score))
    return {k: round(sum(v) / len(v), 4) for k, v in sorted(scores.items())}


def run(client: Client, dataset: str, split: str | None, prefix: str, target, evaluators) -> dict:
    data = client.list_examples(dataset_name=dataset, splits=[split]) if split else dataset
    results = evaluate(target, data=data, evaluators=evaluators, experiment_prefix=prefix, max_concurrency=2,
                       metadata={"model": model, "split": split or "all", "dataset": dataset})
    scores = average(results)
    print(f"{prefix} on {dataset} [{split or 'all'}]: {json.dumps(scores)}")
    return {"experiment": results.experiment_name, "dataset": dataset, "split": split or "all", "scores": scores}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets-only", action="store_true")
    parser.add_argument("--recreate", action="store_true")
    parser.add_argument("--split", choices=["dev", "test"], default="test", help="benchmark split (default: test)")
    parser.add_argument("--skip-scenarios", action="store_true")
    parser.add_argument("--scenarios-only", action="store_true", help="skip the benchmark experiments")
    args = parser.parse_args()

    client = Client()
    tag = _get_agent_tag(client, PROJECT)
    ensure_dataset(client, BENCHMARK, "Sentinel benchmark: one example per synthetic world (world 1 dev, world 2 test).",
                   benchmark_examples(), args.recreate, tag)
    ensure_dataset(client, SCENARIOS, "Sentinel scenarios: world 0 demo cases for safeguard and behaviour checks.",
                   scenario_examples(), args.recreate, tag)
    if args.datasets_only:
        return

    experiments = [] if args.scenarios_only else [
        run(client, BENCHMARK, args.split, f"rules-only-{args.split}", rules_only_target, BENCHMARK_EVALUATORS),
        run(client, BENCHMARK, args.split, f"sentinel-{args.split}", sentinel_target, BENCHMARK_EVALUATORS),
    ]
    if not args.skip_scenarios:
        experiments += [
            run(client, SCENARIOS, None, "rules-only-scenarios", rules_only_target, BENCHMARK_EVALUATORS + [memory_safeguards]),
            run(client, SCENARIOS, None, "sentinel-scenarios", sentinel_target, BENCHMARK_EVALUATORS + BEHAVIOUR_EVALUATORS),
        ]

    summary = json.loads(SUMMARY.read_text()) if SUMMARY.exists() else {}
    summary.setdefault("runs", {})
    for e in experiments:
        kind = "benchmark" if e["dataset"] == BENCHMARK else "scenarios"
        system = "sentinel" if e["experiment"].startswith("sentinel") else "rules-only"
        summary["runs"][f"{kind}:{e['split']}:{system}"] = e
    summary["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary["model"] = model
    summary["note"] = ("Synthetic benchmark generated by data/generate.py. Rules tuned on dev only; headline numbers "
                       "are from the test split. Human answers in the 'sentinel' runs are scripted from "
                       "reviewer_answers.jsonl.")
    SUMMARY.parent.mkdir(exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=1))
    print(f"saved {SUMMARY}")


if __name__ == "__main__":
    main()
