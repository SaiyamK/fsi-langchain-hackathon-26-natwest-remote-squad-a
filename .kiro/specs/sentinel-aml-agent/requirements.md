# Requirements: Sentinel AML Agent

Source documents: #[[file:USE_CASE.md]] (what and why), #[[file:DEMO_SCRIPT.md]] (what the judges see),
#[[file:PLAN.md]] (design source of truth). Ground rules and submission rules: #[[file:HACKATHON.md]].

All requirements use EARS phrasing. "Sentinel" means the code in `sentinel_aml_agent/`.

## R1. Submission and repository

**User story:** As the team, we want a submission that matches the hackathon rules, so that judges can find and run it.

1. THE submission SHALL contain `sentinel_aml_agent/agents.py` holding the supervisor code, and no `agent.py`.
2. THE submission SHALL contain the Jupyter notebook `sentinel_aml_agent/modules/01_sentinel_demo.ipynb`, which imports from `agents`.
3. THE `langgraph.json` SHALL register graph `sentinel` as `./agents.py:agent`.
4. THE `README.md` SHALL name the two submission files at the top and give the commands to install, run, check and evaluate.
5. WHEN the starter folders `01_`-`03_` are removed from the repo and from `[tool.uv.workspace].members`, THE notebook and scripts SHALL still run (Sentinel never imports from a starter folder).
6. THE repository SHALL never contain `.env`, API keys or real customer data, in any commit.

## R2. Synthetic, labelled data

**User story:** As the team, we want deterministic synthetic data with labels, so that the demo and evals are reproducible.

1. THE generator `data/generate.py` SHALL produce the same files byte for byte for the same `--seed` and `--world`.
2. World 0 SHALL contain exactly the demo cast in DEMO_SCRIPT.md: Daniel Hughes, Sophie Clarke (two credits ten months apart), Marcus Reid, the five-account mule ring into Northgate Trading Ltd, and Liam Walsh's seed precedent dated 2026-03-10.
3. Each world SHALL contain about 200 background customers over 2 months, including benign-but-unusual activity that rules flag.
4. THE generator SHALL write a label for every transaction with `decision`, `risk_score`, `ambiguous`, `pattern`, `expect_override` and `month`.
5. WHEN a mule forward happens before the ring is confirmable, THE label SHALL be `ambiguous: true, decision: escalate`.
6. Worlds 1-4 SHALL be the dev split and worlds 5-6 the test split. World 0 SHALL NOT be used in the eval.

## R3. Rules tier

**User story:** As an AML analyst, I want obvious non-cases cleared without an LLM, so that I only see cases worth investigating.

1. THE rule scorer SHALL be deterministic and score each transaction 0-100 with plain-English reasons, using only the customer's history up to that transaction's timestamp.
2. WHEN the rule score is below `rules_clear_below` (default 30), THE system SHALL auto-clear the transaction with `decided_by="rules"` and make no LLM call.
3. WHEN run in baseline mode, THE scorer SHALL escalate at `rules_escalate_at` (default 30) or above and clear otherwise, with no LLM.
4. On world 0 and the dev worlds, at least 90% (target 95%) of transactions SHALL end in the rules tier.

## R4. Multi-agent investigation

**User story:** As an AML analyst, I want grey-zone cases investigated by specialists, so that verdicts come with evidence.

1. THE supervisor SHALL be built with `create_deep_agent` and SHALL have four sub-agents: `pattern-analyst`, `kyc-precedent`, `fund-flow` and `sar-writer`.
2. THE supervisor SHALL call `kyc-precedent` for every investigated transaction, and only the other specialists the rule reasons call for.
3. Each sub-agent except `sar-writer` SHALL return its structured findings model (`PatternFindings`, `KycFindings`, `NetworkFindings`). `sar-writer` SHALL return a `SarDraft`.
4. THE supervisor SHALL call `record_decision` exactly once per investigated transaction.
5. WHEN the final decision is `escalate`, THE supervisor SHALL obtain a `SarDraft` from `sar-writer` using only the gathered evidence.
6. No tool SHALL accept `user_id` from the model. Customer scope SHALL come from the run context only.

## R5. Human in the loop

