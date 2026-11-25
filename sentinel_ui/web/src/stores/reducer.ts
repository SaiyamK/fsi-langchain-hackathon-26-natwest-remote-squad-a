import type { Activity, Alert, CaseSummary, Counters, ServerEvent, SessionInfo, Snapshot, TxRow } from "@/types/api";

/** Live session state, built from a snapshot and then kept current by server events (pure, so it's testable). */
export interface LiveState {
  session: SessionInfo | null;
  txById: Record<string, TxRow>;
  /** Released transaction IDs, oldest first. */
  txOrder: string[];
  cases: Record<string, CaseSummary>;
  counters: Counters | null;
  /** Alerts waiting for the analyst, newest first (EX-4.4). */
  alerts: Alert[];
  activity: Record<string, Activity>;
  /** Investigation IDs, most recently started first (EX-1.4). */
  activityOrder: string[];
  /** Bumped on reset so views drop local state. */
  epoch: number;
}

export const emptyLive: LiveState = {
  session: null,
  txById: {},
  txOrder: [],
  cases: {},
  counters: null,
  alerts: [],
  activity: {},
  activityOrder: [],
  epoch: 0,
};

export function fromSnapshot(snap: Snapshot, epoch = 0): LiveState {
  const txById: Record<string, TxRow> = {};
  for (const t of snap.transactions) txById[t.transaction_id] = t;
  const cases: Record<string, CaseSummary> = {};
  for (const c of snap.cases) cases[c.case_id] = c;
  const activity: Record<string, Activity> = {};
  for (const a of snap.activity) activity[a.transaction_id] = a;
  return {
    session: snap.session,
    txById,
    txOrder: snap.transactions.map((t) => t.transaction_id),
    cases,
    counters: snap.counters,
    alerts: [...snap.alerts].reverse(),
    activity,
    activityOrder: snap.activity.map((a) => a.transaction_id).reverse(),
    epoch,
  };
}

export function applyEvent(state: LiveState, event: ServerEvent): LiveState {
  switch (event.type) {
    case "tx": {
      const t = event.data;
      const known = t.transaction_id in state.txById;
      return {
        ...state,
        txById: { ...state.txById, [t.transaction_id]: t },
        txOrder: known ? state.txOrder : [...state.txOrder, t.transaction_id],
      };
    }
    case "case":
      return { ...state, cases: { ...state.cases, [event.data.case_id]: event.data } };
    case "case_removed": {
      const cases = { ...state.cases };
      delete cases[event.data.case_id];
      return { ...state, cases };
    }
    case "counters":
      return { ...state, counters: event.data };
    case "session":
      return { ...state, session: event.data };
    case "activity": {
      const a = event.data;
      const known = a.transaction_id in state.activity;
      return {
        ...state,
        activity: { ...state.activity, [a.transaction_id]: a },
        activityOrder: known ? state.activityOrder : [a.transaction_id, ...state.activityOrder].slice(0, 60),
      };
    }
    case "alert": {
      const rest = state.alerts.filter((x) => x.transaction_id !== event.data.transaction_id);
      return { ...state, alerts: [event.data, ...rest] };
    }
    case "alert_removed":
      return { ...state, alerts: state.alerts.filter((x) => x.transaction_id !== event.data.transaction_id) };
    case "reset":
      return { ...emptyLive, session: event.data, epoch: state.epoch + 1 };
    default:
      return state;
  }
}

/** Queue order (FQ-3): needs analyst first, then severity, then newest. */
export function sortCases(cases: CaseSummary[]): CaseSummary[] {
  const rank = (c: CaseSummary) => (c.status === "awaiting_analyst" ? 0 : c.status === "new" ? 1 : 2);
  return [...cases].sort(
    (a, b) => rank(a) - rank(b) || b.severity - a.severity || b.last_ts.localeCompare(a.last_ts),
  );
}
