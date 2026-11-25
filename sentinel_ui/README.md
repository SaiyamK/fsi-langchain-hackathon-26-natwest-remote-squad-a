# Sentinel analyst workspace (UI)

The AML analyst's workspace over the Sentinel agents: a live transaction stream, the flagged-transaction queue, and
a case view with the money-flow network. Spec: [requirement.md](../.kiro/specs/sentinel-aml-agent-ui/requirement.md) ·
design: [design.md](../.kiro/specs/sentinel-aml-agent-ui/design.md) · tasks: [tasks.md](../.kiro/specs/sentinel-aml-agent-ui/tasks.md).

> Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only.

**New here? Read [HOW_IT_WORKS.md](HOW_IT_WORKS.md)**: what Start does, the modes, and where every number on screen
comes from.

```
sentinel_ui/
├── api/   FastAPI service. Imports sentinel_aml_agent (never edits it): rules tier, agents, human review, cases, SSE
└── web/   React 19 + Vite + TypeScript + Tailwind v4: Live Stream, Flagged queue, Case / Network View, Results
```

## Run it

From the repo root, once: `uv sync --all-packages` and `cd sentinel_ui/web && pnpm install`.

```bash
# terminal 1: API on :8000 (from the repo root)
uv run uvicorn sentinel_api.app:app --app-dir sentinel_ui/api --port 8000

# terminal 2: web on :5173 (proxies /api to :8000)
cd sentinel_ui/web && pnpm dev
```

Open http://localhost:5173 and press **Start**. For a single process, run `pnpm build` and the API serves
`web/dist` at http://localhost:8000.

## Modes (`SENTINEL_UI_MODE`)

| Mode | What runs | When |
|---|---|---|
| `offline` | Rules tier only; every flagged transaction goes to the analyst. Labelled on screen | No model key in `.env` (the default then) |
| `live` | The real supervisor and sub-agents, every investigation | Key in `.env`, no recording |
| `record` | Live, and saves every investigation to `recordings/world0.json` | Once before the demo (~15-20 min for world 0) |
| `replay` | Plays the recording back, labelled `REPLAY` with the recording time (DEC-003) | Stage demo (the default when a recording exists) |

```bash
SENTINEL_UI_MODE=record uv run uvicorn sentinel_api.app:app --app-dir sentinel_ui/api --port 8000   # rehearsal
SENTINEL_LIVE_TX=TX-000254 uv run uvicorn sentinel_api.app:app --app-dir sentinel_ui/api --port 8000 # replay, Sophie live
```

Other settings: `SENTINEL_SPEED` (transactions per second, default 8), `SENTINEL_REPLAY_SPEED` (default 3× the recorded pace).
In replay, a recorded pause still waits for the analyst, and their answer is saved through the agents' own
`apply_review`, so precedents are real.

## Demo path

1. **Live Stream**: Start. Most rows go *Cleared by rules*; flagged ones go *Under review* → *Flagged* / *Needs analyst*
   in place. The summary bar shows rules-only vs Sentinel alerts climbing apart.
2. **Needs your decision** slides in for Sophie's £18,000 credit: clear it with a note → *Saved to memory*.
3. **Fast-forward 10 months**: her second credit is auto-cleared with a *Sentinel remembers* card.
4. **Flagged** → the mule-ring case: the network replays itself (sources → 5 mules → Northgate → Kestrel FZE), with
   pass-through, consolidation, new-account and cross-border flags, and Liam's old clearance shown **OVERRIDDEN**.
5. **Results**: rules-only vs Sentinel from `sentinel_aml_agent/results/eval_summary.json` (written by the eval run).

`P` toggles presenter mode. The wind icon turns motion off.

## Deployed copy

https://sentinel-aml.justpush.cloud (basic auth, user `team`). Runs on the team VPS behind the Cloudflare tunnel and
Traefik (`coolify` network, `http` entrypoint), from `/opt/sentinel-aml-ui` with [compose.yaml](compose.yaml).
It runs in `replay` from [recordings/world0.json](recordings/world0.json) (15 recorded investigations, `gpt-6-sol`),
so the demo makes no model calls. Flagged transactions with no recording, including Sophie's £18,000 credit, go
straight to the analyst. To record more, set `SENTINEL_UI_MODE=record` in `sentinel_ui/.env` on the server and restart;
the repo-root `.env` (chmod 600) holds the keys. The LangSmith gateway answered `402 blocked by gateway policies` on
25 Nov, so check one model call works before recording.

```bash
# update: sync the needed files, then rebuild (run from the repo root)
rsync -az --relative --exclude node_modules --exclude .venv --exclude __pycache__ --exclude dist \
  ./pyproject.toml ./uv.lock ./.dockerignore ./sentinel_aml_agent ./sentinel_ui \
  root@srv1475135.hstgr.cloud:/opt/sentinel-aml-ui/
ssh root@srv1475135.hstgr.cloud 'cd /opt/sentinel-aml-ui/sentinel_ui && docker compose up -d --build'
```

`sentinel_ui/.env` on the server holds `SENTINEL_BASIC_AUTH='team:<apr1 hash>'` (single quotes, so the `$`s survive).
Traefik only routes the container once its health check passes (about 30 s after start).

## Checks

```bash
cd sentinel_ui/api && uv run pytest              # cases, session, human review, counters (no LLM)
cd sentinel_ui/web && pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

## For the agent / eval team

- The UI reads, never writes, `sentinel_aml_agent/`. It reuses `rules.scorer`, `utils.graph`, `utils.stream`
  helpers, `tools.decisions.apply_review` and `hard_flags_for`, and `tools.precedents`.
- The Results view expects `results/eval_summary.json` shaped like `{"experiments": {"rules-only": {"name", "url",
  "metrics": {...}}, "sentinel": {...}}, "dataset", "n_transactions", "created_at", "headline"}`. Metric keys it
  labels: `false_positive_rate`, `recall_planted`, `decision_accuracy`, `review_routing`, `reviews_month1`,
  `reviews_month2`, `override_correctness`, `llm_share`, `tokens_per_investigation`. Others are shown as-is.
