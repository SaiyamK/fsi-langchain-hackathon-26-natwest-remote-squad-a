# PLAN.md: Building Sentinel

Implementation plan for the use case in [USE_CASE.md](USE_CASE.md) and the demo in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).
Read [HACKATHON.md](HACKATHON.md) first for ground rules and repo conventions.

> Synthetic data only. Outputs are drafts for analyst review, not legal, compliance or regulatory advice.

## 1. Decisions this plan makes

| Decision | Choice | Why |
|---|---|---|
| Where the code lives | New folder **`sentinel_aml_agent/`** (no number prefix), created by copying `02_transaction_monitoring_agent/` and extending it | The `01_`-`03_` starters are removed before final submission, so Sentinel must not depend on them at runtime: everything it reuses is **copied** in. USE_CASE.md and DEMO_SCRIPT.md use the same folder name |
| Removing the starters before submission | Delete `01_`, `02_`, `03_` (and optionally `00_dcode_setup`), and remove them from `[tool.uv.workspace].members` in `/pyproject.toml`. Then run `uv sync --all-packages` and the notebook once more | Proves Sentinel is self-contained. Do this at Checkpoint B, not at 15:55 |
| Hard flag present but the agent says `clear` | **Human in the loop**: force `interrupt()` so the analyst decides | Agreed. The agent can't clear a hard-flag case on its own, and a human sees every such case |
| Labels for mule forwards before the ring is confirmable | `ambiguous: true, decision: escalate` | Agreed |
| Submission files | **`agents.py`** holds the real supervisor code (no `agent.py`), and **`modules/01_sentinel_demo.ipynb`** is the notebook. `langgraph.json` points at `./agents.py:agent`; the notebook and scripts import `from agents import build_agent` | The attendee guide asks for a notebook plus `agents.py`. Putting the code in that file, rather than a one-line re-export, means a judge who opens it sees the multi-agent build, and the notebook visibly runs the submitted file |
| Base pattern | 02's memory, `interrupt()`, confidence checks, `db.py`, eval harness; 03's `create_deep_agent` + `SubAgent` + `response_format`; 01's screening functions and watchlists | Everything Sentinel needs already exists in one of the three starters |
| Where the human-review `interrupt()` lives | In `record_decision`, called **only by the supervisor**, never inside a sub-agent | Same place as 02, so pause/resume works the way it already does in Studio and the notebook. Avoids relying on interrupts propagating out of nested sub-agent runs |
| Who enforces safeguards | **Code**, not the LLM. Hard red flags, precedent expiry and scope are computed deterministically in `record_decision` | Matches 02's rule: deterministic checks can add human oversight but never remove it. The LLM explains; code decides what's allowed |
| "Now" for expiry and the network | The **transaction's timestamp**, not the wall clock | Makes Fast-forward deterministic and stops the network tool seeing future transactions |
| Processing order | One **global stream across all customers, sorted by timestamp**, with one thread per customer | The mule ring can only be detected if other customers' transactions have already been seen. 02 processed one customer at a time |
| Decision vocabulary | `clear | escalate` everywhere (tools, prompts, labels, evaluators, resume payload) | AML reviews after the fact; it doesn't block payments |

## 2. What we reuse, and how

| Source | File | Reuse in `sentinel_aml_agent/` |
|---|---|---|
| 02 | `utils/db.py`, `utils/__init__.py`, `utils/models.py`, `utils/attendee.py` | Copy unchanged |
| 02 | `utils/state.py` (`MyAgentContext`) | Extend: add rule-tier thresholds, `precedent_ttl_days`, `as_of` |
| 02 | `tools/transactions.py`, `tools/customers.py` | Keep the customer-scoped lookup pattern (`runtime.context.user_id`). `get_customer_profile` returns the KYC profile; free-text notes move to precedents |
| 02 | `tools/decisions.py` (`record_decision`, `_confidence_checks`) | Extend: `clear|escalate`, hard-flag checks, precedent-aware grey-zone check, override logging. Same `interrupt()` and `("decisions", user_id)` audit record |
| 02 | `utils/transaction_processing.py` | Extend: rules tier before `agent.invoke`, global ordering, LLM-call counter. Keep the `reviewer_answers` auto-resume loop for evals |
| 02 | `evals/scoring_evals.py` | Keep all three evaluators unchanged. Add new ones in the same file |
| 02 | `scripts/run_experiments.py` | Keep dataset creation, `_get_agent_tag`, `evaluate`, `average_scores`. Swap the two experiments for `rules-only` vs `sentinel`. Import `build_agent` from `agents` instead of `agent` |
| 02 | `langgraph.json`, `pyproject.toml`, `instructions.md` | Copy and edit (graph name, deps, AML prompt) |
| 03 | `agent.py` (`create_deep_agent(..., subagents=[...])`) | Pattern for the supervisor, written into `agents.py` |
| 03 | `sub_agent.py` (`SubAgent` dict, `response_format=PydanticModel`) | Pattern for the 4 sub-agents and their structured findings |
| 01 | `tools/screening.py` (`check_sanctions`, `check_pep`), `data/sanctions_list.jsonl`, `data/pep_list.jsonl` | **Copy** into `sentinel_aml_agent/` (see note below) |

