# DECISIONS.md: Decisions taken along the way

A running log of decisions made after PLAN.md, USE_CASE.md and DEMO_SCRIPT.md were written. The base docs are
**not** edited for these. HACKATHON.md is never edited.

**How to use this file.** The plan is still PLAN.md and the spec in `.kiro/specs/sentinel-aml-agent/`. This file is
mostly a **backlog**: improvements we'll take if doable, without letting them block a checkpoint. Only the entries
marked **Required** must be applied, because they keep the demo honest.

**Status values:**
- `Required`: apply it. These are the "no cheating" rules (DEC-002, DEC-003, DEC-004).
- `Backlog`: do it if it fits in the timebox; otherwise follow the base docs and skip it. Never let a backlog item delay Checkpoint A (13:00) or B (15:45).
- `Info`: a reference or a completed item, nothing to build.
- `Rejected`: recorded so we don't revisit it.

When a backlog item is picked up, note it in the commit message (for example `(task 5.1, DEC-010)`). When one is
dropped, leave it as `Backlog`; it's part of the "next steps" story.

> Synthetic data only. Outputs are drafts for analyst review, not legal, compliance or regulatory advice.

---

## DEC-001 · Where we get LangChain, LangGraph and Deep Agents facts
**Status:** Info · 2026-11-25

