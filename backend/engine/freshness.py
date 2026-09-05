"""
Freshness engine — when a bag is resting, ready, or tired.

Two clocks run in parallel and the shorter one wins:

  Sealed clock — days since roast. Drives resting → ready → tired.
  Open clock   — days since the bag was opened. Oxygen is the dominant
                 staling factor once air is in, regardless of the roast date.

Freezing pauses both: a bag frozen on day 20 thaws on day 20.

Storage affects the OPEN clock only. Degassing is CO2 leaving the bean and is
not changed by the container, so storage must never touch the rest period.

No I/O and no AI. Every number below is a convention, adjustable in one place.
"""

SECONDS_PER_DAY = 86400

# Days until the bag is ready, as a range. Reported as a range on purpose:
# roasters disagree with each other about resting more than roast levels
# differ from one another, so a single ready-day would be false precision.
READY_RANGE_DAYS = {
    "light": (10, 20),
    "medium": (5, 12),
    "dark": (2, 5),
}
DEFAULT_ROAST = "medium"

# Processes that keep fermenting in the bag and need extra rest.
SLOW_REST_PROCESSES = ("natural", "anaerobic", "fermented")
SLOW_REST_BONUS_DAYS = 3

# Sealed-clock staling boundary.
TIRED_DAYS = {
    "light": 42,
    "medium": 30,
    "dark": 21,
}

# Decaf loses its structure sooner; the bean is more damaged before it is roasted.
DECAF_TIRED_FACTOR = 0.7

# Open clock: roughly three weeks of good drinking once air is in.
OPEN_CLOCK_BASE_DAYS = 21

# Storage multipliers on the open clock only.
#   vacuum assumes the vacuum is re-established every time the canister is
#   closed. Fellow's own guidance is that an Atmos holds its seal 3-4 days and
#   should be re-twisted every 4-5 days, so a canister pumped once and left for
#   a week behaves closer to `airtight`.
# The 1.5 is derived from a vendor claim ("up to 50% longer"), not an
# independent measurement. It is the least-evidenced number in this module.
STORAGE_MULTIPLIERS = {
    "bag_ambient": 0.8,
    "airtight": 1.0,
    "vacuum": 1.5,
}
DEFAULT_STORAGE = "vacuum"

PHASE_AWAITING = "awaiting_roast_date"
PHASE_RESTING = "resting"
PHASE_READY = "ready"
PHASE_TIRED = "tired"


def _normalize_roast(roast):
    """Map a roast string onto a known key, or None if unrecognized."""
    if not roast:
        return None
    r = str(roast).strip().lower()
    for key in READY_RANGE_DAYS:
        if key in r:
            return key
    return None


def _is_slow_rest(process):
    if not process:
        return False
    p = str(process).strip().lower()
    return any(token in p for token in SLOW_REST_PROCESSES)


def ready_range(roast, process=None):
    """Days after roast when the bag should come into its window.

    Returns (low, high). Storage is deliberately not a parameter — it must not
    influence the rest period.
    """
    key = _normalize_roast(roast) or DEFAULT_ROAST
    low, high = READY_RANGE_DAYS[key]
    if _is_slow_rest(process):
        low += SLOW_REST_BONUS_DAYS
        high += SLOW_REST_BONUS_DAYS
    return (low, high)


def tired_day(roast, is_decaf=False):
    """Day, on the sealed clock, when the bag is past its best."""
    key = _normalize_roast(roast) or DEFAULT_ROAST
    days = TIRED_DAYS[key]
    if is_decaf:
        days *= DECAF_TIRED_FACTOR
    return days


def open_clock_days(storage=None):
    """How many days of good drinking remain once the bag is opened."""
    multiplier = STORAGE_MULTIPLIERS.get(storage or DEFAULT_STORAGE)
    if multiplier is None:
        multiplier = STORAGE_MULTIPLIERS[DEFAULT_STORAGE]
    return OPEN_CLOCK_BASE_DAYS * multiplier


def _elapsed_days(start, now, frozen_at=None, thawed_at=None):
    """Days between start and now, excluding any time spent frozen.

    The frozen interval is [frozen_at, thawed_at], or [frozen_at, now] if the
    bag is still in the freezer. Only the part of that interval that overlaps
    [start, now] is subtracted, so freezing before a bag was opened does not
    credit the open clock.
    """
    if start is None or now is None or now <= start:
        return 0.0

    elapsed = now - start

    if frozen_at is not None:
        freeze_end = thawed_at if thawed_at is not None else now
        overlap_start = max(frozen_at, start)
        overlap_end = min(freeze_end, now)
        if overlap_end > overlap_start:
            elapsed -= (overlap_end - overlap_start)

    return max(0.0, elapsed / SECONDS_PER_DAY)


def effective_age_days(bag, now):
    """Age on the sealed clock, with frozen time removed."""
    return _elapsed_days(
        bag.get("roast_date"), now,
        bag.get("frozen_at"), bag.get("thawed_at"),
    )


def open_age_days(bag, now):
    """Age on the open clock, with frozen time removed. None if never opened."""
    if not bag.get("opened_at"):
        return None
    return _elapsed_days(
        bag.get("opened_at"), now,
        bag.get("frozen_at"), bag.get("thawed_at"),
    )


def is_frozen(bag):
    return bool(bag.get("frozen_at")) and not bag.get("thawed_at")


def compute_phase(bag, now):
    """Full freshness read for a bag.

    Returns a dict that always carries `phase`. Window numbers are present only
    when a real roast date exists — a freshness claim without one would be a
    guess dressed as a fact.
    """
    if not bag.get("roast_date"):
        return {
            "phase": PHASE_AWAITING,
            "message": "Enter the roast date from the bag to see its window.",
            "frozen": is_frozen(bag),
        }

    roast = bag.get("roast")
    process = bag.get("process")
    is_decaf = bool(bag.get("is_decaf"))
    storage = bag.get("storage")

    assumed_roast = _normalize_roast(roast) is None

    age = effective_age_days(bag, now)
    low, high = ready_range(roast, process)
    sealed_tired = tired_day(roast, is_decaf)

    open_age = open_age_days(bag, now)
    open_limit = open_clock_days(storage)

    # Shorter clock wins.
    tired_by_seal = age >= sealed_tired
    tired_by_air = open_age is not None and open_age >= open_limit

    if age < low:
        phase = PHASE_RESTING
    elif tired_by_seal or tired_by_air:
        phase = PHASE_TIRED
    else:
        phase = PHASE_READY

    result = {
        "phase": phase,
        "age_days": round(age, 1),
        "ready_range_days": [low, high],
        "tired_day": round(sealed_tired, 1),
        "frozen": is_frozen(bag),
        "assumed_roast": assumed_roast,
        "storage": storage or DEFAULT_STORAGE,
    }

    if open_age is not None:
        result["open_age_days"] = round(open_age, 1)
        result["open_limit_days"] = round(open_limit, 1)
        result["limiting_clock"] = "open" if tired_by_air and not tired_by_seal else "sealed"
    else:
        result["limiting_clock"] = "sealed"

    if phase == PHASE_RESTING:
        result["message"] = "Still resting — ready in about {}-{} days off roast.".format(low, high)
    elif phase == PHASE_TIRED:
        result["message"] = (
            "Past its best — the bag has been open a while."
            if tired_by_air and not tired_by_seal
            else "Past its best on the roast date."
        )
    else:
        result["message"] = "In the window."

    if assumed_roast:
        result["message"] += " Roast level unknown, assuming medium."

    return result
