# Design: Sentinel AML Agent

**The design is PLAN.md.** It holds the decisions, file layout, contracts (schemas, store namespaces, function
signatures, sub-agent outputs), component design, cut list and risks. This file doesn't repeat it.

#[[file:PLAN.md]]

This file only adds the implementation details PLAN.md leaves open. Each one is marked **proposed**. If accepted,
fold it into PLAN.md and sync USE_CASE.md and DEMO_SCRIPT.md, so PLAN.md stays the single source of truth.

## D1. Where each world's data lives (proposed)

PLAN.md has 7 worlds (0 = demo, 1-4 = dev, 5-6 = test), but 02's `utils/db.py` reads one fixed `data/` folder.

- World 0 is written to `data/*.jsonl` (what the notebook and Studio read).
- Worlds 1-6 are written to `data/worlds/world_<N>/*.jsonl`, with the same table names.
- `utils/db.py` gets one addition: a `ContextVar` holding the active data folder, defaulting to `data/`, and a context manager `db.use_world(n)`.
  The eval target function wraps each run in `with db.use_world(n):`. LangGraph copies context variables into its worker threads, so tools read the right world even with `max_concurrency=2`.
- Shared reference tables (`sanctions_list`, `pep_list`) stay in `data/` and are read from there in every world.

## D2. Eval splits (proposed)

One LangSmith dataset, `<LANGSMITH_PROJECT>-sentinel`, with 6 examples (worlds 1-6). Each example is tagged with
split `dev` or `test` via `create_examples(..., splits=[...])`. Experiments run on
`client.list_examples(dataset_name=..., splits=["test"])`. Tuning runs locally on dev and is not reported.

## D3. Notebook interrupts that aren't on stage (proposed)

The day-1 stream may pause on transactions the demo doesn't feature (for example the early mule forwards labelled
"ask a human"). The notebook's `on_interrupt` callback answers those from `reviewer_answers.jsonl`, and prints one
line each. It opens the `ipywidgets` panel only for transactions in a `LIVE_REVIEW` set (Sophie's first credit).

## D4. World 0 fixed cast (proposed IDs and dates)

| Customer | `user_id` | Key events (world 0) |
|---|---|---|
| Daniel Hughes | `CUS-0001` | 4 × £9,500 cash deposits at 3 branches, 2026-10-06 to 2026-10-08 |
| Sophie Clarke | `CUS-0002` | £18,000 from new counterparty `EXT-EMP-0002` on 2026-10-14; £19,200 from the same counterparty on 2027-08-14 (precedent valid to 2027-10-14) |
| Marcus Reid | `CUS-0003` | PEP-linked; £250,000 out 2026-11-03, £240,000 back via a different account 2026-11-20 |
| Liam Walsh, Chloe Evans, Ben Taylor, Amira Khan, Josh Patel | `CUS-0040`-`CUS-0044` | Small inbound transfers, then forwards of ≥ 90% within hours to Northgate, 2026-11-09 to 2026-11-13; the 5th forward confirms the ring |
| Northgate Trading Ltd | `CUS-0050` | New business account, opened 2026-10-25 |
| Liam's seed precedent | `CUS-0040` | Cleared 2026-03-10 ("Transfers from flatmates for rent"), expires 2027-03-10, so it's valid at the time and must be **overridden**, not ignored |

World 0's stream is October-November 2026 plus a short August 2027 slice for Fast-forward.

## D5. Commit and branch practice

- Work on `main`. Keep it runnable after every task.
- Commit after each task with a Conventional Commit message that names the task, for example `feat(rules): add rule scorer and baseline (task 2.1)`.
- Before every commit: `git status`, `git diff --staged`, and `git grep -n "lsv2_" -- .` must return nothing.
- Push at each checkpoint (A and B) and at submission. Tag the submitted commit `submission`.
