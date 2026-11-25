"""Shared data shapes (PLAN.md section 4).

The Pydantic models are the sub-agents' structured outputs (`response_format`, as in the 03 starter's
`SectionSummary`). The TypedDicts describe what we store: precedents and decision records.
"""

from typing import Literal, TypedDict

from pydantic import BaseModel, Field

Pattern = Literal["none", "structuring", "anomalous_credit", "round_tripping", "mule_fan_in"]
Decision = Literal["clear", "escalate"]

DISCLAIMER = "Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only."


#
# Sub-agent outputs
#
class PatternFindings(BaseModel):
    """What the pattern analyst found in one customer's recent activity."""

    pattern: Pattern = Field(description="The typology that best fits, or 'none'")
    evidence: list[str] = Field(description="Facts that support it, each citing transaction IDs and amounts")
    aggregate_amount: float = Field(description="Total amount of the transactions involved, in GBP")
    window_hours: float = Field(description="Time span of those transactions, in hours")
    risk_score: int = Field(ge=0, le=100, description="0 = clearly fine, 100 = clearly suspicious")
    confidence: float = Field(ge=0, le=1, description="How sure you are, 0 to 1")


class KycFindings(BaseModel):
    """What the KYC & precedent agent found about the customer."""

    risk_rating: str = Field(description="The customer's KYC risk rating")
    screening_hits: list[str] = Field(description="Sanctions or PEP matches, one line each; empty if none")
    precedents_applicable: list[str] = Field(description="Keys of valid, in-scope precedents")
    precedents_expired: list[str] = Field(description="Keys of precedents that exist but have expired or don't match scope")
    hard_flags: list[str] = Field(description="Sanctions hit, PEP status or confirmed ring membership; empty if none")
    risk_score: int = Field(ge=0, le=100, description="Customer-level risk, 0 to 100")


class NetworkFindings(BaseModel):
    """What the fund-flow agent found across accounts."""

    pattern: Pattern = Field(description="'mule_fan_in', 'round_tripping' or 'none'")
    accounts: list[str] = Field(description="Account IDs involved")
    collector_account: str | None = Field(description="The account money is funnelled to, if any")
    pass_through_ratio: float = Field(description="Share of incoming money sent straight on, 0 to 1")
    ring_confirmed: bool = Field(description="True only if the network tool reports a confirmed ring")


class SarDraft(BaseModel):
    """A Suspicious Activity Report draft, built only from evidence already gathered."""

    subject: str = Field(description="Customer name and ID")
    pattern: Pattern
    timeline: list[str] = Field(description="Dated events, oldest first, each citing a transaction ID")
    evidence: list[str] = Field(description="Facts copied from the findings, each citing a transaction ID")
    narrative: str = Field(description="Three to six sentences on why this is suspicious")
    precedents_cited_or_overridden: list[str] = Field(description="Precedents considered and what happened to them")
    disclaimer: str = Field(default=DISCLAIMER, description=f"Always exactly: {DISCLAIMER}")


#
# Stored records
#
class Precedent(TypedDict):
    """An analyst's past decision, stored in ("precedents", user_id) under f"{counterparty_id}:{pattern}"."""

    user_id: str
    counterparty_id: str
    pattern: str
    decision: str
    note: str
    analyst: str
    created_at: str   # ISO date
    expires_at: str   # ISO date


class DecisionRecord(TypedDict, total=False):
    """One decision, stored in ("decisions", user_id) under the transaction ID. A superset of the starter's record."""

    transaction_id: str
    risk_score: int
    model_confidence: float | None
    confidence: float | None
    confidence_checks: list[str]
    agent_decision: str | None
    final_decision: str
    decided_by: Literal["rules", "agent", "human"]
    reason: str
    pattern: str
    hard_flags: list[str]
    precedents_cited: list[str]
    precedents_overridden: list[dict]
    rule_score: int
    rule_reasons: list[str]
    sar_id: str | None
    trace_run_id: str | None
