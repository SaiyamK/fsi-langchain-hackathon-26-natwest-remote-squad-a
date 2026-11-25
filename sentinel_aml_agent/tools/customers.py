"""The customer's KYC profile (`data/customer_profiles.jsonl`). Analyst notes live in precedents, not here."""

from langchain.tools import ToolRuntime, tool

from utils import db
from utils.state import MyAgentContext


@tool(parse_docstring=True)
def get_customer_profile(runtime: ToolRuntime[MyAgentContext]) -> dict | str:
    """Look up the KYC profile of the customer this run is about: occupation, risk rating, PEP flag, expected
    monthly credits and cash, and when the account was opened. No arguments needed.
    """
    profile = db.get("customer_profiles", user_id=runtime.context.user_id)
    return profile or "No profile found for this customer."
