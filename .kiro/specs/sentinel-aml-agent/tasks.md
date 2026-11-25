# Tasks: Sentinel AML Agent

Requirements: #[[file:.kiro/specs/sentinel-aml-agent/requirements.md]] · Design: #[[file:PLAN.md]] and
#[[file:.kiro/specs/sentinel-aml-agent/design.md]] · Rules: #[[file:HACKATHON.md]]

Owner of every task: Kiro (Claude). Tasks run in order. Each task ends in a runnable, committed state.
Paths are relative to `sentinel_aml_agent/` unless they start with `/`.

## Working rules for every task

1. **Read before writing.** Re-read the PLAN.md section the task cites. Don't invent schemas or signatures; use PLAN.md section 4.
2. **Done means verified.** Run the task's "Done when" command and read the output before ticking the box. A command exiting with no error isn't enough.
3. **One task, one commit.** Use a Conventional Commit message naming the task, for example `feat(rules): add rule scorer and baseline (task 2.1)`.
4. **Secret check before every commit:** `git status`, `git diff --staged`, and `git grep -nE "lsv2_[a-z]{2}_[0-9a-f]{16}" -- .` must show no `.env` and no keys. (The pattern matches real key shapes only, so it doesn't flag these instructions.)
5. **Keep `main` runnable.** Never commit a broken import. If a task overruns its timebox, commit what works behind a flag and move on.
6. **Commands:** run Python from `sentinel_aml_agent/` with `uv run`. Only ever run `uv sync --all-packages` from the repo root.
7. **Checkpoints are hard gates.** Don't start the next phase until the checkpoint's checks pass. If time runs short, drop optional tasks (`*`) in the order of PLAN.md section 10.
8. **Sync docs.** If a task changes a decision, update PLAN.md first, then USE_CASE.md and DEMO_SCRIPT.md. Never edit HACKATHON.md.

Tasks marked `*` are optional and are on the PLAN.md cut list.

**Backlog: #[[file:DECISIONS.md]].** Read it at the start of each task. Entries marked **Required** (DEC-002, DEC-003,
DEC-004: the "no cheating" rules) always apply. Entries marked **Backlog** are improvements to take only if they fit
the task's timebox; otherwise do the task as written here and skip them. A backlog item never delays a checkpoint.
Name any backlog item you pick up in the commit message, for example `(task 5.1, DEC-010)`.

**Timing.** Phases run one after another, because there's one owner. The times below are latest finish times, not
start times; if work starts before 10:00, pull everything forward. The two checkpoint deadlines don't move: A by
13:00, B (feature freeze) by 15:45.

---

## Phase 0: Scaffold (finish by 10:30)

- [x] 0.1 Create `sentinel_aml_agent/` from the 02 starter
  - Copy `02_transaction_monitoring_agent/` to `/sentinel_aml_agent/`, excluding `.langgraph_api/`, `__pycache__/`, `images/` and `modules/`.
  - Rename `agent.py` to `agents.py`. Set `langgraph.json` graph `sentinel` to `./agents.py:agent`.
  - `pyproject.toml`: name `sentinel-aml-agent`; add `deepagents>=0.7,<1`, `networkx`, `matplotlib`, `ipywidgets`, `pydantic>=2,<3`.
  - Add `"sentinel_aml_agent"` to `[tool.uv.workspace].members` in `/pyproject.toml`; run `uv sync --all-packages` from the root.
  - Point `scripts/run_experiments.py` imports at `agents`.
  - Keep 02's `utils/models.py` unchanged, so the model comes from `MODEL_NAME` in `/.env`.
  - **Done when:** `uv run python -c "import agents, networkx, matplotlib, ipywidgets, deepagents; from utils.models import model; print(model)"` prints `openai:gpt-6-sol`, and `git grep -n "from agent import\|import agent$" sentinel_aml_agent` returns nothing.
  - _Requirements: R1.1, R1.3, R11.2_

