# Design: AML Analyst Workspace (Sentinel UI)

*Implements [requirement.md](requirement.md) · Backend: `sentinel_aml_agent/` (unchanged; imported) · 2026-11-25*

> Every screen shows: *"Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only."*

## U1. Shape

```
sentinel_ui/
├── api/                  Python, FastAPI. A thin service over sentinel_aml_agent (imports it; never edits it)
│   ├── sentinel_api/
│   │   ├── app.py        routes + SSE
│   │   ├── session.py    the stream session: clock, rules tier, agent queue, statuses, counters, cases
│   │   ├── bridge.py     runs one investigation (live) and turns callbacks into agent-step events
│   │   ├── recording.py  record a live run; replay it (DEC-003: labelled on screen)
│   │   ├── cases.py      case grouping + graph, metrics, red flags, timeline, balances (pure, deterministic)
│   │   ├── results.py    reads results/eval_summary.json for the Results view
│   │   └── models.py     Pydantic response models (the API contract)
│   └── tests/            pytest; no LLM needed
└── web/                  React 19 + Vite + TypeScript (strict) + Tailwind v4 + shadcn-style primitives
    └── src/
        ├── app/          router, providers, layout shell
        ├── components/ui/      primitives (Button, Badge, Card, Dialog, Tooltip…)
        ├── components/layout/  NavBar, SummaryBar, Disclaimer, ModeBanner
        ├── features/
        │   ├── stream/   Live Stream (LS-*)
        │   ├── queue/    Flagged Transactions (FQ-*)
        │   ├── case/     Case / Network View (CV-*, FR-4..FR-9)
        │   ├── agents/   Agent activity panel (EX-1)
        │   ├── memory/   Memory cards (EX-2)
        │   ├── alerts/   "Needs your decision" (EX-4)
        │   └── results/  Results view (EX-13)
        ├── lib/          api client, SSE, formatters, status meta (EX-9)
        ├── stores/       Zustand session store + pure reducer
        └── types/        API types (mirror api/sentinel_api/models.py)
```

Why a separate folder: the agent team owns `sentinel_aml_agent/`; the UI only imports from it
(`build_agent`, `rules.scorer`, `utils.graph`, `tools.decisions.apply_review`, `tools.precedents`), so neither side
blocks the other. DEC-004 applies: no code branches on demo names or IDs.

## U2. Runtime model

