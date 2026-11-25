# HACKATHON.md

Context for AI coding agents (and humans) working in this repo during the FSI Hackathon. Read this before making
changes.

**Sources, in order:** the **LangChain FSI Hackathon Flight Deck v1.0** (25 November 2026, shared after the
kick-off) is the source of truth for today. The attendee guide PDF it replaces is kept below only where the flight
deck says nothing new.

## Event

- **Event:** LangChain FSI Hackathon, London. GridIron, 8th floor. Wednesday 25 November 2026.
- **Team:** **Chain & Grab** (LangSmith workspace "NatWest - Remote A"). The flight deck's submission name format
  is `Team name | NatWest`, which gives `Chain & Grab | NatWest` unless LangChain says otherwise.
- **Goal:** build the smallest complete solution that solves one clear FSI problem, works end to end, has a control
  or human decision, produces a LangSmith trace, has measurable evaluation evidence, and can be explained in 5 minutes.
- **Fork/remote:** `origin` is `https://github.com/SaiyamK/fsi-langchain-hackathon-26-natwest-remote-squad-a.git`.
- **Our project:** Sentinel, multi-agent AML transaction monitoring, in `sentinel_aml_agent/`.

### Hard stops today

| Time | What happens |
|------|--------------|
| 10:00-13:00 | Build block 1 |
| 13:00-14:00 | Lunch |
| 14:00-15:45 | Build block 2 and submission |
| **15:45** | **Submission deadline** |
| 16:00 | Demos and judging begin: 5 minutes per team, then Q&A |

### Target checkpoints (recommended)

| By | Done |
|---|---|
| 13:00 | One working happy path · one LangSmith trace · one control or human-review point · problem statement and architecture drafted |
| 15:00 | Normal and difficult cases tested · evaluation results captured · trace and result screenshots saved · main demo path stable |
| 15:15 | Major features frozen · README and presentation finished · demo rehearsed · fallback screenshots ready |
| 15:35 | Final commit done · repository and presentation links checked · submitted early enough to recover from errors |

## Judging (30 points)

| Area | What scores |
|------|-------------|
| **1. Use-case impact** | A recognisable financial-services problem · a clearly identified user · measurable KPIs · **estimated ROI or value** |
| **2. Technical depth** | Appropriate use of LangGraph, LangChain or Deep Agents · complete system design and architecture · evidence of controls, evaluations, memory, middleware or human review |
| **3. Presentation** | Demo finishes within 5 minutes · solution works end to end · team explains the design and answers questions |

## Required submission

**In the forked repository:**
- the **notebook**;
- the **agent file**. The flight deck says `agent.py`; the attendee guide said `agents.py`. **The team decided to
  keep `agents.py`** (DECISIONS.md DEC-018);
- a **README containing team name, company, use case and run instructions**;
- **any evaluations or datasets created**.

**In the presentation:** the problem and who it helps · an end-to-end demonstration · results, KPIs, estimated ROI and
evaluation scores · how the solution was built · the repository link.

**Submission steps:**
1. Use the name format `Team name | NatWest`.
2. Fork one repository per team.
3. Commit the notebook and the agent file.
4. Complete the 5-minute presentation template ("FSI Hackathon — Submission Template.pptx").
5. Name the slides **`HACK_NATWEST_TEAMNAME`** (ours: `HACK_NATWEST_CHAINANDGRAB`).
6. Submit the fork link and slides through the official route, https://langch.in/hack-sub, **before 15:45**.

### Where our deliverables are

| Required | Path |
|---|---|
| Notebook | `sentinel_aml_agent/modules/01_sentinel_demo.ipynb` (committed with outputs of a live run) |
| Agent file | `sentinel_aml_agent/agents.py` |
| README (team, company, use case, run instructions) | `README.md` (repo root) |
| Evaluations | `sentinel_aml_agent/evals/` (evaluators, SAR rubric, online evaluator setup), `sentinel_aml_agent/results/eval_summary.json` (scores), `sentinel_aml_agent/scripts/run_experiments.py` |
| Datasets | `sentinel_aml_agent/data/` (generator + synthetic JSONL tables) and the LangSmith datasets `fsi-hackathon-remote-squad-a-sentinel-benchmark` and `-sentinel-scenarios` |
| Screenshots (fallback) | `sentinel_aml_agent/results/screenshots/` |