- [x] 0.2 Copy screening from the KYC starter
  - Copy `01_kyc_agent/tools/screening.py` to `tools/screening.py` with a header comment naming its source.
  - Copy `01_kyc_agent/data/sanctions_list.jsonl` and `pep_list.jsonl` to `data/`.
  - **Done when:** `uv run python -c "from tools.screening import check_pep; print(check_pep('Viktor Harlan'))"` returns one hit.
  - _Requirements: R1.5_

- [x] 0.3 Spike: do sub-agent tools see the run context and store? (timebox 20 min) — passed
  - Build a throwaway `create_deep_agent` with one sub-agent whose tool returns `runtime.context.user_id` and `runtime.store is not None`. Invoke with a context and an `InMemoryStore`.
  - Record the result in PLAN.md section 11 (risk row 1). If either is missing, pick the fallback there before phase 3.
  - Delete the spike file.
  - **Done when:** PLAN.md records "spike passed" or the chosen fallback.
  - _Requirements: R4.6_

- [x] 0.4 Trace once in LangSmith
  - Run the copied agent once so the project's "Agent" tag exists (02's `_get_agent_tag` needs it before dataset creation).
  - **Done when:** a trace appears in project `fsi-hackathon-<ATTENDEE_NAME>`.
  - _Requirements: R11.1_

- [x] 0.5 Commit `chore(scaffold): sentinel_aml_agent from starter (tasks 0.1-0.4)`.

## Phase 1: Contracts and data (finish by 11:15)

- [x] 1.1 Context and schemas
  - `utils/state.py`: extend `MyAgentContext` with `rules_clear_below=30`, `rules_escalate_at=30`, `precedent_ttl_days=365`, `as_of=""`; keep `confidence_threshold=0.7`, `checked_confidence=0.5`, `grey_zone=(30, 70)`.
  - `utils/schemas.py`: `PatternFindings`, `KycFindings`, `NetworkFindings`, `SarDraft` (Pydantic, fields from PLAN.md 4.4), `Precedent`, and the decision record as a `TypedDict` (PLAN.md 4.2).
  - **Done when:** `uv run python -c "from utils.schemas import *; from utils.state import MyAgentContext; MyAgentContext()"` succeeds.
  - _Requirements: R4.3, R6.1_

- [x] 1.2 World-aware database (verified by `scripts/check_db_worlds.py`, including LangChain worker threads)
  - Add a `ContextVar` data folder and a `use_world(n)` context manager to `utils/db.py` (design.md D1). Reference tables stay in `data/`.
  - **Done when:** inside `with db.use_world(1):` a query reads `data/worlds/world_1/`, and outside it reads `data/`.
  - _Requirements: R2.6_

