"""Results view (EX-13): the saved rules-only vs Sentinel comparison.

The eval team writes `sentinel_aml_agent/results/eval_summary.json` (PLAN.md section 7) and the UI only reads it,
never runs evals. The shape isn't final yet, so this passes it through and the client shows the metrics it finds.
Expected shape:

    {"created_at": "...", "dataset": "...", "n_transactions": 950,
     "experiments": {"rules-only": {"name": "...", "url": "...", "metrics": {"false_positive_rate": 0.4, ...}},
                     "sentinel":   {"name": "...", "url": "...", "metrics": {...}}},
     "headline": "optional one plain sentence, written from real results"}
"""

import json

from sentinel_api import AGENT_ROOT

SUMMARY_PATH = AGENT_ROOT / "results" / "eval_summary.json"


def load_results() -> dict:
    if not SUMMARY_PATH.exists():
        return {"available": False, "path": str(SUMMARY_PATH.relative_to(AGENT_ROOT.parent)),
                "message": "No eval results yet. The eval run (task 5.3) writes this file."}
    try:
        data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"available": False, "message": f"eval_summary.json is not valid JSON: {exc}"}
    return {"available": True, "data": normalise(data)}


def normalise(data: dict) -> dict:
    """Accept the eval team's `runs` shape ({"benchmark:test:sentinel": {"experiment", "dataset", "split", "scores"}})
    and present the held-out test split as rules-only vs Sentinel. The headline is computed from those numbers."""
    runs = data.get("runs")
    if not isinstance(runs, dict):
        return data
    split = "test" if any(k.startswith("benchmark:test:") for k in runs) else "dev"
    picked = {name: runs.get(f"benchmark:{split}:{name}") for name in ("rules-only", "sentinel")}
    experiments = {name: {"name": r.get("experiment", name), "metrics": r.get("scores", {})}
                   for name, r in picked.items() if r}
    out = {"created_at": data.get("updated_at"), "model": data.get("model"), "note": data.get("note"),
           "split": split, "experiments": experiments,
           "dataset": next((r.get("dataset") for r in picked.values() if r), None)}
    base, ours = (experiments.get("rules-only", {}).get("metrics", {}), experiments.get("sentinel", {}).get("metrics", {}))
    fp0, fp1 = base.get("false_positive_rate"), ours.get("false_positive_rate")
    r0, r1 = base.get("recall_planted"), ours.get("recall_planted")
    if isinstance(fp0, (int, float)) and isinstance(fp1, (int, float)) and fp0 > 0:
        cut = (fp0 - fp1) / fp0
        recall = ("with no loss of recall" if isinstance(r0, (int, float)) and isinstance(r1, (int, float)) and r1 >= r0
                  else f"with recall {r1:.0%} vs {r0:.0%}" if isinstance(r1, (int, float)) and isinstance(r0, (int, float)) else "")
        out["headline"] = f"On the held-out {split} split, Sentinel cut the false-positive rate by {cut:.0%} {recall}".strip() + "."
    return out
