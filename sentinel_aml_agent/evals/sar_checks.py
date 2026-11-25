"""Code checks on SAR drafts (DEC-010 category 6). No LLM: groundedness is checked against the database.

`sar_grounded`: every transaction ID cited in the SAR is a real transaction of that customer (or of a
counterparty account in the same world, for network cases) visible at the time of the investigation, and the
disclaimer is exactly the required text. The LLM judge (`sar_rubric.md`) only scores completeness.
"""

import re

from utils import db
from utils.schemas import DISCLAIMER

TX_ID = re.compile(r"TX-\d{5,6}")


def sar_grounded(sar: dict, as_of: str) -> tuple[float, list[str]]:
    """Return (score 0-1, problems). Score 1 means every cited ID is real and visible, and the disclaimer matches."""
    problems = []
    text = " ".join(str(sar.get(k, "")) for k in ("timeline", "evidence", "narrative", "precedents_cited_or_overridden"))
    cited = sorted(set(TX_ID.findall(text)))
    known = {t["transaction_id"]: t for t in db.table("transactions")}
    for tid in cited:
        t = known.get(tid)
        if t is None:
            problems.append(f"{tid} does not exist")
        elif as_of and t["timestamp"] > as_of:
            problems.append(f"{tid} is after the investigation time")
    if sar.get("disclaimer") != DISCLAIMER:
        problems.append("disclaimer missing or changed")
    if not cited:
        problems.append("no transaction IDs cited")
    checks = len(cited) + 2
    return round(max(0.0, 1 - len(problems) / checks), 3), problems