- [x] 1.3 Generator: world 0 demo cast (verified by `scripts/check_data.py`; includes DEC-010's expired, out-of-scope and control customers)
  - `data/generate.py --seed 42 --world 0` writes `customer_profiles`, `transactions`, `analyst_labels`, `reviewer_answers` and `seed_precedents` with the IDs, amounts and dates in design.md D4. Marcus is added to `pep_list.jsonl`.
  - **Done when:** running it twice gives identical file hashes (`shasum data/*.jsonl`), and the D4 events are in `transactions.jsonl`.
  - _Requirements: R2.1, R2.2, R2.4, R2.5_

- [x] 1.4 Generator: background customers and worlds 1-6 — **done with DEC-006 applied**: world 1 (dev) and world 2 (test), 36 customers and 863 / 950 transactions each, instead of 6 worlds × 200. Verified by `scripts/check_data.py`
  - About 200 background customers per world over 2 months: salaries, rent, card spend, benign large credits, benign cash-heavy businesses (rules false positives), plus planted cases of each pattern.
  - Add repeat benign-ambiguous cases in month 2 with reviewer notes in month 1, so the month 1 → month 2 metric can move.
  - Worlds 1-6 go to `data/worlds/world_<N>/`.
  - **Done when:** each world has 150-250 customers, at least one planted case of each pattern, labels for 100% of transactions, and stable hashes across two runs.
  - _Requirements: R2.3, R2.4, R2.6_

- [x] 1.5 Commit `feat(data): labelled synthetic generator (tasks 1.1-1.4)`.

## Phase 2: Rules, tools and routing (finish by 12:15)

- [x] 2.1 Rule scorer and baseline (verified by `scripts/check_rules.py`; network watchlist added, DEC-013)
  - `rules/scorer.py`: `score(tx, history, profile, ctx) -> (int, list[str])` with the features in PLAN.md 5.1, and `baseline_decision(score, ctx)`.
  - **Done when:** on world 0, Daniel's 4th deposit, Sophie's credits and every mule forward score ≥ 30, and at least 90% of world 0 transactions score < 30.
  - _Requirements: R3.1-R3.4_

- [x] 2.2 Fund-flow graph (verified by `scripts/check_graph.py`; signature is `fan_in_summary(account_id, as_of)`, reading the active world)
  - `utils/graph.py`: `build_graph(as_of)` (edges only from transactions before `as_of`) and `fan_in_summary(g, account_id, window_hours=72)`.
  - **Done when:** in world 0, `ring_confirmed` is false at the 4th mule forward and true at the 5th.
  - _Requirements: R7.4, R7.5_

- [x] 2.3 Customer-scoped tools
  - `tools/transactions.py`: `get_transaction`, `get_recent_transactions(days=30)` (up to `as_of`).
  - `tools/customers.py`: `get_customer_profile` (KYC profile only).
  - `tools/screening.py`: `screen_customer` tool wrapper on the profile name.
  - `tools/precedents.py`: `find_precedents(counterparty_id, pattern)`, returning valid, expired and out-of-scope lists.
  - No tool takes `user_id` as an argument.
  - **Done when:** each tool returns the expected result for a world 0 customer when called with a test `ToolRuntime` context, and `grep -n "user_id:" tools/*.py` shows no tool parameter named `user_id`.
  - _Requirements: R4.6, R6.3_

- [x] 2.4 Privileged network tool
  - `tools/network.py`: `trace_fund_flows()`, starting from `runtime.context.user_id`'s account. It returns graph summaries only and writes each call to `("network_audit",)`.
  - **Done when:** called for Liam at the 5th forward, it returns all 5 feeders and Northgate with no profile fields, and one audit record exists.
  - _Requirements: R7.1-R7.3_

- [x] 2.5 `record_decision` with safeguards
  - Extend 02's tool as specified in PLAN.md 5.4, steps 1-6: `clear|escalate`, hard flags, precedent scope and expiry, override logging, the precedent-aware grey-zone check, forced review for hard flag + `clear`, precedent save on resume.
  - **Done when:** direct calls cover four cases: (a) grey zone with no precedent → interrupt; (b) grey zone with a valid precedent → no interrupt; (c) Liam with his precedent and a confirmed ring → precedent overridden, and a `clear` verdict interrupts; (d) a resume with a note saves a precedent with the right `expires_at`.
  - _Requirements: R5.1-R5.4, R6.4-R6.6_

- [x] 2.6 Global stream runner
  - `utils/stream.py`: `global_stream`, `load_seed_precedents(store)`, and `process_stream(agent, ctx, transactions, reviewer_answers=None, on_interrupt=None)`.
  - The rules tier runs first and writes `decided_by="rules"` records. Interrupts are answered by `on_interrupt` or `reviewer_answers`. LLM calls and tokens are counted with `get_usage_metadata_callback()`.
  - Each supervisor invoke passes `run_id=uuid4()` (saved as `trace_run_id` in the decision record) and tags `sentinel`, `investigation`, with metadata `transaction_id`, `user_id`, `rule_score`. (Built: `decided_by` and `pattern` can't be tags, because tags are set before the run starts; the annotation queue selects runs by `trace_run_id` from the decision records instead.)
  - **Done when:** running world 0 with a stub agent records a decision for every transaction, and `llm_share` matches the share of rule scores ≥ 30.
  - _Requirements: R3.2, R6.1, R6.7, R8.1-R8.3_

- [x] 2.7 Commit `feat(core): rules tier, tools, safeguards and stream runner (tasks 2.1-2.6)`.

## Phase 3: Agents (finish by 13:00, Checkpoint A)

- [x] 3.1 Pattern analyst and KYC & precedent sub-agents
  - `sub_agents/pattern_analyst.py` + `.md`, `sub_agents/kyc_precedent.py` + `.md`, as `SubAgent` dicts with `response_format` (03's pattern). Apply the spike outcome from 0.3.
  - **Done when:** each returns a valid findings object for Daniel's 4th deposit.
  - _Requirements: R4.1, R4.3_

- [x] 3.2 Supervisor in `agents.py`
  - `create_deep_agent` with `get_transaction`, `get_customer_profile`, `record_decision`, the sub-agents and `instructions.md` (PLAN.md 5.2).
  - Opens with a judge-readable docstring: what Sentinel is, the three tiers, the four sub-agents, where human review happens, and the disclaimer.
  - **Done when:** `uv run langgraph dev` loads graph `sentinel`. With context `{"user_id": "CUS-0001"}` and Daniel's 4th deposit as the message, the trace shows the supervisor calling `kyc-precedent` and `pattern-analyst` in one turn, then `record_decision` once, with `escalate`.
  - _Requirements: R1.1, R1.3, R4.1, R4.2, R4.4_

- [x] 3.3 Scenario checks
  - `scripts/check_scenarios.py` runs world 0 with seed precedents and scripted answers, then asserts the expected tier and verdict for each scripted transaction: Daniel escalates; Sophie's first credit interrupts; after the note, her second credit auto-clears and cites the precedent; at least 90% clear in the rules tier.
  - **Done when:** it prints PASS for each scenario and exits 0.
  - _Requirements: R3.4, R5.1, R5.4, R6.5_

- [x] 3.4 **Checkpoint A (by 13:00)**
  - `check_scenarios.py` passes.
  - Time Daniel's case from rule flag to verdict on `gpt-6-sol`, and record the seconds in PLAN.md section 11. Above ~30s, plan for `REPLAY=1` on stage.
  - Commit `feat(agents): supervisor with pattern and KYC sub-agents (tasks 3.1-3.3)` and push.

## Phase 4: Network, SAR and the remaining scenarios (finish by 14:40)

- [ ] 4.1 Fund-flow sub-agent and Liam override
  - `sub_agents/fund_flow.py` + `.md`; the only holder of `trace_fund_flows`. Add the mule scenario to `check_scenarios.py`: the 5th forward escalates, and Liam's precedent is in `precedents_overridden` with the reason.
  - **Done when:** `check_scenarios.py` passes, including the mule ring.
  - _Requirements: R4.1, R6.4, R7.1-R7.5_

- [ ] 4.2 SAR writer sub-agent
  - `sub_agents/sar_writer.py` + `.md`: no tools, `SarDraft` output with the fixed disclaimer. The supervisor calls it after an `escalate`.
  - Write `evals/sar_rubric.md` now (completeness criteria for a SAR draft), because 5.2 and 5.6 both use it.
  - **Done when:** Daniel's escalation produces a `SarDraft` whose evidence items all appear in the tool results, and whose `disclaimer` matches R10.4.
  - _Requirements: R4.5, R10.4_

- [ ]* 4.3 Marcus Reid round-trip (cut list item 1)
  - Add Marcus to `check_scenarios.py`; the fund-flow agent finds the round-trip and the PEP flag is a hard flag.
  - _Requirements: R2.2_

- [ ] 4.4 Commit `feat(agents): fund-flow and SAR writer sub-agents (tasks 4.1-4.3)`.

## Phase 5: Evals (finish by 15:10)

- [ ] 5.1 New evaluators
  - Add `false_positive_rate`, `recall_planted`, `reviews_month1`, `reviews_month2`, `override_correctness`, `llm_share` and `cost_per_1k` to `evals/scoring_evals.py`. Leave 02's three evaluators unchanged.
  - **Done when:** on hand-made outputs and labels, each evaluator returns the value worked out by hand.
  - _Requirements: R9.1, R9.2_

- [ ]* 5.2 SAR LLM-as-judge, offline (cut list item 3; uses `evals/sar_rubric.md`)
  - `evals/sar_judge.py`: pass or fail per escalation for completeness, citing evidence, and no facts absent from the evidence.
  - _Requirements: R9.2_

- [ ] 5.3 Experiment runner
  - Update `scripts/run_experiments.py`: one example per world for worlds 1-6, with `dev`/`test` splits (design.md D2). The target wraps each run in `db.use_world(n)`, loads seed precedents, and returns decisions plus counters.
  - Experiments: `rules-only` and `sentinel` on the test split. Write `results/eval_summary.json`.
  - **Done when:** both experiments appear in LangSmith, and `results/eval_summary.json` has every metric for both.
  - _Requirements: R9.3, R9.4_

- [ ] 5.4 Tune on dev
  - Adjust rule weights and thresholds on worlds 1-4 only, until dev hits the R3.4 rules-tier share and `check_scenarios.py` still passes. Then rerun 5.3 on test once.
  - **Done when:** the test results come from one run made after tuning finished, and are recorded in `eval_summary.json`.
  - _Requirements: R9.5_

- [ ] 5.5 Commit `feat(evals): rules-only vs sentinel experiments (tasks 5.1-5.4)`.

- [ ] 5.6 Online evaluator for SAR drafts (PLAN.md 7.1; timebox 15 min)
  - In the LangSmith UI: Tracing → `fsi-hackathon-<ATTENDEE_NAME>` → Online Evaluators → + Evaluator → LLM-as-a-Judge. Filter to `sar-writer` runs, sampling 100%, feedback key `sar_complete` (0-1), prompt from `evals/sar_rubric.md`. Turn on **Apply to past runs** with today's date.
  - Record every setting in `evals/online_evaluators.md`. Check the field names against the docs MCP (`docs-langchain`), page "Set up LLM-as-a-judge online evaluators", before writing them down.
  - **Done when:** after one new escalation (Daniel), the `sar-writer` run in LangSmith carries `sar_complete` feedback from the evaluator.
  - _Requirements: R12.1, R12.2_

- [ ] 5.7 Annotation queue for analyst review (PLAN.md 7.1; timebox 30 min)
  - `scripts/annotation_queue.py`, extending 02 Module 3's code: `create_feedback_config` for `correct_decision` (categorical `clear`/`escalate`) and `evidence_sufficient` (yes/no); `create_annotation_queue("sentinel-analyst-review-<ATTENDEE>", rubric_items=...)`; `add_runs_to_annotation_queue` for every `decided_by == "human"` decision's `trace_run_id`, plus a seeded 10% sample of agent decisions. Call `wait_for_all_tracers()` first, as 02 does.
  - `--collect` reads the queue's feedback with `list_feedback` and writes `results/annotation_summary.json`: reviewed count, agent-analyst agreement rate, disagreements, and `"simulated": true|false`.
  - A person reviews at least the human-decided cases in the LangSmith UI. Only if there's no time, `--simulate` writes feedback from `reviewer_answers.jsonl`, and the summary says `simulated: true` (DEC-003).
  - Optional (cut list item 2): the automation rule (feedback `sar_complete` < 0.7 → add to queue), set in the UI and recorded in `evals/online_evaluators.md`; and adding disagreements to the scenario dataset with `create_examples`.
  - **Done when:** the queue in LangSmith shows the human-decided runs, and `--collect` writes a summary whose reviewed count matches the feedback in LangSmith.
  - _Requirements: R12.3-R12.5_

- [ ] 5.8 Commit `feat(monitoring): online SAR evaluator and analyst annotation queue (tasks 5.6-5.7)`.

## Phase 6: Demo notebook (finish by 15:45, Checkpoint B)

- [ ] 6.1 Replay mode
  - `utils/replay.py`: when `REPLAY=1`, set a SQLite LLM cache at `results/llm_cache.db`. Add `sentinel_aml_agent/results/llm_cache.db` to `/.gitignore` if it's large.
  - **Done when:** a second run of Daniel's case with `REPLAY=1` makes no network LLM calls (check the usage counter or LangSmith).
  - _Requirements: R10.3_

- [ ] 6.2 Notebook shell
  - `modules/01_sentinel_demo.ipynb`: the R10.4 header disclaimer, `sys.path` setup (as in 02), the `REPLAY` toggle, `from agents import build_agent`, and seed precedent loading.
  - _Requirements: R1.2, R10.4_

- [ ] 6.3 Stream and scenario cells
  - Cells in DEMO_SCRIPT order: day-1 stream with a live counter; Daniel with a compact trace summary; Sophie with the `ipywidgets` analyst panel (design.md D3 for other interrupts); Fast-forward 10 months; mule ring with the NetworkX + matplotlib graph and Liam's override line.
  - _Requirements: R10.1, R8.2_

- [ ] 6.4 Results cells
  - The eval table loaded from `results/eval_summary.json`, a link to the LangSmith comparison, and Daniel's SAR draft with the stamp.
  - A monitoring cell: Daniel's SAR `sar_complete` score from the online evaluator (read with `list_feedback`), and the queue's reviewed count and agreement rate from `results/annotation_summary.json`, with "simulated" shown if it applies. Links to the online evaluator and the queue.
  - _Requirements: R9.4, R10.1, R10.4, R12.6_

- [ ] 6.5 **Checkpoint B / feature freeze (by 15:45)**
  - Remove `01_`-`03_` (and `00_dcode_setup`) and their entries in `/pyproject.toml`. Run `uv sync --all-packages` from the root.
  - Run `check_scenarios.py`, then the notebook top to bottom on a fresh kernel with `REPLAY=1`, then once live if time allows.
  - Commit `chore(submission): remove starters; notebook verified (tasks 6.1-6.5)` and push.
  - _Requirements: R1.5, R10.2_

## Phase 7: Submission (15:45-16:00)

- [ ] 7.1 README
  - The top section names the two submission files (`agents.py`, `modules/01_sentinel_demo.ipynb`). Then: one-paragraph summary, quick start (`uv sync --all-packages`, `.env` from `.env.example`), how to run the notebook, Studio, `check_scenarios.py` and `run_experiments.py`, the architecture diagram, eval results, and the disclaimer.
  - _Requirements: R1.4_

- [ ] 7.2 Final checks
  - Run every item in PLAN.md section 12 (definition of done) and tick it.
  - `git grep -nE "lsv2_[a-z]{2}_[0-9a-f]{16}" $(git rev-list --all)` returns nothing; `.env` isn't tracked.
  - _Requirements: R1.6_

- [ ] 7.3 Commit, push and tag
  - Commit `docs: submission README (task 7.1)`, push, then `git tag submission && git push origin submission`.
  - **Done when:** the tag is on GitHub and the repo's file list shows `sentinel_aml_agent/agents.py` and the notebook.

- [ ]* 7.4 Backup video and rehearsal (presenters)
  - Screen-record one clean `REPLAY=1` run. Rehearse to 4:45.

---

## Traceability

| Requirement | Tasks |
|---|---|
| R1 Submission | 0.1, 0.2, 3.2, 6.2, 6.5, 7.1-7.3 |
| R2 Data | 1.2-1.4, 4.3 |
| R3 Rules tier | 2.1, 2.6, 3.3, 5.4 |
| R4 Multi-agent | 0.3, 1.1, 2.3, 3.1, 3.2, 4.1, 4.2 |
| R5 Human in the loop | 2.5, 3.3 |
| R6 Memory and safeguards | 1.1, 2.3, 2.5, 2.6, 3.3, 4.1 |
| R7 Network | 2.2, 2.4, 4.1 |
| R8 Stream | 2.6, 6.3 |
| R9 Evals | 5.1-5.4, 6.4 |
| R10 Notebook | 4.2, 6.1-6.5 |
| R11 Observability | 0.1, 0.4, 3.2 |
| R12 Monitoring and analyst review | 2.6, 4.2, 5.6-5.8, 6.4 |