**Why copy 01's screening instead of importing it:** every topic has top-level packages named `utils` and `tools`,
so `01_kyc_agent/tools/screening.py`'s `from utils import db` would pick up `sentinel_aml_agent/`'s `utils`. It's a small, pure file.
Copy it and keep a comment pointing at the source.

## 3. Target layout

```
sentinel_aml_agent/
├── README.md                      new: setup, run, demo, eval
├── pyproject.toml                 from 02 + deepagents, networkx, matplotlib, ipywidgets
├── langgraph.json                 graph "sentinel" -> ./agents.py:agent
├── agents.py                      SUBMISSION FILE. Supervisor: create_deep_agent(subagents=[...]); exports build_agent, agent
├── instructions.md                supervisor system prompt
├── sub_agents/
│   ├── __init__.py                SUBAGENTS list
│   ├── pattern_analyst.py         + pattern_analyst.md
│   ├── kyc_precedent.py           + kyc_precedent.md
│   ├── fund_flow.py               + fund_flow.md
│   └── sar_writer.py              + sar_writer.md
├── tools/
│   ├── transactions.py            get_transaction, get_recent_transactions (customer-scoped)
│   ├── customers.py               get_customer_profile (KYC profile)
│   ├── screening.py               copied from 01; plus screen_customer tool wrapper
│   ├── precedents.py              find_precedents (scope + expiry aware)
│   ├── network.py                 trace_fund_flows: the ONE privileged cross-customer tool, audited
│   └── decisions.py               record_decision (extended from 02)
├── rules/
│   └── scorer.py                  deterministic rule scorer: score + reasons; also the rules-only baseline
├── utils/
│   ├── db.py, models.py, attendee.py, __init__.py   copied from 02
│   ├── state.py                   MyAgentContext (extended)
│   ├── schemas.py                 Pydantic: findings, Verdict, Precedent, SarDraft
│   ├── graph.py                   builds the NetworkX fund-flow graph up to `as_of`
│   ├── stream.py                  global stream, rules tier, routing, LLM counter (extends 02's transaction_processing)
│   └── replay.py                  REPLAY=1 LLM cache for the demo
├── data/
│   ├── generate.py                seeded, labelled synthetic generator
│   ├── customer_profiles.jsonl    KYC profiles (generated)
│   ├── transactions.jsonl         AML schema (generated)
│   ├── analyst_labels.jsonl       + pattern, expect_override, month (generated)
│   ├── reviewer_answers.jsonl     scripted analyst answers for evals and auto-resume (generated)
│   ├── seed_precedents.jsonl      e.g. Liam's old clearance (generated)
│   ├── sanctions_list.jsonl       copied from 01, plus any Sentinel entries
│   └── pep_list.jsonl             copied from 01, plus Marcus Reid's PEP link
├── evals/
│   ├── scoring_evals.py           02's 3 evaluators + new metrics
│   ├── sar_judge.py               LLM-as-judge for SAR drafts (offline)
│   ├── sar_rubric.md              the one SAR rubric, shared by the offline judge and the online evaluator
│   └── online_evaluators.md       exact settings of the LangSmith online evaluator (UI setup, so it's repeatable)
├── scripts/
│   ├── run_experiments.py         rules-only vs sentinel (extends 02)
│   ├── check_scenarios.py         asserts each scripted demo transaction lands in the expected tier/verdict
│   └── annotation_queue.py        creates the analyst review queue, adds runs, collects feedback (extends 02 Module 3)
├── results/                       saved eval summary (JSON) the notebook loads; no secrets
└── modules/
    └── 01_sentinel_demo.ipynb     SUBMISSION FILE. The demo notebook; imports from agents.py
```

