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
    return {"available": True, "data": data}