**User story:** As an AML analyst, I want to be asked only when the agents are unsure, and for my answer to be remembered.

1. WHEN confidence after checks is below `confidence_threshold` (default 0.7), THE system SHALL pause with `interrupt()` inside `record_decision`, called only by the supervisor.
2. WHEN a hard red flag is present and the agent's decision is `clear`, THE system SHALL pause for human review.
3. THE interrupt payload SHALL include the evidence, the reasons for review and any precedents found.
4. WHEN resumed with `{"decision": "clear"|"escalate", "note": "..."}` and a non-empty note, THE system SHALL save a precedent with `expires_at = as_of + precedent_ttl_days`.

## R6. Memory and safeguards

**User story:** As the MLRO, I want memory that helps analysts but can never be used to clear a launderer.

1. THE system SHALL store precedents in `("precedents", user_id)` keyed by `counterparty_id:pattern`, and every decision (including rules-tier auto-clears) in `("decisions", user_id)`.
2. THE system SHALL treat the transaction's timestamp as "now" for expiry checks and the network graph.
3. A precedent SHALL apply only when `user_id`, `counterparty_id` and `pattern` all match and `as_of < expires_at`.
4. WHEN a hard red flag (sanctions hit, PEP, confirmed ring membership) is present, THE system SHALL move any cited precedent to `precedents_overridden` with a reason.
5. WHEN a valid, in-scope precedent exists and there are no hard flags, THE grey-zone check SHALL be satisfied (the one stated relaxation).
6. THE safeguards in 6.3-6.5 SHALL be enforced in code in `record_decision`, never only by a prompt.
7. THE system SHALL load `seed_precedents.jsonl` into the store at the start of each notebook, eval and scenario-check run.

## R7. Cross-customer network analysis

**User story:** As an AML analyst, I want mule rings found across accounts, which per-customer rules can't see.

1. THE `trace_fund_flows` tool SHALL be held only by `fund-flow`, and its starting account SHALL come from the run context.
2. THE tool SHALL return graph summaries (account IDs, amounts, timings) and never customer profiles.
3. THE tool SHALL write every call to `("network_audit",)`.
4. THE graph SHALL include only transactions before `as_of`.
5. WHEN the fifth feeder forwards to Northgate Trading Ltd in world 0, `ring_confirmed` SHALL become true for that account, and not before.

## R8. Stream processing

1. THE runner SHALL process all customers in one global timestamp order, with one thread per customer.
2. THE runner SHALL resolve interrupts from `reviewer_answers` in evals, and through an `on_interrupt` callback in the notebook.
3. THE runner SHALL report LLM calls, tokens and the share of transactions that reached an LLM.

## R9. Evaluation

**User story:** As a judge, I want real numbers against a fair baseline.

1. THE eval SHALL keep the starter's `decision_accuracy_eval`, `score_alignment_eval` and `review_routing_eval` unchanged.
2. THE eval SHALL add `false_positive_rate`, `recall_planted`, `reviews_month1`, `reviews_month2`, `override_correctness`, `llm_share` and `cost_per_1k`, and the `sar_quality` LLM-as-judge.
3. THE experiment runner SHALL run `rules-only` and `sentinel` on the test split of dataset `<LANGSMITH_PROJECT>-sentinel`, with one example per world.
4. THE runner SHALL save the averaged results to `results/eval_summary.json`. THE notebook SHALL only load this file.
5. Rules SHALL be tuned on the dev split only.

## R10. Demo notebook

1. THE notebook SHALL follow the DEMO_SCRIPT run of show: header disclaimer, day-1 stream counter, structuring, human review, Fast-forward, mule ring with network graph, eval results, SAR draft.
2. THE notebook SHALL run top to bottom on a fresh kernel, both live and with `REPLAY=1`.
3. WHEN `REPLAY=1`, THE notebook SHALL use LLM responses cached from a rehearsal run.
4. THE header and every SAR draft SHALL carry: "Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only."

## R11. Observability

1. Every agent run SHALL be traced to LangSmith project `fsi-hackathon-<ATTENDEE_NAME>`.
2. THE model SHALL come from `MODEL_NAME` in `.env` (`openai:gpt-6-sol`), never hardcoded.
