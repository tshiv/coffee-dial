"""
One-lever dial-in — change exactly one variable per round, and say why.

Rating vocabulary is the existing one already written to `brews.rating`:
good | bright | flat | bitter.

Grind is a legal lever here. A product that pushes a profile to a machine
cannot turn your grinder, so it has to leave grind alone; Coffee Dial tells you
the setting *before* you grind, which makes grind the most direct lever
available for an extraction fault.

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

LEVERS = {
    "bitter": {
        "lever": "grind",
        "field": "micron_delta",
        "delta": MICRON_STEP,
        "reason": "Bitter means over-extracted. Going one step coarser cuts "
                  "surface area so less comes out of the grounds.",
    },
    "bright": {
        "lever": "temp",
        "field": "temp_delta_c",
        "delta": TEMP_STEP_C,
        "reason": "Bright means under-extracted. A little more heat pulls more "
                  "from the same grounds without touching your grinder.",
    },
    "flat": {
        "lever": "ratio",
        "field": "ratio_delta",
        "delta": -RATIO_STEP,
        "reason": "Flat is a strength problem, not an extraction one. A "
                  "stronger ratio puts more coffee under the same water.",
    },
}

EMPTY_CHAIN = {"micron_delta": 0.0, "temp_delta_c": 0.0, "ratio_delta": 0.0}


def normalize_ratings(ratings):
    if ratings is None:
        return []
    if isinstance(ratings, str):
        return [ratings]
    return [r for r in ratings if r]


def next_adjustment(ratings):
    """Decide the single change for the next brew.

    Args:
        ratings: one rating string, or several for the same brew (two people
                 drinking from one pot will not always agree).

    Returns a dict with:
        lever          — 'grind' | 'temp' | 'ratio' | None
        field / delta  — what to add to the chain, absent when lever is None
        reason         — plain sentence for the UI
        noted          — defects seen but not acted on this round
        chain_complete — True once the cup is called good
    """
    found = normalize_ratings(ratings)

    if not found:
        return {
            "lever": None,
            "reason": "No rating recorded, so nothing changes.",
            "noted": [],
            "chain_complete": False,
        }

    if "good" in found:
        return {
            "lever": None,
            "reason": "Called good — stop changing things.",
            "noted": [r for r in found if r != "good"],
            "chain_complete": True,
        }

    defects = [r for r in PRIORITY if r in found]

    if not defects:
        return {
            "lever": None,
            "reason": "No actionable defect recorded.",
            "noted": found,
            "chain_complete": False,
        }

    # Opposing signals on the same axis cancel out rather than guessing.
    if OPPOSING.issubset(set(defects)):
        return {
            "lever": None,
            "reason": "Bitter and bright together point opposite ways, so "
                      "nothing moves this round. Brew it again and rate one.",
            "noted": defects,
            "chain_complete": False,
        }

    primary = defects[0]
    spec = LEVERS[primary]
    return {
        "lever": spec["lever"],
        "field": spec["field"],
        "delta": spec["delta"],
        "reason": spec["reason"],
        "noted": [d for d in defects if d != primary],
        "chain_complete": False,
    }


def apply_adjustment(chain, adjustment):
    """Fold one adjustment into the accumulated chain deltas.

    Returns a new dict; the input chain is not mutated.
    """
    result = dict(EMPTY_CHAIN)
    result.update({k: v for k, v in (chain or {}).items() if k in EMPTY_CHAIN})

    if adjustment.get("lever") and adjustment.get("field"):
        result[adjustment["field"]] += adjustment["delta"]

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