Root changes: add `"sentinel_aml_agent"` to `[tool.uv.workspace].members` in `/pyproject.toml`, then run
`uv sync --all-packages` from the repo root.

## 4. Contracts (agree these first so workstreams can build in parallel)

### 4.1 Data schemas

`customer_profiles.jsonl`
```json
{"user_id": "CUS-0001", "name": "Daniel Hughes", "account_id": "ACC-0001", "customer_type": "individual",
 "occupation": "market trader", "risk_rating": "low", "pep": false, "home_country": "GB", "currency": "GBP",
 "expected_monthly_credits": 12000, "expected_monthly_cash": 12000, "account_opened": "2019-04-02"}
```

`transactions.jsonl` (02's fields kept where they still make sense; AML fields added)
```json
{"transaction_id": "TX-000123", "user_id": "CUS-0001", "account_id": "ACC-0001", "timestamp": "2026-10-06T10:14",
 "direction": "in", "txn_type": "cash_deposit", "amount": 9500, "currency": "GBP",
 "counterparty_id": null, "counterparty_name": null, "branch": "Leeds Briggate", "country": "GB",
 "reference": "", "channel": "branch"}
```
`txn_type` is one of `cash_deposit | cash_withdrawal | faster_payment | bacs | card | internal_transfer`.
`counterparty_id` is an `ACC-` ID when the counterparty banks with us (needed for the network), else an `EXT-` ID.

`analyst_labels.jsonl` (02's fields + 3 new)
```json
{"transaction_id": "TX-000123", "decision": "escalate", "risk_score": 90, "ambiguous": false,
 "pattern": "structuring", "expect_override": false, "month": 1}
```
`pattern` is one of `none | structuring | anomalous_credit | round_tripping | mule_fan_in`.

`seed_precedents.jsonl` / precedent store value
```json
{"user_id": "CUS-0040", "counterparty_id": "*flatmates*", "pattern": "mule_fan_in", "decision": "clear",
 "note": "Transfers from flatmates for rent", "analyst": "seed", "created_at": "2026-03-10", "expires_at": "2027-03-10"}
```

### 4.2 Store namespaces (LangGraph store, as in 02)

| Namespace | Key | Value | Written by |
|---|---|---|---|
| `("precedents", user_id)` | `f"{counterparty_id}:{pattern}"` | Precedent (above) | `record_decision` after a human answer; seeded at start |
| `("decisions", user_id)` | `transaction_id` | Decision record (below) | `record_decision`, and the rules tier for auto-clears |
| `("network_audit",)` | uuid | `{as_of, seed_account, hops, accounts_returned, caller}` | `trace_fund_flows` on every call |

Decision record, a superset of 02's so its evaluators keep working:
```python
{"transaction_id", "risk_score", "model_confidence", "confidence", "confidence_checks",
 "agent_decision", "final_decision", "decided_by",            # decided_by: "rules" | "agent" | "human"
 "reason", "pattern", "hard_flags", "precedents_cited", "precedents_overridden",
 "rule_score", "rule_reasons", "sar_id", "trace_run_id"}  # trace_run_id: LangSmith root run, for the annotation queue
```
The stream runner sets `trace_run_id` by passing its own `run_id=uuid4()` in the invoke config, and the tags
`sentinel`, `decided_by:<rules|agent|human>` and `pattern:<pattern>` so LangSmith filters and rules can target runs.
```python
```

### 4.3 Function signatures

```python
# rules/scorer.py
def score(tx: dict, history: list[dict], profile: dict, ctx: MyAgentContext) -> tuple[int, list[str]]: ...
#   history = this customer's earlier transactions up to tx["timestamp"]

# utils/graph.py
def build_graph(as_of: str) -> nx.DiGraph: ...                    # edges from transactions before as_of
def fan_in_summary(g, account_id, window_hours=72) -> dict: ...  # feeders, collector, pass-through ratios

# utils/stream.py
def global_stream(start=None, end=None) -> list[dict]: ...        # all customers, timestamp order
def process_stream(agent, ctx, transactions, reviewer_answers=None, on_interrupt=None) -> dict: ...
#   returns {"decisions": [...], "llm_calls": n, "tokens": {...}}
```

### 4.4 Sub-agent outputs (`utils/schemas.py`, used as `response_format` like 03's `SectionSummary`)

| Sub-agent | Output model | Key fields |
|---|---|---|
| `pattern-analyst` | `PatternFindings` | `pattern`, `evidence: list[str]`, `aggregate_amount`, `window_hours`, `risk_score`, `confidence` |
| `kyc-precedent` | `KycFindings` | `risk_rating`, `screening_hits`, `precedents_applicable`, `precedents_expired`, `hard_flags`, `risk_score` |
| `fund-flow` | `NetworkFindings` | `pattern`, `accounts`, `collector_account`, `pass_through_ratio`, `ring_confirmed: bool` |
| `sar-writer` | `SarDraft` | `subject`, `pattern`, `timeline`, `evidence`, `narrative`, `precedents_cited_or_overridden`, `disclaimer` |

## 5. Component design

### 5.1 Rule scorer (tier 1, and the baseline)
Deterministic. Sums points for:
- Cash deposit between £9,000 and £9,999 (just under the £10,000 monitoring threshold)
- Rolling 48h cash total above the customer's `expected_monthly_cash`
- Single credit at least 3× `expected_monthly_credits`
- First payment from a new counterparty
- Pass-through: at least 90% of credits received in the last 24h sent out again
- Outbound then inbound of a similar amount via a different counterparty within 30 days (round-trip)
- Multiplier for `risk_rating=high` or `pep=true`

The score is below `ctx.rules_clear_below` (default 30): auto-clear, recorded with `decided_by="rules"`, no LLM call.
Otherwise the transaction goes to the supervisor.
**Baseline mode:** escalate if score ≥ `ctx.rules_escalate_at` (default 30), else clear. Same code, so the comparison is fair.
Tune weights on the **dev** split only, until about 95% of transactions clear in tier 1 and `check_scenarios.py` passes.

### 5.2 Supervisor (`agents.py`, Deep Agent)
The file starts with a short docstring a judge can read in 30 seconds: what Sentinel is, the three tiers, the 4 sub-agents, where the human review happens, and the disclaimer.
`create_deep_agent(model=init_chat_model(model), tools=[get_transaction, get_customer_profile, record_decision],
subagents=SUBAGENTS, system_prompt=instructions.md, context_schema=MyAgentContext, **kwargs)`.
The prompt:
- Receive `New transaction: TX-… (rule score S: reasons)`.
- Pick only the specialists the rule reasons call for, and call them **in the same turn** so they run in parallel.
- Call `kyc-precedent` every time.
- Combine the findings, then call `record_decision` once.
- If the final decision is `escalate`, call `sar-writer` with the evidence.
- Reply in one sentence.

### 5.3 Sub-agents (`SubAgent` dicts, as in 03)
- **pattern-analyst**: `get_recent_transactions(days=30)` (customer-scoped) and `get_customer_profile`. Finds structuring, spikes and anomalous credits.
- **kyc-precedent**: `get_customer_profile`, `screen_customer` (01's `check_sanctions`/`check_pep` on the profile name), and `find_precedents(counterparty_id, pattern)`. Reports which precedents are valid, expired or out of scope. It reports hard flags but does not enforce them; `record_decision` does.
- **fund-flow**: the only holder of `trace_fund_flows()`. The seed account is taken from `runtime.context.user_id`, **not from a model argument**, so the privilege stays narrow. It returns graph summaries (account IDs, amounts, timings), never profiles. Every call is written to `("network_audit",)`.
- **sar-writer**: no tools. It only uses the evidence passed in. Structured `SarDraft` with a fixed disclaimer field.

### 5.4 `record_decision` (extended from 02)
Args: `transaction_id, risk_score, confidence, decision: Literal["clear","escalate"], pattern, reason, precedents_cited: list[str]`.
Deterministic steps, in order:
1. `hard_flags` = sanctions/PEP hit on the customer (01 functions), plus `fan_in_summary(...).ring_confirmed` for this account.
2. Validate the cited precedents: right scope (`user_id`, `counterparty_id`, `pattern`) and `as_of < expires_at`. Invalid ones are dropped with a reason.
3. If `hard_flags` is non-empty, any cited precedent is moved to `precedents_overridden` with the reason. If `decision == "clear"`, force human review.
4. Confidence checks, as in 02: grey-zone score (30 to 69) lowers confidence to `checked_confidence`. **Exception:** a valid, in-scope precedent with no hard flags satisfies the grey-zone check, because a human already decided this exact case. This is the one place a check is relaxed; say so in Q&A.
5. If `confidence < confidence_threshold`, call `interrupt({...evidence, why_review, precedents...})`, then resume with `{"decision": "clear"|"escalate", "note": "..."}`. If there's a note, save a precedent with `expires_at = as_of + precedent_ttl_days`.
6. Write the decision record to `("decisions", user_id)`.

### 5.5 Stream runner (`utils/stream.py`, extends 02's `process_transactions`)
For each transaction in global time order:
1. Run the rule scorer.
2. Auto-clear, or invoke the supervisor on thread `user_id` with `context=replace(ctx, user_id=..., as_of=tx["timestamp"])`.
3. Resolve interrupts from `reviewer_answers` (evals), or through an `on_interrupt` callback (the notebook's `ipywidgets` panel).

Count LLM calls and tokens with `langchain_core.callbacks.get_usage_metadata_callback()` to get the "% of transactions reaching an LLM" and cost per 1,000 transactions figures.

### 5.6 Memory
- Short-term: the checkpointer, one thread per customer, as in 02. `get_recent_transactions` reads the DB up to `as_of`, so the pattern analyst doesn't depend on chat history length.
- Long-term: precedents and decisions in the store. `seed_precedents.jsonl` is loaded into the store when the run starts (in the notebook, evals and `check_scenarios.py`).

### 5.7 Replay mode (`utils/replay.py`)
`REPLAY=1` sets a LangChain SQLite LLM cache (`set_llm_cache(SQLiteCache("results/llm_cache.db"))`) that was filled during a good rehearsal run.
This only replays if prompts are byte-identical, so keep IDs, timestamps and seeds fixed.
Verify on a cold kernel before the demo. If the gateway model rejects `temperature=0` (some reasoning models do), drop it and rely on replay.

## 6. Data generator (`data/generate.py`)
- `--seed`, `--world N`: each "world" is about 200 background customers over 2 months, plus the seeded demo cast. Only world 0 holds the exact DEMO_SCRIPT names, amounts and dates.
- Demo cast, as in DEMO_SCRIPT.md:
  - **Daniel Hughes:** 4 × £9,500 cash deposits at 3 branches in 48h.
  - **Sophie Clarke:** £18,000 from a new employer counterparty in month 1, then £19,200 from the same counterparty 10 months later.
  - **Marcus Reid:** PEP-linked. £250k out, then £240k back via a different account.
  - **Mule ring:** Liam, Chloe, Ben, Amira and Josh receive many small transfers and forward almost all of it within hours to **Northgate Trading Ltd**. Liam gets a seed precedent cleared on 2026-03-10.
- Background noise: salaries, rent, card spend, the occasional benign large credit (anomalous but labelled `clear`), and benign cash-heavy businesses. This gives the rules realistic false positives for Sentinel to remove.
- Labels are written at generation time (`decision`, `risk_score`, `ambiguous`, `pattern`, `expect_override`, `month`).
- **Labelling the first mule forwards (agreed):** the ring can't be confirmed until enough feeders exist. Label the forwards before the threshold as `ambiguous: true, decision: escalate`, so the right outcome is "asks a human".
- Split: worlds 1 to 4 are **dev** and worlds 5 to 6 are **test**. Report on test only. World 0 is the demo and is not in the eval.

## 7. Evals

Reuse 02's harness. One dataset example is **one world** (its global stream plus reviewer answers), and outputs keep 02's shape (`{"decisions": [...]}` vs `{"labels": {tx_id: label}}`), so `decision_accuracy_eval`, `score_alignment_eval` and `review_routing_eval` run unchanged.

| New evaluator (`evals/scoring_evals.py`) | Definition |
|---|---|
| `false_positive_rate` | Escalated, but labelled `clear` ÷ all labelled `clear` (lower is better) |
| `recall_planted` | Escalated, among labels with `pattern != none` |
| `reviews_month1`, `reviews_month2` | Count of `decided_by == "human"` by label `month` |
| `override_correctness` | Share of `expect_override` transactions with a non-empty `precedents_overridden` and final decision `escalate` |
| `llm_share`, `cost_per_1k` | From the runner's counters, returned in outputs |
| `sar_quality` (`evals/sar_judge.py`) | LLM-as-judge via the gateway model with structured output: complete, evidence-cited, no facts absent from the evidence. Pass/fail per escalation |

Experiments (`scripts/run_experiments.py`): `rules-only` (the baseline mode of the same scorer, no LLM) and `sentinel`.
Dataset name: `f"{LANGSMITH_PROJECT}-sentinel"`. Keep 02's `_get_agent_tag` prerequisite: trace the agent once before creating the dataset.
Write the averaged results to `results/eval_summary.json`. The notebook only **loads** this file and never runs evals live.

### 7.1 Monitor and govern in LangSmith: online evaluator and annotation queue
Offline experiments prove Sentinel on a benchmark. These two features show how it would be **watched and corrected
after go-live**, covering the "monitor, govern, improve" part of the hackathon lifecycle.

**Online evaluator: every SAR draft is judged as it's written.**
- An LLM-as-judge online evaluator on the tracing project `fsi-hackathon-<ATTENDEE_NAME>`, filtered to `sar-writer` runs (by run name, or tag `subagent:sar-writer`), sampling 100%.
- Feedback key `sar_complete` (0-1), with a short comment. The prompt is `evals/sar_rubric.md`, the same rubric the offline `sar_judge.py` uses, so online and offline scores mean the same thing.
- Set up in the LangSmith UI (Tracing → project → Online Evaluators → + Evaluator → LLM-as-a-Judge), because the docs describe online evaluators as a UI feature. `evals/online_evaluators.md` records every setting (name, filter, sampling, model, prompt, feedback key) so anyone can recreate it. Use **Apply to past runs** when creating it, so existing SARs are scored too.
- Groundedness stays a **code** check (`sar_grounded`, offline), because an online judge can't see our database.

**Annotation queue: the analyst's review desk in LangSmith.**
- `scripts/annotation_queue.py`, following 02 Module 3's pattern (`create_feedback_config`, `create_annotation_queue` with rubric items, `add_runs_to_annotation_queue`).
- Queue `sentinel-analyst-review-<ATTENDEE>` with rubric items:
  - `correct_decision` (categorical: `clear` / `escalate`): what the analyst would decide;
  - `evidence_sufficient` (yes/no): did the investigation gather enough to decide?
- **What goes in:**
  - every case decided by a human (`decided_by == "human"`), using `trace_run_id`, so interrupt decisions also get a reviewable trace;
  - a sample of agent-only decisions (default 10%), as a spot check of the cases no human saw;
  - SAR drafts scoring below 0.7 on the online evaluator, via a LangSmith **automation rule** (filter: feedback `sar_complete` < 0.7 → action: add to annotation queue), set up in the UI and recorded in `evals/online_evaluators.md`.
- **What comes out:** `annotation_queue.py --collect` reads the feedback and writes `results/annotation_summary.json`: the number reviewed, the **agent-analyst agreement rate**, and the disagreements. Disagreements are added to the scenario dataset as new labelled examples (02's "growing datasets" pattern), so the next experiment tests them.
- **Honesty (DEC-003):** reviews are done by a person in the LangSmith UI. If time forces simulated reviews (02's `SIMULATE_ANNOTATIONS`), the summary and the notebook say "simulated" next to every number that uses them.

**In the demo** (inside the existing 3:45-4:30 eval slot, about 10 seconds): "After go-live, every SAR is judged automatically as it's written; weak ones, and a sample of the agent's own decisions, land in the analyst's review queue, and their corrections become new test cases." Show the online evaluator scores on the project, then the queue.

## 8. Demo notebook (`modules/01_sentinel_demo.ipynb`)
The cells follow the DEMO_SCRIPT run of show:
1. Header disclaimer, setup (`sys.path` to the folder root, as in 02), `REPLAY` toggle, load seed precedents.
2. **Stream: day 1**: a live counter of processed transactions, % cleared by rules and LLM calls.
3. **Structuring**: Daniel. Print a compact trace summary from the decision record and sub-agent findings.
4. **Unsure, so ask a human**: Sophie. The `ipywidgets` panel (evidence, why it's unsure, note box, Clear/Escalate buttons) resumes the graph with `Command(resume=...)`.
5. **Fast-forward 10 months**: Sophie's second credit auto-clears and cites the precedent.
6. **Mule ring**: a NetworkX and matplotlib graph with Northgate highlighted, then Liam's precedent override line.
7. **Eval results** from `results/eval_summary.json`, plus a link to the LangSmith experiment comparison.
7b. **Monitoring** (section 7.1): the online evaluator's `sar_complete` scores and the annotation queue counts and agreement rate from `results/annotation_summary.json`, with links to both in LangSmith.
8. **SAR draft** for Daniel, with the stamp.

## 9. Schedule (build blocks today)

Each checkpoint ends with a working, committed state. Cut from the bottom of section 10 if a checkpoint slips.

| When | Workstream 1: Data & eval | Workstream 2: Rules & routing | Workstream 3: Agents & memory | Workstream 4: Notebook & pitch |
|---|---|---|---|---|
| **10:00-10:30** | Agree section 4 contracts together. One person scaffolds `sentinel_aml_agent/` (copy 02, rename graph, workspace member, `uv sync --all-packages`, trace once) | | **Spike:** confirm sub-agent tools receive `runtime.context` and `runtime.store` in deepagents 0.7.28 (see risks) | Slide skeleton on the template, once it's shared |
| **10:30-11:30** | `generate.py` world 0 (demo cast) + labels | `rules/scorer.py` + baseline mode | `record_decision` (`clear|escalate`, hard flags, precedents), `find_precedents`, `screening.py` copy | Notebook shell, disclaimer, counter cell |
| **11:30-12:30** | Background noise + worlds 1 to 6 | `stream.py` global runner + LLM counter; `check_scenarios.py` | Supervisor + `pattern-analyst` + `kyc-precedent` | `ipywidgets` analyst panel wired to `Command(resume=...)` |
| **12:30-13:00** | **Checkpoint A (MVP):** Daniel escalates, Sophie pauses then her second credit auto-clears from the precedent, ≥ 90% cleared by rules. Commit. | | | |
| **14:00-15:00** | Eval dataset + new evaluators; first `rules-only` run | Tune rule weights on dev | `utils/graph.py` + `fund-flow` agent + `network_audit`; Liam override | Network graph cell, trace summary cells |
| **15:00-15:30** | `sentinel` experiment on test, write `eval_summary.json`; online evaluator + automation rule (UI), `annotation_queue.py` (section 7.1) | Replay cache: fill and verify on a cold kernel | `sar-writer` + `sar_judge.py` + `sar_rubric.md` | Eval results cell + SAR cell + monitoring cell |
| **15:30-15:45** | **Checkpoint B (feature freeze):** remove the `01_`-`03_` starters and their workspace entries, run `uv sync --all-packages`, then the full notebook top to bottom with `REPLAY=1`. Commit. | | | |
| **15:45-16:00** | Final README (names the two submission files at the top), check `agents.py` docstring, `git status` check for secrets, push | | | Rehearse to 4:45; record a backup video if there's time |

## 10. Cut list (drop from the bottom first)
1. Marcus Reid round-trip (mention it in Q&A only)
2. Annotation queue extras: the automation rule from low SAR scores, the 10% agent spot-check sample, and growing the dataset from disagreements (keep the queue with human-reviewed cases)
3. `sar_quality` offline LLM-as-judge (keep the online evaluator, which uses the same rubric)
4. `cost_per_1k` (keep `llm_share`)
5. Month 1 → month 2 review metric
6. Annotation queue entirely, then the online evaluator (both are about 10 seconds of the demo; the offline eval stays)
7. Live `ipywidgets` panel (fall back to a scripted `Command(resume=...)` cell)
8. Fund-flow as a sub-agent (fall back to a deterministic network check inside `record_decision`, still drawn in the notebook)
9. Deep Agents supervisor (fall back to 02's `create_agent` with the specialists as plain tools; listed in USE_CASE.md)

Never cut: rules tier, human-in-the-loop with a precedent, the hard-flag override, the rules-only vs Sentinel eval, and the disclaimer.

## 11. Risks to check early

| Risk | Check | Fallback |
|---|---|---|
| Sub-agent tools may not see `runtime.context` / `runtime.store` | **Spike passed (task 0.3, deepagents 0.7.28, `gpt-6-sol`):** a sub-agent tool read `runtime.context.user_id` from the parent's `context=`, and wrote to `runtime.store`; the parent saw the write. Matches the docs (Deep Agents → Subagents → Context management) | Not needed. (Was: closures over a per-run context, or move lookups to the supervisor. Never let the model pass `user_id`) |
| Live latency: about 4 investigations, each a supervisor plus 2 to 3 sub-agents | **Measured at Checkpoint A (`gpt-6-sol`, `check_scenarios.py`):** Daniel's structuring case 34-36s (about 15 model calls, ~50k tokens, including the SAR); Sophie's cases 19-21s; Grace and Tom 19-22s. Daniel is above ~30s, so plan `REPLAY=1` for him on stage, with the banner (DEC-003); Sophie fits live | `REPLAY=1` by default on stage; parallel sub-agent calls; the supervisor calls only the specialists it needs |
| Mule ring confirmed on the wrong transaction | `check_scenarios.py` asserts the 5th forward triggers `ring_confirmed` | Pre-compute `fan_in_summary` per account and `as_of` |
| Eval cost and runtime | Count LLM calls on one dev world | Fewer background customers per world; `max_concurrency=2` as in 02 |
| `.langgraph_api/`, `__pycache__/`, `results/llm_cache.db` committed | Already git-ignored except the cache | Add `sentinel_aml_agent/results/llm_cache.db` to `.gitignore` if it holds anything sensitive (synthetic only, but it's large) |
| `uv sync` inside `sentinel_aml_agent/` breaks other topics | | Only `uv sync --all-packages` at the root |

## 12. Definition of done
- [x] `uv sync --all-packages` installs cleanly with `sentinel_aml_agent/` in the workspace
- [x] `uv run langgraph dev` in `sentinel_aml_agent/` loads graph `sentinel`. Context `{"user_id": "CUS-0001"}` plus `New transaction: TX-…` runs end to end
- [x] `uv run python scripts/check_scenarios.py` passes: every scripted demo transaction lands in the expected tier and verdict
- [x] `uv run python scripts/run_experiments.py` creates both experiments in LangSmith and writes `results/eval_summary.json`
- [ ] The online evaluator scores new `sar-writer` runs with `sar_complete` in the tracing project, and its settings are in `evals/online_evaluators.md` — **settings written; waiting on the user to create it in the LangSmith UI**
- [ ] The annotation queue `sentinel-analyst-review-<ATTENDEE>` holds the human-decided cases, and `annotation_queue.py --collect` writes `results/annotation_summary.json` (marked "simulated" if reviews were simulated) — **queue created with 5 runs; waiting on a person to review, then `--collect`**
- [x] The notebook runs top to bottom on a fresh kernel, live and with `REPLAY=1`
- [x] Traces visible in project `fsi-hackathon-<ATTENDEE_NAME>`
- [x] Submission files present in `sentinel_aml_agent/`: `agents.py` (the real supervisor code, no `agent.py`) and `modules/01_sentinel_demo.ipynb` (imports from `agents`)
- [x] README updated and names the two submission files at the top; disclaimer on the notebook header and SARs
- [x] `git status` / `git diff --staged` show no `.env` or keys before push

## 13. Open questions
- [x] Folder: `sentinel_aml_agent/`, self-contained; starters removed before submission
- [x] Labels for mule forwards before the ring is confirmable: `ambiguous` + `escalate`
- [x] Hard flag + agent says `clear`: human in the loop
- [x] Model: `MODEL_NAME="openai:gpt-6-sol"` in `.env` (verified through the gateway). At Checkpoint A, time Daniel's case on it; if it's too slow for the live demo, rely on `REPLAY=1` rather than switching model
- [x] Workstream owners: all four are owned by Kiro (Claude). With one owner, section 9 runs as a sequence, not in parallel: build in the order data → rules → agents → notebook within each time slot, and treat the checkpoints as hard gates
- [ ] Source for the false-positive statistic on slide 1. Proposed: Columbia SIPA, "Detecting Financial Crimes: Evaluating the Efficacy of Automated Transaction Monitoring" (about 90-95% false positives on average): https://www.sipa.columbia.edu/detecting-financial-crimes-evaluating-efficacy-automated-transaction-monitoring. Check the page before it goes on the slide
