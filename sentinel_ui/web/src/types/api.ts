// Mirrors sentinel_ui/api/sentinel_api/models.py. Change both together.

export type TxStatus = "cleared_rules" | "under_review" | "cleared" | "flagged" | "needs_analyst";
export type CaseStatus = "new" | "awaiting_analyst" | "cleared" | "escalated";
export type Role = "source" | "mule" | "hub" | "sink" | "subject" | "other";
export type FlagState = "fired" | "not_fired" | "no_data";
export type StepState = "waiting" | "working" | "done";
export type Mode = "live" | "record" | "replay" | "offline";
export type Decision = "clear" | "escalate";

export interface Party {
  account: string | null;
  name: string;
}

export interface MemoryCard {
  kind: "cited" | "overridden" | "saved";
  key: string;
  note: string;
  analyst: string;
  created_at: string | null;
  expires_at: string | null;
  reason: string;
  scope: string;
}

export interface TxRow {
  transaction_id: string;
  user_id: string;
  account_id: string;
  customer_name: string;
  timestamp: string;
  direction: "in" | "out";
  txn_type: string;
  amount: number;
  currency: string;
  country: string | null;
  branch: string | null;
  sender: Party;
  receiver: Party;
  rule_score: number;
  rule_reasons: string[];
  baseline: Decision;
  status: TxStatus;
  pattern: string | null;
  case_id: string | null;
  reason: string | null;
  decided_by: "rules" | "agent" | "human" | null;
  final_decision: Decision | null;
  confidence: number | null;
  memory: MemoryCard[];
  sar_id: string | null;
  trace_run_id: string | null;
  replayed: boolean;
  seq: number;
}

export interface ShapeNode {
  id: string;
  role: Role;
}

export interface CaseSummary {
  case_id: string;
  kind: "network" | "single";
  pattern: string;
  layout: "chain" | "fan_in" | "fan_out";
  lead_account: string;
  lead_name: string;
  accounts: number;
  transaction_ids: string[];
  flagged_transaction_ids: string[];
  related_transaction_ids: string[];
  total_amount: number;
  first_ts: string;
  last_ts: string;
  verdict: Decision | null;
  confidence: number | null;
  why: string;
  status: CaseStatus;
  severity: number;
  shape_nodes: ShapeNode[];
  shape_edges: [string, string][];
  updated_seq: number;
}

export interface Step {
  key: string;
  label: string;
  state: StepState;
  finding: string | null;
  tools: string[];
}

export interface Activity {
  transaction_id: string;
  customer_name: string;
  amount: number;
  steps: Step[];
  verdict: string | null;
  confidence: number | null;
  route: "auto_cleared" | "escalated" | "sent_to_analyst" | null;
  route_reason: string | null;
  memory: MemoryCard[];
  done: boolean;
  replayed: boolean;
  seconds: number | null;
  trace_run_id: string | null;
}

export interface Alert {
  transaction_id: string;
  case_id: string | null;
  customer_name: string;
  amount: number;
  currency: string;
  pattern: string;
  question: string;
  leaning: string;
  main_reason: string;
  why_review: string[];
  hard_flags: string[];
}

export interface Counters {
  received: number;
  total: number;
  cleared_rules: number;
  under_review: number;
  cleared: number;
  flagged: number;
  needs_analyst: number;
  investigations: number;
  model_calls: number;
  tokens: number;
  rules_alerts: number;
  sentinel_alerts: number;
  analyst_touches: number;
  false_positives_avoided: number;
  minutes_per_alert: number;
  analyst_hours_saved: number;
  avg_tokens_per_investigation: number;
  tokens_if_all_to_agents: number;
}

export interface SessionInfo {
  mode: Mode;
  state: "idle" | "running" | "paused" | "finished";
  clock: string | null;
  speed: number;
  replay: { recorded_at: string; model: string | null; investigations: number } | null;
  live_transactions: string[];
  agents_available: boolean;
  model: string | null;
}

