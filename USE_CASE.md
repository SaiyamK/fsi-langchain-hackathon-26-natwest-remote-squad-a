# Sentinel: Multi-Agent AML Transaction Monitoring

*Use-case write-up for the team · LangChain FSI Hackathon (NatWest) · 2026-11-25*
*Companion doc: [DEMO_SCRIPT.md](DEMO_SCRIPT.md) · Code: `sentinel_aml_agent/` · Built from the organiser starter `02_transaction_monitoring_agent` · Plan: [PLAN.md](PLAN.md)*

> Outputs of this project are drafts for analyst review, **not legal, compliance or regulatory advice**. All data is synthetic.

## TL;DR

**Sentinel** is a multi-agent anti-money-laundering (AML) transaction monitoring system for **AML analysts in a UK bank's financial crime team**. Deterministic rules clear most transactions. A triage supervisor (Deep Agents) sends only grey-zone cases to specialist sub-agents: pattern analysis, KYC and precedents, fund-flow networks, and SAR drafting. A human is asked only when the agents are genuinely unsure. Sentinel **remembers** each customer's history and every analyst decision, with safeguards so that memory can never be used to clear a launderer. It **reasons across customers** to find money-mule rings. We **measure** it against a rules-only baseline in LangSmith.

We build on the organiser's transaction-monitoring starter. We reuse its memory, human-review and eval patterns, and move the domain from card fraud to AML.

## Who it's for

| User | Today's pain | What Sentinel gives them |
|---|---|---|
| **AML analyst** (primary) | Most of the day goes on clearing false alerts; customers cleared before get re-investigated; SAR narratives are written by hand | Fewer, better alerts with evidence pre-assembled; past decisions remembered; one-click SAR draft |
| **Head of financial crime / MLRO** (buyer) | Analyst headcount grows with volume; regulators expect every decision explained | Measurable drop in alert volume at equal or better detection; full audit trail of every decision |

## Why it matters

