"""Cases: grouping flagged transactions, and everything the Case / Network View draws (design.md U4).

Pure and deterministic: computed from world-0 data up to `as_of`, plus the session's decision records. The ring
definition comes from `utils.graph` (the agents' own), so the UI and the agents never disagree about a ring.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from statistics import median

from rules.scorer import (  # sentinel_aml_agent: same thresholds the rules tier uses
    FAN_IN_SENDERS,
    FAN_IN_WINDOW,
    LARGE_MULTIPLE,
    NEAR_THRESHOLD_LOW,
    CASH_THRESHOLD,
    NEW_ACCOUNT_DAYS,
    PASS_THROUGH_RATIO,
    PASS_THROUGH_WINDOW,
)
from utils.graph import confirmed_rings

from sentinel_api.models import (
    BalancePoint,
    GraphEdge,
    GraphNode,
    Metric,
    Moment,
    RedFlag,
    ShapeNode,
    TimelineItem,
    Transfer,
)
from sentinel_api.world import World, is_flow, ts

SINGLE_WINDOW = timedelta(hours=72)
FAN_OUT_MIN_RECIPIENTS = 5

PATTERN_LABELS = {
    "mule_fan_in": "Mule ring",
    "structuring": "Structuring",
    "anomalous_credit": "Anomalous credit",
    "round_tripping": "Round-tripping",
    "fan_out": "Fan-out",
    "fan_in": "Fan-in",
    "none": "Unclassified",
}

THRESHOLDS = {
    "Near-threshold band": f"£{NEAR_THRESHOLD_LOW:,}–£{CASH_THRESHOLD - 1:,}",
    "Pass-through": f"≥ {PASS_THROUGH_RATIO:.0%} passed on within {int(PASS_THROUGH_WINDOW.total_seconds() // 3600)} h",
    "Fan-in": f"≥ {FAN_IN_SENDERS} distinct senders within {int(FAN_IN_WINDOW.total_seconds() // 3600)} h",
    "New account": f"opened < {NEW_ACCOUNT_DAYS} days before",
    "Large movement": f"≥ {LARGE_MULTIPLE}× expected monthly credits",
}


def money(amount: float) -> str:
    return f"£{amount:,.0f}" if amount >= 100 else f"£{amount:,.2f}"


def hours_between(a: str, b: str) -> float:
    return abs((ts(b) - ts(a)).total_seconds()) / 3600


#
# Grouping
#
def ring_index(as_of: str | None) -> dict[str, str]:
    """{account_id: collector_account} for every account in a ring confirmed by `as_of`."""
    if not as_of:
        return {}
    index = {}
    for collector, ring in confirmed_rings(as_of).items():
        index[collector] = collector
        for feeder in ring["feeder_accounts"]:
            index[feeder] = collector
    return index


def case_id_for(tx: dict, pattern: str | None, rings: dict[str, str]) -> str:
    """Network case if the account is in a confirmed ring (as of the session clock), else one case per customer and
    pattern. Earlier forwards join the ring's case once the ring is confirmed."""
    if tx["account_id"] in rings:
        return f"CASE-RING-{rings[tx['account_id']]}"
    return f"CASE-{tx['user_id']}-{pattern or 'none'}"


#
# Graph
#
@dataclass
class CaseGraph:
    nodes: dict[str, str] = field(default_factory=dict)          # id -> role
    transfers: list[tuple[str, str, dict]] = field(default_factory=list)  # (source, target, tx)
    layout: str = "fan_in"
    hub: str | None = None

    def add(self, source: str, target: str, tx: dict, roles: tuple[str, str]):
        if any(t["transaction_id"] == tx["transaction_id"] for _, _, t in self.transfers):
            return
        self.transfers.append((source, target, tx))
        for node, role in zip((source, target), roles):
            self.nodes.setdefault(node, role)

    def sorted_transfers(self) -> list[tuple[str, str, dict]]:
        return sorted(self.transfers, key=lambda x: (x[2]["timestamp"], x[2]["transaction_id"]))