export interface Snapshot {
  session: SessionInfo;
  transactions: TxRow[];
  cases: CaseSummary[];
  counters: Counters;
  alerts: Alert[];
  activity: Activity[];
}

export interface Transfer {
  transaction_id: string;
  timestamp: string;
  amount: number;
  currency: string;
  txn_type: string;
}

export interface GraphNode {
  id: string;
  label: string;
  role: Role;
  external: boolean;
  hard_flags: string[];
  flags: string[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  amount: number;
  count: number;
  transfers: Transfer[];
}

export interface Metric {
  label: string;
  value: string;
  hint: string | null;
}

export interface RedFlag {
  key: string;
  label: string;
  applies_to: string[];
  applicable: boolean;
  state: FlagState;
  evidence: string;
}

export interface TimelineItem {
  transaction_id: string;
  timestamp: string;
  source: string;
  target: string;
  amount: number;
  edge_id: string;
}

export interface Moment {
  timestamp: string;
  label: string;
  kind: "first_in" | "peak" | "cash_out" | "flagged";
}

export interface BalancePoint {
  timestamp: string;
  balance: number;
}

export interface AuditEntry {
  at: string;
  kind: string;
  detail: string;
}

export interface DecisionRecord {
  transaction_id: string;
  final_decision?: Decision | null;
  agent_decision?: Decision | null;
  decided_by?: string | null;
  reason?: string;
  pattern?: string;
  confidence?: number | null;
  model_confidence?: number | null;
  confidence_checks?: string[];
  why_review?: string[];
  hard_flags?: string[];
  precedents_relied_on?: string[];
  precedents_overridden?: { key: string; note?: string; reason?: string }[];
  precedents_dropped?: { key: string; reason: string }[];
  rule_score?: number;
  rule_reasons?: string[];
  analyst_note?: string;
  sar_id?: string | null;
  trace_run_id?: string | null;
}

export interface CaseDetail {
  summary: CaseSummary;
  finding: string;
  as_of: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  metrics: Metric[];
  red_flags: RedFlag[];
  thresholds: Record<string, string>;
  timeline: TimelineItem[];
  moments: Moment[];
  balances: Record<string, BalancePoint[]>;
  decisions: DecisionRecord[];
  activity: Activity[];
  alerts: Alert[];
  audit: AuditEntry[];
  network_audit: { as_of: string; seed_account: string; caller: string; accounts_returned: string[] }[];
  sar_ids: string[];
}

export interface AccountDetail {
  account_id: string;
  name: string;
  external: boolean;
  customer_type: string | null;
  occupation: string | null;
  bank: string;
  account_opened: string | null;
  account_age_days: number | null;
  risk_rating: string | null;
  pep: boolean | null;
  screening: string[];
  hard_flags: string[];
  expected_monthly_credits: number | null;
  expected_monthly_cash: number | null;
  money_in: number;
  money_out: number;
  counterparties: number;
  precedents: MemoryCard[];
  transactions: Transfer[];
}

export interface SarDraft {
  subject: string;
  pattern: string;
  timeline: string[];
  evidence: string[];
  narrative: string;
  precedents_cited_or_overridden: string[];
  disclaimer: string;
  transaction_id?: string;
}

export interface ResultsResponse {
  available: boolean;
  message?: string;
  path?: string;
  data?: {
    created_at?: string;
    dataset?: string;
    n_transactions?: number;
    headline?: string;
    note?: string;
    split?: string;
    model?: string;
    experiments?: Record<string, { name?: string; url?: string; metrics?: Record<string, number | string | null> }>;
  };
}

export type ServerEvent =
  | { type: "tx"; data: TxRow }
  | { type: "case"; data: CaseSummary }
  | { type: "case_removed"; data: { case_id: string } }
  | { type: "counters"; data: Counters }
  | { type: "session"; data: SessionInfo }
  | { type: "activity"; data: Activity }
  | { type: "alert"; data: Alert }
  | { type: "alert_removed"; data: { transaction_id: string } }
  | { type: "reset"; data: SessionInfo };
