# Demo Script: Sentinel, multi-agent AML transaction monitoring

**Team:** Chain & Grab · **Length:** strict **5:00** (judged), then Q&A · **Timings:** the flight deck's demo shape
(HACKATHON.md).
**Format:** slides on the "FSI Hackathon — Submission Template", named `HACK_NATWEST_CHAINANDGRAB`, plus the live
notebook `sentinel_aml_agent/modules/01_sentinel_demo.ipynb`.
**Presenters:** a **Narrator** who talks and a **Driver** who runs cells. Keep them different people.
**One-line pitch:** *Sentinel gives AML analysts a team of agents that investigate only what matters, remember
every decision safely, find money-mule rings across accounts, and are measured against rules.*

> The notebook header and every SAR draft carry: *"Draft for analyst review, not legal, compliance or regulatory
> advice. Synthetic data only."*

All numbers below are real, from the LangSmith experiments in DECISIONS.md DEC-016 and the ROI estimate in
README.md. Don't round them up on stage.

---

## Run of show

| Time | Segment (flight deck) | Surface |
|---|---|---|
| 0:00–0:30 | User, problem and why it matters | Slide 1 |
| 0:30–1:00 | What the agent does | Slide 2 |
| 1:00–2:45 | End-to-end demonstration | Notebook sections 1–5 |
| 2:45–3:30 | LangSmith trace and evaluation | LangSmith + notebook sections 6–7 |
| 3:30–4:15 | Architecture, controls and human review | Slide 3 |
| 4:15–4:45 | Results, value and limitations | Slide 4 |
| 4:45–5:00 | Conclusion, next step and repository link | Slide 5 |

---

## Before going on stage

1. From `sentinel_aml_agent/`, record a fresh live run: `REPLAY=record uv run jupyter notebook modules/01_sentinel_demo.ipynb`, then **Run All**. That takes about 4 minutes and fills the replay cache.
2. Restart the kernel with `REPLAY=1` (`REPLAY=1 uv run jupyter notebook …`), then **Run All** up to section 3 so the analyst panel is waiting. The banner must read **"REPLAY: model responses recorded from the live run at …"**. Leave it on screen: it's the honest label (DEC-003).
3. Open these tabs in this order:
   - the notebook;
   - LangSmith → the tracing project → Daniel's investigation trace (use the notebook's trace link);
   - LangSmith → dataset `…-sentinel-benchmark` → **Compare** `rules-only-test-*` vs `sentinel-test-*`;
   - the slides;
   - a fully executed copy of the notebook (fallback).
4. Have the fallback screenshots ready (`sentinel_aml_agent/results/screenshots/`).
5. Rehearse to **4:45**.

---

## Slides (on the submission template)

1. **Problem and user.**
   - AML analysts in a UK bank's financial-crime team spend most of their time clearing false alerts. Rules-based monitoring is commonly put at 90–95% false positives ([Columbia SIPA](https://www.sipa.columbia.edu/detecting-financial-crimes-evaluating-efficacy-automated-transaction-monitoring); check the page first).
   - Mule rings spread money across many low-risk accounts.
   - Calling an LLM on every transaction is too slow and too costly.
2. **What Sentinel does.**
   - Rules first, so about 95% of transactions never reach an LLM.
   - A Deep Agents supervisor and four specialists investigate the rest.
   - A human decides when the agents are unsure, and the answer becomes a precedent.
   - Memory can't clear a launderer.
3. **Architecture and controls.**
   - Rules tier (with ring check) → supervisor → pattern analyst · KYC & precedent · fund-flow · SAR writer → `record_decision` → `interrupt()` → analyst → precedent store.
   - Controls in code: hard flags beat precedents; scope and expiry; an unconfirmed mule network goes to a human; the one audited cross-customer tool; call limits per investigation.
   - Footer: *"Built from the organiser starters: we added the rules tier, multi-agent investigation, cross-account reasoning, safe precedents, SAR drafting and a rules-only baseline eval."*
4. **Results, value and limitations.**
   - KPI table: false positives **30 → 2**; precision **33% → 88%**; recall **100% = 100%**; **4.7%** of transactions reach an LLM.
   - ROI: **37% less analyst time** per million transactions, about **8,800 hours or £395k**, with the assumptions shown.
   - Limitations: synthetic data; scripted human answers in the evals; a small benchmark.
5. **Close.** One sentence on what it does. Next steps: an ML scorer in tier 1, case-management integration, public AML benchmarks. The repository link: https://github.com/SaiyamK/fsi-langchain-hackathon-26-natwest-remote-squad-a.

---

## Demo customers (world 0, seeded)

| Customer | Profile | Role |
|---|---|---|
| **Daniel Hughes** | Market trader, about £12k cash a month | Structuring: four £9,500 deposits, three branches, 48 hours |
| **Sophie Clarke** | Salaried, about £3,500 a month | £18,000 from a new payer → human → precedent; £19,200 ten months later → auto-cleared |
| **Mule ring:** Liam Walsh, Chloe Evans, Ben Taylor, Amira Khan, Josh Patel → **Northgate Trading Ltd** | Students → a new business account | 4th forward goes to a human; the ring is confirmed at the 5th; Liam's old clearance is overridden |
| Marcus Reid | PEP-linked | Round trip (Q&A only) |
| About 35 others | Mixed | Background traffic |

