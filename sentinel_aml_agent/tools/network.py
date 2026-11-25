"""The ONE privileged cross-customer tool (R7). Only the fund-flow sub-agent is given it.

- The starting account comes from the run context, not from the model, so the model can't point it at an
  arbitrary customer.
- It returns graph summaries (account IDs, amounts, timings), never customer profiles.
- Every call is written to the ("network_audit",) namespace in the store.
"""

import uuid

from langchain.tools import ToolRuntime, tool

from utils import db
from utils.graph import fan_in_summary
from utils.state import MyAgentContext


@tool(parse_docstring=True)
def trace_fund_flows(runtime: ToolRuntime[MyAgentContext]) -> dict:
    """Trace where this customer's money comes from and goes to across our accounts, up to now: pass-through
    forwards, the account they converge on, and whether a fan-in mule ring is confirmed. No arguments needed.
    """
    ctx = runtime.context
    profile = db.get("customer_profiles", user_id=ctx.user_id)
    if profile is None:
        return {"error": "No account found for this customer."}
    summary = fan_in_summary(profile["account_id"], ctx.as_of)
    if runtime.store is not None:
        runtime.store.put(("network_audit",), str(uuid.uuid4()), {
            "as_of": ctx.as_of, "seed_account": profile["account_id"], "caller": "fund-flow",
            "accounts_returned": sorted(set(summary["feeder_accounts"]) | ({summary["collector_account"]} - {None})),
            "trace_run_id": ctx.trace_run_id,
        })
    return summary
