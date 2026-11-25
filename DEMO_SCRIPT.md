# Demo Script — "Sentinel": Multi-Agent AML Transaction Monitoring

**Length:** strict **5:00** (judged), then Q&A.
**Format:** slides on the standard template (provided on the day) + live **Jupyter notebook** demo.
**Presenters:** Narrator (talks) + Driver (runs cells). Keep them separate people.
**One-line pitch:** *Sentinel gives AML analysts a team of agents that investigate only what matters, remember every decision safely, find money-mule networks across accounts, and are measured against rules.*

> Notebook header and SAR drafts carry: *"Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only."*

---

## Run of show

| Time | Segment | Surface |
|---|---|---|
| 0:00–0:40 | Problem, user, value | Slides 1–2 |
| 0:40–1:00 | Architecture + what we built on the starter | Slide 3 |
| 1:00–1:20 | Normal traffic | Notebook |
| 1:20–1:55 | Structuring | Notebook |
| 1:55–2:35 | Human-in-the-loop → precedent | Notebook |
| 2:35–3:00 | Precedent payoff | Notebook |
| 3:00–3:45 | Mule ring + safeguard override | Notebook |
| 3:45–4:30 | Eval results | Notebook / Slide 4 |
| 4:30–5:00 | SAR draft + close | Notebook / Slide 5 |

---

## Slides (on the provided template)

