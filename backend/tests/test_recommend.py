"""Recommendation targets — the numbers are decided once, then formatted."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import dialin  # noqa: E402
from engine.recommend import build_recommendation, compute_targets, lever_headroom  # noqa: E402
from equipment.loader import get_grinder, get_brewer, get_brewers  # noqa: E402

COFFEE = {"roast": "light", "origin": "Ethiopia", "process": "washed"}
GRINDER = get_grinder("fellow_ode_gen2")
AIDEN = get_brewer("fellow_aiden")
FIXED_ID = next(k for k, v in get_brewers().items()
                if "fixed" in v.get("parameters", {}).get("temp_c", {}))
FIXED = get_brewer(FIXED_ID)


def _rec(brewer=AIDEN, chain=None, coffee=COFFEE, oz=12):
    return build_recommendation(coffee, GRINDER, brewer, oz, [], chain=chain)


def test_recipe_ratio_matches_recommendation_ratio_after_a_ratio_move():
    """The old builders recomputed ratio themselves and showed the stale one."""
    chain = dialin.apply_adjustment(dialin.EMPTY_CHAIN, dialin.next_adjustment("flat"))
    rec = _rec(chain=chain)
    assert rec["recipe"]["ratio"] == rec["ratio"]
    assert rec["recipe"]["dose_g"] == rec["dose_g"]
    # And the dose really is the adjusted ratio's dose.
    assert abs(rec["water_g"] / rec["ratio"] - rec["dose_g"]) < 0.6


def test_temperature_is_clamped_to_the_brewer_max():
    rec = _rec(chain={"micron_delta": 0, "temp_delta_c": 20, "ratio_delta": 0})
    assert rec["recipe"]["temp_c"] == AIDEN["parameters"]["temp_c"]["max"]
    assert any("pinned" in n for n in rec["bias_notes"])


def test_fixed_temperature_brewer_ignores_a_temperature_delta():
    base = _rec(brewer=FIXED)
    dialed = _rec(brewer=FIXED, chain={"micron_delta": 0, "temp_delta_c": 2, "ratio_delta": 0})
    fixed = FIXED["parameters"]["temp_c"]["fixed"]
    assert base["recipe"]["temp_c"] == fixed
    assert dialed["recipe"]["temp_c"] == fixed
    assert not any("°C" in n for n in dialed["bias_notes"])


def test_ratio_is_clamped_to_the_brewer_range():
    rec = _rec(chain={"micron_delta": 0, "temp_delta_c": 0, "ratio_delta": -10})
    assert rec["ratio"] == AIDEN["parameters"]["ratio"]["min"]


def test_zero_chain_is_a_no_op_with_no_dialin_notes():
    assert _rec(chain=dialin.EMPTY_CHAIN) == _rec(chain=None)
    assert not any(n.startswith("Dial-in") for n in _rec(chain=None)["bias_notes"])


def test_every_recipe_type_reports_the_decided_targets():
    """Whatever the brewer, the recipe carries the engine's numbers, not its own."""
    chain = {"micron_delta": 0, "temp_delta_c": -2, "ratio_delta": -0.5}
    seen = set()
    for bid, brewer in get_brewers().items():
        rec = build_recommendation(COFFEE, GRINDER, brewer, 12, [], chain=chain)
        t = compute_targets(COFFEE, brewer, 12, [], chain)
        assert rec["recipe"]["temp_c"] == t["temp_c"], bid
        assert rec["recipe"]["ratio"] == t["ratio"], bid
        assert rec["recipe"]["dose_g"] == round(t["dose_g"], 1), bid
        seen.add(rec["recipe"]["type"])
    assert len(seen) >= 5


# ─── Headroom ─────────────────────────────────────────────────────────────────

def test_headroom_blocks_both_temp_moves_on_a_fixed_brewer():
    h = lever_headroom(COFFEE, FIXED, 12)
    assert h["temp+"] and h["temp-"]
    assert h["grind+"] is None and h["ratio-"] is None


def test_headroom_blocks_hotter_once_at_the_max():
    at_max = {"micron_delta": 0, "temp_delta_c": 50, "ratio_delta": 0}
    h = lever_headroom(COFFEE, AIDEN, 12, at_max)
    assert h["temp+"] is not None
    assert h["temp-"] is None


def test_headroom_is_open_at_the_start():
    h = lever_headroom(COFFEE, AIDEN, 12)
    assert all(v is None for v in h.values()), h


def test_third_bright_in_a_row_moves_grind_once_temp_is_pinned():
    """The engine picks a lever the brewer can still move."""
    chain = dialin.EMPTY_CHAIN
    levers = []
    for _ in range(5):
        adj = dialin.next_adjustment("bright", lever_headroom(COFFEE, AIDEN, 12, chain))
        levers.append(adj["lever"])
        chain = dialin.apply_adjustment(chain, adj)
    assert "temp" in levers and "grind" in levers
    assert levers.index("grind") > levers.index("temp")
    rec = _rec(chain=chain)
    assert rec["recipe"]["temp_c"] <= AIDEN["parameters"]["temp_c"]["max"]
