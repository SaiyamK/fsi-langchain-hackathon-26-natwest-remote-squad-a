"""The analyst's review desk in LangSmith: an annotation queue (task 5.7, PLAN.md 7.1, R12).

Extends the organiser starter's Module 3 code (feedback configs, a queue with rubric items, adding runs, reading
feedback back). Runs come from a saved Sentinel run, by default `results/scenario_run.json` written by
`scripts/check_scenarios.py --save`, whose investigations are root runs in the tracing project.

    uv run python scripts/annotation_queue.py            # create the queue, add runs
    uv run python scripts/annotation_queue.py --collect  # read reviews, write results/annotation_summary.json
    uv run python scripts/annotation_queue.py --simulate # ONLY if no person can review: write reviews from the
                                                         # analyst labels, marked simulated (DEC-003)

What goes in: every human-decided case, plus a seeded 10% sample (at least one) of agent-only decisions.
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langsmith import Client  # noqa: E402

from utils import PROJECT_ROOT, db  # noqa: E402
from utils.attendee import ATTENDEE  # noqa: E402

QUEUE_NAME = f"sentinel-analyst-review-{ATTENDEE}"
RUN_FILE = PROJECT_ROOT / "results" / "scenario_run.json"
SUMMARY = PROJECT_ROOT / "results" / "annotation_summary.json"
SPOT_CHECK = 0.10
DECISIONS = {0: "clear", 1: "escalate"}


def selected_cases(run_file: Path) -> list[dict]:
    rows = [r for r in json.loads(run_file.read_text())["results"] if r.get("trace_run_id")]
    humans = [r for r in rows if r["decided_by"] == "human"]
    agent_only = sorted((r for r in rows if r["decided_by"] == "agent"), key=lambda r: r["transaction_id"])
    k = max(1, round(SPOT_CHECK * len(agent_only))) if agent_only else 0
    sample = random.Random(7).sample(agent_only, k)
    return [r | {"why_queued": "human-decided"} for r in humans] + [r | {"why_queued": "spot-check"} for r in sample]


def ensure_queue(client: Client):
    for key, cfg in {
        "correct_decision": {"type": "categorical", "categories": [{"value": 0, "label": "clear"},
                                                                   {"value": 1, "label": "escalate"}]},
        "evidence_sufficient": {"type": "categorical", "categories": [{"value": 0, "label": "no"},
                                                                      {"value": 1, "label": "yes"}]},
    }.items():
        try:
            client.create_feedback_config(key, feedback_config=cfg)
        except Exception:
            pass  # already exists in this workspace
    existing = list(client.list_annotation_queues(name=QUEUE_NAME))
    if existing:
        return existing[0]
    return client.create_annotation_queue(
        name=QUEUE_NAME,
        description="Sentinel AML: cases an analyst decided, plus a spot check of the agents' own decisions. Synthetic data.",
        rubric_instructions=(
            "Open the record_decision tool call to see the verdict, the evidence and any precedents. Then answer: "
            "what would YOU decide (correct_decision), and did the investigation gather enough evidence to decide "
            "(evidence_sufficient)? Use the comment to say why. Synthetic data; not regulatory advice."
        ),
        rubric_items=[
            {"feedback_key": "correct_decision", "description": "Your decision for this transaction.", "is_required": True},
            {"feedback_key": "evidence_sufficient", "description": "Was the evidence enough to decide?", "is_required": True},
        ],
    )


def add(client: Client, run_file: Path):
    queue = ensure_queue(client)
    cases = selected_cases(run_file)
    client.add_runs_to_annotation_queue(queue.id, run_ids=[c["trace_run_id"] for c in cases])
    (PROJECT_ROOT / "results" / "annotation_cases.json").write_text(json.dumps(cases, indent=1, default=str))
    print(f"Queue '{queue.name}': added {len(cases)} runs "
          f"({sum(c['why_queued'] == 'human-decided' for c in cases)} human-decided, "
          f"{sum(c['why_queued'] == 'spot-check' for c in cases)} spot-check).")


def simulate(client: Client):
    cases = json.loads((PROJECT_ROOT / "results" / "annotation_cases.json").read_text())
    labels = {l["transaction_id"]: l for l in db.table("analyst_labels")}
    for c in cases:
        label = labels[c["transaction_id"]]["decision"]
        client.create_feedback(c["trace_run_id"], key="correct_decision", score=1 if label == "escalate" else 0,
                               value=label, comment="SIMULATED from analyst_labels.jsonl")
        client.create_feedback(c["trace_run_id"], key="evidence_sufficient", score=1, value="yes",
                               comment="SIMULATED")
    print(f"Wrote simulated reviews for {len(cases)} runs (marked SIMULATED).")


def collect(client: Client):
    cases = {c["trace_run_id"]: c for c in json.loads((PROJECT_ROOT / "results" / "annotation_cases.json").read_text())}
    reviews: dict[str, dict] = {}
    for fb in client.list_feedback(run_ids=list(cases), feedback_key=["correct_decision", "evidence_sufficient"]):
        r = reviews.setdefault(str(fb.run_id), {})
        value = fb.value if isinstance(fb.value, str) else DECISIONS.get(int(fb.score)) if fb.score is not None else None
        if fb.key == "evidence_sufficient":
            value = fb.value if isinstance(fb.value, str) else ("yes" if fb.score else "no")
        r[fb.key] = value
        r["simulated"] = r.get("simulated", False) or "SIMULATED" in (fb.comment or "")
    reviewed = [(cases[rid], r) for rid, r in reviews.items() if "correct_decision" in r]
    agree = [c["final_decision"] == r["correct_decision"] for c, r in reviewed]
    summary = {
        "queue": QUEUE_NAME,
        "queued": len(cases),
        "reviewed": len(reviewed),
        "agreement_rate": round(sum(agree) / len(agree), 3) if agree else None,
        "evidence_sufficient_rate": round(sum(r.get("evidence_sufficient") == "yes" for _, r in reviewed) / len(reviewed), 3)
        if reviewed else None,
        "disagreements": [{"transaction_id": c["transaction_id"], "sentinel": c["final_decision"],
                           "analyst": r["correct_decision"], "trace_run_id": c["trace_run_id"]}
                          for (c, r), ok in zip(reviewed, agree) if not ok],
        "simulated": any(r.get("simulated") for _, r in reviewed),
    }
    SUMMARY.write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--from", dest="run_file", default=str(RUN_FILE))
    args = parser.parse_args()
    client = Client()
    if args.simulate:
        simulate(client)
    elif args.collect:
        collect(client)
    else:
        add(client, Path(args.run_file))


if __name__ == "__main__":
    main()