One **session** = one pass over world 0 in timestamp order (the notebook's global stream, DEC-007).

1. **Clock.** A producer thread releases transactions at `speed` transactions per second. Pause stops releases;
   background investigations keep going (LS-7). **Fast-forward** releases the next N days at once.
2. **Rules tier.** Each released transaction is scored with `rules.scorer.score_with_network` against the customer's
   earlier history. The baseline verdict (`baseline_decision`) is stored for the value ticker (EX-3). Below
   `rules_clear_below`: status `cleared_rules`, no LLM.
3. **Agent queue.** Otherwise status `under_review` and the transaction is queued. One worker thread investigates in
   order, as the notebook does.
4. **Investigation** (`bridge.py`): invokes the supervisor on the customer's thread with the same context as
   `utils/stream.py` (`as_of`, rule score, run ID). A LangChain callback handler watches `task` tool calls
   (`subagent_type`) and `record_decision`, and emits `agent.step` events with a one-line finding parsed from each
   specialist's structured output (EX-1). The decision record is read back from the store as in `stream.py`.
5. **Human review.** An `interrupt()` becomes status `needs_analyst` + an alert (EX-4). The worker waits on a
   per-transaction future until the analyst posts a decision, then resumes with `Command(resume=…)`.
   `record_decision` itself saves the note as a precedent (unchanged backend code).
6. **Status.** `cleared` / `flagged` / `needs_analyst` → resolved, written back in place.

### Live vs replay (DEC-003)

A full world-0 run is ~34 investigations × 20-35 s, too long for a 5-minute demo.

| Mode | What runs | Banner |
|---|---|---|
| `live` | Every investigation calls the model | none |
| `record` | Live, and every investigation's events are saved to `sentinel_ui/recordings/world0.json` with time offsets, trace IDs and the recording time | none |
| `replay` | Investigations are replayed from the recording at their real pace × speed. Transactions in `SENTINEL_LIVE_TX` (e.g. Sophie's) still run live | `REPLAY: agent results recorded from the live run at <time>` with the LangSmith link |

In replay, a recorded interrupt still waits for the analyst; the analyst's answer is applied with
`tools.decisions.apply_review` (same code as live), so precedents in the store are real either way.

## U3. API contract

REST (JSON) + one SSE stream. Types live in `api/sentinel_api/models.py` and are mirrored in `web/src/types/api.ts`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/state` | Full snapshot: session, transactions (released), cases, counters, alerts, activity |
| GET | `/api/events` | SSE: `tx`, `case`, `counters`, `session`, `activity`, `alert`, `memory` events, each carrying the full updated entity |
| POST | `/api/stream/{start\|pause\|resume\|reset}` | Stream controls (LS-7) |
| POST | `/api/stream/fast-forward` `{days}` | Fast-forward |
| POST | `/api/stream/speed` `{tx_per_second}` | Speed (EX-8.4) |
| GET | `/api/cases/{case_id}` | Case detail: graph, metrics, red flags, timeline, balances, explanation, audit |
| GET | `/api/accounts/{account_id}?as_of=` | Account panel (FR-7) |
| POST | `/api/transactions/{tx_id}/decision` `{decision, note}` | Analyst decision; note required (FR-9.1) |
| GET | `/api/sars/{sar_id}` | SAR draft written by the sar-writer agent |
| GET | `/api/results` | Results view (EX-13) from `sentinel_aml_agent/results/eval_summary.json` |

Event delivery: server-side state is authoritative; every event carries the whole updated entity, so the client
reducer is a pure upsert, and a reconnect is just `GET /api/state` again.

## U4. Cases

- **Network case:** a transaction whose account is in a confirmed ring (`utils.graph.ring_membership`) belongs to
  `CASE-RING-<collector>`. The graph is built from `ring["forwards"]`, the feeders' inbound payments in the
  24 h before each forward (sources), and the collector's outbound non-internal payments (cash-out / sink).
- **Single-customer case:** `CASE-<user_id>-<pattern>`, grouping that customer's flagged transactions of one
  pattern. The graph is the customer plus its counterparties in the window (branches for cash), with the timeline
  as the main view (FQ-8).
- **Roles** (FR-4.3): `source`, `mule`, `hub`, `sink`, `subject`, `other`. **Hard flags** from
  `tools.decisions.hard_flags_for`.
- **Layouts** (FR-4.5) are computed on the client and are deterministic: fan-in radial, fan-out radial, mule ring
  left → right in columns (source → mule → hub → sink).
- **Red flags** (FR-5.2) are computed from data. Device/IP is not in the data, so that flag is **No data** (FR-5.4).
- **Balances** (FR-6.4): there's no balance column, so the view shows *net flow since the window started*,
  labelled as such.

## U5. Value ticker (EX-3)

All computed from the session; no fixed numbers (EX-3.2).

| Figure | How |
|---|---|
| Rules-only alerts | Released transactions whose baseline verdict is `escalate` |
| Sentinel alerts | Transactions whose final status is `flagged`, or `needs_analyst`/resolved by a human |
| False positives avoided | Baseline `escalate`, label `clear`, Sentinel `clear` (labels used only here, as the spec allows) |
| Analyst hours saved | (rules-only alerts − analyst touches) × `minutes_per_alert` (default 20, shown on request) |
| Model usage | Model calls and tokens so far vs *if every transaction went to the agents* (average tokens per investigation × transactions). Tokens, not money: DEC-005 |

## U6. Frontend standards

- React 19, React Router 7, Vite, TypeScript `strict`, Tailwind CSS v4, shadcn-style primitives (Radix + `cva`),
  Lucide icons, Zustand for the live session store, TanStack Query for request/response data (case detail,
  account, results), `motion` for transitions, Vitest + Testing Library.
- Feature folders; components small (< ~150 lines), logic in hooks or pure functions; pure functions unit-tested
  (reducer, layouts, formatters).
- **Colour meanings (EX-9)** in one place (`lib/status.ts`): green cleared, amber review/needs analyst, red
  flagged/escalated, purple memory, grey cleared by rules. Every status also has an icon and a text label.
- **Motion (EX-16):** status changes animate in place; `prefers-reduced-motion` and an in-app toggle turn it off.
- Accessible by default: semantic landmarks, focus-visible rings, keyboard reachable actions, `aria-live` for new
  flags and alerts.
- Light and dark themes via CSS variables.

## U7. Out of this build

P3 items (EX-10 Ask Sentinel, EX-11 heat strip, FR-4.11 node cap, FR-9.5 export) and the scenarios with no data in
world 0 (B fan-out from IBM HI-Small, D benign look-alike). The fan-out layout and red flags are implemented
generically, so they work when that data exists.
