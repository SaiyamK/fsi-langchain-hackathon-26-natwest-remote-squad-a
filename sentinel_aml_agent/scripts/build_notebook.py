"""Write `modules/01_sentinel_demo.ipynb` from the cells below, so the notebook's source is reviewable as code.

    uv run python scripts/build_notebook.py
    uv run jupyter nbconvert --to notebook --execute --inplace modules/01_sentinel_demo.ipynb --ExecutePreprocessor.timeout=1800
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "modules" / "01_sentinel_demo.ipynb"

CELLS = [
    ("md", """# Sentinel: multi-agent AML transaction monitoring

> **Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only.**

Sentinel helps an AML analyst in a UK bank's financial-crime team:

1. **Rules** (tier 1) score every transaction and clear most of them with no LLM call.
2. **Agents** (tier 2): a Deep Agents supervisor investigates the rest, delegating in parallel to four specialists:
   pattern analyst, KYC & precedent, fund-flow (the one audited cross-customer tool) and SAR writer.
3. **A human** (tier 3) decides when the agents aren't confident. The analyst's note becomes a **precedent** with an
   expiry date. Safeguards are code, not prompts: hard red flags beat precedents, and precedents must match scope.

Everything is traced to LangSmith and measured against a rules-only baseline. The code is in `agents.py`.
Set `REPLAY=1` before starting the kernel to replay a recorded live run (shown in the banner below)."""),
    ("code", """import sys
from pathlib import Path

sys.path.insert(0, str(Path().resolve().parent))  # the sentinel_aml_agent folder

from utils import db, replay

replay.enable()
from utils.demo import Demo, eval_tables, md, monitoring

demo = Demo()
md(f"**{replay.replay_banner()}** · {demo.seeded} old analyst precedents loaded into long-term memory.")"""),
    ("md", """## 1. Normal traffic: rules first
Every transaction from 1 to 5 October. The rules clear almost all of them in milliseconds. The few they flag
(first payments to a new supplier that look like pass-through) go to the agents, who find the legitimate
explanation, so these false alerts never reach an analyst as alerts. Where the agents aren't sure, they ask for a
review instead of guessing."""),
    ("code", """run = demo.stream("2026-10-01", "2026-10-06", "Stream: 1-5 October")"""),
    ("md", """## 2. Structuring
Daniel Hughes, a market trader, deposits four lots of £9,500 cash at three branches in 48 hours. Each one is just
under the bank's £10,000 cash-monitoring threshold, so each looks fine alone. The 3rd already raises an alert; the
4th has the most evidence."""),
    ("code", """deposits = sorted(db.query("transactions", user_id="CUS-0001", txn_type="cash_deposit"), key=lambda t: t["timestamp"])
daniel = [t["transaction_id"] for t in deposits if "2026-10-06" <= t["timestamp"] < "2026-10-09"]
run = demo.case(daniel)"""),
    ("md", """## 3. Unsure, so ask a human
Sophie Clarke receives £18,000, about five times her monthly salary, from a counterparty she's never been paid by.
It could be fraud, a bonus or a property sale. If the agents aren't confident, the graph pauses (`interrupt()`) and
the analyst panel appears. **Type a note and click Clear or Escalate.**"""),
    ("code", """sophie_1 = "TX-000254"
review = demo.start_review(sophie_1)
demo.panel(review)"""),
    ("code", """# Only needed when the notebook runs unattended (nobody clicked above): the scripted analyst answers, labelled.
demo.ensure_answered(review, sophie_1)"""),
    ("md", """## 4. Ten months later: the precedent pays off
Same employer, a similar amount, August 2027. The agents find the analyst's precedent (same customer, same
counterparty, same pattern, not expired), and nobody has to investigate it twice."""),
    ("code", """run = demo.case(["TX-001130"])"""),
    ("md", """## 5. Money-mule ring, and a safeguard override
Five low-risk accounts receive small transfers and forward almost everything to **Northgate Trading Ltd**, a new
business account, within hours. No single customer looks suspicious. The 4th forward goes to a human (the ring
isn't confirmed yet); at the 5th, the graph check confirms the ring. Then Liam Walsh receives money from his
"flatmate", which an analyst cleared months ago. **That precedent must not let him through.**"""),
    ("code", """run = demo.case(["TX-000762", "TX-000770", "TX-000779"])"""),
    ("code", """demo.network_graph("ACC-0050", "2026-11-12T16:00")"""),
    ("md", """## 6. Does it work? Evals in LangSmith
Numbers from real experiment runs, loaded from file (never run live). The baseline is the same tier 1 on its own."""),
    ("code", """eval_tables()"""),
    ("md", """## 7. After go-live: monitor and govern
An online evaluator in LangSmith judges every SAR draft as it's written, and an annotation queue puts human-decided
cases and a sample of the agents' own decisions in front of an analyst."""),
    ("code", """monitoring()"""),
    ("md", """## 8. The hand-off: a SAR draft
Built by the SAR writer from the evidence the investigation gathered, nothing else. Every transaction it cites was
checked in code against the database."""),
    ("code", """demo.sar("TX-000167")"""),
    ("code", """md(f"**Session:** {demo.totals['transactions']} transactions · {demo.totals['rules']} cleared by rules · "
   f"{len(demo.investigations)} investigations · {demo.totals['escalate']} escalated · "
   f"{demo.totals['model_calls']} model calls. {replay.replay_banner()}")"""),
]


def main():
    cells = []
    for kind, src in CELLS:
        lines = src.splitlines(keepends=True)
        cell = {"cell_type": "markdown" if kind == "md" else "code", "metadata": {}, "source": lines}
        if kind == "code":
            cell |= {"execution_count": None, "outputs": []}
        cells.append(cell)
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3 (.venv)", "language": "python",
                                                       "name": "python3"},
                                       "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(nb, indent=1))
    print(f"wrote {OUT} ({len(cells)} cells)")


if __name__ == "__main__":
    main()
