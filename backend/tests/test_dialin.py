"""One-lever dial-in tests. Pure functions — no server, no database."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import dialin  # noqa: E402
from engine.recommend import build_recommendation  # noqa: E402
from equipment.loader import get_grinder, get_brewer  # noqa: E402


# ─── Lever selection ──────────────────────────────────────────────────────────

def test_bitter_moves_grind_coarser():
    adj = dialin.next_adjustment("bitter")
    assert adj["lever"] == "grind"
    assert adj["delta"] > 0


def test_bright_moves_temperature_up():
    adj = dialin.next_adjustment("bright")
    assert adj["lever"] == "temp"
    assert adj["delta"] > 0


def test_flat_moves_ratio_stronger():
    adj = dialin.next_adjustment("flat")
    assert adj["lever"] == "ratio"
    assert adj["delta"] < 0


def test_good_ends_the_chain():
    adj = dialin.next_adjustment("good")
    assert adj["lever"] is None
    assert adj["chain_complete"] is True


def test_no_rating_changes_nothing():
    adj = dialin.next_adjustment(None)
    assert adj["lever"] is None
    assert adj["chain_complete"] is False


# ─── One lever at a time ──────────────────────────────────────────────────────

def test_exactly_one_lever_moves_per_round():
    """The core promise: a round changes one field and notes the rest."""
    adj = dialin.next_adjustment(["bitter", "flat"])
    chain = dialin.apply_adjustment(dialin.EMPTY_CHAIN, adj)

    assert adj["lever"] == "grind"
    assert chain["micron_delta"] != 0
    # The other two axes are untouched, byte for byte.
    assert chain["temp_delta_c"] == 0.0
    assert chain["ratio_delta"] == 0.0
    # The unacted defect is not lost, just deferred.
    assert "flat" in adj["noted"]


def test_opposing_defects_cancel_rather_than_guess():
    adj = dialin.next_adjustment(["bitter", "bright"])
    chain = dialin.apply_adjustment(dialin.EMPTY_CHAIN, adj)

    assert adj["lever"] is None
    assert chain == dialin.EMPTY_CHAIN
    assert set(adj["noted"]) == {"bitter", "bright"}


def test_good_alongside_a_defect_still_ends_the_chain():
    adj = dialin.next_adjustment(["good", "flat"])
    assert adj["chain_complete"] is True
    assert adj["lever"] is None


# ─── Chaining ─────────────────────────────────────────────────────────────────

def test_repeated_bitter_compounds_in_the_same_direction():
    chain = dialin.EMPTY_CHAIN
    chain = dialin.apply_adjustment(chain, dialin.next_adjustment("bitter"))
    first = chain["micron_delta"]
    chain = dialin.apply_adjustment(chain, dialin.next_adjustment("bitter"))

    assert chain["micron_delta"] == first * 2


def test_opposite_defects_across_rounds_partly_undo():
    chain = dialin.EMPTY_CHAIN
    chain = dialin.apply_adjustment(chain, dialin.next_adjustment("bitter"))
    chain = dialin.apply_adjustment(chain, dialin.next_adjustment("flat"))

    assert chain["micron_delta"] > 0
    assert chain["ratio_delta"] < 0


def test_apply_adjustment_does_not_mutate_input():
    original = dict(dialin.EMPTY_CHAIN)
    dialin.apply_adjustment(original, dialin.next_adjustment("bitter"))
    assert original == dialin.EMPTY_CHAIN


def test_chain_from_row_reads_stored_deltas():
    row = {"chain_micron_delta": 60.0, "chain_temp_delta_c": None, "chain_ratio_delta": -0.5}
    chain = dialin.chain_from_row(row)
    assert chain["micron_delta"] == 60.0
    assert chain["temp_delta_c"] == 0.0
    assert chain["ratio_delta"] == -0.5


def test_chain_from_missing_row_is_empty():
    assert dialin.chain_from_row(None) == dialin.EMPTY_CHAIN


# ─── Integration with the recommendation engine ───────────────────────────────

COFFEE = {"roast": "light", "origin": "Ethiopia", "process": "washed"}


def _recommend(chain=None):
    return build_recommendation(
        COFFEE, get_grinder("fellow_ode_gen2"), get_brewer("hario_v60_02"),
        12, [], chain=chain,
    )


def test_bitter_chain_produces_a_coarser_setting():
    base = _recommend()
    chain = dialin.apply_adjustment(dialin.EMPTY_CHAIN, dialin.next_adjustment("bitter"))
    dialed = _recommend(chain)

    assert dialed["target_microns"] > base["target_microns"]
    # Only grind moved.
    assert dialed["ratio"] == base["ratio"]
    assert dialed["recipe"]["temp_c"] == base["recipe"]["temp_c"]


def test_bright_chain_only_raises_temperature():
    base = _recommend()
    chain = dialin.apply_adjustment(dialin.EMPTY_CHAIN, dialin.next_adjustment("bright"))
    dialed = _recommend(chain)

    assert dialed["recipe"]["temp_c"] > base["recipe"]["temp_c"]
    assert dialed["target_microns"] == base["target_microns"]
    assert dialed["ratio"] == base["ratio"]


def test_flat_chain_only_strengthens_ratio():
    base = _recommend()
    chain = dialin.apply_adjustment(dialin.EMPTY_CHAIN, dialin.next_adjustment("flat"))
    dialed = _recommend(chain)

    assert dialed["ratio"] < base["ratio"]
    assert dialed["dose_g"] > base["dose_g"]
    assert dialed["target_microns"] == base["target_microns"]
    assert dialed["recipe"]["temp_c"] == base["recipe"]["temp_c"]


def test_empty_chain_matches_no_chain_at_all():
    assert _recommend(dialin.EMPTY_CHAIN) == _recommend(None)


def test_chain_takes_precedence_over_aggregate_history():
    """A per-coffee chain wins; the roast-level prior is for unbrewed coffees."""
    history = [{"roast": "light", "rating": "bitter"} for _ in range(5)]

    with_history = build_recommendation(
        COFFEE, get_grinder("fellow_ode_gen2"), get_brewer("hario_v60_02"),
        12, history,
    )
    with_chain = build_recommendation(
        COFFEE, get_grinder("fellow_ode_gen2"), get_brewer("hario_v60_02"),
        12, history,
        chain={"micron_delta": 0.0, "temp_delta_c": 2.0, "ratio_delta": 0.0},
    )

    # The aggregate bias fires without a chain and is suppressed with one.
    assert any("History:" in n for n in with_history["bias_notes"])
    assert not any("History:" in n for n in with_chain["bias_notes"])