1. **Problem & user:** AML analysts drown in false alerts; money mules and APP-fraud proceeds are spread across accounts; running an LLM on every transaction costs too much. *(Sourced false-positive statistic: about 90-95%, proposed source [Columbia SIPA](https://www.sipa.columbia.edu/detecting-financial-crimes-evaluating-efficacy-automated-transaction-monitoring); check before use.)*
2. **Sentinel in one line + value targets:** ≥ 50% fewer false positives, equal or higher recall, falling analyst workload, ≤ 5% of transactions reach an LLM.
3. **Architecture + delta:** rules → triage supervisor → 4 sub-agents (pattern, KYC & precedent, fund-flow, SAR writer) → confidence router → human-in-the-loop → precedent memory. One-line footer: *"Built on the organiser starter: we added the rules tier, multi-agent investigation, cross-account reasoning, safe precedents, and a baseline eval."*
4. **Eval results:** rules-only vs Sentinel table (real numbers only).
5. **Close:** what it does, what's next (real ML scorer, case-management integration, public AML benchmarks).

---

## Demo customers (seeded, deterministic)

| Customer | KYC profile | Role in demo |
|---|---|---|
| **Daniel Hughes** | Low risk, market trader, cash-heavy, ~£12k cash/month | Structuring |
| **Sophie Clarke** | Low risk, salaried, ~£3,500/month | Ambiguous credit → human → precedent payoff |
| **Marcus Reid** | High risk (PEP-linked) | Round-tripping (one line, or in Q&A) |
| **Mule ring**: Liam Walsh, Chloe Evans, Ben Taylor, Amira Khan, Josh Patel → **Northgate Trading Ltd** | Low-risk students / new accounts → new business account | Fan-in network; Liam has an old analyst clearance that must be overridden |
| ~200 others | Mixed | Background noise + eval set |

---

## Script

### Slides 1–2 — Problem, user, value (0:00–0:40)
**Say:**
> "Fraud teams stop the payment, but the money still lands in a mule network. That's where AML analysts come in, and they spend most of their day clearing false alerts. Rules look at one transaction at a time, so laundering spread across transactions or across accounts slips through. Analysts re-investigate customers they cleared last month. And running an LLM on every transaction is too slow and expensive. Sentinel's goals: halve false positives without missing more laundering, cut analyst workload over time, and send fewer than 5% of transactions to an LLM."

### Slide 3 — Architecture (0:40–1:00)
**Say:**
> "We started from the organiser's transaction-monitoring agent and moved it from card fraud to AML. Rules now clear most traffic. Grey-zone cases go to a triage supervisor built on Deep Agents. It hands the work to four specialists: a pattern analyst, a KYC and precedent agent, a fund-flow network agent, and a SAR writer. If it's confident, it acts. If not, it asks the analyst and remembers the answer."

### Notebook — Normal traffic (1:00–1:20)
**Driver:** Run *Stream: day 1*.
**Output:** Live counter: transactions processed, % cleared by rules, LLM calls so far.
**Say:**
> "Hundreds of transactions, about 95% cleared by rules in milliseconds with no LLM call. The starter sent every one of these to the model."

### Notebook — Structuring (1:20–1:55)
**Output:** Daniel's 4 × £9,500 cash deposits at 3 branches in 48h; the 4th is flagged. Trace summary printed:
1. Supervisor plan → *pattern analyst*
2. Recalls 3 prior deposits, £28,500 total, 3 branches
3. KYC: expected cash ~£12k/**month**; this is £38k in **2 days**
4. Verdict: **Structuring, confidence 0.92 → escalate**

**Say:**
> "Each deposit sits just under the bank's £10,000 cash-monitoring threshold, so each one looks fine alone. The pattern analyst recalls the earlier three. Confidence is high, so it escalates with the evidence already gathered."

### Notebook — Unsure → asks a human (1:55–2:35)
**Output:** Sophie receives £18,000 from a new counterparty. Supervisor verdict: confidence 0.55 → graph **pauses** (`interrupt()`); an `ipywidgets` analyst panel shows the evidence summary and why it's unsure.
**Driver:** Type *"Annual bonus — employer verified via payslip"* → click **Clear**.
**Say:**
> "About five times her monthly salary, from someone new. It could be fraud, a bonus, or a property sale. The agent isn't sure, so it pauses and asks. The analyst's decision becomes a precedent with an expiry date, stored in long-term memory."

### Notebook — Precedent payoff (2:35–3:00)
**Driver:** Run *Fast-forward 10 months*.
**Output:** Sophie receives £19,200 from the same employer → **auto-cleared**: *"Precedent 2026-10-14 'Annual bonus — employer verified', valid until 2027-10-14. Hard red flags: none."*
**Say:**
> "Same case ten months later. The agent clears it on its own and cites the analyst. The analyst doesn't have to investigate it twice."

### Notebook — Mule ring + safeguard (3:00–3:45)
**Output:** Five low-risk accounts receive many small transfers and forward almost everything to **Northgate Trading Ltd** within hours. The 5th forward is flagged. The fund-flow agent's network graph is drawn (matplotlib): senders → 5 mules → Northgate highlighted.
**Then:** *"Liam Walsh: precedent found ('transfers from flatmates', cleared 2026-03-10). **Overridden**: confirmed fan-in network membership (hard red flag)."*
**Say:**
> "No single customer here looks suspicious. The fund-flow agent traced money across accounts and found a mule ring, which per-customer rules can't see. It's the only agent allowed to look across customers, and every call it makes is logged. And note Liam: an analyst cleared him months ago, but the KYC and precedent agent **refused to follow that precedent** because network membership is a hard red flag. Memory helps the agent, but it can't be used to let a launderer through. The same agent also catches round-tripping, for example on our PEP-linked customer."

### Eval results (3:45–4:30)
**Output:** Table loaded from `results/eval_summary.json`, saved from the pre-run LangSmith experiments `rules-only` and `sentinel` (real numbers only):

| Held-out test set (worlds 5-6, [N] tx) | Rules only | Sentinel |
|---|---|---|
| False-positive rate | [X%] | [Y%] |
| Recall on planted cases | [X / N] | [Y / N] |
| Decision accuracy · review routing (starter evaluators) | [a · r] | [a · r] |
| Analyst reviews, month 1 → month 2 | [A → A] | [A → B] |
| Correct precedent overrides | n/a | [K / K] |
| % tx reaching LLM · cost / 1k tx | 0% · £0 | [Z%] · [£C] |

**Driver:** Flash the LangSmith experiment comparison (3–5 seconds).
**Say:**
> "On a held-out labelled set, Sentinel cut false positives by [X]% while catching [as many / more] planted cases. The starter's own evaluators improved too. Analyst reviews dropped from month one to month two as precedents built up, and only [Z]% of transactions ever reached an LLM. An LLM-as-judge also scores every SAR draft."

### SAR draft + close (4:30–5:00)
**Output:** SAR draft for Daniel (subject, pattern, timeline, evidence, narrative, cited precedents/overrides), stamped *"Draft for analyst review, not regulatory advice."*
**Say (final line):**
> "Rules handle most of the volume. Agents investigate the grey zone, a human steps in only when the agents are unsure, every decision is remembered safely, and we measured that it beats rules. That's Sentinel."

---

## Q&A prep

| Likely question | Answer |
|---|---|
| What did you add beyond the starter? | Rules tier (the starter sent every transaction to the LLM), a Deep Agents supervisor + 4 sub-agents, cross-account network reasoning, structured precedents with safeguards, SAR drafting, AML data with a labelled generator, and a rules-only baseline plus 6 new eval metrics. We kept the starter's memory, `interrupt()` and evaluators. |
| Why AML and not card fraud? | Fraud is decided one payment at a time. AML needs reasoning across transactions, across accounts and over time, which is where agents and memory add the most. Mule networks are also a top UK priority. |
| Why agents and not just an ML model? | ML scores; it can't investigate, explain itself, weigh an analyst's written note, or decide to ask a human. We use rules (or ML) to score and agents to investigate. |
| The starter limits tools to one customer. Doesn't the network agent break that? | Deliberately and narrowly. Only the fund-flow agent has one privileged tool; it returns graph summaries, not profiles, and every call is logged. Network laundering can't be found without that view. |
| What if the analyst's precedent is wrong? | Precedents expire, apply only to the exact customer + counterparty + pattern, and can never override hard red flags. We showed this with Liam. Every cited precedent is in the audit trail. |
| How do you stop hallucination? | Verdicts are structured output grounded in tool results; the SAR writer has no tools and only uses the evidence it's given; LLM-as-judge checks SAR drafts for invented facts. Safeguards (hard flags, precedent scope and expiry) are enforced in code, not by the model. |
| You said checks only add oversight. How did Sophie's second credit auto-clear? | That's the one stated exception. A valid precedent for the same customer, counterparty and pattern, with no hard red flags, satisfies the grey-zone check, because an analyst already decided that exact case. Expired or out-of-scope precedents don't count, and hard flags always override. |
| What if the agent wants to clear a case with a hard red flag? | It can't. The code forces human review: an analyst decides every hard-flag case the agent would clear. |
| Can the network agent be pointed at any customer? | No. Its starting account comes from the run's context, not from the model, and every call is written to an audit log. |
| Cost at bank scale? | About 95% of transactions never touch an LLM. We show % of transactions reaching an LLM and cost per 1,000 transactions from the eval. |
| Customer data privacy with LLMs? | Synthetic data here. In production: mask identifiers before LLM calls, keep raw data inside the bank, and use a private model deployment through the gateway. |
| Is your eval just testing your own synthetic data? | Yes, and we say so. It is a controlled benchmark with a held-out split and a fair baseline using the same rules, plus the starter's own evaluators. Next step: public AML datasets (e.g. IBM AML synthetic) and real bank pilots. |
| Why multi-agent instead of one agent? | Each specialist has a narrow toolset and prompt, so it's easier to test, evaluate and swap; the supervisor only combines findings. It also contains the cross-customer privilege to a single agent. |
| What does a regulator see? | Every verdict has its evidence, tool calls, cited/overridden precedents and confidence in the trace and the `decisions` audit store, all exportable. |

---

## Points judges should come away with
1. **Relevance:** a real UK FSI problem (money mules, false positives), a named user (AML analyst), measurable value vs baseline
2. **Clear delta over the starter:** rules tier, multi-agent, cross-account reasoning, safe precedents, SAR, baseline eval
3. **Multi-agent:** supervisor + 4 sub-agents, each doing real work
4. **Memory:** across transactions and across analyst decisions, with safeguards
5. **Evals:** starter evaluators + baseline + new metrics + LLM-as-judge in LangSmith
6. **Presentation:** clean 5:00, deterministic run, confident Q&A

## Build requirements derived from this script
All paths below are inside `sentinel_aml_agent/`. File-level detail, contracts and the timetable are in [PLAN.md](PLAN.md).
- [ ] AML schema in `data/transactions.jsonl` (`account_id`, `counterparty_id`, `direction`, `txn_type`, `branch`) + `pattern`, `expect_override`, `month` in `analyst_labels`
- [ ] `data/generate.py`: seeded worlds. World 0 is the demo cast (Daniel, Sophie ×2, Marcus, mule ring + Liam's old precedent in `seed_precedents.jsonl`); worlds 1-4 dev, 5-6 test, ~200 noise customers each
- [ ] `rules/scorer.py` before `agent.invoke` (also the rules-only baseline); global timestamp-ordered stream in `utils/stream.py`
- [ ] `agents.py` (submission file; holds the code, no `agent.py`): `create_deep_agent` supervisor + pattern analyst, KYC & precedent agent (screening copied from `01_kyc_agent`), fund-flow agent (privileged, audited graph tool), SAR writer
- [ ] Decision vocabulary `clear | escalate` in `record_decision`, `instructions.md`, labels and evaluators
- [ ] Precedent store replacing free-text `customer_notes`: expiry, scope match, hard-flag override, override logging, all enforced in `record_decision`
- [ ] `scripts/check_scenarios.py`: every scripted demo transaction lands in the expected tier and verdict
- [ ] Notebook `modules/01_sentinel_demo.ipynb` (submission file; imports from `agents.py`): header disclaimer, `REPLAY` toggle, stream cells, live counter, trace summaries, `ipywidgets` analyst panel, Fast-forward cell, network graph (NetworkX + matplotlib), eval results table, SAR draft
- [ ] Extend `scripts/run_experiments.py` + `evals/scoring_evals.py`: rules-only baseline, new metrics, LLM-as-judge for SARs (`evals/sar_judge.py`); save `results/eval_summary.json`
- [ ] LangSmith tracing enabled; `MODEL_NAME="openai:gpt-6-sol"`
- [ ] Repo: forked, `README.md` updated, `.env` never committed, starter folders removed at the 15:45 freeze
- [ ] Slides 1–5 on the provided template

## Demo-day safety net
- **Deterministic mode:** fixed seeds, IDs and timestamps; scripted scenario order. Temperature 0 where the model accepts it
- **Pre-computed eval:** run it beforehand; the notebook only loads `results/eval_summary.json`
- **Pre-run notebook:** keep a fully executed copy open in a second tab as a fallback
- **Replay mode, on by default on stage:** `REPLAY=1` uses LLM responses cached from a good rehearsal run. It only replays if prompts are identical, so verify it on a fresh kernel beforehand. Run live only if Daniel's case takes under ~30s
- **Backup video:** screen-record a clean full run the night before
- **Rehearse to 4:45** so there's slack for latency
