"""Benchmark evaluators: detection, calibration, routing and efficiency (DEC-010 categories 1, 2, 3 and 7).

The first three are the organiser starter's evaluators, kept unchanged (R9.1). They compare `outputs["decisions"]`
with `reference_outputs["labels"]` ({transaction_id: analyst label}). The rest are new.

Detection metrics use the FINAL decision (after any human), because that's what reaches an analyst's queue.
"""

from statistics import median


def _decisions_by_id(outputs: dict) -> dict:
    return {decision["transaction_id"]: decision for decision in outputs["decisions"]}


#
# Starter evaluators (unchanged)
#
def decision_accuracy_eval(outputs: dict, reference_outputs: dict) -> float:
    """Share of transactions where the agent's own decision matches the analysts'."""
    decisions = _decisions_by_id(outputs)
    labels = reference_outputs["labels"]
    matches = [
        tx_id in decisions and decisions[tx_id]["agent_decision"] == label["decision"]
        for tx_id, label in labels.items()
    ]
    return sum(matches) / len(matches)


def score_alignment_eval(outputs: dict, reference_outputs: dict) -> float:
    """1 minus the average gap between the agent's and the analysts' risk scores, on a 0-1 scale."""
    decisions = _decisions_by_id(outputs)
    labels = reference_outputs["labels"]
    gaps = [
        abs(decisions[tx_id]["risk_score"] - label["risk_score"]) if tx_id in decisions else 100
        for tx_id, label in labels.items()
    ]
    return 1 - (sum(gaps) / len(gaps) / 100)


def review_routing_eval(outputs: dict, reference_outputs: dict) -> float:
    """Share of transactions where the agent asked a human exactly when analysts said it should."""
    decisions = _decisions_by_id(outputs)
    labels = reference_outputs["labels"]
    correct = [
        tx_id in decisions and (decisions[tx_id]["decided_by"] == "human") == label["ambiguous"]
        for tx_id, label in labels.items()
    ]
    return sum(correct) / len(correct)


#
# 1. Detection quality
#
def _final(outputs: dict, reference_outputs: dict):
    d = _decisions_by_id(outputs)
    for tx_id, label in reference_outputs["labels"].items():
        yield label, d.get(tx_id, {}).get("final_decision", "escalate")


def false_positive_rate(outputs: dict, reference_outputs: dict) -> dict:
    """Escalated, but labelled clear, divided by all labelled clear. Lower is better."""
    pairs = [(l, f) for l, f in _final(outputs, reference_outputs) if l["decision"] == "clear"]
    fp = sum(f == "escalate" for _, f in pairs)
    return {"key": "false_positive_rate", "score": fp / len(pairs) if pairs else None,
            "comment": f"{fp} false positives out of {len(pairs)} transactions labelled clear"}


def false_positives(outputs: dict, reference_outputs: dict) -> dict:
    """The number of alerts an analyst would have to clear for nothing."""
    fp = sum(l["decision"] == "clear" and f == "escalate" for l, f in _final(outputs, reference_outputs))
    return {"key": "false_positives", "score": fp}


def alert_precision(outputs: dict, reference_outputs: dict) -> dict:
    """Of the alerts raised, the share that analysts would also raise."""
    raised = [(l, f) for l, f in _final(outputs, reference_outputs) if f == "escalate"]
    tp = sum(l["decision"] == "escalate" for l, _ in raised)
    return {"key": "alert_precision", "score": tp / len(raised) if raised else None,
            "comment": f"{tp} of {len(raised)} alerts were real"}


def recall_planted(outputs: dict, reference_outputs: dict) -> dict:
    """Of the planted laundering alerts, the share that were escalated."""
    planted = [(l, f) for l, f in _final(outputs, reference_outputs) if l["decision"] == "escalate" and l["pattern"] != "none"]
    caught = sum(f == "escalate" for _, f in planted)
    return {"key": "recall_planted", "score": caught / len(planted) if planted else None,
            "comment": f"caught {caught} of {len(planted)} planted alerts"}


def recall_by_pattern(outputs: dict, reference_outputs: dict) -> dict:
    """Recall for each typology separately."""
    per: dict[str, list[bool]] = {}
    for l, f in _final(outputs, reference_outputs):
        if l["decision"] == "escalate" and l["pattern"] != "none":
            per.setdefault(l["pattern"], []).append(f == "escalate")
    return {"results": [{"key": f"recall_{p}", "score": sum(v) / len(v)} for p, v in sorted(per.items())]}


#
# 3. Human-in-the-loop routing (beyond the starter's review_routing)
#
def human_review_rate(outputs: dict) -> dict:
    d = outputs["decisions"]
    humans = sum(x["decided_by"] == "human" for x in d)
    return {"key": "human_review_rate", "score": humans / len(d) if d else 0.0, "comment": f"{humans} human reviews"}


def reviews_by_month(outputs: dict, reference_outputs: dict) -> dict:
    """Human reviews in month 1 and month 2. Month 2 should fall as precedents build up (DEC-005: by design of the data)."""
    labels = reference_outputs["labels"]
    counts = {1: 0, 2: 0}
    for x in outputs["decisions"]:
        m = labels.get(x["transaction_id"], {}).get("month")
        if x["decided_by"] == "human" and m in counts:
            counts[m] += 1
    return {"results": [{"key": "reviews_month1", "score": counts[1]}, {"key": "reviews_month2", "score": counts[2]}]}


#
# 7. Efficiency
#
def efficiency(outputs: dict) -> dict:
    c = outputs.get("counters", {})
    n = max(c.get("investigations", 0), 1)
    secs = c.get("seconds") or [0]
    return {"results": [
        {"key": "llm_share", "score": c.get("llm_share", 0.0)},
        {"key": "investigations", "score": c.get("investigations", 0)},
        {"key": "model_calls_per_investigation", "score": round(c.get("model_calls", 0) / n, 2)},
        {"key": "tokens_per_investigation", "score": round((c.get("input_tokens", 0) + c.get("output_tokens", 0)) / n)},
        {"key": "p50_seconds_per_investigation", "score": round(median(secs), 1)},
    ]}


BENCHMARK_EVALUATORS = [decision_accuracy_eval, score_alignment_eval, review_routing_eval, false_positive_rate,
                        false_positives, alert_precision, recall_planted, recall_by_pattern, human_review_rate,
                        reviews_by_month, efficiency]
