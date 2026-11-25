# SAR completeness rubric

Shared by the offline judge (`evals/sar_judge.py`) and the LangSmith online evaluator (`evals/online_evaluators.md`),
so `sar_complete` means the same thing in both places (PLAN.md 7.1). Groundedness (no invented facts) is checked in
code by `evals/sar_checks.py`, not here.

You are reviewing a draft Suspicious Activity Report (SAR) written for a bank's AML analyst. All data is synthetic.
Score how complete and usable the draft is. Don't judge whether the customer is guilty.

Give one point for each item that is clearly present:
1. **Subject**: the customer's name and ID.
2. **Typology**: the suspected pattern is named (for example structuring, mule fan-in, round-tripping).
3. **Timeline**: dated events in order, each tied to a transaction ID.
4. **Evidence**: specific amounts and transaction IDs that support the suspicion.
5. **Reasoning**: the narrative explains why the activity is suspicious compared with what's expected for this customer.
6. **Alternatives**: any legitimate explanation that was considered is mentioned, and why it doesn't settle the case.
7. **Precedents**: past analyst decisions are listed with what happened to them (relied on, expired or overridden), or the draft says there were none.
8. **Next step**: what the analyst should check or do next.
9. **Disclaimer**: it says it's a draft for analyst review, not legal, compliance or regulatory advice.

Return `sar_complete` = points / 9, rounded to two decimals, and a one-sentence comment naming any missing items.
