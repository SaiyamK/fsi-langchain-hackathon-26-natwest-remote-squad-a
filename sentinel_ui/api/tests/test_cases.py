"""Case builder: graph, metrics, red flags and the finding, on world-0 data."""

import pytest

from sentinel_api import cases as C
from sentinel_api.world import World

RING_AS_OF = "2026-11-12T23:00"


@pytest.fixture(scope="module")
def world():
    return World.load()


def test_ring_graph_has_sources_mules_hub_and_cash_out(world):
    g = C.ring_graph(world, "ACC-0050", RING_AS_OF)
    roles = {}
    for role in g.nodes.values():
        roles[role] = roles.get(role, 0) + 1
    assert g.layout == "chain"
    assert roles["hub"] == 1 and roles["mule"] == 5
    assert roles["source"] >= 5 and roles["sink"] >= 1


def test_ring_red_flags(world):
    g = C.ring_graph(world, "ACC-0050", RING_AS_OF)
    flags = {f.key: f for f in C.red_flags(world, g, "mule_fan_in", RING_AS_OF)}
    assert flags["pass_through"].state == "fired"
    assert flags["consolidation_cashout"].state == "fired"
    assert flags["cross_border"].state == "fired"
    assert flags["new_account_volume"].state == "fired"  # Northgate: weeks old, no prior inflow
    assert flags["shared_device"].state == "no_data"  # FR-5.4: never "not fired" without data


def test_ring_finding_is_plain_words(world):
    g = C.ring_graph(world, "ACC-0050", RING_AS_OF)
    text = C.finding(world, g, "mule_fan_in")
    assert text.startswith("5 accounts funnelled £")
    assert "Northgate Trading Ltd" in text


def test_ring_not_visible_before_confirmation(world):
    assert C.ring_graph(world, "ACC-0050", "2026-11-10T00:00").transfers == []
    assert C.ring_index("2026-11-10T00:00") == {}


def test_structuring_case(world):
    txs = [world.tx("TX-000159"), world.tx("TX-000167")]
    g = C.single_graph(world, "ACC-0001", txs)
    flags = {f.key: f for f in C.red_flags(world, g, "structuring", "2026-10-08T09:00")}
    assert flags["near_threshold"].state == "fired"
    assert C.finding(world, g, "structuring").startswith("4 cash deposits totalling £38,000 at 3 branches")


def test_case_ids(world):
    rings = C.ring_index(RING_AS_OF)
    liam_forward = world.tx("TX-000717")
    assert C.case_id_for(liam_forward, "mule_fan_in", rings) == "CASE-RING-ACC-0050"
    assert C.case_id_for(world.tx("TX-000167"), "structuring", rings) == "CASE-CUS-0001-structuring"


def test_balances_show_pass_through(world):
    g = C.ring_graph(world, "ACC-0050", RING_AS_OF)
    bal = C.balances(world, g, RING_AS_OF)
    liam = [p.balance for p in bal["ACC-0040"]]
    assert max(liam) > 500 and liam[-1] < 0.2 * max(liam)  # fills, then drains
