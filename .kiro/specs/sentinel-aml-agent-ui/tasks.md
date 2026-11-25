# Tasks: AML Analyst Workspace (Sentinel UI)

Spec: #[[file:.kiro/specs/sentinel-aml-agent-ui/requirement.md]] · Design: #[[file:.kiro/specs/sentinel-aml-agent-ui/design.md]]

Working rules: never edit `sentinel_aml_agent/` from here (import only); no demo-specific code (DEC-004); replay is
labelled on screen (DEC-003); every screen carries the disclaimer.

## Phase U1: API (P1)
- [x] U1.1 Scaffold `sentinel_ui/api` as a workspace member (FastAPI, uvicorn, sse-starlette, pytest)
- [x] U1.2 `cases.py`: case grouping, graph, metrics, red flags, timeline, balances + tests
- [x] U1.3 `session.py`: clock, rules tier, agent queue, statuses, counters, value ticker + tests (rules-only path)
- [ ] U1.4 Live investigation (`investigators.py`) with agent-step events and interrupt/resume — written, **not yet run against the model** (no `.env` on this machine)
- [ ] U1.5 `recording.py`: record and replay, `SENTINEL_LIVE_TX` — written, needs one `record` run to verify
- [x] U1.6 `app.py`: REST + SSE; account, SAR and results endpoints

## Phase U2: Web shell (P1)
- [x] U2.1 Scaffold Vite + React + TS + Tailwind v4 + primitives; lint, typecheck, test scripts
- [x] U2.2 Types, API client, SSE hook, Zustand store + reducer tests
- [x] U2.3 Layout: nav with flag counter (LS-10), summary bar + value ticker (LS-6, EX-3), disclaimer, mode banner

## Phase U3: Screens (P1)
- [x] U3.1 Live Stream: rows, in-place status, highlight, network badge, related rows, detail drawer, controls, filters
- [x] U3.2 Agent activity panel (EX-1) and memory cards (EX-2)
- [x] U3.3 "Needs your decision" alerts (EX-4) with inline note
- [x] U3.4 Flagged queue: cases, ordering, thumbnails, quick filters, search
- [x] U3.5 Case view: header, network graph (layouts, roles, legend, highlight), metrics + red flags
- [x] U3.6 Timeline + replay with animated money flow and balance views (FR-6, EX-5)
- [x] U3.7 Account panel (FR-7), agent explanation (FR-8), analyst actions + SAR draft (FR-9), audit (FR-10)
- [x] U3.8 Results view (EX-13)

## Phase U4: Verify
- [x] U4.1 `pytest`, `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build` all pass
- [ ] U4.2 Walk scenarios 0, A, E, F — done in offline mode (stream, alerts, queue, ring case with replay, dark mode); live/replay pending `.env`
- [x] U4.3 README in `sentinel_ui/`