**Decision.** Use these sources, in this order of trust:
1. The installed packages in `/.venv`: the code that actually runs. Verified versions: `deepagents 0.7.28`, `langchain 1.4.6`, `langgraph 1.2.16`, `langsmith 0.14.11`. Check signatures with `inspect.signature(...)` before relying on a parameter.
2. API reference: [reference.langchain.com](https://reference.langchain.com), also available as MCP server `reference-langchain` at `https://reference.langchain.com/mcp`.
3. Guides: [docs.langchain.com](https://docs.langchain.com) (index at `/llms.txt`), also available as MCP server `docs-langchain` at `https://docs.langchain.com/mcp`.
4. The organiser starters (`01_`-`03_`), written by LangChain against these versions.
5. LangChain engineers on the day.
6. The coding agent's own memory, last. Deep Agents changes quickly.

**Found while building (task 0.4):** in `langsmith 0.14.11`, `Client.list_runs()` warns it's deprecated (removed after 31 Jan 2027) in favour of `client.runs.query()`. It still works today; prefer `client.runs.query()` in new code (annotation queue, notebook monitoring cell).

**Why.** The docs track the latest release, and in places they're already ahead of our pinned versions. For example, they use `gpt-6.1-sol`, while we verified `gpt-6-sol` through the gateway.

---

## DEC-002 · Recall claim: "no loss of recall", not "higher recall"
**Status:** Required (no cheating)

**Decision.** Claim **the same recall as rules-only, with far fewer false positives**. Report recall honestly, even if it comes out lower.

**Why.** Transactions the rules clear never reach the agents, and the rules-only baseline escalates everything the rules flag. So Sentinel's recall can at most equal the baseline's. "Equal or higher recall" can't be true by construction.

**Overrides.** USE_CASE.md "Measurable value" and evaluation targets; DEMO_SCRIPT.md slide 2 and the eval line ("catching as many / more"); requirement R9.

**Task impact.** 5.1 reports `recall_planted` with the target "= rules-only". 6.4 renders that target.

---

## DEC-003 · Replay mode is labelled on screen; one case runs live
**Status:** Required (no cheating) for the banner and the live-run outputs. Running Sophie live on stage is Backlog

**Decision.**
- Whenever `REPLAY=1`, the notebook prints a banner: `REPLAY: model responses recorded from the live run at <time>`, with a link to that run's LangSmith trace.
- Sophie's human-review case runs **live** on stage, because the human step is the interactive part. The other cases may be replayed.
- The committed notebook keeps the outputs of a **live** run, not a replay.

**Why.** Showing recorded responses as if they were live would be misleading. The recording is from a real run, and the trace proves it.

**Overrides.** PLAN.md 5.7 and DEMO_SCRIPT.md "Replay mode, on by default on stage".

**Task impact.** 6.1 adds the banner and records the run time and trace URL when filling the cache. 6.5 commits the live-run outputs.

---

## DEC-004 · No demo-specific code
**Status:** Required (no cheating)

**Decision.**
- No code branches on demo IDs or names (no `if user_id == "CUS-0001"`).
- No prompt mentions demo names, amounts or dates.
- `scripts/check_scenarios.py` and the scenario eval only **observe** behaviour. They never steer it.
- Rules are tuned on the dev world only.

**Why.** The judges should see behaviour that comes from the design, not from special-casing the demo.

**Task impact.** A new working rule in every task. Task 7.2 adds `git grep -n -E "CUS-00(0[1-3]|4[0-4]|50)|Hughes|Clarke|Walsh|Northgate" -- agents.py sub_agents tools rules utils instructions.md`, which must return nothing outside `data/` and tests.

---

## DEC-005 · Say which results are designed into the data
**Status:** Backlog

**Decision.**
- On the eval slide and in the notebook, mark these as properties of **our synthetic benchmark**: the share of transactions reaching an LLM, the month 1 → month 2 fall in reviews, and the ring confirming on the 5th transfer.
- Drop `cost_per_1k` unless there's a published price for the gateway model. Report **tokens per investigation** instead.

**Why.** We wrote the data, the labels and the rules. Saying so is stronger in Q&A than being caught out.

**Overrides.** USE_CASE.md "cost per 1,000 transactions"; requirement R9.2 (`cost_per_1k`).

**Task impact.** 5.1 replaces `cost_per_1k` with `tokens_per_investigation`.

---

## DEC-006 · Eval size cut to fit the day
**Status:** Backlog, **pick up first**. Skipping it leaves the original 6 worlds × 200 customers, which won't finish running today

**Decision.** World 0 is the demo. Add **1 dev world and 1 test world**, each about **40 customers and about 1,000 transactions over 2 months**, so roughly 40 investigations per world. Report the real N on the slide.

**Why.** The original 6 worlds of about 200 customers is roughly 10,000 transactions each. At 5% that's about 500 investigations per world, each about 10 model calls of 30-90 seconds: hours per world.

**Overrides.** PLAN.md section 6 ("worlds 1 to 4 are dev, 5 to 6 are test"); requirements R2.3 and R2.6; design.md D1 and D2 (keep the mechanism, with worlds 1 and 2 only).

**Task impact.** 1.4 generates worlds 1 (dev) and 2 (test). 5.3 and 5.4 use them.

---

## DEC-007 · Evals run customers in parallel; the time-ordered stream is for the notebook
**Status:** Backlog

**Decision.** The eval target runs each customer's transactions in order on that customer's thread, with customers in parallel (`max_concurrency` 4). The notebook keeps the global timestamp-ordered stream, because it tells the story.

**Why.** Processing order doesn't change any verdict:
- the network graph reads the database filtered by `as_of`, not by what has been processed;
- precedents are stored per customer.

Running customers in parallel cuts eval time several times over.

**Overrides.** PLAN.md section 1 "Processing order" (for evals only); requirement R8.1 (notebook only).

**Task impact.** 2.6 `process_stream` accepts `parallel_customers=True` for evals.

---

## DEC-008 · What judges see when they open the repo
**Status:** Backlog

**Decision.**
- Commit `modules/01_sentinel_demo.ipynb` **with outputs** from a live run. Judges may read it without running it.
- After removing the starters, replace the repo root `README.md` with a short pointer to `sentinel_aml_agent/` and the two submission files. The organiser README would otherwise describe deleted folders.

**Task impact.** 6.5 and 7.1.

---

## DEC-009 · Built-in features to use, and ones we're skipping
**Status:** Backlog, except where marked

Checked against the installed versions:

| Feature | Use | Why | Status |
|---|---|---|---|
| `write_todos` planning (Deep Agents built-in) | The supervisor writes a short plan before delegating | The trace then shows planning, which backs the "it plans" claim | Backlog |
| Parallel `task` calls | The supervisor delegates to several specialists in one turn | Documented as running in parallel; cuts latency | Already in PLAN.md 5.2 |
| Sub-agent `response_format` | Structured findings from each specialist | Documented; needs `deepagents>=0.5.3` | Already in PLAN.md 5.3 |
| Filter by sub-agent in LangSmith | The trace view used in the demo | Free | Backlog |
| `ModelCallLimitMiddleware`, `ToolCallLimitMiddleware` (`langchain.agents.middleware`) | Cap model and tool calls per investigation | Backs the cost answer with code | Backlog |
| Built-in filesystem tools | Decide at task 3.2: hide them with a harness profile, or use one on purpose (save the SAR draft as a file) | They're on by default and can distract the model | Backlog (decide at 3.2) |
| `PIIMiddleware` | Mask identifiers before model calls | Backs the privacy Q&A answer with code | Backlog (low priority) |
| Async sub-agents, dynamic sub-agents, skills, Managed Deep Agents deployment | Not used | Each costs time without improving the 5-minute demo | Rejected |

**Task impact.** 3.2 adds `write_todos` guidance to `instructions.md`, plus the two limit middlewares.

---

## DEC-010 · Eval coverage: what we evaluate, and how we show it
**Status:** Backlog. Categories 1-5 first; 6-8 only if there's time. Without it, PLAN.md section 7's evals still apply

**Decision.** We evaluate **8 categories**. The demo shows coverage across all of them, including the gaps, rather than one accuracy number. Categories 1-5 are core. 6-8 are kept small, and are where we cut if time runs short.

### Evaluation categories

| # | Category | Question it answers | Evaluators | Type | Dataset | Target |
|---|---|---|---|---|---|---|
| 1 | **Detection quality** | Does it catch laundering and stop crying wolf? | `decision_accuracy` (starter), `false_positive_rate`, `alert_precision`, `recall_planted`, `recall_by_pattern` | Code vs labels | Benchmark | FP rate ≥ 50% below rules-only; recall = rules-only (DEC-002) |
| 2 | **Risk calibration** | Are its risk scores close to the analysts'? | `score_alignment` (starter) | Code vs labels | Benchmark | Above rules-only |
| 3 | **Human-in-the-loop routing** | Does it ask a human exactly when it should? | `review_routing` (starter), `human_review_rate`, `reviews_month1` → `reviews_month2` | Code vs labels | Benchmark | Routing high; month 2 below month 1 |
| 4 | **Memory safeguards** | Can memory ever clear a launderer? | `precedent_used_when_valid`, `expired_precedent_not_relied_on`, `out_of_scope_precedent_ignored`, `hard_flag_overrides_precedent`, `hard_flag_clear_goes_to_human` | Code, pass/fail | Scenarios | **100%**, any failure is a bug |
| 5 | **Agent behaviour (trajectory)** | Does the multi-agent system behave as designed? | `kyc_called_every_time`, `record_decision_once`, `specialists_match_rule_reasons`, `only_fund_flow_traces_network` | Code over the run's tool calls | Scenarios + benchmark | 100% |
| 6 | **SAR quality** | Is the hand-off usable, with nothing invented? | `sar_grounded` (every evidence item matches a real transaction ID and amount; code), `sar_complete` (LLM-as-judge with a rubric) | Code + LLM judge | Scenarios (escalations) | Grounded 100%; complete on all |
| 7 | **Efficiency** | Is it viable at volume? | `llm_share`, `model_calls_per_investigation`, `tokens_per_investigation`, `p50_seconds_per_investigation` | Code over runner counters | Benchmark | `llm_share` ≤ 5% (DEC-005 caveat) |
| 8 | **Privacy and scope** | Does the cross-customer privilege stay narrow? | `network_calls_audited` (every `trace_fund_flows` call has an audit record), `no_profile_fields_in_network_output` | Code, pass/fail | Scenarios | 100% |

### Typology coverage

| Pattern | Benchmark (dev / test) | Scenario examples | Categories exercised |
|---|---|---|---|
| Structuring | Planted in both worlds | Daniel | 1, 2, 5, 6 |
| Anomalous but benign credit | Planted in both worlds (labelled `clear`) | Sophie, first credit (human) and second (precedent) | 1, 3, 4 |
| Mule ring (fan-in) | Planted in both worlds | Mule ring + Liam's override | 1, 4, 5, 8 |
| Round-tripping | Planted in both worlds | Marcus (optional, cut list item 1) | 1, 4 |
| Expired precedent | — | One extra world-0 customer whose precedent has expired | 4 |
| Out-of-scope precedent | — | One extra world-0 customer whose precedent is for another counterparty | 4 |
| Normal traffic (control) | Most of both worlds | One plain world-0 customer | 1, 7 |

### Known gaps (shown on the coverage slide, not hidden)
- Real or public AML data (synthetic only; next step: public synthetic AML datasets).
- Adversarial inputs, such as prompt injection through transaction references.
- Fairness across customer groups.
- Production latency and load.
- Analyst usability (no user study).

### Datasets and experiments (LangSmith)

| Dataset | Examples | What it's for |
|---|---|---|
| `<LANGSMITH_PROJECT>-sentinel-scenarios` | About 7, one per scenario row above. Each example is the stream for the customers involved, plus scripted reviewer answers | Behaviour and safeguard checks (categories 4, 5, 6, 8). Small enough to run in minutes |
| `<LANGSMITH_PROJECT>-sentinel-benchmark` | 2: world 1 (split `dev`) and world 2 (split `test`). The split is set per example with the `"split"` key in each example dict; `create_examples` has no `splits` argument in `langsmith 0.14.11`. Read back with `list_examples(..., splits=["test"])` | Headline numbers (categories 1, 2, 3, 7). Report on `test` only |

Experiments: `rules-only` and `sentinel` on both datasets, so every number has a baseline next to it in LangSmith's comparison view. If time allows, run the scenario dataset with `num_repetitions=3` and report the pass rate across repeats as a **consistency** figure (Backlog, low priority).

### How we show it in the demo (inside the existing 3:45-4:30 slot)
1. **Coverage table** in the notebook, loaded from `results/eval_summary.json`. One row per category: evaluators, dataset, rules-only, Sentinel, target, and pass ✅ / miss ❌. Misses stay in the table.
2. **Typology matrix** (the table above, with results filled in).
3. **5 seconds in LangSmith:** the `rules-only` vs `sentinel` comparison on the benchmark test split.
4. **One sentence on gaps:** "We cover detection, calibration, routing, safeguards, agent behaviour, SAR quality, efficiency and scope. We don't yet cover adversarial inputs or real data."

### Implementation notes
- Evaluators are plain Python functions with the starter's `(outputs, reference_outputs)` signature, in `evals/scoring_evals.py` (categories 1-3, 7) and `evals/behaviour_evals.py` (categories 4, 5, 8). `evals/sar_judge.py` holds category 6.
- Trajectory evaluators read the supervisor's tool calls from the thread state (`agent.get_state(config)`): the `task` calls and their `subagent_type`, plus `record_decision` calls. The target function returns them as `tool_calls` alongside `decisions`.
- Scenario labels need two new fields: `expect_precedent_use` and `expect_human`. These are added in the generator, for world 0 only.
- The LLM judge uses the same gateway model as the agent. That's a known bias, so groundedness is checked in **code** and the judge only scores completeness against a fixed rubric.

**Overrides.** PLAN.md section 7 (adds categories 4-8 and the scenario dataset); requirements R9.2 and R9.3.

**Task impact.**
- 1.3 adds the expired-precedent, out-of-scope-precedent and control customers to world 0, plus the `expect_precedent_use` and `expect_human` labels.
- 3.3 becomes the scenario dataset runner: the same checks, also registered in LangSmith.
- 5.1 splits into 5.1a (categories 1-3, 7) and 5.1b (categories 4, 5, 8).
- 5.2 implements `sar_grounded` (core) and `sar_complete` (optional).
- 5.3 creates both datasets and runs both experiments.
- 6.4 renders the coverage table and the typology matrix.

**Timing.** The evaluators are small functions. Most of the time goes on runs. Start the benchmark run in the background as soon as Checkpoint A passes, and build the notebook while it runs.

---

## DEC-011 · Docs MCP servers for the coding agent
**Status:** Info · done

**Decision.** `docs-langchain` (`https://docs.langchain.com/mcp`) and `reference-langchain` (`https://reference.langchain.com/mcp`) are in the user-level Kiro MCP config, added by the user. Both were verified with real queries on 2026-11-25.

**First finding.** The Python Deep Agents docs ([Subagents → Context management](https://docs.langchain.com/oss/python/deepagents/subagents#context-management)) say the runtime context passed to the parent `invoke` propagates to every subagent, so subagent tools can read `runtime.context`. Task 0.3's spike still runs, but now to confirm this on our installed `deepagents 0.7.28` and to check `runtime.store`, which that section doesn't cover.

---

## DEC-012 · Labels judge each transaction by what was visible at that moment
**Status:** Required (no cheating) · found while building, before the rule scorer

**Decision.** An alert label goes on every transaction where an analyst, seeing only the history up to that
moment, should raise an alert. Not just on the last step of a pattern.
- **Structuring:** the 3rd near-threshold cash deposit within about 72 hours, and every one after it, are labelled
  `escalate`. The first two are `clear` (pattern `structuring`). For Daniel, that means deposits 3 and 4 both alert.
- **Mule ring:** a mule's forward to the collector is labelled as before (ambiguous + escalate until the ring is
  confirmable). The **collector's inbound leg** is labelled `clear` until the ring is confirmable, and `escalate` after.

**Why.** With "only the last step alerts", the label depends on future transactions that nobody could see yet.
A scorer that correctly alerts on Daniel's 3rd deposit (£28,500 cash in 30 hours against £12,000 expected per
month) would be scored as a false positive, which unfairly penalises both rules-only and Sentinel.

**Overrides.** DEMO_SCRIPT.md says Daniel's "4th is flagged". With this rule the 3rd is flagged first, and the 4th
again. The demo shows the **4th** deposit's investigation, because it has the most evidence (all four deposits),
and mentions that the 3rd already raised an alert.

**Task impact.** 1.3 / 1.4 regenerated; `check_data.py` still passes. 3.3 expects alerts on deposits 3 and 4.

---

## DEC-013 · Tier 1 includes a deterministic network watchlist, and so does the baseline
**Status:** Required (no cheating) for "the baseline gets it too". The second baseline is Backlog

**Found while building (task 2.1).** Per-customer rules scored two late mule transactions at 0: Liam receiving from
his "flatmate" after the ring is confirmed, and the collector's offshore payout. No per-customer rule can see a
ring, so without a cross-account check these never reach any agent, and the Liam override can't happen.

**Decision.**
- `utils/graph.py` detects confirmed fan-in rings deterministically: 5 accounts, each forwarding ≥ 90% of what it
  received in the previous 24h to one collector, within 72h. The generator's labels use the same definition.
- `rules/scorer.score_with_network` raises any money movement by a ring member to at least 60, with the reason
  "account is a feeder/collector in a fan-in ring … (network check)". Card spending and salaries are excluded.
- **The rules-only baseline uses the same tier 1, network check included.** So recall stays equal by construction
  (DEC-002), and the headline comparison is purely "what do the agents add on top of the same deterministic checks".
- The fund-flow agent still has a real job: explaining the ring with evidence, finding rings the deterministic check
  doesn't confirm yet (the earlier forwards go to a human), and feeding the hard flag that overrides Liam's precedent.

**What to say in the demo.** Not "rules can't see mule rings", but: "a per-customer rule can't; our graph check
can, and the agents turn it into an explained, filing-ready case, and override the old clearance."

**Results so far (rules only, tier 1).** World 0: 97.0% cleared by rules, 34 sent to agents, recall 100% of 14
alerts, 20 false positives. World 1 (dev): 95.0% cleared, 43 sent to agents, recall 100% of 15, 28 false positives.
World 2 (test) is not scored until the reported eval run (R9.5).

**Backlog.** Report a second baseline, "per-customer rules only" (`score_all(..., network=False)`), next to the
main one. It shows separately what the graph check adds (recall) and what the agents add (false positives).

---

## DEC-014 · Checkpoint A results and what the build taught us
**Status:** Info · 2026-11-25

**Checkpoint A passed** (`uv run python scripts/check_scenarios.py`, live on `gpt-6-sol`, traced to LangSmith):
6/6 scenario transactions match their analyst labels.
- Daniel, deposits 3 and 4: escalate, no human, SAR draft saved (34-36s each).
- Sophie's first credit: the agents were unsure, the analyst cleared it with a note, and the note became a precedent.
  Her second credit ten months later was auto-cleared, relying on that precedent (19-21s).
- Grace (expired precedent) and Tom (precedent for a different counterparty): neither precedent was relied on, and
  both went to a human (19-22s).
- The rules tier clears 97.0% of world 0, with no LLM call.
- `uv run langgraph dev` serves graph `sentinel`. Daniel's case run through the server API with
  `context={"user_id": "CUS-0001", ...}` escalated with the same reason.

**Built differently from the plan, on purpose:**
- **Structured output retries.** The first live run crashed because a sub-agent left out a required field. Each
  sub-agent's schema is now wrapped in `ToolStrategy(..., handle_errors=True)`, so a schema error goes back to the
  model to fix, without loosening the schemas.
- **Harness profile.** `agents.py` registers a profile for the configured model that hides the built-in filesystem
  tools and the general-purpose sub-agent. Checked: every supervisor model call is offered only
  `get_transaction`, `get_customer_profile`, `record_decision`, `task` and `write_todos` (DEC-009).
- **Limits.** `ModelCallLimitMiddleware(run_limit=20)` and `ToolCallLimitMiddleware("task", run_limit=6)` cap each
  investigation (DEC-009).
- **Planning.** The supervisor called `write_todos` five times in one run, so the prompt now says to call it once.
- **Per-investigation counters.** Model-call counts were mixed up across parallel customers; each investigation
  now has its own counter.

---

## DEC-015 · Two safeguard fixes found by the live mule-ring run
**Status:** Required (safeguards are enforced in code, R6.6) · 2026-11-25

The first live run with the mule ring passed 6/9 scenario transactions. All three failures were real gaps, not
test problems. Both fixes are in `tools/decisions.py` and covered by new no-LLM checks in `check_core.py` (30/30).

1. **Sophie's repeat credit was cleared correctly, but "precedent relied on" wasn't recorded.** The agent cleared it
   with `pattern="none"`, so the scope match (customer + counterparty + pattern) found nothing.
   **Fix:** if the pattern is `none` and the agent cites a precedent for this exact counterparty, scope it by that
   precedent's pattern. Counterparty and expiry are still checked in code; a citation for another counterparty is
   still dropped. The prompt also asks for the resembling pattern even when clearing.
2. **The 4th mule forward was escalated without a human,** although the ring wasn't confirmable yet (label:
   ambiguous, ask a human). **Fix:** a `mule_fan_in` verdict without a ring confirmed by the graph check always
   goes to a human, because it implicates other customers on unconfirmed evidence. This adds oversight; it never
   removes it.
3. **Liam's case escalated, but via a human.** The old precedent pulled the agent's risk score into the grey zone.
   The precedent was overridden in code either way. **Fix (prompt only):** hard flags are named explicitly (sanctions
   or PEP hit, `ring_confirmed: true`), and with a hard flag plus suspicious activity the supervisor escalates with
   high confidence instead of letting an old precedent pull the score down.

**After the fixes:** 9/9 on two consecutive live runs, and every SAR draft is grounded (`evals/sar_checks.py`: every
cited transaction exists and was visible at the time, and the disclaimer is exact). Investigations take 16-52s;
the mule cases are the slowest (28-52s).

---

## DEC-016 · Eval results (phase 5) and how they were produced
**Status:** Info · 2026-11-25 · model `openai:gpt-6-sol` · `scripts/run_experiments.py`

**Method.** World 1 (dev) was run once to check the pipeline; **nothing was tuned after it**. World 2 (test) was
then run once, and those are the reported numbers. Human answers in the `sentinel` runs are scripted from
`reviewer_answers.jsonl`; with no scripted answer, the agents' own decision is accepted (the starter's rule). The
rules-only baseline uses the same tier 1, network check included (DEC-013). All data is synthetic (DEC-005).

