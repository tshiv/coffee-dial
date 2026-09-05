"""
One-lever dial-in — change exactly one variable per round, and say why.

Rating vocabulary is the existing one already written to `brews.rating`:
good | bright | flat | bitter. Several ratings for one brew are stored
comma-joined ("bitter,flat") and read back the same way.

Grind is a legal lever here. A product that pushes a profile to a machine
cannot turn your grinder, so it has to leave grind alone; Coffee Dial tells you
the setting *before* you grind, which makes grind the most direct lever
available for an extraction fault.

Each defect has an ordered list of candidate moves. The first one the brewer
can actually make is taken — a fixed-temperature machine has no temp lever,
and an Aiden already pinned at 99°C cannot go hotter. Which moves are open is
the recommendation engine's call (`recommend.lever_headroom`); this module
only asks.

Deltas accumulate along a chain (v1 -> v2 -> v3) and are applied in
recommend.build_recommendation() after the base target is computed.
"""

MICRON_STEP = 30       # one notch coarser/finer
TEMP_STEP_C = 2.0      # one notch hotter/cooler
RATIO_STEP = 0.5       # one notch stronger/weaker

# Which defect gets acted on when several are recorded for the same brew.
# Extraction faults outrank strength faults: a bitter cup that is also weak is
# over-extracted first and under-dosed second.
PRIORITY = ("bitter", "bright", "flat")

# Ratings that sit on the same axis in opposite directions. Recorded together,
# they cancel rather than the engine picking a side.
OPPOSING = frozenset({"bitter", "bright"})

# A move is a lever plus a direction. Headroom is reported per move because
# "hotter" and "cooler" are blocked by different limits.
MOVES = ("grind+", "grind-", "temp+", "temp-", "ratio+", "ratio-")

LEVERS = {
    "bitter": [
        {
            "move": "grind+", "lever": "grind", "field": "micron_delta",
            "delta": MICRON_STEP,
            "reason": "Bitter means over-extracted. Going one step coarser cuts "
                      "surface area so less comes out of the grounds.",
        },
        {
            "move": "temp-", "lever": "temp", "field": "temp_delta_c",
            "delta": -TEMP_STEP_C,
            "reason": "Bitter means over-extracted. Grind can't go coarser for "
                      "this brewer, so a little less heat pulls less from the "
                      "same grounds instead.",
        },
    ],
    "bright": [
        {
            "move": "temp+", "lever": "temp", "field": "temp_delta_c",
            "delta": TEMP_STEP_C,
            "reason": "Bright means under-extracted. A little more heat pulls "
                      "more from the same grounds without touching your grinder.",
        },
        {
            "move": "grind-", "lever": "grind", "field": "micron_delta",
            "delta": -MICRON_STEP,
            "reason": "Bright means under-extracted. Temperature can't go up "
                      "on this brewer, so go one step finer to pull more from "
                      "the grounds instead.",
        },
    ],
    "flat": [
        {
            "move": "ratio-", "lever": "ratio", "field": "ratio_delta",
            "delta": -RATIO_STEP,
            "reason": "Flat is a strength problem, not an extraction one. A "
                      "stronger ratio puts more coffee under the same water.",
        },
    ],
}

EMPTY_CHAIN = {"micron_delta": 0.0, "temp_delta_c": 0.0, "ratio_delta": 0.0}

# Freshness phases that change what a rating means.
PHASE_TIRED = "tired"
PHASE_RESTING = "resting"


def normalize_ratings(ratings):
    """One rating, a list, or the comma-joined form stored in the database."""
    if ratings is None:
        return []
    if isinstance(ratings, str):
        return [r.strip() for r in ratings.split(",") if r.strip()]
    return [r for r in ratings if r]