def ring_graph(world: World, collector: str, as_of: str) -> CaseGraph:
    """Sources → mules → hub → cash-out, from the ring the agents' network check confirmed."""
    ring = confirmed_rings(as_of).get(collector)
    g = CaseGraph(layout="chain", hub=collector)
    if not ring:
        return g
    g.nodes[collector] = "hub"
    for f in ring["forwards"]:
        g.nodes[f["from"]] = "mule"
    for f in ring["forwards"]:
        start = (ts(f["timestamp"]) - PASS_THROUGH_WINDOW).isoformat(timespec="minutes")
        for t in world.flows(f["from"], start, f["timestamp"]):
            if t["direction"] == "in" and t["txn_type"] != "internal_transfer":
                g.add(world.counterparty_node(t), f["from"], t, ("source", "mule"))
        out_leg = world.tx(f["transaction_id"])
        if out_leg:
            g.add(f["from"], collector, out_leg, ("mule", "hub"))
    first = min(f["timestamp"] for f in ring["forwards"])
    for t in world.flows(collector, first, as_of):
        if t["direction"] == "out" and t["txn_type"] != "internal_transfer":
            g.add(collector, world.counterparty_node(t), t, ("hub", "sink"))
    return g


def single_graph(world: World, account_id: str, case_txs: list[dict]) -> CaseGraph:
    """One customer and its counterparties in the 72 hours up to each flagged transaction."""
    g = CaseGraph(hub=account_id)
    g.nodes[account_id] = "subject"
    for ct in case_txs:
        start = (ts(ct["timestamp"]) - SINGLE_WINDOW).isoformat(timespec="minutes")
        for t in world.flows(account_id, start, ct["timestamp"]):
            other = world.counterparty_node(t)
            if t["direction"] == "in":
                g.add(other, account_id, t, ("source", "subject"))
            else:
                g.add(account_id, other, t, ("subject", "sink"))
    outs = {target for source, target, _ in g.transfers if source == account_id}
    ins = {source for source, target, _ in g.transfers if target == account_id}
    g.layout = "fan_out" if len(outs) >= FAN_OUT_MIN_RECIPIENTS and len(outs) > len(ins) else "fan_in"
    return g


def edges_of(g: CaseGraph) -> list[GraphEdge]:
    grouped: dict[tuple[str, str], list[dict]] = {}
    for source, target, t in g.sorted_transfers():
        grouped.setdefault((source, target), []).append(t)
    return [
        GraphEdge(id=f"{s}->{d}", source=s, target=d, amount=round(sum(t["amount"] for t in txs), 2), count=len(txs),
                  transfers=[Transfer(transaction_id=t["transaction_id"], timestamp=t["timestamp"], amount=t["amount"],
                                      currency=t["currency"], txn_type=t["txn_type"]) for t in txs])
        for (s, d), txs in grouped.items()
    ]


def shape(g: CaseGraph) -> tuple[list[ShapeNode], list[tuple[str, str]]]:
    pairs = sorted({(s, d) for s, d, _ in g.transfers})
    return [ShapeNode(id=n, role=r) for n, r in g.nodes.items()], pairs


#
# Balances, timeline, moments
#
def balances(world: World, g: CaseGraph, as_of: str) -> dict[str, list[BalancePoint]]:
    """Net flow since the case window began, for our own accounts on the graph (there's no balance column)."""
    if not g.transfers:
        return {}
    start = (ts(g.sorted_transfers()[0][2]["timestamp"]) - PASS_THROUGH_WINDOW).isoformat(timespec="minutes")
    out = {}
    for node, role in g.nodes.items():
        if not world.is_ours(node) or role not in ("mule", "hub", "subject"):
            continue
        running, points = 0.0, [BalancePoint(timestamp=start, balance=0.0)]
        for t in world.flows(node, start, as_of):
            running += t["amount"] if t["direction"] == "in" else -t["amount"]
            points.append(BalancePoint(timestamp=t["timestamp"], balance=round(running, 2)))
        out[node] = points
    return out


def timeline(g: CaseGraph) -> list[TimelineItem]:
    return [TimelineItem(transaction_id=t["transaction_id"], timestamp=t["timestamp"], source=s, target=d,
                         amount=t["amount"], edge_id=f"{s}->{d}") for s, d, t in g.sorted_transfers()]


def moments(g: CaseGraph, bal: dict[str, list[BalancePoint]], flagged_at: str | None, world: World) -> list[Moment]:
    items = g.sorted_transfers()
    out: list[Moment] = []
    if items:
        first = items[0][2]
        out.append(Moment(timestamp=first["timestamp"], kind="first_in",
                          label=f"First money in: {money(first['amount'])} to {world.name(items[0][1])}"))
    if g.hub and bal.get(g.hub):
        peak = max(bal[g.hub], key=lambda p: p.balance)
        if peak.balance > 0:
            out.append(Moment(timestamp=peak.timestamp, kind="peak",
                              label=f"{world.name(g.hub)} peaks at {money(peak.balance)} net inflow"))
    sink_moves = [(s, d, t) for s, d, t in items if g.nodes.get(d) == "sink" and g.layout == "chain"]
    if sink_moves:
        s, d, t = sink_moves[0]
        out.append(Moment(timestamp=t["timestamp"], kind="cash_out",
                          label=f"{money(t['amount'])} sent out to {world.name(d)}"))
    if flagged_at:
        out.append(Moment(timestamp=flagged_at, kind="flagged", label="Sentinel flagged the case"))
    return sorted(out, key=lambda m: m.timestamp)