## Five-minute demo shape (recommended)

| Time | Segment |
|---|---|
| 0:00-0:30 | User, problem and why it matters |
| 0:30-1:00 | What the agent does |
| 1:00-2:45 | End-to-end demonstration |
| 2:45-3:30 | LangSmith trace and evaluation |
| 3:30-4:15 | Architecture, controls and human review |
| 4:15-4:45 | Results, value and limitations |
| 4:45-5:00 | Conclusion and next step |

DEMO_SCRIPT.md uses an older run of show; where they differ, follow this shape.

## Non-negotiable controls

1. **Synthetic or public data only.** No NatWest, customer or proprietary data.
2. **No NatWest code.**
3. **Never commit `.env` files, keys, tokens or credentials.** Never print, log or paste them into files, commands,
   issues, PR text, Teams or Copilot prompts. Edit `.env.example` (placeholders only) when adding variables.
4. Outputs are not legal, compliance or regulatory advice. Keep that disclaimer in user-facing text and the demo.
5. The team keeps the rights to its project code.

## Recommended ownership

Product/story (problem, user, KPI, value) · Agent (workflow, tools, end-to-end build) · Controls (guardrails, human
review, failure handling) · Evaluation (datasets, traces, scores, screenshots) · Submission (README, repository,
slides, links) · Demo (narration, timing, Q&A).

## Open points (from the flight deck)

- Final remote demonstration and judging arrangements still need confirmation.
- Several NatWest squads compete as separate teams. Use `Team name | NatWest` unless LangChain says otherwise.

## Resources

- Master deck: "FSI Hackathon London _ 25 Nov 2026 _ Master Deck.pdf"
- Presentation template: "FSI Hackathon — Submission Template.pptx"
- Starter repository: https://langch.in/fsi-hack
- Submission: https://langch.in/hack-sub
- LangChain Chat: https://chat.langchain.com
- LangSmith: https://smith.langchain.com · Docs: https://docs.langchain.com (also as MCP servers `docs-langchain` and `reference-langchain`)
- Questions before the day: Avtar (avtar.raikmo@langchain.dev) or Tanmaiyii (tanmaiyii.rao@langchain.dev)

## Working in this repo

### Environment
- Python 3.11+ managed with [uv](https://docs.astral.sh/uv/). One `.venv` at the repo root.
- Install from the repo root: `uv sync --all-packages`. **Don't run plain `uv sync` inside `sentinel_aml_agent/`.**
- Run Python from inside `sentinel_aml_agent/` (for example `uv run python scripts/check_core.py`), or imports of
  `utils` and `tools` fail.

### Configuration
- One `.env` at the repo root, from `.env.example`: `ATTENDEE_NAME`, `LANGSMITH_API_KEY`, `LANGSMITH_WORKSPACE_ID`,
  `LANGSMITH_PROJECT`, `MODEL_NAME` (we use `openai:gpt-6-sol`).
- Models go through the LangSmith LLM Gateway. Don't hardcode model names or keys.
- Tracing is on; traces go to project `fsi-hackathon-<ATTENDEE_NAME>`.

### Running
See the run instructions in `README.md`. Studio: `uv run langgraph dev` in `sentinel_aml_agent/` (graph `sentinel`).

### Code conventions
- Layout: `agents.py` (exports `agent`), `instructions.md`, `sub_agents/`, `tools/`, `rules/`, `utils/`, `data/`
  (JSONL tables read through `utils/db.py`), `evals/`, `scripts/`, `results/`, `modules/` (notebook), `langgraph.json`.
- The notebook is generated by `scripts/build_notebook.py`; change the script, not the notebook.
- Safeguards live in code (`tools/decisions.py`), not prompts. No code or prompt may refer to demo customers (DEC-004).

## Priorities for agents working here

1. Keep the project runnable. Verify with a real run before reporting done.
2. Favour what the judges score: impact with KPIs and ROI, technical depth with controls and evals, a 5-minute demo.
3. Never commit secrets. Check `git status` and `git diff --staged` before any commit.
4. Don't push, force-push or change the git remote unless the user asks.
5. Planning docs: PLAN.md is the plan; DECISIONS.md records later decisions and wins where they conflict.