def next_adjustment(ratings, headroom=None, bag_phase=None):
    """Decide the single change for the next brew.

    Args:
        ratings: one rating string, or several for the same brew (two people
                 drinking from one pot will not always agree).
        headroom: {move: None | "why it is blocked"} from
                  recommend.lever_headroom(). None means every move is open.
        bag_phase: the bag's freshness phase when this brew was made, if the
                   brew came from a bag. A tired bag changes what "flat" means.

    Returns a dict with:
        lever          — 'grind' | 'temp' | 'ratio' | None
        move / field / delta — what to add to the chain, absent when lever is None
        reason         — plain sentence for the UI
        noted          — defects seen but not acted on this round
        chain_complete — True once the cup is called good
        freshness_note — present when the bag's phase colours the reading
    """
    found = normalize_ratings(ratings)
    headroom = headroom or {}

    if not found:
        return _no_move("No rating recorded, so nothing changes.", [])

    if "good" in found:
        result = _no_move("Called good — stop changing things.",
                          [r for r in found if r != "good"], complete=True)
        return result

    defects = [r for r in PRIORITY if r in found]

    if not defects:
        return _no_move("No actionable defect recorded.", found)

    # Opposing signals on the same axis cancel out rather than guessing.
    if OPPOSING.issubset(set(defects)):
        return _no_move(
            "Bitter and bright together point opposite ways, so nothing moves "
            "this round. Brew it again and rate one.", defects)

    # A stale bag tastes flat. Tuning the ratio to that would bake a tired
    # bag's defect into the chain, so the ratio lever is off the table.
    if bag_phase == PHASE_TIRED and defects == ["flat"]:
        result = _no_move(
            "This bag was past its window when you brewed it, and flat is what "
            "stale tastes like. Nothing moves — a stronger ratio would tune the "
            "recipe to a tired bag. Rate the next cup from a fresh one.",
            defects)
        result["freshness_note"] = "Rated from a tired bag."
        return result

    primary = defects[0]
    noted = [d for d in defects if d != primary]
    blocked = []
    for candidate in LEVERS[primary]:
        why = headroom.get(candidate["move"])
        if why is None:
            result = {
                "lever": candidate["lever"],
                "move": candidate["move"],
                "field": candidate["field"],
                "delta": candidate["delta"],
                "reason": candidate["reason"],
                "noted": noted,
                "chain_complete": False,
            }
            if blocked:
                result["reason"] += " ({})".format(" ".join(blocked))
            _add_phase_note(result, bag_phase)
            return result
        blocked.append(why)

    result = _no_move(
        "Nothing left to move for {}: {}".format(primary, " ".join(blocked)),
        noted)
    _add_phase_note(result, bag_phase)
    return result


def _no_move(reason, noted, complete=False):
    return {"lever": None, "reason": reason, "noted": noted, "chain_complete": complete}


def _add_phase_note(result, bag_phase):
    if bag_phase == PHASE_TIRED:
        result["freshness_note"] = (
            "Rated from a tired bag — treat this round as a weak signal.")
    elif bag_phase == PHASE_RESTING:
        result["freshness_note"] = (
            "Rated while the bag was still resting — it will change on its "
            "own over the next few days.")


def apply_adjustment(chain, adjustment):
    """Fold one adjustment into the accumulated chain deltas.

    Returns a new dict; the input chain is not mutated.
    """
    result = normalize_chain(chain)

    if adjustment.get("lever") and adjustment.get("field"):
        result[adjustment["field"]] += adjustment["delta"]

    return result


def normalize_chain(chain):
    """A full chain dict with every axis present, from a partial one or None."""
    result = dict(EMPTY_CHAIN)
    for key in EMPTY_CHAIN:
        value = (chain or {}).get(key)
        if value:
            result[key] = float(value)
    return result


def chain_from_row(row):
    """Read accumulated deltas off a brews row (sqlite Row or dict)."""
    if row is None:
        return dict(EMPTY_CHAIN)
    get = row.get if hasattr(row, "get") else lambda k, d=None: row[k]
    chain = dict(EMPTY_CHAIN)
    for field in EMPTY_CHAIN:
        try:
            value = get("chain_" + field)
        except (KeyError, IndexError):
            value = None
        if value is not None:
            chain[field] = float(value)
    return chain


def chain_for_child(parent_row, headroom=None):
    """The chain, version and adjustment for the brew that follows `parent_row`.

    A brew row stores the deltas that were applied to *that* brew. The next
    brew inherits them plus the one move its parent's rating calls for.
    """
    get = parent_row.get if hasattr(parent_row, "get") else lambda k: parent_row[k]
    bag_phase = None
    try:
        bag_phase = get("bag_phase")
    except (KeyError, IndexError):
        pass
    adjustment = next_adjustment(get("rating"), headroom, bag_phase)
    chain = apply_adjustment(chain_from_row(parent_row), adjustment)
    version = (get("version") or 1) + 1
    return chain, version, adjustment
