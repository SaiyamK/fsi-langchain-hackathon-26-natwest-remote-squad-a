# Sentinel: multi-agent AML transaction monitoring

| | |
|---|---|
| **Team** | Chain & Grab |
| **Company** | NatWest |
| **Event** | LangChain FSI Hackathon, London, 25 November 2026 |
| **Use case** | Anti-money-laundering (AML) transaction monitoring for AML analysts |
| **Repository** | https://github.com/SaiyamK/fsi-langchain-hackathon-26-natwest-remote-squad-a |

> **Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only.** No NatWest,
> customer or proprietary data, and no NatWest code.

## Submission

| Required | Where |
|---|---|
| Notebook | [`sentinel_aml_agent/modules/01_sentinel_demo.ipynb`](sentinel_aml_agent/modules/01_sentinel_demo.ipynb), committed with the outputs of a live run |
| Agent | [`sentinel_aml_agent/agents.py`](sentinel_aml_agent/agents.py) |
| README | this file |
| Evaluations | [`sentinel_aml_agent/evals/`](sentinel_aml_agent/evals/) (evaluators in 8 categories), [`sentinel_aml_agent/results/eval_summary.json`](sentinel_aml_agent/results/eval_summary.json) (scores), [`sentinel_aml_agent/scripts/run_experiments.py`](sentinel_aml_agent/scripts/run_experiments.py) |
| Datasets | [`sentinel_aml_agent/data/`](sentinel_aml_agent/data/) (seeded generator and synthetic tables), plus LangSmith datasets `fsi-hackathon-remote-squad-a-sentinel-benchmark` and `fsi-hackathon-remote-squad-a-sentinel-scenarios` |

## The use case

**Who it helps:** AML analysts in a UK bank's financial-crime team, and the MLRO who is accountable for them.

**The problem:**
- Rules-based monitoring buries analysts in false alerts. Industry sources commonly put the false-positive rate at
  90-95% (for example [Columbia SIPA](https://www.sipa.columbia.edu/detecting-financial-crimes-evaluating-efficacy-automated-transaction-monitoring)).
- Laundering spread across transactions (structuring) or across accounts (money-mule rings) slips past
  per-transaction rules.
- Customers cleared before get investigated again from scratch.
- Calling an LLM on every transaction is too slow and too expensive at bank volumes.

**What Sentinel does:**
1. **Rules first.** Every transaction is scored deterministically, including a cross-account ring check. About
   95% are cleared with no LLM call.
2. **Agents investigate the rest.** A Deep Agents supervisor plans and delegates in parallel to four specialists:
   - **pattern analyst**: structuring, anomalous credits, round trips;
   - **KYC & precedent**: sanctions and PEP screening, plus analysts' past decisions;
   - **fund-flow**: the one audited cross-customer tool, for mule rings;
   - **SAR writer**: a structured Suspicious Activity Report draft, built only from the gathered evidence.
3. **A human decides when the agents are unsure.** The graph pauses (`interrupt()`), and the analyst's note becomes
   a **precedent** with an expiry date, so the same case isn't investigated twice.
4. **Memory can't be used to clear a launderer.** Safeguards are code, not prompts: hard red flags (sanctions, PEP,
   a confirmed ring) beat any precedent; precedents apply only to the same customer, counterparty and pattern, and
   only until they expire; a suspected but unconfirmed mule network always goes to a human.

## Results and KPIs

LangSmith experiments on a **held-out synthetic test world**: 36 customers, 950 transactions, 15 planted
laundering alerts. Model `openai:gpt-6-sol`. The baseline is the same rules tier on its own. Rules were tuned on a
separate dev world only.

| KPI | Rules only | Sentinel |
|---|---|---|
| False positives | 30 | **2** (−93%) |
| Alert precision | 33% | **88%** |
| Recall on planted laundering (structuring, mule ring, round trip) | 100% | **100%** |
| Decision accuracy (starter evaluator) | 0.968 | **0.993** |
| Transactions reaching an LLM | 0% | **4.7%** |
| Per investigation | – | 12 model calls · 36k tokens · 22 s median |
| Human review questions | – | 34 (3.6% of transactions) |

On the scenario suite, every safeguard, trajectory, SAR-groundedness and network-scope check scores 1.0. The eight
evaluation categories, the gaps we don't cover yet, and the LangSmith experiment names are in the notebook,
section 6, and in [DECISIONS.md](DECISIONS.md) (DEC-016).

### Estimated value (ROI)

An **illustrative estimate** from the test-world rates, scaled to **1 million transactions**. Replace the
assumptions with a bank's own figures.

| | Rules only | Sentinel |
|---|---|---|
| Alerts for an analyst to work (true + false) | 47,400 | 17,900 |
| Quick review questions from the agents | – | 35,800 |
| Analyst hours (assumptions below) | 23,700 | 14,900 |
| **Analyst time saved** | | **8,800 hours (37%), about £395k at £45/hour** |
| LLM tokens used | 0 | about 1.7 billion (cost depends on the gateway price) |

**Assumptions:** 30 minutes to work an alert; 10 minutes to answer a review question; £45 per analyst hour,
fully loaded. False positives fall by 93%, but analyst time falls by 37%, because Sentinel asks quick questions
instead of guessing. Not counted: fewer repeat investigations as precedents build up, and faster SAR drafting.

**Limitations:**
- The data, labels and rules are ours, synthetic and small.
- Human answers in the experiments are scripted.
- The month 1 → month 2 fall in reviews (28 → 6) comes from repeat cases planted in the data.
- The LLM judge uses the same model family as the agent, so groundedness is checked in code instead.

## Run instructions

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), and a LangSmith API key and workspace ID.