#
# Metrics, red flags, finding
#
def _received_before(world: World, account: str, at: str) -> float:
    start = (ts(at) - PASS_THROUGH_WINDOW).isoformat(timespec="minutes")
    return sum(t["amount"] for t in world.flows(account, start, at)
               if t["direction"] == "in" and t["timestamp"] < at)


def _pass_through(world: World, g: CaseGraph) -> list[tuple[str, float, float]]:
    """(account, ratio passed on, hours held) for each outbound from a mule/subject worth ≥ 90% of 24h inflow."""
    out = []
    for s, d, t in g.sorted_transfers():
        if g.nodes.get(s) not in ("mule", "subject") or t["direction"] != "out":
            continue
        received = _received_before(world, s, t["timestamp"])
        if received > 0 and t["amount"] >= PASS_THROUGH_RATIO * received:
            ins = [x for x in world.flows(s, (ts(t["timestamp"]) - PASS_THROUGH_WINDOW).isoformat(timespec="minutes"),
                                          t["timestamp"]) if x["direction"] == "in"]
            held = hours_between(ins[-1]["timestamp"], t["timestamp"]) if ins else 0.0
            out.append((s, t["amount"] / received, held))
    return out


def _categories(pattern: str, layout: str) -> set[str]:
    cats = {"mule_fan_in": {"mule_ring", "fan_in"}, "structuring": {"fan_in"}, "anomalous_credit": {"fan_in"},
            "round_tripping": {"mule_ring", "fan_out"}}.get(pattern, set())
    return cats | ({"fan_out"} if layout == "fan_out" else set())


