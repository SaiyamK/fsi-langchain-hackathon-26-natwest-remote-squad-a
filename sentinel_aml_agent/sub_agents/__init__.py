"""Sentinel's four specialist sub-agents (PLAN.md 5.3), as `SubAgent` dicts with structured output (03 starter pattern).

Each specialist has a narrow toolset. Only `fund-flow` holds the privileged cross-customer tool, and only the
supervisor holds `record_decision`, so only the supervisor can pause for a human.
"""

from deepagents import SubAgent
from langchain.agents.structured_output import ToolStrategy

from tools.customers import get_customer_profile
from tools.network import trace_fund_flows
from tools.precedents import find_precedents
from tools.screening import screen_customer
from tools.transactions import get_recent_transactions, get_transaction
from utils import PROJECT_ROOT
from utils.schemas import KycFindings, NetworkFindings, PatternFindings, SarDraft

PROMPTS = PROJECT_ROOT / "sub_agents"


def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


pattern_analyst: SubAgent = {
    "name": "pattern-analyst",
    "description": "Looks at ONE customer's recent activity for structuring, anomalous credits and round trips, and "
                   "for legitimate explanations. Pass the transaction ID and what the rules flagged. Returns PatternFindings.",
    "system_prompt": _prompt("pattern_analyst"),
    "tools": [get_transaction, get_customer_profile, get_recent_transactions],
    "response_format": ToolStrategy(PatternFindings, handle_errors=True),  # a schema error goes back to the model to fix
}

kyc_precedent: SubAgent = {
    "name": "kyc-precedent",
    "description": "Checks the customer's KYC profile, sanctions/PEP screening and analysts' past decisions "
                   "(precedents). Call it for EVERY transaction. Pass the transaction ID, its counterparty_id and the "
                   "pattern being considered. Returns KycFindings.",
    "system_prompt": _prompt("kyc_precedent"),
    "tools": [get_customer_profile, screen_customer, find_precedents],
    "response_format": ToolStrategy(KycFindings, handle_errors=True),  # a schema error goes back to the model to fix
}

fund_flow: SubAgent = {
    "name": "fund-flow",
    "description": "Traces money across accounts to find mule networks (pass-through forwards converging on one "
                   "collector). Pass the transaction ID. Returns NetworkFindings.",
    "system_prompt": _prompt("fund_flow"),
    "tools": [get_transaction, trace_fund_flows],
    "response_format": ToolStrategy(NetworkFindings, handle_errors=True),  # a schema error goes back to the model to fix
}

sar_writer: SubAgent = {
    "name": "sar-writer",
    "description": "Drafts a Suspicious Activity Report AFTER an escalation is recorded. It has no tools, so pass ALL "
                   "the evidence: customer name and ID, transaction IDs, amounts, dates, findings, hard flags and "
                   "precedents overridden. Returns SarDraft.",
    "system_prompt": _prompt("sar_writer"),
    "tools": [],
    "response_format": ToolStrategy(SarDraft, handle_errors=True),  # a schema error goes back to the model to fix
}

SUBAGENTS = [pattern_analyst, kyc_precedent, fund_flow, sar_writer]
