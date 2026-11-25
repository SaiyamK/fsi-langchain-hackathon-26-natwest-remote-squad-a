# Fallback screenshots

The flight deck asks for screenshots of a successful trace and of the results, saved by 15:00, in case the live demo
fails. Save them here as PNG files with these names:

| File | What to capture |
|---|---|
| `01_trace_daniel.png` | LangSmith trace of Daniel's investigation: the supervisor's plan, parallel sub-agents, `record_decision` |
| `02_trace_sophie_interrupt.png` | Sophie's paused investigation and the resume with the analyst's note |
| `03_mule_graph.png` | The notebook's fan-in network graph |
| `04_experiment_compare.png` | LangSmith comparison of `rules-only-test-*` vs `sentinel-test-*` on the benchmark dataset |
| `05_eval_coverage.png` | The notebook's coverage table (section 6) |
| `06_annotation_queue.png` | The analyst review queue in LangSmith |
| `07_sar_draft.png` | Daniel's SAR draft with the disclaimer |

Synthetic data only. Check that no API key, `.env` content or real data is visible before committing.
