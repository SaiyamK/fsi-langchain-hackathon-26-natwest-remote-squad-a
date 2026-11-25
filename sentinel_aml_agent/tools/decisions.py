"""Record the supervisor's verdict, and ask a human when the agents shouldn't decide alone (PLAN.md 5.4).

Extended from the organiser starter's `record_decision`. Everything that keeps memory safe is plain code here,
not a prompt (R6.6):
1. Hard flags: sanctions or PEP hit, or the account is in a confirmed fan-in ring.
2. Precedents in scope for this transaction (same customer, counterparty and pattern) are found by code, whether or
   not the model cited them; cited ones that don't apply are dropped with a reason.
3. With a hard flag, every in-scope precedent is overridden, and a `clear` verdict goes to a human.
4. Grey-zone scores lower confidence, unless a valid in-scope `clear` precedent exists and there are no hard flags
   (the one stated relaxation: a human already decided this exact case).
5. Below the confidence threshold, `interrupt()` pauses for the analyst. Their note becomes a precedent.
6. Every decision is written to ("decisions", user_id).

Only the supervisor has this tool, so only the supervisor ever pauses (PLAN.md section 1).
"""

from datetime import date, timedelta
from typing import Literal

from langchain.tools import ToolRuntime, tool
from langgraph.types import interrupt

from tools.precedents import classify_precedents, precedent_key
from tools.screening import screen_profile
from utils import db
from utils.graph import ring_membership
from utils.state import MyAgentContext

PatternName = Literal["none", "structuring", "anomalous_credit", "round_tripping", "mule_fan_in"]


def hard_flags_for(profile: dict, as_of: str) -> list[str]:
    """Hard red flags that no precedent can override (R6.4)."""
    flags = []
    for hit in screen_profile(profile):
        flags.append(f"{hit['list']} match: {hit['matched_name']} ({hit['details']})")
    ring = ring_membership(profile["account_id"], as_of)
    if ring:
        role = "collector" if profile["account_id"] == ring["collector_account"] else "feeder"
        flags.append(f"confirmed fan-in ring member ({role}, collector {ring['collector_account']}, "
                     f"confirmed {ring['confirmed_at']})")
    return flags


def assess(store, ctx: MyAgentContext, transaction: dict | None, risk_score: int, confidence: float,
           decision: str, pattern: str, precedents_cited: list[str]) -> dict:
    """Apply the deterministic safeguards. Returns what to record and whether a human must decide."""
    profile = db.get("customer_profiles", user_id=ctx.user_id) or {}
    flags = hard_flags_for(profile, ctx.as_of) if profile else []
    counterparty = transaction.get("counterparty_id") if transaction else None
    # Scope = customer + counterparty + pattern. When the agents clear a case they may call the pattern "none"; if
    # they cite a precedent for this exact counterparty, scope it by that precedent's own pattern (DEC-015).
    # Counterparty and expiry are still checked here, in code.
    patterns = {pattern}
    if pattern == "none":
        patterns |= {k.split(":", 1)[1] for k in precedents_cited or [] if ":" in k
                     and k.split(":", 1)[0] == (counterparty or "*")}
    found = {"valid": [], "expired": [], "out_of_scope": []}
    for pat in sorted(patterns):
        part = classify_precedents(store, ctx.user_id, counterparty, pat, ctx.as_of)
        for bucket in ("valid", "expired"):
            found[bucket] += [p for p in part[bucket] if p["key"] not in {q["key"] for q in found[bucket]}]
    in_scope_keys = {p["key"] for p in found["valid"]}
    ring_flag = any(f.startswith("confirmed fan-in ring") for f in flags)

    dropped = []
    for key in precedents_cited or []:
        if key not in in_scope_keys:
            why = ("expired" if any(p["key"] == key for p in found["expired"])
                   else "not for this counterparty and pattern")
            dropped.append({"key": key, "reason": why})

    overridden, relied_on = [], []
    if flags:
        overridden = [{"key": p["key"], "note": p["note"], "reason": "hard red flag: " + "; ".join(flags)}
                      for p in found["valid"]]
    else:
        relied_on = [p["key"] for p in found["valid"] if p["decision"] == "clear"]

    checks = []
    low, high = ctx.grey_zone
    if low <= risk_score < high and not relied_on:
        checks.append(f"risk score {risk_score} is in the grey zone ({low}-{high - 1})")
    if flags and decision == "clear":
        checks.append("hard red flag present, so a human must decide any 'clear'")
    if pattern == "mule_fan_in" and not ring_flag:
        checks.append("mule network suspected but not confirmed by the graph check; it involves other "
                      "customers, so a human decides (DEC-015)")

    final_confidence = min(confidence, ctx.checked_confidence) if checks else confidence
    needs_human = final_confidence < ctx.confidence_threshold or (flags and decision == "clear")
    return {
        "hard_flags": flags,
        "precedents_valid": [p["key"] for p in found["valid"]],
        "precedents_expired": [p["key"] for p in found["expired"]],
        "precedents_cited": [k for k in precedents_cited or [] if k in in_scope_keys],
        "precedents_relied_on": relied_on,
        "precedents_dropped": dropped,
        "precedents_overridden": overridden,
        "confidence_checks": checks,
        "confidence": final_confidence,
        "needs_human": bool(needs_human),
        "counterparty_id": counterparty,
    }