def red_flags(world: World, g: CaseGraph, pattern: str, as_of: str) -> list[RedFlag]:
    cats = _categories(pattern, g.layout)
    items = g.sorted_transfers()
    flags: list[RedFlag] = []

    def add(key, label, applies, state, evidence):
        flags.append(RedFlag(key=key, label=label, applies_to=applies, applicable=bool(cats & set(applies)),
                             state=state, evidence=evidence))

    # 1. Newly opened account with a sudden jump in volume: inflow in the case is at least 5× the account's own
    #    inflow over the 30 days before the case started
    new_accounts = []
    case_start = items[0][2]["timestamp"] if items else as_of
    for node, role in g.nodes.items():
        p = world.profiles_by_account.get(node)
        if not p or role not in ("hub", "mule", "subject"):
            continue
        age = (ts(case_start[:10]) - ts(p["account_opened"])).days  # age when the case began, not today
        received = sum(t["amount"] for s, d, t in items if d == node)
        before = (ts(case_start) - timedelta(days=30)).isoformat(timespec="minutes")
        prior = sum(t["amount"] for t in world.flows(node, before, case_start)
                    if t["direction"] == "in" and t["timestamp"] < case_start)
        if age < NEW_ACCOUNT_DAYS and received > 0 and received >= 5 * prior:
            new_accounts.append(f"{p['name']} opened {age} days before; received {money(received)} in the case "
                                f"vs {money(prior)} in the previous 30 days")
    add("new_account_volume", "Newly opened account with a sudden jump in volume", ["mule_ring", "fan_in"],
        "fired" if new_accounts else "not_fired",
        "; ".join(new_accounts) or f"No case account under {NEW_ACCOUNT_DAYS} days old with a jump in volume")

    # 2. Shared device / IP: not in the data (FR-5.4)
    add("shared_device", "Shared device ID or IP address across unrelated accounts", ["mule_ring"], "no_data",
        "Device and IP data are not in this data source")

    # 3. Pass-through
    pt = _pass_through(world, g)
    add("pass_through", "Pass-through: most incoming money leaves within hours", ["mule_ring"],
        "fired" if pt else "not_fired",
        "; ".join(f"{world.name(a)} passed on {r:.0%} after {h:.1f} h" for a, r, h in pt) or "No account passed on ≥ 90% within 24 h")

    # 4. Near-threshold transfers into the hub/subject
    near = [t for s, d, t in items if d == g.hub and NEAR_THRESHOLD_LOW <= t["amount"] < CASH_THRESHOLD]
    add("near_threshold", "Many transfers just below a reporting/monitoring threshold", ["fan_in"],
        "fired" if len(near) >= 3 else "not_fired",
        f"{len(near)} credits in the {THRESHOLDS['Near-threshold band']} band: "
        + ", ".join(t["transaction_id"] for t in near) if near else "No credits in the near-threshold band")

    # 5. Consolidation followed by a large withdrawal / wire
    hub_in = sum(t["amount"] for s, d, t in items if d == g.hub)
    hub_out = [t for s, d, t in items if s == g.hub and g.nodes.get(d) == "sink"]
    out_total = sum(t["amount"] for t in hub_out)
    fired = g.layout == "chain" and hub_in > 0 and out_total >= 0.5 * hub_in
    add("consolidation_cashout", "Consolidation followed immediately by a large withdrawal, wire or crypto purchase",
        ["fan_in"], "fired" if fired else "not_fired",
        (f"{world.name(g.hub)} received {money(hub_in)} and sent {money(out_total)} out "
         f"({', '.join(t['transaction_id'] for t in hub_out)})") if hub_out else "No cash-out from the hub")

    # 6. Large deposit followed quickly by many smaller transfers
    split = []
    for s, d, t in items:
        p = world.profiles_by_account.get(d)
        if p and t["amount"] >= LARGE_MULTIPLE * max(p["expected_monthly_credits"], 1):
            end = (ts(t["timestamp"]) + timedelta(hours=24)).isoformat(timespec="minutes")
            recipients = {world.counterparty_node(x) for x in world.flows(d, t["timestamp"], end) if x["direction"] == "out"}
            if len(recipients) >= FAN_OUT_MIN_RECIPIENTS:
                split.append(f"{money(t['amount'])} into {p['name']}, then {len(recipients)} recipients within 24 h")
    add("deposit_then_split", "A large deposit followed quickly by many smaller transfers to unrelated recipients",
        ["fan_out"], "fired" if split else "not_fired", "; ".join(split) or "No large deposit split to 5+ recipients")

    # 7. No payroll or vendor relationship explains the outgoing transfers
    outs = [(s, d, t) for s, d, t in items if g.nodes.get(s) in ("subject", "hub") and t["direction"] == "out"]
    def had_relationship(account: str, recipient: str, before: str) -> bool:
        return any(x.get("counterparty_id") == recipient and x["timestamp"] < before
                   for x in world.by_account.get(account, []))

    new_rel = [d for s, d, t in outs if not had_relationship(s, d, t["timestamp"])]
    share = len(set(new_rel)) / len({d for _, d, _ in outs}) if outs else 0.0
    add("no_relationship", "No payroll or vendor relationship explains the outgoing transfers", ["fan_out"],
        "fired" if outs and share >= 0.8 else "not_fired",
        f"{share:.0%} of recipients had no earlier relationship" if outs else "No outgoing transfers in the case")

    # 8. Several banks, currencies or countries
    countries = sorted({t.get("country") or "GB" for _, _, t in items})
    currencies = sorted({t["currency"] for _, _, t in items})
    abroad = [t for _, _, t in items if (t.get("country") or "GB") != "GB"]
    add("cross_border", "Several banks, currencies or countries crossed in a short time", ["mule_ring", "fan_out"],
        "fired" if len(countries) > 1 or len(currencies) > 1 else "not_fired",
        f"Countries {', '.join(countries)}; currencies {', '.join(currencies)}"
        + (f"; {money(sum(t['amount'] for t in abroad))} sent to {', '.join(sorted({t.get('counterparty_name') or '?' for t in abroad}))}" if abroad else ""))
    return flags


