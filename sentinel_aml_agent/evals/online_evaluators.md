# LangSmith online evaluator and automation rule (task 5.6, PLAN.md 7.1, R12.1-R12.2)

Set up once in the LangSmith UI, following "Set up LLM-as-a-judge online evaluators" in the LangSmith docs.
Recorded here so anyone can recreate it exactly.

## 1. Online evaluator: `sar_complete` on every SAR draft

| Setting | Value |
|---|---|
| Where | LangSmith → **Tracing** → project `fsi-hackathon-<ATTENDEE_NAME>` (from `LANGSMITH_PROJECT` in `.env`) → **Online Evaluators** → **+ Evaluator** → **LLM-as-a-Judge Evaluator** → Create from scratch |
| Name | `sar-completeness` |
| Trigger on | **Runs** |
| Filter | `eq(name, "sar-writer")`. Verified in traces: the sub-agent's run is a `chain` run named `sar-writer`, the child of the supervisor's `task` call |
| Sampling rate | `1` (100%) |
| Apply to past runs | On, from 2026-11-25 (backfills the SARs already written by `check_scenarios.py`) |
| Model | The workspace's gateway model, `gpt-6-sol` if offered (same family as the agent: a known bias, which is why groundedness is checked in code, not by this judge) |
| Prompt | The text of `evals/sar_rubric.md`, followed by `SAR draft:\n{{output}}` |
| Variable mapping | `output` → the run's **outputs** (the `structured_response` SarDraft) |
| Feedback key | `sar_complete`, type continuous, 0 to 1, plus a comment |

**Check:** run `uv run python scripts/run_case.py TX-000167` (Daniel escalates and a SAR is written), wait about a
minute, then open that trace's `sar-writer` run: it should carry `sar_complete` feedback.

## 2. Automation rule: weak SARs go to the analyst queue (optional, cut list item 2)

| Setting | Value |
|---|---|
| Where | Same project → **Automations** (or **+ Rule**) |
| Filter | `and(eq(name, "sar-writer"), eq(feedback_key, "sar_complete"), lt(feedback_score, 0.7))` |
| Action | **Add to annotation queue** → `sentinel-analyst-review-<ATTENDEE>` (created by `scripts/annotation_queue.py`) |
| Sampling | `1` |

## Status
- [ ] Online evaluator created (fill in date and who): ____
- [ ] Checked on Daniel's SAR, score: ____
- [ ] Automation rule created: ____