---

## Script

### 0:00–0:30 · User, problem and why it matters (Slide 1)
**Say:**
> "We're Chain & Grab. Our user is the AML analyst. Rules-based monitoring buries them in false alerts, around nine
> in ten by common industry estimates. And the laundering that matters is spread out: across several deposits, or
> across a ring of mule accounts that each look fine alone. Putting an LLM on every transaction would be far too
> slow and expensive. So we built Sentinel."

### 0:30–1:00 · What the agent does (Slide 2)
**Say:**
> "Rules go first and clear about 95% of traffic with no LLM call. What's left goes to a supervisor built on Deep
> Agents, which plans and sends four specialists out in parallel: patterns, KYC and past decisions, money flows
> across accounts, and a SAR writer. If the agents are sure, they act. If they're not, they ask the analyst, and
> the answer becomes a precedent. And no precedent can ever clear a launderer."

### 1:00–2:45 · End-to-end demonstration (Notebook)

**1:00–1:10 · Section 1, normal traffic** *(already run)*.
**Driver:** Point at the counter and the banner.
**Say:**
> "Five days of transactions: about 96% cleared by rules in milliseconds. The few flagged went to the agents, who
> found the legitimate explanation. This is a replay of a live run, and the banner says so."

**1:10–1:35 · Section 2, structuring.**
**Driver:** Scroll to Daniel's deposits 3 and 4.
**Say:**
> "Daniel deposits £9,500 cash, four times, at three branches in two days. That's just under the £10,000
> monitoring threshold every time. Deposit three already raises an alert, and deposit four has the full picture:
> £38,000 in two days against £12,000 expected a month. The supervisor delegated to the pattern analyst and the KYC
> agent in parallel, escalated with confidence 0.86, and the SAR writer drafted the report. We'll see that at the
> end."

**1:35–2:05 · Section 3, unsure, so it asks a human.**
**Driver:** In the analyst panel, type *"Annual bonus — employer verified via payslip"* → click **Clear**.
**Say:**
> "Sophie receives £18,000, five times her salary, from someone who's never paid her. Bonus? Fraud? The agents
> aren't sure, so the graph pauses and asks. The analyst checks the payslip and clears it, and that note is saved
> as a precedent with a twelve-month expiry."

**2:05–2:15 · Section 4, the precedent pays off.**
**Driver:** Scroll to TX-001130.
**Say:**
> "Ten months later, the same employer pays £19,200. The agents find the analyst's precedent, still valid, with no
> red flags, and clear it on their own. Nobody investigates it twice."

**2:15–2:45 · Section 5, mule ring and safeguard override.**
**Driver:** Scroll through the three verdicts, then the network graph.
**Say:**
> "Five student accounts pass almost everything on to a new business account within hours. On the fourth forward
> the ring isn't confirmed yet, so a human decides. At the fifth, our graph check confirms it, and the fund-flow
> agent, the only one allowed to look across customers and fully audited, explains it. Then Liam: an analyst
> cleared his 'flatmate' transfers in March. Ring membership is a hard red flag, so the code overrides that
> precedent. Memory helps, but it can't let a launderer through."

### 2:45–3:30 · LangSmith trace and evaluation
**Driver:**
1. Switch to the LangSmith trace of Daniel's investigation, about 15 seconds. Point to the supervisor's plan (`write_todos`), the parallel `task` calls to the sub-agents, and `record_decision`.
2. Switch to the benchmark **Compare** view, about 10 seconds.
3. Back in the notebook, show section 6 (the coverage table) and section 7 (monitoring), about 15 seconds.

**Say:**
> "Every decision is traced: the plan, each specialist, the tools and the verdict. We evaluated on a held-out
> synthetic world against the same rules on their own: eight categories, from detection to memory safeguards to
> whether the agent calls the right specialists. Safeguards and behaviour score 100% on our scenarios. After
> go-live, an online evaluator scores every SAR, and an annotation queue puts the human-decided cases in front of
> an analyst."

*(If the online evaluator or queue reviews aren't set up yet, the monitoring cell says so; say "it's configured,
waiting for its first scores".)*

### 3:30–4:15 · Architecture, controls and human review (Slide 3)
**Say:**
> "The architecture has three tiers: rules, agents, human. The controls are code, not prompts. Hard flags (sanctions,
> PEP, a confirmed ring) beat any precedent. A precedent must match the customer, counterparty and pattern, and it
> expires. A suspected mule network always goes to a human. Only the supervisor can pause the graph, and only the
> fund-flow agent can look across customers, logged on every call. Middleware caps model calls per investigation,
> and the filesystem tools are hidden from the model."

