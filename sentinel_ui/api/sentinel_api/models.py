"""The API contract. Mirrored in `sentinel_ui/web/src/types/api.ts`; change both together."""

from typing import Literal

from pydantic import BaseModel, Field

TxStatus = Literal["cleared_rules", "under_review", "cleared", "flagged", "needs_analyst"]
CaseStatus = Literal["new", "awaiting_analyst", "cleared", "escalated"]
Role = Literal["source", "mule", "hub", "sink", "subject", "other"]
FlagState = Literal["fired", "not_fired", "no_data"]
StepState = Literal["waiting", "working", "done"]
Mode = Literal["live", "record", "replay", "offline"]


class Party(BaseModel):
    account: str | None
    name: str


class MemoryCard(BaseModel):
    kind: Literal["cited", "overridden", "saved"]
    key: str
    note: str = ""
    analyst: str = ""
    created_at: str | None = None
    expires_at: str | None = None
    reason: str = ""
    scope: str = ""


class TxRow(BaseModel):
    transaction_id: str
    user_id: str
    account_id: str
    customer_name: str
    timestamp: str
    direction: Literal["in", "out"]
    txn_type: str
    amount: float
    currency: str
    country: str | None = None
    branch: str | None = None
    sender: Party
    receiver: Party
    rule_score: int
    rule_reasons: list[str]
    baseline: Literal["clear", "escalate"]
    status: TxStatus
    pattern: str | None = None
    case_id: str | None = None
    reason: str | None = None
    decided_by: Literal["rules", "agent", "human"] | None = None
    final_decision: Literal["clear", "escalate"] | None = None
    confidence: float | None = None
    memory: list[MemoryCard] = Field(default_factory=list)
    sar_id: str | None = None
    trace_run_id: str | None = None
    replayed: bool = False
    seq: int = 0


class ShapeNode(BaseModel):
    id: str
    role: Role


class CaseSummary(BaseModel):
    case_id: str
    kind: Literal["network", "single"]
    pattern: str
    layout: Literal["chain", "fan_in", "fan_out"]
    lead_account: str
    lead_name: str
    accounts: int
    transaction_ids: list[str]
    flagged_transaction_ids: list[str]
    related_transaction_ids: list[str]
    total_amount: float
    first_ts: str
    last_ts: str
    verdict: Literal["clear", "escalate"] | None
    confidence: float | None
    why: str
    status: CaseStatus
    severity: int
    shape_nodes: list[ShapeNode]
    shape_edges: list[tuple[str, str]]
    updated_seq: int = 0


class Step(BaseModel):
    key: str
    label: str
    state: StepState
    finding: str | None = None
    tools: list[str] = Field(default_factory=list)


class Activity(BaseModel):
    transaction_id: str
    customer_name: str
    amount: float
    steps: list[Step]
    verdict: str | None = None
    confidence: float | None = None
    route: Literal["auto_cleared", "escalated", "sent_to_analyst"] | None = None
    route_reason: str | None = None
    memory: list[MemoryCard] = Field(default_factory=list)
    done: bool = False
    replayed: bool = False
    seconds: float | None = None
    trace_run_id: str | None = None


class Alert(BaseModel):
    transaction_id: str
    case_id: str | None
    customer_name: str
    amount: float
    currency: str
    pattern: str
    question: str
    leaning: str
    main_reason: str
    why_review: list[str]
    hard_flags: list[str]


class Counters(BaseModel):
    received: int = 0
    total: int = 0
    cleared_rules: int = 0
    under_review: int = 0
    cleared: int = 0
    flagged: int = 0
    needs_analyst: int = 0
    investigations: int = 0
    model_calls: int = 0
    tokens: int = 0
    rules_alerts: int = 0
    sentinel_alerts: int = 0
    analyst_touches: int = 0
    false_positives_avoided: int = 0
    minutes_per_alert: int = 20
    analyst_hours_saved: float = 0.0
    avg_tokens_per_investigation: float = 0.0
    tokens_if_all_to_agents: int = 0


class ReplayInfo(BaseModel):
    recorded_at: str
    model: str | None = None
    investigations: int


class SessionInfo(BaseModel):
    mode: Mode
    state: Literal["idle", "running", "paused", "finished"]
    clock: str | None
    speed: float
    replay: ReplayInfo | None = None
    live_transactions: list[str] = Field(default_factory=list)
    agents_available: bool
    model: str | None = None


class Snapshot(BaseModel):
    session: SessionInfo
    transactions: list[TxRow]
    cases: list[CaseSummary]
    counters: Counters
    alerts: list[Alert]
    activity: list[Activity]


#
# Case detail
#
class Transfer(BaseModel):
    transaction_id: str
    timestamp: str
    amount: float
    currency: str
    txn_type: str


class GraphNode(BaseModel):
    id: str
    label: str
    role: Role
    external: bool
    hard_flags: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    amount: float
    count: int
    transfers: list[Transfer]


class Metric(BaseModel):
    label: str
    value: str
    hint: str | None = None


class RedFlag(BaseModel):
    key: str
    label: str
    applies_to: list[str]
    applicable: bool
    state: FlagState
    evidence: str


class TimelineItem(BaseModel):
    transaction_id: str
    timestamp: str
    source: str
    target: str
    amount: float
    edge_id: str


class Moment(BaseModel):
    timestamp: str
    label: str
    kind: Literal["first_in", "peak", "cash_out", "flagged"]


class BalancePoint(BaseModel):
    timestamp: str
    balance: float


class AuditEntry(BaseModel):
    at: str
    kind: str
    detail: str


class CaseDetail(BaseModel):
    summary: CaseSummary
    finding: str
    as_of: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    metrics: list[Metric]
    red_flags: list[RedFlag]
    thresholds: dict[str, str]
    timeline: list[TimelineItem]
    moments: list[Moment]
    balances: dict[str, list[BalancePoint]]
    decisions: list[dict]
    activity: list[Activity]
    alerts: list[Alert]
    audit: list[AuditEntry]
    network_audit: list[dict]
    sar_ids: list[str]


class AccountDetail(BaseModel):
    account_id: str
    name: str
    external: bool
    customer_type: str | None = None
    occupation: str | None = None
    bank: str
    account_opened: str | None = None
    account_age_days: int | None = None
    risk_rating: str | None = None
    pep: bool | None = None
    screening: list[str]
    hard_flags: list[str]
    expected_monthly_credits: float | None = None
    expected_monthly_cash: float | None = None
    money_in: float
    money_out: float
    counterparties: int
    precedents: list[MemoryCard]
    transactions: list[Transfer]


class DecisionIn(BaseModel):
    decision: Literal["clear", "escalate"]
    note: str = Field(min_length=1, description="Required (FR-9.1)")


class SpeedIn(BaseModel):
    tx_per_second: float = Field(gt=0, le=200)


class FastForwardIn(BaseModel):
    days: int = Field(gt=0, le=730)
