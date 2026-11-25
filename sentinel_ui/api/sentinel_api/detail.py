"""Case and account detail for the Case / Network View (FR-4 to FR-10)."""

from datetime import timedelta

from tools.decisions import hard_flags_for  # sentinel_aml_agent
from tools.screening import screen_profile

from sentinel_api import cases as C
from sentinel_api.models import AccountDetail, CaseDetail, MemoryCard, Transfer
from sentinel_api.session import Session, _scope
from sentinel_api.world import ts


def case_detail(session: Session, case_id: str) -> CaseDetail | None:
    with session.lock:
        summary = session.cases.get(case_id)
        if summary is None:
            return None
        as_of = session.clock() or ""
        records = [session.records[t] | {"transaction_id": t} for t in summary.transaction_ids if t in session.records]
        activity = [session.activity[t] for t in summary.transaction_ids if t in session.activity]
        alerts = [session.alerts[t] for t in summary.transaction_ids if t in session.alerts]
        run_ids = {r.get("trace_run_id") for r in records if r.get("trace_run_id")}
        flagged_at = min((session.rows[t].timestamp for t in summary.flagged_transaction_ids), default=None)
        audit = session.audit_for(case_id)

    world = session.world
    g = session.case_graph(case_id)
    flags = C.red_flags(world, g, summary.pattern, as_of)
    hard = {}
    for node in g.nodes:
        profile = world.profiles_by_account.get(node)
        if profile:
            found = hard_flags_for(profile, as_of)
            if found:
                hard[node] = found
    bal = C.balances(world, g, as_of)
    network_audit = []
    for item in session.store.search(("network_audit",), limit=1000):
        if item.value.get("trace_run_id") in run_ids:
            network_audit.append(dict(item.value))
    return CaseDetail(
        summary=summary, finding=C.finding(world, g, summary.pattern), as_of=as_of,
        nodes=C.nodes_of(world, g, hard, flags), edges=C.edges_of(g),
        metrics=C.metrics(world, g, summary.pattern), red_flags=flags, thresholds=C.THRESHOLDS,
        timeline=C.timeline(g), moments=C.moments(g, bal, flagged_at, world), balances=bal,
        decisions=records, activity=activity, alerts=alerts, audit=audit, network_audit=network_audit,
        sar_ids=[r["sar_id"] for r in records if r.get("sar_id")],
    )


def account_detail(session: Session, account_id: str, days: int = 30) -> AccountDetail:
    world = session.world
    as_of = session.clock() or (world.transactions[-1]["timestamp"] if world.transactions else "")
    start = (ts(as_of) - timedelta(days=days)).isoformat(timespec="minutes") if as_of else ""
    profile = world.profiles_by_account.get(account_id)
    if profile is None:
        # External counterparty: only what our customers' transactions show
        txs = [t for t in world.transactions if t.get("counterparty_id") == account_id and start <= t["timestamp"] <= as_of]
        return AccountDetail(
            account_id=account_id, name=world.name(account_id), external=True, bank="Another bank",
            screening=[], hard_flags=[],
            money_in=sum(t["amount"] for t in txs if t["direction"] == "out"),
            money_out=sum(t["amount"] for t in txs if t["direction"] == "in"),
            counterparties=len({t["account_id"] for t in txs}), precedents=[],
            transactions=[_transfer(t) for t in txs])

    txs = world.flows(account_id, start, as_of)
    overridden = {}
    with session.lock:
        for record in session.records.values():
            for o in record.get("precedents_overridden") or []:
                overridden[o.get("key")] = o.get("reason", "")
    precedents = []
    for item in session.store.search(("precedents", profile["user_id"]), limit=200):
        p = dict(item.value)
        kind = "overridden" if item.key in overridden else "cited"
        precedents.append(MemoryCard(kind=kind, key=item.key, note=p.get("note", ""), analyst=p.get("analyst", ""),
                                     created_at=p.get("created_at"), expires_at=p.get("expires_at"),
                                     reason=overridden.get(item.key, ""), scope=_scope(p)))
    opened = profile.get("account_opened")
    return AccountDetail(
        account_id=account_id, name=profile["name"], external=False, customer_type=profile.get("customer_type"),
        occupation=profile.get("occupation"), bank="Our bank", account_opened=opened,
        account_age_days=(ts(as_of[:10]) - ts(opened)).days if opened and as_of else None,
        risk_rating=profile.get("risk_rating"), pep=profile.get("pep"),
        screening=[f"{h['list']}: {h['matched_name']} ({h['details']})" for h in screen_profile(profile)],
        hard_flags=hard_flags_for(profile, as_of) if as_of else [],
        expected_monthly_credits=profile.get("expected_monthly_credits"),
        expected_monthly_cash=profile.get("expected_monthly_cash"),
        money_in=round(sum(t["amount"] for t in txs if t["direction"] == "in"), 2),
        money_out=round(sum(t["amount"] for t in txs if t["direction"] == "out"), 2),
        counterparties=len({world.counterparty_node(t) for t in txs}),
        precedents=precedents, transactions=[_transfer(t) for t in txs])


def _transfer(t: dict) -> Transfer:
    return Transfer(transaction_id=t["transaction_id"], timestamp=t["timestamp"], amount=t["amount"],
                    currency=t["currency"], txn_type=t["txn_type"])
