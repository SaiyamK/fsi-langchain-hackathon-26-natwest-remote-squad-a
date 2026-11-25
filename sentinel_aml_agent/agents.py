"""Sentinel: multi-agent AML transaction monitoring. SUBMISSION FILE.

Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only.

How a transaction is handled
1. Rules (tier 1, `rules/scorer.py`): every transaction is scored deterministically, including a cross-account
   ring check. Low scores are auto-cleared with no LLM call (about 95-97% of traffic). The same tier, alone, is
   the rules-only baseline we evaluate against.
2. Agents (tier 2, this file): the triage supervisor, a Deep Agent, plans the investigation and delegates in
   parallel to four specialists (`sub_agents/`):
   - pattern-analyst: structuring, anomalous credits and round trips in one customer's history;
   - kyc-precedent: KYC profile, sanctions/PEP screening, and analysts' past decisions (precedents);
   - fund-flow: the one privileged cross-customer tool, audited, for money-mule rings;
   - sar-writer: a structured Suspicious Activity Report draft, from gathered evidence only.
3. Human (tier 3, `tools/decisions.py`): `record_decision`, held only by the supervisor, applies the safeguards
   in code (hard flags beat precedents; precedents must match scope and be unexpired) and calls `interrupt()`
   when the agents aren't confident. The analyst's note becomes a precedent with an expiry date.

Memory: a checkpointer thread per customer (short-term) and the LangGraph store (long-term: precedents, the
decision audit trail, SAR drafts and the network-tool audit log). Every run is traced to LangSmith.

Run it:  `uv run langgraph dev` (graph "sentinel"), or `modules/01_sentinel_demo.ipynb`.
"""

from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, create_deep_agent, register_harness_profile
from langchain.agents.middleware import ModelCallLimitMiddleware, TodoListMiddleware, ToolCallLimitMiddleware
from langchain.chat_models import init_chat_model

from sub_agents import SUBAGENTS
from tools.customers import get_customer_profile
from tools.decisions import record_decision
from tools.transactions import get_transaction
from utils.models import PROJECT_ROOT, model
from utils.state import MyAgentContext

INSTRUCTIONS = (PROJECT_ROOT / "instructions.md").read_text(encoding="utf-8")

# Keep the supervisor focused on our four specialists: hide the harness's built-in filesystem tools and its
# general-purpose sub-agent for this model (DEC-009). Planning (write_todos) is added explicitly below.
register_harness_profile(
    model,
    HarnessProfile(
        excluded_tools=frozenset({"ls", "read_file", "write_file", "edit_file", "delete", "glob", "grep", "execute"}),
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
)


def build_agent(**kwargs):
    """Build the Sentinel supervisor. Pass `checkpointer` and `store` to give it memory."""
    return create_deep_agent(
        model=init_chat_model(model),
        tools=[get_transaction, get_customer_profile, record_decision],
        system_prompt=INSTRUCTIONS,
        subagents=SUBAGENTS,
        context_schema=MyAgentContext,
        middleware=[
            TodoListMiddleware(),
            ModelCallLimitMiddleware(run_limit=20, exit_behavior="end"),   # cost cap per investigation
            ToolCallLimitMiddleware(tool_name="task", run_limit=6),        # at most 6 delegations per investigation
        ],
        name="sentinel-supervisor",
        **kwargs,
    )


agent = build_agent()
