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