From the **repo root**:

```bash
uv sync --all-packages
cp .env.example .env
# Edit .env: ATTENDEE_NAME, LANGSMITH_API_KEY, LANGSMITH_WORKSPACE_ID; MODEL_NAME="openai:gpt-6-sol"
cd sentinel_aml_agent
```

| To | Run (from `sentinel_aml_agent/`) |
|---|---|
| Open the demo notebook (choose `.venv/bin/python` as the kernel) | `uv run jupyter notebook modules/01_sentinel_demo.ipynb` |
| Record a live run for replay, then replay it on stage (a banner says so) | `REPLAY=record uv run jupyter notebook …`, then `REPLAY=1 uv run jupyter notebook …` |
| Chat with the agent in LangGraph Studio | `uv run langgraph dev`. Graph `sentinel`; context `{"user_id": "CUS-0001", "as_of": "2026-10-08T08:58"}`; message `New transaction: TX-000167`; resume a pause with `{"decision": "clear", "note": "…"}` |
| Check the demo scenarios live (9 investigations, about 2 minutes) | `uv run python scripts/check_scenarios.py --with-mule` |
| Run the LangSmith experiments (rules-only vs Sentinel) | `uv run python scripts/run_experiments.py` |
| Create or read the analyst review queue in LangSmith | `uv run python scripts/annotation_queue.py` (add `--collect` to read reviews) |
| Run the checks that need no LLM | `uv run python scripts/check_core.py` (also `check_data`, `check_rules`, `check_graph`) |
| Regenerate the synthetic data (seeded, byte-identical) | `uv run python data/generate.py` |

Never run plain `uv sync` inside `sentinel_aml_agent/`; use `uv sync --all-packages` from the root.

## How it was built

LangChain (tools with `ToolRuntime`, structured output, middleware), LangGraph (checkpointer, store,
`interrupt()`), Deep Agents (`create_deep_agent` supervisor with planning and four `SubAgent`s), and LangSmith
(LLM Gateway, tracing, datasets, experiments, annotation queue, online evaluator). Built from the organiser's
starters (removed before submission; still in git history). From them we kept memory, human review and
evaluators (transaction monitoring), sanctions/PEP screening (KYC), and the sub-agent pattern (document summary).
Details are in [`sentinel_aml_agent/README.md`](sentinel_aml_agent/README.md).

```
README.md                        this file (team, company, use case, run instructions)
sentinel_aml_agent/
├── agents.py                    the agent (submission file)
├── modules/01_sentinel_demo.ipynb   the notebook (submission file)
├── instructions.md, sub_agents/ supervisor and specialist prompts
├── tools/, rules/, utils/       tools, safeguards, rules tier, graph, runner, replay
├── evals/                       evaluations
├── data/                        datasets (generator + synthetic tables)
├── results/                     eval scores, saved runs, screenshots
└── scripts/                     experiments, checks, annotation queue, notebook builder
USE_CASE.md · DEMO_SCRIPT.md · PLAN.md · DECISIONS.md · HACKATHON.md   planning and decisions
.kiro/specs/                     requirements, design notes and task lists
```
