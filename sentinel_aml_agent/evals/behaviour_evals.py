"""Scenario evaluators: memory safeguards, agent behaviour, SAR quality, privacy and scope
(DEC-010 categories 4, 5, 6 and 8). Code only, pass/fail style scores. Any failure here is a bug.

Inputs: `outputs` = {"decisions", "investigations", "network_audit"} from the target; `reference_outputs["labels"]`.
"""

from evals.sar_checks import sar_grounded
from utils import db


def _by_id(rows):
    return {r["transaction_id"]: r for r in rows}


def _share(flags: list[bool], key: str, what: str) -> dict:
    return {"key": key, "score": (sum(flags) / len(flags)) if flags else None,
            "comment": f"{sum(flags)}/{len(flags)} {what}" if flags else f"no {what} cases in this example"}


#
# 4. Memory safeguards
#
def memory_safeguards(outputs: dict, reference_outputs: dict) -> dict:
    d = _by_id(outputs["decisions"])
    labels = reference_outputs["labels"]
    use, no_wrong, override = [], [], []
    for tid, l in labels.items():
        x = d.get(tid)
        if x is None:
            continue
        relied = bool(x.get("precedents_relied_on"))
        if l["expect_precedent_use"]:
            use.append(relied)
        elif x["decided_by"] != "rules":
            no_wrong.append(not relied)
        if l["expect_override"]:
            override.append(bool(x.get("precedents_overridden")) and x["final_decision"] == "escalate")
    flag_clear = [x["decided_by"] == "human" for x in d.values() if x.get("hard_flags") and x.get("agent_decision") == "clear"]
    return {"results": [
        _share(use, "precedent_used_when_valid", "valid precedents relied on"),
        _share(no_wrong, "no_reliance_on_invalid_precedent", "investigations without wrongful reliance"),
        _share(override, "hard_flag_overrides_precedent", "precedents overridden by hard flags"),
        _share(flag_clear, "hard_flag_clear_goes_to_human", "hard-flag 'clear' verdicts sent to a human"),
    ]}


#
# 5. Agent behaviour (trajectory)
#
def trajectory(outputs: dict) -> dict:
    kyc, once, matched = [], [], []
    for inv in outputs["investigations"]:
        calls = inv["tool_calls"]
        subs = [c["subagent"] for c in calls if c["subagent"]]
        kyc.append("kyc-precedent" in subs)
        once.append(sum(c["name"] == "record_decision" for c in calls) == 1)
        reasons = " ".join(inv.get("rule_reasons", [])).lower()
        need_flow = any(w in reasons for w in ("ring", "sends on", "internal senders"))
        need_pattern = any(w in reasons for w in ("cash", "credit", "payment", "counterparty", "back from"))
        matched.append((not need_flow or "fund-flow" in subs) and (not need_pattern or "pattern-analyst" in subs
                                                                    or need_flow))
    return {"results": [
        _share(kyc, "kyc_called_every_time", "investigations that called kyc-precedent"),
        _share(once, "record_decision_once", "investigations with exactly one record_decision"),
        _share(matched, "specialists_match_rule_reasons", "investigations calling the specialists the reasons call for"),
    ]}


#
# 6. SAR quality (code part; completeness is the LLM judge / online evaluator)
#
def sar_quality(outputs: dict) -> dict:
    scores, missing = [], 0
    for inv in outputs["investigations"]:
        if inv.get("final_decision") != "escalate":
            continue
        if not inv.get("sar"):
            missing += 1
            scores.append(0.0)
            continue
        with db.use_world(outputs.get("world", 0)):
            s, _ = sar_grounded(inv["sar"], inv["as_of"])
        scores.append(s)
    return {"results": [
        {"key": "sar_grounded", "score": sum(scores) / len(scores) if scores else None,
         "comment": f"{len(scores)} escalations, {missing} without a SAR"},
        {"key": "sar_written_for_escalations", "score": (len(scores) - missing) / len(scores) if scores else None},
    ]}


#
# 8. Privacy and scope
#
def network_scope(outputs: dict) -> dict:
    audit = outputs.get("network_audit", [])
    flow_calls = sum(c["subagent"] == "fund-flow" for inv in outputs["investigations"] for c in inv["tool_calls"])
    return {"results": [
        {"key": "network_calls_audited", "score": 1.0 if len(audit) >= flow_calls else len(audit) / max(flow_calls, 1),
         "comment": f"{len(audit)} audit records for {flow_calls} fund-flow delegations"},
        {"key": "network_returns_account_ids_only",
         "score": 1.0 if all(all(a.startswith("ACC-") or a.startswith("EXT-") for a in r["accounts_returned"])
                             for r in audit) else 0.0},
    ]}


BEHAVIOUR_EVALUATORS = [memory_safeguards, trajectory, sar_quality, network_scope]
