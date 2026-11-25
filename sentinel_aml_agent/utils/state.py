"""The run context every tool reads. The model never sees it and can't change it.

Extends the organiser starter's `MyAgentContext` (02_transaction_monitoring_agent/utils/state.py) with the rules-tier
thresholds, the precedent lifetime and `as_of`, the timestamp that counts as "now" for this run (PLAN.md section 1).
"""

from dataclasses import dataclass


@dataclass
class MyAgentContext:
    """Information passed in with every run. Tools can read it; the model can't."""

    user_id: str = ""                       # the customer this run is about; tools are scoped to it
    as_of: str = ""                         # the current transaction's timestamp: "now" for expiry and the network graph

    # Human review (kept from the starter)
    confidence_threshold: float = 0.7       # below this, a human decides
    checked_confidence: float = 0.5         # what a fired check lowers the confidence to
    grey_zone: tuple[int, int] = (30, 70)   # risk scores 30-69 are "unusual, but could be legitimate"

    # Rules tier (PLAN.md 5.1)
    rules_clear_below: int = 30             # rule score below this: auto-clear, no LLM call
    rules_escalate_at: int = 30             # rules-only baseline: escalate at or above this

    # Memory (PLAN.md 5.4)
    precedent_ttl_days: int = 365           # an analyst's precedent expires after this many days

    # Set by the stream runner for each investigation, so the decision record can carry them
    rule_score: int = 0
    rule_reasons: tuple[str, ...] = ()
    trace_run_id: str = ""                  # the LangSmith root run of this investigation (annotation queue, R12.4)
