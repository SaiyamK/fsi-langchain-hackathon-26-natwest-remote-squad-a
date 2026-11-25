# HACKATHON.md

Context for AI coding agents (and humans) working in this repo during the FSI Hackathon. Read this before making changes.

## Event

- **Event:** FSI Hackathon, London. GridIron, 8th floor. Wednesday 25 November 2026, 08:15 to 19:00.
- **Team:** NatWest Remote Squad A (LangSmith workspace "NatWest - Remote A").
- **Goal:** Teams of 4 to 6 build a working AI agent for a financial services problem using LangChain, LangGraph,
  Deep Agents and LangSmith. The aim is to cover the full lifecycle: build, test, deploy, monitor, govern, improve.
- **Fork/remote:** `origin` is `https://github.com/SaiyamK/fsi-langchain-hackathon-26-natwest-remote-squad-a.git`.

### Schedule

| Time | What happens |
|------|--------------|
| 08:15-09:00 | Registration, breakfast, laptop and LangSmith access check |
| 09:00-10:00 | Welcome, LangSmith walkthrough, setup check, concepts (Deep Agents, LangGraph), live demo |
| 10:00-13:00 | Build block 1 (LangChain engineers circulating) |
| 13:00-14:00 | Lunch |
| 14:00-16:00 | Build block 2 |
| 16:00-17:00 | Team demos and judging (about 5 minutes per team plus Q&A) |
| 17:00-17:15 | Winners, prizes, close |
| 17:15-19:00 | Networking and drinks |

## Ground rules (must follow)

1. **Synthetic or public data only.** Never add real customer or confidential data to the repo, prompts or traces.
2. **Keep `.env` and API keys out of git.** `.env` holds the LangSmith key. Never print, log, commit or paste its
   values into files, commands, issues or PR text. Edit `.env.example` (placeholders only) when adding new variables.
3. **Outputs are not legal, compliance or regulatory advice.** Keep that disclaimer in any user-facing text or demo.
4. Keep the use case industry-generic. Do not reference NatWest-internal systems, policies or data.
5. The team keeps the rights to its project code.

## Judging (30 points)

Work should be steered toward these three areas:

| Area | What scores |
|------|-------------|
| Use case relevance and impact | A real FSI problem, a clear user, measurable value |
| Technical complexity | Sound use of LangChain fundamentals, multi-agent patterns, memory, evals |
| Presentation | A clear 5-minute demo on the standard slide template, and good handling of Q&A |

## Submission

- A **Jupyter notebook** plus the agent code file (the guide calls it `agents.py`; the starters here use `agent.py`),
  in a forked GitHub repo. Confirm the exact expected filename on the day.
- The slide template and full submission guidance are shared on the day.
- Keep the notebook runnable top to bottom with `.venv/bin/python` as the kernel.

## Starter templates

These are starting points, not requirements. Build on one, adapt one, or build a new use case with the same tools.

| Difficulty | Folder | Pattern | What it does |
|------------|--------|---------|--------------|
| Easy | `01_kyc_agent` | LangGraph | Extracts applicant details, screens sanctions and PEP lists, scores risk, routes high-risk cases to a human |
| Medium | `02_transaction_monitoring_agent` | Deep Agents / `create_agent` | Scores a transaction stream, remembers earlier ones, asks a human when unsure, evals with LangSmith |
| Hard | `03_document_summary_agent` | Deep Agents, map-reduce | Summarises a long regulatory document into a reviewable brief using parallel sub-agents |
| Optional | `00_dcode_setup` | `dcode` CLI | Terminal coding agent setup (not part of the submission) |

Each folder has its own `README.md`. Read it before editing that folder.

## Working in this repo

### Environment

- Python 3.11+ managed with [uv](https://docs.astral.sh/uv/). One shared `.venv` at the repo root serves all topics.
- Install from the repo root: `uv sync --all-packages`.
- **Do not run plain `uv sync` inside a topic folder.** It trims the shared environment and breaks the other topics.
  `uv run` and `uv add` are fine inside a topic folder.
- Run Python files from inside their topic folder (for example `uv run python agent.py`), or imports of `utils`
  and `tools` fail.

### Configuration

- A single `.env` at the repo root, copied from `.env.example`. Required: `ATTENDEE_NAME`, `LANGSMITH_API_KEY`,
  `LANGSMITH_WORKSPACE_ID`, `LANGSMITH_PROJECT`.
- Models go through the LangSmith LLM Gateway. Change the model with `MODEL_NAME` (`provider:model`) in `.env`.
  Do not hardcode model names or keys in code.
- Tracing is on (`LANGSMITH_TRACING=true`). Traces appear in the project `fsi-hackathon-<ATTENDEE_NAME>`.

### Running

- Agent in LangGraph Studio, from the topic folder: `uv run langgraph dev` (serves on `http://127.0.0.1:2024`).
- Notebooks, from the topic folder: `uv run jupyter notebook`.
- KYC input is `{"customer_id": "CUST-001"}`. High-risk customers pause at `human_review` and wait for
  `{"decision": "approve" | "reject", "notes": "..."}`.
- Transaction monitoring context is `{"user_id": "USR-001"}` and the message is `New transaction: TX-1003`.
- Document summary message is `Summarise document PS26-4 for FIRM-001`.

### Code conventions

- Each agent folder follows the same layout: `agent.py` (exports `agent`), `instructions.md` (system prompt),
  `tools/`, `utils/`, `data/` (JSONL tables read via `utils/db.py`), `modules/` (notebooks), `langgraph.json`.
- Tools read data through `utils/db.py` (`table`, `query`, `get`). Data files are re-read on every query, so edits
  to `data/*.jsonl` apply without a restart.
- Notebooks have mirrored `.py` files in some topics. Keep the two in sync when changing either.
- Keep changes small and runnable. A working end-to-end demo matters more than breadth.

## Priorities for agents working here

1. Keep the project runnable at all times. Verify with a real run before reporting done.
2. Favor features that raise the judging score: a clear FSI use case, human-in-the-loop, memory, evals in
   LangSmith, and a demo that can be shown in 5 minutes.
3. Add evals and traces where they show the agent is measurably good, not as decoration.
4. Never commit secrets. Check `git status` and `git diff --staged` before any commit.
5. Do not push, force-push or change the git remote unless the user asks.

## Useful links

- LangSmith: https://smith.langchain.com
- Docs: https://docs.langchain.com
- Courses: https://academy.langchain.com (LangSmith Essentials, Intro to LangChain, Intro to LangGraph, Intro to Deep Agents)
- Questions: Avtar (avtar.raikmo@langchain.dev) or Tanmaiyii (tanmaiyii.rao@langchain.dev)