### 4:15–4:45 · Results, value and limitations (Slide 4)
**Say:**
> "On the test world, 950 transactions: false positives fell from 30 to 2, precision rose from 33% to 88%, and we
> caught every planted case, the same as the rules. Only 4.7% of transactions touched an LLM. Scaled to a million
> transactions, that's about 37% less analyst time, roughly 8,800 hours a year at our stated assumptions. Not 93%,
> because Sentinel asks quick questions instead of guessing. The limits: synthetic data, scripted human answers in
> the eval, and a small benchmark."

### 4:45–5:00 · Conclusion and next step (Slide 5)
**Say (final line):**
> "Rules take the volume, agents investigate the grey zone, a human decides when they're unsure, and memory never
> clears a launderer. Next: a real ML scorer and public AML benchmarks. The repo link is on the slide. We're Chain
> & Grab; that's Sentinel."

---

## Q&A prep

| Likely question | Answer |
|---|---|
| What did you add beyond the starter? | A rules tier (the starter sent every transaction to the LLM), a Deep Agents supervisor with 4 sub-agents, cross-account ring detection, structured precedents with safeguards in code, SAR drafting, a labelled AML data generator, a rules-only baseline and 8 eval categories. We kept the starter's memory, `interrupt()` and its 3 evaluators unchanged. |
| Recall is 100% for both. What do the agents add? | Precision. Both catch every planted case, because the agents only see what the rules flag, and the baseline escalates everything flagged. The agents remove the false alerts: 30 down to 2. That's the analyst's time. |
| Isn't your ring check just another rule? | Yes, the confirmation is deterministic, and the baseline gets it too, so the comparison is fair. Per-customer rules can't see a ring at all. The agents turn the flag into an explained case, send the unconfirmed early forwards to a human, and override the old precedent. |
| Why AML and not card fraud? | Fraud is decided one payment at a time. AML needs reasoning across transactions, accounts and time, which is where agents and memory add the most. |
| Why agents and not an ML model? | ML scores; it can't investigate, explain itself, weigh an analyst's written note, or decide to ask a human. Rules (or ML) score; agents investigate. |
| Doesn't the network agent break the one-customer rule? | Deliberately and narrowly. One tool, held by one agent. Its starting account comes from the run context, not the model. It returns account IDs and amounts, never profiles, and every call is audited. |
| What if the analyst's precedent is wrong? | It expires, applies only to the same customer, counterparty and pattern, and can't override a hard flag. We showed Liam's being overridden. Every precedent relied on or overridden is in the audit record. |
| How did Sophie's second credit auto-clear if checks only add oversight? | That's the one stated exception: a valid, in-scope precedent with no hard flags satisfies the grey-zone check, because an analyst already decided that exact case. Expired or out-of-scope precedents don't count; our evals check both. |
| Can the agent clear a hard-flag case? | No. The code forces a human decision on any hard-flag case the agent wants to clear. |
| How do you stop hallucination? | Findings are structured output from tool results. The SAR writer has no tools and only sees the evidence. Code checks that every transaction a SAR cites exists and was visible at the time: 100% on our runs. |
| How did you get the ROI? | From the test-world rates, scaled to a million transactions, with stated assumptions: 30 minutes per alert, 10 per review question, £45 an hour. Replace them with a bank's figures. LLM cost depends on the gateway price, so we report tokens. |
| Cost and speed? | About 95% of transactions never touch an LLM. Each investigation takes about 12 model calls, 36k tokens and 22 seconds median, with hard caps in middleware. |
| Isn't the demo a replay? | Yes, and the banner says so: the responses were recorded from a live run, with the trace linked. Rules, safeguards and memory run for real, and the analyst's click is live. We can run it fully live if there's time. |
| Is your eval just your own synthetic data? | Yes, and we say so: a held-out world, a fair baseline using the same rules, tuning on dev only, and the starter's own evaluators. Next: public AML datasets and a pilot. |
| Why multi-agent? | Each specialist has a narrow toolset, so it's easier to test, evaluate and swap, and the cross-customer privilege is contained in one agent. Our trajectory evals check that the right specialists are called. |
| Data privacy with LLMs? | Synthetic data here. In production: mask identifiers before LLM calls, keep raw data in the bank, and use a private deployment through the gateway. |
| What does a regulator see? | For every decision: the evidence, tool calls, precedents relied on or overridden, confidence and who decided, in the trace and the decision audit store. |

---

## Points judges should come away with
1. **Impact:** a recognisable FSI problem, a named user, KPIs against a baseline (false positives 30 → 2) and an ROI estimate with stated assumptions.
2. **Technical depth:** LangGraph, LangChain and Deep Agents; a supervisor with 4 sub-agents; memory with safeguards in code; middleware; human review; 8 eval categories in LangSmith.
3. **Presentation:** 5:00 end to end, honest about replay and limitations, confident Q&A.

## Demo-day safety net
- **Replay with the banner** (`REPLAY=1`), re-recorded on the day. The analyst click is live.
- **The eval is pre-computed;** the notebook only loads `results/eval_summary.json`.
- **A fully executed notebook** is open in a second tab.
- **Screenshots** are in `sentinel_aml_agent/results/screenshots/`.
- **Rehearse to 4:45.**
