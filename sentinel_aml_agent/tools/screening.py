"""Screen a name against the watchlists in the bank's database (`data/sanctions_list.jsonl` and `data/pep_list.jsonl`).

Copied from the organiser starter `01_kyc_agent/tools/screening.py` (the starter folders are removed before
submission, so Sentinel keeps its own copy). Plain Python, no LLM. In a real bank this would call a screening provider.
"""

from difflib import SequenceMatcher

from utils import db

MATCH_THRESHOLD = 0.85


def name_similarity(a: str, b: str) -> float:
    """Score how alike two names are, from 0 (nothing in common) to 1 (identical)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def check_sanctions(name: str, date_of_birth: str | None = None) -> list[dict]:
    """Return the sanctions list entries whose name closely matches."""
    hits = []
    for entry in db.table("sanctions_list"):
        score = name_similarity(name, entry["name"])
        if score >= MATCH_THRESHOLD:
            hits.append(
                {
                    "list": "sanctions",
                    "matched_name": entry["name"],
                    "score": round(score, 2),
                    "date_of_birth_matches": date_of_birth is not None and entry["date_of_birth"] == date_of_birth,
                    "details": entry["program"],
                }
            )
    return hits


def check_pep(name: str) -> list[dict]:
    """Return the PEP list entries whose name closely matches."""
    hits = []
    for entry in db.table("pep_list"):
        score = name_similarity(name, entry["name"])
        if score >= MATCH_THRESHOLD:
            hits.append(
                {
                    "list": "pep",
                    "matched_name": entry["name"],
                    "score": round(score, 2),
                    "details": f"{entry['position']}, {entry['country']}",
                }
            )
    return hits


#
# Tool wrapper for the KYC & precedent agent (Sentinel addition)
#
from langchain.tools import ToolRuntime, tool  # noqa: E402

from utils.state import MyAgentContext  # noqa: E402


def screen_profile(profile: dict) -> list[dict]:
    """Sanctions and PEP hits for a customer profile, including the profile's own PEP flag."""
    hits = check_sanctions(profile["name"], profile.get("date_of_birth")) + check_pep(profile["name"])
    if profile.get("pep") and not any(h["list"] == "pep" for h in hits):
        hits.append({"list": "pep", "matched_name": profile["name"], "score": 1.0, "details": "PEP flag on KYC profile"})
    return hits


@tool(parse_docstring=True)
def screen_customer(runtime: ToolRuntime[MyAgentContext]) -> dict:
    """Screen the customer this run is about against the sanctions and PEP lists. No arguments needed."""
    profile = db.get("customer_profiles", user_id=runtime.context.user_id)
    if profile is None:
        return {"hits": [], "note": "No profile found for this customer."}
    return {"screened_name": profile["name"], "hits": screen_profile(profile)}
