"""Freshness engine tests. Pure functions — no server, no database."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import freshness  # noqa: E402

DAY = freshness.SECONDS_PER_DAY
NOW = 1_800_000_000


def bag(**overrides):
    base = {
        "roast": "medium",
        "process": "washed",
        "is_decaf": 0,
        "storage": "airtight",
        "roast_date": NOW - 10 * DAY,
        "opened_at": None,
        "frozen_at": None,
        "thawed_at": None,
    }
    base.update(overrides)
    return base


# ─── Rest periods ─────────────────────────────────────────────────────────────

def test_light_rests_longer_than_dark():
    light_low, light_high = freshness.ready_range("light", "washed")
    dark_low, dark_high = freshness.ready_range("dark", "washed")
    assert light_low > dark_low
    assert light_high > dark_high


def test_natural_process_adds_rest():
    washed = freshness.ready_range("light", "washed")
    natural = freshness.ready_range("light", "natural")
    assert natural[0] == washed[0] + freshness.SLOW_REST_BONUS_DAYS
    assert natural[1] == washed[1] + freshness.SLOW_REST_BONUS_DAYS


def test_anaerobic_counts_as_slow_rest():
    washed = freshness.ready_range("light", "washed")
    anaerobic = freshness.ready_range("light", "Anaerobic Natural")
    assert anaerobic[0] > washed[0]


def test_unknown_roast_assumes_medium_and_says_so():
    result = freshness.compute_phase(bag(roast="city+"), NOW)
    assert result["assumed_roast"] is True
    assert "assuming medium" in result["message"]
    assert result["ready_range_days"] == list(freshness.READY_RANGE_DAYS["medium"])


def test_decaf_tires_sooner():
    assert freshness.tired_day("medium", is_decaf=True) < freshness.tired_day("medium")


# ─── Phases ───────────────────────────────────────────────────────────────────

def test_no_roast_date_gives_no_window_numbers():
    result = freshness.compute_phase(bag(roast_date=None), NOW)
    assert result["phase"] == freshness.PHASE_AWAITING
    assert "ready_range_days" not in result
    assert "tired_day" not in result


def test_fresh_light_roast_is_resting():
    result = freshness.compute_phase(
        bag(roast="light", roast_date=NOW - 3 * DAY), NOW
    )
    assert result["phase"] == freshness.PHASE_RESTING


def test_rested_medium_is_ready():
    result = freshness.compute_phase(
        bag(roast="medium", roast_date=NOW - 8 * DAY), NOW
    )
    assert result["phase"] == freshness.PHASE_READY


def test_old_bag_is_tired():
    result = freshness.compute_phase(
        bag(roast="medium", roast_date=NOW - 60 * DAY), NOW
    )
    assert result["phase"] == freshness.PHASE_TIRED


# ─── Freezing ─────────────────────────────────────────────────────────────────

def test_frozen_bag_stops_aging():
    frozen = bag(roast_date=NOW - 40 * DAY, frozen_at=NOW - 30 * DAY)
    assert freshness.effective_age_days(frozen, NOW) == 10
    assert freshness.is_frozen(frozen) is True


def test_bag_frozen_mid_rest_thaws_mid_rest():
    """Frozen on day 3, thawed 100 days later — still day 3 on the clock."""
    b = bag(
        roast="light",
        roast_date=NOW - 103 * DAY,
        frozen_at=NOW - 100 * DAY,
        thawed_at=NOW,
    )
    assert freshness.effective_age_days(b, NOW) == 3
    assert freshness.compute_phase(b, NOW)["phase"] == freshness.PHASE_RESTING


def test_thawed_bag_resumes_where_it_paused():
    b = bag(
        roast_date=NOW - 50 * DAY,
        frozen_at=NOW - 45 * DAY,
        thawed_at=NOW - 2 * DAY,
    )
    # 5 days before freezing + 2 days since thawing
    assert freshness.effective_age_days(b, NOW) == 7


def test_clearing_a_freeze_restores_plain_age():
    b = bag(roast_date=NOW - 20 * DAY, frozen_at=None, thawed_at=None)
    assert freshness.effective_age_days(b, NOW) == 20


# ─── Open clock ───────────────────────────────────────────────────────────────

def test_opened_bag_tires_before_sealed_twin():
    roast_date = NOW - 25 * DAY
    sealed = freshness.compute_phase(bag(roast_date=roast_date), NOW)
    opened = freshness.compute_phase(
        bag(roast_date=roast_date, storage="bag_ambient", opened_at=NOW - 24 * DAY), NOW
    )
    assert sealed["phase"] == freshness.PHASE_READY
    assert opened["phase"] == freshness.PHASE_TIRED
    assert opened["limiting_clock"] == "open"


def test_never_opened_bag_has_no_open_clock():
    result = freshness.compute_phase(bag(), NOW)
    assert "open_age_days" not in result
    assert result["limiting_clock"] == "sealed"


def test_freezing_before_opening_does_not_credit_open_clock():
    """The frozen interval only counts against a clock it actually overlaps."""
    b = bag(
        roast_date=NOW - 60 * DAY,
        frozen_at=NOW - 50 * DAY,
        thawed_at=NOW - 10 * DAY,
        opened_at=NOW - 5 * DAY,
    )
    assert freshness.open_age_days(b, NOW) == 5


# ─── Storage ──────────────────────────────────────────────────────────────────

def test_vacuum_extends_open_clock():
    assert freshness.open_clock_days("vacuum") > freshness.open_clock_days("airtight")
    assert freshness.open_clock_days("airtight") > freshness.open_clock_days("bag_ambient")


def test_storage_changes_tired_but_never_the_rest_period():
    """The whole point of the split: storage touches oxidation, not degassing."""
    roast_date = NOW - 26 * DAY
    opened_at = NOW - 25 * DAY

    airtight = freshness.compute_phase(
        bag(roast="light", roast_date=roast_date, opened_at=opened_at, storage="airtight"), NOW
    )
    vacuum = freshness.compute_phase(
        bag(roast="light", roast_date=roast_date, opened_at=opened_at, storage="vacuum"), NOW
    )

    # Identical rest period — storage must not leak into degassing.
    assert airtight["ready_range_days"] == vacuum["ready_range_days"]
    # Different outcome on the open clock.
    assert airtight["open_limit_days"] < vacuum["open_limit_days"]
    assert airtight["phase"] == freshness.PHASE_TIRED
    assert vacuum["phase"] == freshness.PHASE_READY


def test_unknown_storage_falls_back_to_default():
    assert freshness.open_clock_days("mason jar in the sun") == freshness.open_clock_days(
        freshness.DEFAULT_STORAGE
    )
