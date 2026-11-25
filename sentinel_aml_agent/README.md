# Sentinel: multi-agent AML transaction monitoring

> **Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only.**

## Submission files

| File | What it is |
|---|---|
| [`agents.py`](agents.py) | The agent: a Deep Agents supervisor with four specialist sub-agents, human review and safe memory |
| [`modules/01_sentinel_demo.ipynb`](modules/01_sentinel_demo.ipynb) | The demo notebook, committed with the outputs of a live run |

## What it does

Sentinel helps **AML analysts** in a UK bank's financial-crime team. Rules-based monitoring buries them in false
alerts, and it can't see laundering spread across transactions or across accounts.

1. **Rules (tier 1)** score every transaction deterministically, including a cross-account ring check, and clear
   about 95% of them with no LLM call.
2. **Agents (tier 2):** a triage supervisor (Deep Agents) plans and delegates in parallel to four specialists:
   - **pattern-analyst**: structuring, anomalous credits, round trips;
   - **kyc-precedent**: KYC, sanctions/PEP screening, and analysts' past decisions (precedents);
   - **fund-flow**: the one privileged cross-customer tool, audited, for money-mule rings;
   - **sar-writer**: a structured Suspicious Activity Report draft, from gathered evidence only.
3. **Human (tier 3):** when the agents aren't confident, the graph pauses (`interrupt()`) and asks the analyst. The
   analyst's note becomes a precedent with an expiry date.

**Safeguards are code, not prompts** (`tools/decisions.py`): hard red flags (sanctions, PEP, a confirmed ring) beat
any precedent; a precedent only applies to the same customer, counterparty and pattern, and only until it
expires; a suspected but unconfirmed mule network always goes to a human.

```
transaction ─▶ rules (tier 1) ──low──▶ auto-clear (no LLM)
                   │ flagged
                   ▼
          supervisor (Deep Agent) ──▶ pattern-analyst · kyc-precedent · fund-flow   (in parallel)
                   │
            record_decision (code: hard flags, precedent scope + expiry, confidence checks)
              │             │                    │
          clear         escalate ─▶ sar-writer   unsure ─▶ interrupt() ─▶ analyst ─▶ precedent (long-term memory)
```

## Results (LangSmith experiments, held-out test world)

950 synthetic transactions, 15 planted laundering alerts, model `openai:gpt-6-sol`. The baseline is the same
tier 1 on its own. Rules were tuned on the dev world only.

| | Rules only | Sentinel |
|---|---|---|
| False positives | 30 | **2** (−93%) |
| Alert precision | 33% | **88%** |
| Recall on planted alerts | 100% | **100%** |
| Transactions reaching an LLM | 0% | 4.7% |
| Per investigation | – | 12 model calls · 36k tokens · 22 s median |

The scenario suite (memory safeguards, agent trajectory, SAR groundedness, network scope) scores 1.0 on every
check. Eight evaluation categories, and the known gaps, are shown in the notebook. Caveats: the data, labels
and rules are ours; human answers in the experiments are scripted; the fall in reviews from month 1 to month 2
comes from repeat cases planted in the data. Full write-up: [`DECISIONS.md`](../DECISIONS.md) (DEC-016).

## Quick start

From the **repo root**:

```bash
uv sync --all-packages
cp .env.example .env      # fill in ATTENDEE_NAME, LANGSMITH_API_KEY, LANGSMITH_WORKSPACE_ID
```

Then from `sentinel_aml_agent/`:

| Command | What it does |
|---|---|
| `uv run jupyter notebook modules/01_sentinel_demo.ipynb` | The demo. Pick `.venv/bin/python` as the kernel |
| `REPLAY=1 uv run jupyter notebook …` | The same, replaying recorded model responses (the banner says so). `REPLAY=record` re-records |
| `uv run langgraph dev` | LangGraph Studio, graph `sentinel`. Context `{"user_id": "CUS-0001", "as_of": "2026-10-08T08:58"}`, message `New transaction: TX-000167`; resume a pause with `{"decision": "clear" or "escalate", "note": "…"}` |
| `uv run python scripts/check_scenarios.py --with-mule` | Live behaviour check on the demo scenarios (9 investigations, about 2 minutes) |
| `uv run python scripts/run_experiments.py` | LangSmith datasets and experiments: rules-only vs Sentinel; writes `results/eval_summary.json` |
| `uv run python scripts/annotation_queue.py` | The analyst review queue in LangSmith (`--collect` reads reviews back) |
| `uv run python data/generate.py` | Regenerate the synthetic data (seeded, byte-identical) |
| `uv run python scripts/check_core.py` | No-LLM checks: tools, safeguards, runner (also `check_data`, `check_rules`, `check_graph`) |

Never run plain `uv sync` inside this folder; use `uv sync --all-packages` from the root.

## Layout

```
agents.py              supervisor (submission file)
instructions.md        supervisor prompt
sub_agents/            the four specialists and their prompts
tools/                 customer-scoped tools, the audited network tool, record_decision (safeguards)
rules/scorer.py        tier 1 and the rules-only baseline
utils/                 data access (per world), graph, stream runner, replay, notebook helpers
data/                  generator and generated JSONL tables (world 0 demo; worlds/1 dev, worlds/2 test)
evals/                 evaluators (8 categories), SAR rubric and checks, online evaluator setup
scripts/               experiments, scenario checks, annotation queue, notebook builder
results/               eval_summary.json and saved runs the notebook loads
modules/               the demo notebook
```

## Built on

The organiser's starters (removed before submission, kept in git history): the transaction-monitoring agent's
memory, `interrupt()` review, confidence checks and evaluators; the KYC agent's sanctions/PEP screening; and the
document agent's Deep Agents sub-agent pattern. Design and decisions: [`PLAN.md`](../PLAN.md),
[`DECISIONS.md`](../DECISIONS.md), [`USE_CASE.md`](../USE_CASE.md), [`DEMO_SCRIPT.md`](../DEMO_SCRIPT.md).