def apply_review(store, ctx: MyAgentContext, transaction_id: str, counterparty_id: str | None, pattern: str,
                 answer: dict) -> str:
    """Validate the analyst's answer and, if they left a note, save it as a precedent (R5.4)."""
    decision = answer.get("decision")
    if decision not in ("clear", "escalate"):
        raise ValueError(f"The analyst's decision must be 'clear' or 'escalate', got {decision!r}")
    note = (answer.get("note") or "").strip()
    if note and store is not None:
        today = date.fromisoformat(ctx.as_of[:10])
        store.put(("precedents", ctx.user_id), precedent_key(counterparty_id, pattern), {
            "user_id": ctx.user_id, "counterparty_id": counterparty_id or "*", "pattern": pattern,
            "decision": decision, "note": note, "analyst": answer.get("analyst", "human"),
            "created_at": today.isoformat(), "expires_at": (today + timedelta(days=ctx.precedent_ttl_days)).isoformat(),
            "source_transaction_id": transaction_id,
        })
    return decision


@tool(parse_docstring=True)
def record_decision(
    transaction_id: str,
    risk_score: int,
    confidence: float,
    decision: Literal["clear", "escalate"],
    pattern: PatternName,
    reason: str,
    runtime: ToolRuntime[MyAgentContext],
    precedents_cited: list[str] | None = None,
) -> str:
    """Record your verdict on the transaction under investigation. Call this exactly once per transaction.

    Args:
        transaction_id: The ID of the transaction you investigated.
        risk_score: How suspicious it is, from 0 (clearly fine) to 100 (clearly laundering).
        confidence: How sure you are of your verdict, from 0 (guessing) to 1 (certain).
        decision: "clear" if no alert is needed, "escalate" to raise an alert for a SAR.
        pattern: The typology that best fits: none, structuring, anomalous_credit, round_tripping or mule_fan_in.
        reason: Two or three sentences citing the evidence (transaction IDs, amounts, findings).
        precedents_cited: Keys of analyst precedents you relied on, exactly as the KYC & precedent agent reported them.
    """
    ctx = runtime.context
    store = runtime.store
    transaction = db.get("transactions", transaction_id=transaction_id, user_id=ctx.user_id)
    result = assess(store, ctx, transaction, risk_score, confidence, decision, pattern, precedents_cited or [])

    final_decision, decided_by, note = decision, "agent", ""
    if result["needs_human"]:
        answer = interrupt({
            "transaction_id": transaction_id,
            "risk_score": risk_score,
            "model_confidence": confidence,
            "confidence": result["confidence"],
            "agent_decision": decision,
            "pattern": pattern,
            "reason": reason,
            "why_review": result["confidence_checks"] or [f"the agents' confidence ({confidence}) is below "
                                                          f"{ctx.confidence_threshold}"],
            "hard_flags": result["hard_flags"],
            "precedents": {"valid": result["precedents_valid"], "expired": result["precedents_expired"],
                           "overridden": result["precedents_overridden"]},
            "rule_score": ctx.rule_score,
            "rule_reasons": list(ctx.rule_reasons),
            "question": "Clear or escalate? Reply with {'decision': 'clear' or 'escalate', 'note': 'optional'}",
        })
        final_decision = apply_review(store, ctx, transaction_id, result["counterparty_id"], pattern, answer)
        decided_by, note = "human", (answer.get("note") or "")

    record = {
        "transaction_id": transaction_id, "risk_score": risk_score, "model_confidence": confidence,
        "confidence": result["confidence"], "confidence_checks": result["confidence_checks"],
        "agent_decision": decision, "final_decision": final_decision, "decided_by": decided_by,
        "reason": reason, "pattern": pattern, "hard_flags": result["hard_flags"],
        "precedents_cited": result["precedents_cited"], "precedents_relied_on": result["precedents_relied_on"],
        "precedents_dropped": result["precedents_dropped"], "precedents_overridden": result["precedents_overridden"],
        "analyst_note": note, "rule_score": ctx.rule_score, "rule_reasons": list(ctx.rule_reasons),
        "sar_id": None, "trace_run_id": ctx.trace_run_id or None, "as_of": ctx.as_of,
    }
    if store is not None:
        store.put(("decisions", ctx.user_id), transaction_id, record)

    summary = f"Recorded {transaction_id}: {final_decision} (decided by {decided_by})."
    if result["precedents_overridden"]:
        summary += " Precedents overridden by hard flags: " + ", ".join(p["key"] for p in result["precedents_overridden"]) + "."
    if result["precedents_dropped"]:
        summary += " Cited precedents not applied: " + ", ".join(f"{d['key']} ({d['reason']})" for d in result["precedents_dropped"]) + "."
    return summary
