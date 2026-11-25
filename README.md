# Sentinel · NatWest Remote Squad A · LangChain FSI Hackathon, London, 25 Nov 2026

> **Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only.**

**Sentinel** is a multi-agent AML transaction monitoring system for AML analysts: rules clear most traffic, a
Deep Agents supervisor and four specialists investigate the grey zone, a human decides when the agents are unsure,
and analyst decisions become precedents that can never clear a launderer. It's measured against a rules-only
baseline in LangSmith.

## Submission

| File | What it is |
|---|---|
| [`sentinel_aml_agent/agents.py`](sentinel_aml_agent/agents.py) | The agent |
| [`sentinel_aml_agent/modules/01_sentinel_demo.ipynb`](sentinel_aml_agent/modules/01_sentinel_demo.ipynb) | The demo notebook, with outputs from a live run |

Start with [`sentinel_aml_agent/README.md`](sentinel_aml_agent/README.md): results, how to run it, and the layout.

## Setup

Python 3.11+ and [uv](https://docs.astral.sh/uv/). From this folder:

```bash
uv sync --all-packages
cp .env.example .env    # fill in ATTENDEE_NAME, LANGSMITH_API_KEY, LANGSMITH_WORKSPACE_ID
```

Models are reached through the LangSmith LLM Gateway; set `MODEL_NAME` in `.env` (we used `openai:gpt-6-sol`).

## Documents

| Doc | Purpose |
|---|---|
| [`USE_CASE.md`](USE_CASE.md) | The problem, the user, the architecture and the evaluation design |
| [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) | The 5-minute demo and Q&A prep |
| [`PLAN.md`](PLAN.md) | The implementation plan |
| [`DECISIONS.md`](DECISIONS.md) | Decisions made while building, including the eval results (DEC-016) |
| [`HACKATHON.md`](HACKATHON.md) | The hackathon's rules, from the attendee guide |
| [`.kiro/specs/sentinel-aml-agent/`](.kiro/specs/sentinel-aml-agent/) | Requirements, design notes and the task list we built from |

Built from the organiser's starter templates (`01_kyc_agent`, `02_transaction_monitoring_agent`,
`03_document_summary_agent`), which were removed before submission and remain in the git history.