def metrics(world: World, g: CaseGraph, pattern: str) -> list[Metric]:
    items = g.sorted_transfers()
    if not items:
        return []
    span = hours_between(items[0][2]["timestamp"], items[-1][2]["timestamp"])
    if g.layout == "chain":
        mules = [n for n, r in g.nodes.items() if r == "mule"]
        senders = [n for n, r in g.nodes.items() if r == "source"]
        pt = _pass_through(world, g)
        into_hub = sum(t["amount"] for s, d, t in items if d == g.hub)
        cash_out = [t for s, d, t in items if s == g.hub and g.nodes.get(d) == "sink"]
        last_in = max((t["timestamp"] for s, d, t in items if d == g.hub), default=None)
        to_cash = hours_between(last_in, cash_out[0]["timestamp"]) if cash_out and last_in else None
        countries = {t.get("country") or "GB" for _, _, t in items}
        return [
            Metric(label="Mule accounts", value=str(len(mules))),
            Metric(label="Distinct senders into mules", value=str(len(senders))),
            Metric(label="Hops", value="3", hint="source → mule → hub → cash-out"),
            Metric(label="Total into hub", value=money(into_hub)),
            Metric(label="Passed on by each mule", value=", ".join(f"{r:.0%}" for _, r, _ in pt) or "—",
                   hint="share of the previous 24 h inflow forwarded"),
            Metric(label="Typical holding time", value=f"{median(h for _, _, h in pt):.1f} h" if pt else "—"),
            Metric(label="Time to cash-out", value=f"{to_cash:.1f} h" if to_cash is not None else "not yet",
                   hint="last forward into the hub → first payment out"),
            Metric(label="Cash-out", value=", ".join(sorted({f"{t['txn_type'].replace('_', ' ')} to {t.get('counterparty_name')}" for t in cash_out})) or "none yet"),
            Metric(label="Countries", value=str(len(countries)), hint=", ".join(sorted(countries))),
            Metric(label="Time span", value=f"{span:.0f} h"),
        ]
    subject = g.hub
    p = world.profiles_by_account.get(subject, {})
    ins = [t for s, d, t in items if d == subject]
    outs = [t for s, d, t in items if s == subject]
    near = [t for t in ins if NEAR_THRESHOLD_LOW <= t["amount"] < CASH_THRESHOLD]
    branches = {t.get("branch") for t in ins if t["txn_type"] == "cash_deposit"}
    out = [
        Metric(label="Money in", value=money(sum(t["amount"] for t in ins)), hint=f"{len(ins)} credits"),
        Metric(label="Money out", value=money(sum(t["amount"] for t in outs)), hint=f"{len(outs)} payments"),
        Metric(label="Distinct counterparties", value=str(len(g.nodes) - 1)),
        Metric(label="Time span", value=f"{span:.0f} h"),
    ]
    if near:
        out.append(Metric(label="Just below £10,000", value=str(len(near)), hint=f"at {len(branches)} branches"))
    if p:
        out.append(Metric(label="Expected a month", value=money(p.get("expected_monthly_credits", 0)),
                          hint=f"cash {money(p.get('expected_monthly_cash', 0))}"))
    return out


def finding(world: World, g: CaseGraph, pattern: str) -> str:
    """The graph title: the finding in plain words (FR-4.6)."""
    items = g.sorted_transfers()
    if not items:
        return "No money movements visible yet"
    span = hours_between(items[0][2]["timestamp"], items[-1][2]["timestamp"])
    if g.layout == "chain":
        mules = [n for n, r in g.nodes.items() if r == "mule"]
        into = [t for s, d, t in items if d == g.hub]
        text = (f"{len(mules)} accounts funnelled {money(sum(t['amount'] for t in into))} into "
                f"{world.name(g.hub)} within {hours_between(into[0]['timestamp'], into[-1]['timestamp']):.0f} hours")
        cash = [(d, t) for s, d, t in items if s == g.hub and g.nodes.get(d) == "sink"]
        if cash:
            text += f"; {money(sum(t['amount'] for _, t in cash))} then left for {world.name(cash[0][0])}"
        return text
    ins = [t for s, d, t in items if d == g.hub]
    if pattern == "structuring":
        cash = [t for t in ins if t["txn_type"] == "cash_deposit"]
        branches = {t.get("branch") for t in cash}
        return (f"{len(cash)} cash deposits totalling {money(sum(t['amount'] for t in cash))} at {len(branches)} "
                f"branches within {span:.0f} hours into {world.name(g.hub)}")
    if g.layout == "fan_out":
        outs = {d for s, d, t in items if s == g.hub}
        return f"{world.name(g.hub)} split money to {len(outs)} recipients within {span:.0f} hours"
    biggest = max(items, key=lambda x: x[2]["amount"])
    return (f"{money(biggest[2]['amount'])} {'from' if biggest[1] == g.hub else 'to'} "
            f"{world.name(biggest[0] if biggest[1] == g.hub else biggest[1])} for {world.name(g.hub)} "
            f"({PATTERN_LABELS.get(pattern, pattern).lower()})")


def nodes_of(world: World, g: CaseGraph, hard_flags: dict[str, list[str]], flags: list[RedFlag]) -> list[GraphNode]:
    fired_accounts: dict[str, list[str]] = {}
    for f in flags:
        if f.state != "fired":
            continue
        for node in g.nodes:
            if world.name(node) in f.evidence:
                fired_accounts.setdefault(node, []).append(f.label)
    return [GraphNode(id=n, label=world.name(n), role=r, external=not world.is_ours(n),
                      hard_flags=hard_flags.get(n, []), flags=fired_accounts.get(n, []))
            for n, r in g.nodes.items()]