**Headline: benchmark test split (world 2: 36 customers, 950 transactions, 15 planted alerts)**

| Metric | Rules only | Sentinel |
|---|---|---|
| False positives (alerts an analyst clears for nothing) | 30 | **2** (−93%) |
| False-positive rate (of transactions labelled clear) | 3.2% | **0.2%** |
| Alert precision | 33% | **88%** |
| Recall on planted alerts (all 4 typologies) | 100% | **100%** (equal, as designed: DEC-002) |
| Decision accuracy (starter evaluator) | 0.968 | **0.993** |
| Score alignment (starter evaluator) | 0.938 | 0.942 |
| Review routing (starter evaluator) | 0.990 | 0.975 (lower: Sentinel asks a human in some cases the labels don't mark ambiguous) |
| Transactions reaching an LLM | 0% | **4.7%** (45 investigations) |
| Model calls · tokens · median seconds per investigation | – | 12.1 · 36k · 22s |
| Human reviews, month 1 → month 2 | – | 28 → 6 (the repeat cases are planted in the data: DEC-005) |

Dev split (world 1) for comparison: false positives 28 → 4, precision 35% → 79%, recall 100% → 100%, LLM share 5.0%.

**Scenario suite (world 0, 6 scenarios, 9 investigated transactions).** Memory safeguards, agent behaviour, SAR and
network-scope evaluators all score 1.0: valid precedent used, no reliance on expired or out-of-scope precedents,
hard flag overrides Liam's precedent, `kyc-precedent` called every time, `record_decision` once, specialists match
the rule reasons, every SAR grounded, every network call audited. Rules-only on the same scenarios: equal recall,
but it can't use or override precedents (0.0) and escalates the benign cases (FP rate 1.0).

**Fixes made while running evals.**
- Rules-only on the scenario dataset first scored only the selected transactions, so they had no history. It now
  scores the whole world, then picks them. (The benchmark was unaffected: it always scored whole worlds.)
- Evaluators with nothing to measure in an example (for example no planted alert in a scenario) now return no
  score instead of 0 or 1, so averages aren't distorted.
- Rules-tier records now carry `agent_decision="clear"`, which the starter's `decision_accuracy_eval` compares.

**LangSmith.** Datasets `<project>-sentinel-benchmark` (dev/test splits) and `<project>-sentinel-scenarios`.
Experiments `rules-only-*` and `sentinel-*` on both, viewable side by side in each dataset's comparison view.

---

## DEC-017 · Notebook, replay, starter removal and submission state
**Status:** Info · 2026-11-25

**Notebook** (`modules/01_sentinel_demo.ipynb`, generated by `scripts/build_notebook.py` from `utils/demo.py`
helpers). It is committed with the outputs of a **live** run (REPLAY=record, 161 model calls, 12 investigations),
as DEC-003 and DEC-008 require. The analyst panel (ipywidgets) resumes Sophie's paused investigation; when the
notebook runs unattended, the next cell answers with the scripted analyst and says so.

**Replay.** `utils/replay.py` caches model responses keyed on what the model actually saw: message IDs and usage
metadata are excluded from the key, because they change on every run without changing the prompt. Verified: a
fresh kernel with `REPLAY=1` replayed 161/161 calls, 0 live, with identical verdicts. The banner prints the
recording time, the replayed vs live counts, and that rules, safeguards and memory still run for real. The cache
file is git-ignored; re-create it with `REPLAY=record` before the demo.

**Background reviews in the notebook.** Three first-time supplier payments on 3 October asked for a review. They
have no scripted analyst answer, so the agents' decision (clear) stands, as in the starter, and the notebook says so.

**Starters removed (Checkpoint B).** `00_dcode_setup` and `01`-`03` were deleted and removed from the workspace
(still in git history). After `uv sync --all-packages`: every no-LLM check passes, `check_scenarios.py
--with-mule` passes 9/9 live, the notebook runs with `REPLAY=1` with no errors, and `langgraph dev` serves graph
`sentinel` (Daniel escalated through the server API). The root README now points at Sentinel (DEC-008).

**Waiting on people, not code:**
- the LangSmith online evaluator (`evals/online_evaluators.md`, about 5 minutes in the UI);
- reviewing the annotation queue `sentinel-analyst-review-saiyam-kalra`, then `scripts/annotation_queue.py --collect`;
- the slides (template on the day), the source check for the false-positive statistic, and rehearsal.

---

## DEC-018 · The flight deck becomes today's source of truth
**Status:** Required · 2026-11-25

The LangChain FSI Hackathon Flight Deck v1.0, shared after the kick-off, replaces the attendee guide for today.
HACKATHON.md now follows it, at the user's request.

- **Agent file name: keep `agents.py`.** The flight deck lists `agent.py`; the attendee guide said `agents.py`. The
  team chose to keep `agents.py`. The README and HACKATHON.md point to it. If the organisers insist on `agent.py`,
  rename it and update `langgraph.json` and the 5 imports in `scripts/` and `utils/demo.py`.
- **README format.** The root README now has the team name, company, use case and run instructions, plus where the
  notebook, the agent, the evaluations and the datasets are. Team name: **Chain & Grab** (chosen by the team; a
  pun on LangChain, LangGraph, chain of custody and smash-and-grab). Submission name per the flight deck:
  `Chain & Grab | NatWest`. Slides: `HACK_NATWEST_CHAINANDGRAB`.
- **ROI is now judged.** The README gives an illustrative estimate per million transactions, with stated
  assumptions: 30 minutes per alert, 10 minutes per review question, £45 per hour. Analyst time falls by **37%**,
  not 93%, because Sentinel replaces some alerts with quick review questions. We show the honest figure.
- **Demo shape.** The flight deck's run of show (problem 0:30, what it does 1:00, demo to 2:45, trace and evals to
  3:30, architecture and controls to 4:15, results and value to 4:45, close) supersedes DEMO_SCRIPT.md's timings.
- **Screenshots** for the fallback go in `sentinel_aml_agent/results/screenshots/` (list of what to capture there).
- **Deadline** is 15:45 for submission through https://langch.in/hack-sub. Final commit by 15:35.