- Industry sources commonly put rules-based AML false-positive rates at about **90-95%** (proposed citation: [Columbia SIPA](https://www.sipa.columbia.edu/detecting-financial-crimes-evaluating-efficacy-automated-transaction-monitoring); check the page before it goes on a slide). Most analyst time goes on harmless alerts.
- **Money mules and authorised push payment (APP) fraud proceeds** are a top UK financial-crime priority. Mule networks spread money across many low-risk accounts, so rules that look at one transaction or one customer miss them.
- Laundering is spread across transactions (structuring) and across accounts (mule rings, round-tripping).
- Regulators expect every alert decision to be explainable and auditable.
- Calling an LLM on every transaction is too slow and too expensive at bank volumes.

**Bridge from the starter's fraud framing (one line in the pitch):** *"Fraud teams stop the payment; the money still lands in a mule network. That's where Sentinel works."*

**Measurable value we'll show** (targets; we report actual results from the eval):
- **≥ 50% fewer false-positive alerts** than rules-only
- **Equal or higher recall** on planted laundering cases
- **Analyst reviews fall from month 1 to month 2** as precedents build up
- **≤ 5% of transactions reach an LLM**, with cost per 1,000 transactions shown

## Why agents, not just ML

ML models can *score* a transaction. They can't *investigate* it: pull history, check KYC, trace funds across accounts, weigh an analyst's written note from last year, explain the verdict in words, or decide to ask a human. Sentinel uses rules or ML for scoring and agents for investigation.

## Solution

Every transaction goes through one of three tiers, so the expensive steps run only where they add value:

| Tier | Who decides | When | Outcome |
|---|---|---|---|
| 1. Rules | Deterministic scorer | Every transaction; rule score below 30 ends here (target ~95%) | Auto-clear, no LLM call |
| 2. Agents | Supervisor + specialist sub-agents | Rule score 30 or above | `clear` or `escalate` when confident |
| 3. Human | AML analyst | Agent confidence below 0.7, any deterministic check fires, or a hard red flag with a `clear` verdict | `clear` / `escalate` with a note, which is saved as a precedent |

**Decision vocabulary:** `clear | escalate`. Escalated cases get a SAR draft. AML monitoring reviews transactions after they happen and raises alerts; it doesn't block payments. This replaces the starter's card-fraud `approve | block`.

What makes it different:
1. **Multi-agent investigation:** a supervisor plans the investigation and hands parts of it to specialist sub-agents.
2. **Rules first:** the starter sends every transaction to the LLM; Sentinel sends only about 5%.
3. **Remembers transactions:** it recalls a customer's recent activity before judging the current one.
4. **Remembers decisions, safely:** analyst verdicts become cited precedents. Precedents expire and never override hard red flags.
5. **Reasons across customers:** the fund-flow agent traces money between accounts to find mule rings.
6. **Proves it works:** evaluated in LangSmith against a rules-only baseline.
7. **Hands off a filing-ready output:** a SAR draft with evidence, timeline, narrative and cited precedents.

## Architecture

```
Transaction stream (synthetic)
      │
      ▼
┌──────────────┐  low score   ┌─────────────┐
│ Rule scorer  │─────────────▶│ AUTO-CLEAR  │
└──────┬───────┘              └─────────────┘
       │ grey zone / high
       ▼
┌────────────────────────────────────────────────────────┐
│ TRIAGE SUPERVISOR (Deep Agent: plans, delegates,       │
│ combines findings → verdict + confidence + evidence)   │
│                                                        │
│  ├─▶ Pattern analyst      short-term memory, typology  │
│  │                        checks (structuring, spikes) │
│  ├─▶ KYC & precedent agent  KYC profile, sanctions/PEP │
│  │                        precedents, hard-flag rules  │
│  ├─▶ Fund-flow / network  cross-account graph:         │
│  │   agent                round-trips, mule fan-in     │
│  └─▶ SAR writer           structured SAR draft         │
│                                                        │
│  record_decision (code): hard flags, precedent scope + │
│  expiry, confidence checks → route                     │
└──────┬────────────────┬────────────────┬───────────────┘
  conf. high,      conf. high,      conf. middling, a check
  clear            escalate         fired, or hard flag + clear
                                         │
       ▼                ▼                ▼
  AUTO-CLEAR       ESCALATE +     interrupt() → analyst
  (cites           SAR draft          │ clear / escalate + note
   precedent)                         ▼
                                resume graph → save precedent
                                to long-term memory
```

### Agents

| Agent | Responsibility | Tools / memory |
|---|---|---|
| Triage supervisor | Plans, delegates to specialists, combines findings, sets verdict + confidence | `create_deep_agent`, `task` tool for sub-agents |
| Pattern analyst | Multi-transaction typologies for one customer (structuring, spikes, anomalous credits) | `get_recent_transactions(days=30)` (customer-scoped, up to the transaction's timestamp), KYC profile |
| KYC & precedent agent | Customer risk context; sanctions/PEP screening; finds applicable precedents and reports which are valid, expired or out of scope; reports hard flags | KYC profile, `screen_customer` (sanctions/PEP lists copied from `01_kyc_agent`), `find_precedents` |
| Fund-flow / network agent | Traces money across accounts; finds round-trips and fan-in rings | **The one privileged cross-customer tool**, `trace_fund_flows`, over a NetworkX graph |
| SAR writer | Drafts the Suspicious Activity Report from the evidence it's given | No tools; structured output (Pydantic `SarDraft`) |

The supervisor calls only the specialists the rule reasons call for, in the same turn so they run in parallel. It always calls the KYC & precedent agent. Sub-agents never pause for a human: only the supervisor calls `record_decision`, which holds the `interrupt()`, as in the starter.

**Design note: the cross-customer exception.** The starter deliberately limits every tool to the customer in the run's context, so the agent can't read another customer's data. Only the fund-flow agent gets one explicit, privileged tool that can see across accounts. Its starting account comes from the run's context, not from the model, so the model can't point it at an arbitrary customer. It returns graph summaries (accounts, flows, timings), never customer profiles, and every call is written to a `network_audit` log. We say this openly in the demo and in Q&A.

### Memory model
- **Short-term (checkpointer, one thread per customer, as in the starter):** the conversation for each customer. The pattern analyst reads the customer's recent transactions (last 30 days) from the database, up to the current transaction's timestamp, so it doesn't depend on chat history length.
- **Long-term (LangGraph store):** the starter's free-text `customer_notes` become **structured precedents** keyed by customer + counterparty + pattern, `{decision, note, analyst, created_at, expires_at}`. Every decision, including rule-tier auto-clears, also goes in the `decisions` audit store, as in the starter. Old precedents (such as Liam's) are loaded from `seed_precedents.jsonl` at the start of a run.
- **Reference data:** KYC profile per customer (risk rating, PEP flag, expected monthly credits and cash, occupation).
- **"Now" is the transaction's timestamp,** not the wall clock. Expiry checks and the network graph use it, which makes Fast-forward deterministic and stops the network tool seeing future transactions.
- **One global stream:** transactions from all customers are processed in timestamp order (one thread per customer). The starter processed one customer at a time, which can't detect a mule ring.

### Memory safeguards (enforced in code, not by the LLM)
`record_decision` applies these deterministically. The agents explain; the code decides what's allowed.
- **Expiry:** each precedent has an `expires_at` (default 12 months). Once expired, the agent can show it but can't rely on it to auto-clear.
- **Hard red flags always win:** a sanctions hit, PEP status, or confirmed mule-network membership overrides any precedent. The trace records "precedent found → overridden (reason)".
- **Hard flag but the agent says `clear` → human in the loop:** the agent can never clear a hard-flag case on its own.
- **Scope match:** a precedent applies only to the same customer + counterparty + pattern.
- **Audit trail:** every verdict logs the precedents it cited or overrode; the SAR draft includes them.
- Same principle as the starter's confidence checks: **deterministic checks can add human oversight but never remove it,** with one stated exception. A valid, in-scope precedent with no hard flags satisfies the grey-zone check, because a human already decided this exact case. That is what lets Sophie's second credit auto-clear. We say so in Q&A.

### Confidence routing (thresholds to tune; starter default 0.7)
- High-confidence `escalate` → auto-escalate + SAR draft
- High-confidence `clear` → auto-clear
- Hard red flag with a `clear` verdict → human-in-the-loop via `interrupt()`
- Otherwise, or any deterministic check fires → human-in-the-loop via `interrupt()`

## Detection scenarios

| Pattern | Example in demo | What catches it |
|---|---|---|
| Structuring | 4 × £9,500 cash deposits at 3 branches in 48h, just under the bank's £10,000 cash-monitoring threshold (Daniel Hughes) | Pattern analyst + KYC baseline |
| Anomalous large credit | £18,000 from a new counterparty, about 5× monthly salary (Sophie Clarke) | Uncertainty → analyst; months later auto-cleared from precedent |
| Round-tripping | £250k out, £240k back via a different account (Marcus Reid, PEP-linked) | Fund-flow agent + tighter KYC threshold |
| Money-mule ring (fan-in) | 5 low-risk accounts receive many small transfers and forward almost all of it within hours to one new business account (Northgate Trading Ltd) | Fund-flow agent graph; KYC & precedent agent overrides an old clearance on one mule (Liam Walsh) |

## Evaluation

- **Dataset:** the synthetic generator labels every transaction (`decision` `clear` / `escalate`, `risk_score`, `ambiguous`, plus new `pattern`, `expect_override` and `month`, extending the starter's `analyst_labels` schema). It generates seeded "worlds": about 200 background customers over 2 months each, with planted structuring, round-tripping, mule-ring and anomalous-but-benign cases. **World 0** is the demo cast and is not in the eval. **Worlds 1-4** are dev (tuning); **worlds 5-6** are the held-out test (reporting). One dataset example is **one world** (its whole global stream), because decisions depend on memory and the mule ring spans customers. Outputs keep the starter's shape, so its evaluators run unchanged.
- **Mule labels:** forwards made before the ring can be confirmed are labelled `ambiguous: true, decision: escalate`, so the right outcome is "asks a human".
- **Baseline:** the same rule scorer on its own (rules-only).
- **Evaluators:**

| Evaluator | Source | Why it matters | Target |
|---|---|---|---|
| `decision_accuracy` | Starter (kept) | Matches analyst decisions | Higher than rules-only |
| `score_alignment` | Starter (kept) | Risk scores close to analysts' | Higher than rules-only |
| `review_routing` | Starter (kept) | Asks a human exactly when it should | High |
| False-positive rate | New | Analyst time wasted | ≥ 50% lower than rules-only |
| Recall on planted cases | New | Laundering missed | ≥ rules-only |
| Analyst reviews, month 1 → month 2 | New | Learning from precedents | Falls |
| Correct precedent overrides | New | Memory safeguards work | 100% on planted cases |
| % tx reaching LLM; cost / 1,000 tx | New | Production viability | ≤ 5% |
| SAR draft quality (LLM-as-judge) | New | Complete, evidence-cited, no invented facts | Pass on all escalations |

- **Tooling:** extend the starter's `scripts/run_experiments.py`. The starter already compares experiments (baseline vs threshold 0.8); we run `rules-only` vs `sentinel` the same way, on dataset `<LANGSMITH_PROJECT>-sentinel`. LLM calls and tokens are counted with `get_usage_metadata_callback()`.
- **Rule:** we show only numbers from a real eval run. Run it beforehand, save it to `results/eval_summary.json`, and load that file in the notebook; never run it live.

## Starter: reused vs new

| Area | Reused from the starter | New in Sentinel |
|---|---|---|
| Agent structure | `agent.py` (renamed to `agents.py`), `tools/`, `utils/`, `instructions.md`, `ToolRuntime` context | Deep-agent supervisor + 4 sub-agents |
| Memory | Checkpointer per customer thread; store with `customer_notes` + `decisions` | Structured precedents with expiry, scope, override |
| Human review | `interrupt()` in `record_decision` + deterministic confidence checks | Hard-red-flag checks; precedent-override logging |
| Data | `utils/db.py` JSONL tables | AML schema fields (`account_id`, `counterparty_id`, `direction`, `txn_type`, `branch`); labelled generator; `pattern`, `expect_override`, `month` in labels; seed precedents |
| Screening | Sanctions/PEP lists + tools copied from `01_kyc_agent` | Wired into the KYC & precedent agent |
| Evals | Dataset builder, 3 evaluators, experiment runner | Rules-only baseline, 6 new metrics, LLM-as-judge for SARs |
| Pre-filter | — (every transaction goes to the LLM) | Deterministic rule scorer |
| Network | — (tools limited to one customer) | Privileged cross-customer graph tool |
| Output | One-sentence decision | SAR draft |
| Platform | LangSmith gateway (`MODEL_NAME`), tracing, `langgraph dev`, `.env`/`.gitignore` | — |

## Deliverables (per hackathon rules)

Submitted in the **forked GitHub repo**, inside `sentinel_aml_agent/`. The organiser starter folders (`01_`-`03_`) are removed before submission, so everything Sentinel reuses from them is copied into `sentinel_aml_agent/`.

The two required submission files:

- **`agents.py`**: the name the rules require. It holds the real supervisor code (the starter's `agent.py` is renamed, not kept alongside), and `langgraph.json` points at `./agents.py:agent`
- **Jupyter notebook** `modules/01_sentinel_demo.ipynb`: the demo itself. It imports from `agents.py`, so it runs the submitted file

Supporting files:
- Data generator `data/generate.py` + generated JSONL tables in `data/`
- Eval scripts (`scripts/run_experiments.py`, `scripts/check_scenarios.py`) and the saved `results/eval_summary.json`
- The starter folders and their `[tool.uv.workspace]` entries are removed at the feature freeze (15:45), then `uv sync --all-packages` and the notebook are re-run to prove Sentinel is self-contained
- Updated `README.md`; `.env` stays out of git (the starter's `.gitignore` already handles this)
- Slides on the provided template (template shared on the day)

## Scope

**In scope**
- Labelled synthetic AML data generator (seeded demo customers + ~200 background customers)
- Global stream simulation (all customers, timestamp order) in the notebook with time-skip (Fast-forward), building on the starter's `transaction_stream(start, end)` and `process_transactions`
- Replay mode (`REPLAY=1`, a cached copy of a good run's LLM responses) for the stage demo
- Rule scorer → supervisor + sub-agents → confidence router → `interrupt()`
- Short- and long-term memory with safeguards
- Analyst prompt in the notebook (`ipywidgets`) to resume the graph
- Network graph visual (NetworkX + matplotlib)
- SAR draft generation with a "not regulatory advice" stamp
- Eval harness extensions + LangSmith experiments; tracing throughout

**Out of scope**
- Card fraud scenarios (the starter's domain; one bridge line in the pitch only)
- Web app / custom UI (the notebook is the demo)
- Real or confidential customer data (ground rule)
- Production ML scoring, core-banking integration, real SAR filing, auth, scaling

## Tech stack

| Layer | Choice |
|---|---|
| Base | `sentinel_aml_agent/`, copied from the organiser starter `02_transaction_monitoring_agent` (+ screening copied from `01_kyc_agent`, Deep Agents pattern from `03_document_summary_agent`) |
| Orchestration | LangGraph (checkpointer, store, `interrupt()`) |
| Agents | LangChain Deep Agents (`create_deep_agent` supervisor + sub-agents) |
| LLM | `openai:gpt-6-sol` via the LangSmith LLM Gateway, set by `MODEL_NAME` in `.env` (verified through the gateway; starter default was `openai:gpt-6-luna`) |
| Graph analysis | NetworkX |
| Observability & eval | LangSmith (tracing, datasets, experiments, LLM-as-judge) |
| Demo surface | Jupyter notebook + `ipywidgets` + matplotlib |
| Data | Starter's JSONL tables + labelled synthetic generator |

## Success criteria (mapped to judging, 30 points)

| Judging area | What judges must see |
|---|---|
| **Use case relevance & impact** | A real UK FSI problem (AML false positives, money mules); a named user (AML analyst); measurable value: false positives, recall, analyst workload and cost vs baseline |
| **Technical complexity** | LangChain fundamentals (tools, `ToolRuntime`, structured output, checkpointer, store); **multi-agent** supervisor + 4 sub-agents; **memory** short-term + long-term with safeguards; **evals**: starter evaluators + baseline + new metrics + LLM-as-judge; a clear delta over the starter |
| **Presentation** | A strict 5:00 demo that runs deterministically; slides on the standard template; prepared Q&A answers (see [DEMO_SCRIPT.md](DEMO_SCRIPT.md)) |

## Workstreams

| # | Workstream | Delivers | Owner |
|---|---|---|---|
| 1 | Data & eval | AML schema, labelled generator (incl. mule ring), dev/test split, eval extensions + experiments | Kiro (Claude) |
| 2 | Rules & routing | Rule scorer (also the baseline), global stream runner, confidence router, hard-flag checks, `interrupt()`/resume | Kiro (Claude) |
| 3 | Agents & memory | Supervisor, 4 sub-agents, cross-customer graph tool, precedent store + safeguards, SAR writer | Kiro (Claude) |
| 4 | Notebook, slides & pitch | Demo notebook, network graph visual, slides on template, rehearsal, Q&A prep, backup video | Kiro (Claude) builds the notebook; the presenters own slides, rehearsal and delivery |

With one owner, the workstreams run in sequence rather than in parallel: data → rules → agents → notebook within each time slot, with the 13:00 and 15:45 checkpoints as hard gates. The timetable, contracts and cut list are in [PLAN.md](PLAN.md).

**Start with workstream 1:** the scenarios, the eval and the demo all depend on the data.

## Risks and fallbacks

- **LLM latency or API failure on stage** → replay mode with cached responses (`REPLAY=1`, on by default on stage) + backup video. At the 13:00 checkpoint, time Daniel's case from rule flag to verdict; above ~30s it won't fit live.
- **Agents give a different verdict each run** → fixed seed, scripted scenario order, replay cache. Temperature 0 where the model accepts it (some reasoning models reject it).
- **Sub-agent tools may not see the run's context or store** → checked first at 10:00; fallback is tools built per run, or moving lookups to the supervisor. The model never passes `user_id`.
- **Scope creep** → build only what [DEMO_SCRIPT.md](DEMO_SCRIPT.md) needs; drop items in the order of the cut list in [PLAN.md](PLAN.md).
- **Deep Agents rough edges** → fall back to the starter's `create_agent` pattern with the specialists as plain tools.
- **Eval numbers disappoint** → tune on dev split, report on held-out test; present honest numbers.
- **Mule-ring detection too slow live** → pre-compute the graph; the fund-flow agent queries it as a tool.
- **Eval runtime/cost** (the starter runs the LLM on every transaction in every stream) → the rules tier cuts LLM calls; keep the eval set small enough to run in minutes.

## Ground rules checklist

- [ ] Synthetic data only, with no real customer or confidential data
- [ ] `.env` and API keys never committed (the starter's `.gitignore` covers `.env`; check before every push)
- [ ] "Not legal / compliance / regulatory advice" stamped on the notebook header and SAR drafts
- [ ] Setup complete and LangSmith invite accepted (was due 24 Nov, so confirm everyone has done it)

## Open questions

- [x] Code folder: `sentinel_aml_agent/`, self-contained; starters removed before submission
- [x] Submission files: `agents.py` holds the supervisor code (no `agent.py`); notebook `modules/01_sentinel_demo.ipynb` imports from it
- [x] Model: `MODEL_NAME="openai:gpt-6-sol"`
- [x] Owners: Kiro (Claude) for all four workstreams
- [x] Eval dataset: seeded worlds of ~200 customers; worlds 1-4 dev, 5-6 test, world 0 demo only
- [x] Mule forwards before the ring is confirmable: `ambiguous` + `escalate`
- [x] Hard flag + agent says `clear`: human in the loop
- [ ] Source for the false-positive-rate statistic on slides. Proposed: [Columbia SIPA, "Detecting Financial Crimes: Evaluating the Efficacy of Automated Transaction Monitoring"](https://www.sipa.columbia.edu/detecting-financial-crimes-evaluating-efficacy-automated-transaction-monitoring) (about 90-95% on average). Check the page before it goes on a slide
