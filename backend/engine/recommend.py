"""
Recommendation engine — computes grind settings and brew profiles.

Pipeline:
  1. Decide the three brew targets — grind (microns), temperature, ratio.
     Each is base + fixed offsets + dial-in chain delta, clamped to the
     brewer's range. The chain is just another offset source; a zero chain
     changes nothing.
  2. Translate microns to a grinder-specific setting
  3. Hand the finished targets to the brewer's recipe builder, which only
     formats them into steps or a machine profile

Temperature and ratio are decided here, not inside the recipe builders, so
there is exactly one place where a number can be nudged or clamped.
"""

from .grind import (
    get_base_target_microns,
    get_origin_micron_offset,
    get_process_micron_offset,
    get_volume_micron_offset,
    get_origin_temp_offset,
    get_process_temp_offset,
    microns_to_setting,
    format_grind_setting,
)
from .recipes import build_recipe
from . import dialin

GRAMS_PER_OZ = 29.5735

ROAST_RATIO_ADJUSTMENTS = {
    "light": +0.5,
    "medium-light": +0.25,
    "medium": 0,
    "medium-dark": -0.25,
    "dark": -0.5,
}


def build_recommendation(coffee_data, grinder, brewer, oz, history_rows, chain=None):
    """Build a complete brew recommendation.

    Args:
        coffee_data: dict with roast, origin, process, etc. from AI parsing
        grinder: grinder definition dict from equipment loader
        brewer: brewer definition dict from equipment loader
        oz: desired output in ounces
        history_rows: list of past brew dicts with roast/rating fields
        chain: accumulated one-lever dial-in deltas for this specific coffee.
            When present it takes precedence over the aggregate roast-level
            learning, which stays as the prior for a coffee you have not
            brewed yet.

    Returns:
        dict with grinder_setting, grinder_display, target_microns, recipe, bias_notes
    """
    targets = compute_targets(coffee_data, brewer, oz, history_rows, chain)

    grinder_setting = microns_to_setting(grinder, targets["target_microns"])
    grinder_display = format_grind_setting(grinder, grinder_setting)

    recipe = build_recipe(brewer, coffee_data, targets)

    return {
        "grinder_name": grinder["name"],
        "grinder_setting": grinder_setting,
        "grinder_display": grinder_display,
        "target_microns": round(targets["target_microns"]),
        "brewer_name": brewer["name"],
        "dose_g": round(targets["dose_g"], 1),
        "water_g": round(targets["water_g"]),
        "water_oz": oz,
        "ratio": targets["ratio"],
        "temp_c": targets["temp_c"],
        "recipe": recipe,
        "bias_notes": targets["notes"],
        "chain": targets["chain"],
    }


def compute_targets(coffee_data, brewer, oz, history_rows, chain=None):
    """The three numbers every recipe is built from, plus how they were reached.

    Returns a dict with target_microns, temp_c, ratio, dose_g, water_g, the
    normalized chain, the bias notes, and `limits` — the brewer's range for
    each axis, used by lever_headroom().
    """
    chain = dialin.normalize_chain(chain)
    has_chain = any(chain.values())
    notes = []

    microns, micron_limits = _grind_target(coffee_data, brewer, oz, history_rows, chain, has_chain, notes)
    temp_c, temp_limits = _temp_target(coffee_data, brewer, chain, notes)
    ratio, ratio_limits = _ratio_target(coffee_data, brewer, chain, notes)

    water_g = oz * GRAMS_PER_OZ
    dose_g = water_g / ratio

    return {
        "target_microns": microns,
        "temp_c": temp_c,
        "ratio": ratio,
        "dose_g": dose_g,
        "water_g": water_g,
        "chain": chain,
        "notes": notes,
        "limits": {"grind": micron_limits, "temp": temp_limits, "ratio": ratio_limits},
    }


def lever_headroom(coffee_data, brewer, oz, chain=None):
    """Which dial-in moves are still open for this brewer at this chain.

    Returns {move: None | reason} for every move in dialin.MOVES. None means
    the move is open; a string says why it is not. A fixed-temperature brewer
    blocks both temp moves; a value already at the brewer's limit blocks the
    move that would push past it.
    """
    t = compute_targets(coffee_data, brewer, oz, [], chain)
    limits = t["limits"]
    result = {}

    def check(move, current, step, limit, label, unit):
        lo, hi = limit["min"], limit["max"]
        if limit.get("fixed"):
            result[move] = "{} is fixed at {}{} on this brewer.".format(label, current, unit)
        elif step > 0 and hi is not None and current + step > hi:
            result[move] = "Already at the brewer's max {} ({}{}).".format(label.lower(), hi, unit)
        elif step < 0 and lo is not None and current + step < lo:
            result[move] = "Already at the brewer's min {} ({}{}).".format(label.lower(), lo, unit)
        else:
            result[move] = None

    check("grind+", t["target_microns"], dialin.MICRON_STEP, limits["grind"], "Grind", "µm")
    check("grind-", t["target_microns"], -dialin.MICRON_STEP, limits["grind"], "Grind", "µm")
    check("temp+", t["temp_c"], dialin.TEMP_STEP_C, limits["temp"], "Temperature", "°C")
    check("temp-", t["temp_c"], -dialin.TEMP_STEP_C, limits["temp"], "Temperature", "°C")
    check("ratio+", t["ratio"], dialin.RATIO_STEP, limits["ratio"], "Ratio", "")
    check("ratio-", t["ratio"], -dialin.RATIO_STEP, limits["ratio"], "Ratio", "")
    return result


# ─── Targets ──────────────────────────────────────────────────────────────────

def _grind_target(coffee_data, brewer, oz, history_rows, chain, has_chain, notes):
    roast = coffee_data.get("roast", "medium")
    origin = coffee_data.get("origin", "")
    process = coffee_data.get("process", "")
    extraction_type = brewer.get("extraction_type", "percolation")

    microns = get_base_target_microns(roast, extraction_type)

    origin_offset = get_origin_micron_offset(origin)
    if origin_offset != 0:
        microns += origin_offset
        origin_name = origin.split(",")[0].strip().title() if origin else ""
        notes.append(f"{origin_name} origin: {'coarser' if origin_offset > 0 else 'finer'}")

    process_offset = get_process_micron_offset(process)
    if process_offset != 0:
        microns += process_offset
        notes.append(f"{process} process: coarser grind")

    volume_offset = get_volume_micron_offset(oz)
    if volume_offset != 0:
        microns += volume_offset
        notes.append(f"{oz}oz volume adjustment")

    # Per-coffee chain wins; the aggregate roast-level learning is the prior
    # for a coffee you have not brewed yet. Both work in micron space, so
    # either survives a change of grinder.
    if has_chain:
        delta = chain["micron_delta"]
        if delta:
            microns += delta
            notes.append("Dial-in: {} microns {}".format(
                abs(round(delta)), "coarser" if delta > 0 else "finer"))
    else:
        similar = [b for b in history_rows if b["roast"] == roast]
        if similar:
            bitter_count = sum(1 for b in similar if b["rating"] == "bitter")
            bright_count = sum(1 for b in similar if b["rating"] == "bright")
            flat_count = sum(1 for b in similar if b["rating"] == "flat")
            if bitter_count > bright_count + flat_count:
                microns += 30
                notes.append(f"History: {bitter_count} bitter brews → coarser")
            elif bright_count + flat_count > bitter_count:
                microns -= 30
                notes.append(f"History: {bright_count + flat_count} bright/flat brews → finer")

    grind_range = brewer.get("target_grind_microns", {"min": 300, "max": 1200})
    limits = {"min": grind_range["min"], "max": grind_range["max"], "fixed": False}
    microns = _clamp(microns, limits, chain["micron_delta"], "grind", "µm", notes)
    return microns, limits


def _temp_target(coffee_data, brewer, chain, notes):
    temp_param = brewer.get("parameters", {}).get("temp_c", {})

    # Fixed temp (e.g., Moccamaster): nothing to decide, and the chain's temp
    # delta cannot apply. It is a lever the dial-in must never pick — see
    # lever_headroom().
    if "fixed" in temp_param:
        fixed = temp_param["fixed"]
        return fixed, {"min": fixed, "max": fixed, "fixed": True}

    base = temp_param.get("default", 94)
    offset = (get_origin_temp_offset(coffee_data.get("origin", ""))
              + get_process_temp_offset(coffee_data.get("process", "")))
    temp = base + offset

    delta = chain["temp_delta_c"]
    if delta:
        temp += delta
        notes.append("Dial-in: {}{}°C".format("+" if delta > 0 else "-", abs(round(delta, 1))))

    limits = {"min": temp_param.get("min", 85), "max": temp_param.get("max", 100), "fixed": False}
    temp = _clamp(temp, limits, delta, "temperature", "°C", notes)
    return round(temp, 1), limits


def _ratio_target(coffee_data, brewer, chain, notes):
    ratio_param = brewer.get("parameters", {}).get("ratio") or {}
    base = ratio_param.get("default", 16)
    roast = coffee_data.get("roast", "medium")
    ratio = base + ROAST_RATIO_ADJUSTMENTS.get(roast, 0)

    delta = chain["ratio_delta"]
    if delta:
        ratio += delta
        notes.append("Dial-in: ratio {} to 1:{}".format(
            "stronger" if delta < 0 else "weaker", round(ratio, 1)))

    limits = {"min": ratio_param.get("min"), "max": ratio_param.get("max"), "fixed": False}
    ratio = _clamp(ratio, limits, delta, "ratio", "", notes)
    return round(ratio, 1), limits


def _clamp(value, limits, chain_delta, label, unit, notes):
    lo, hi = limits.get("min"), limits.get("max")
    clamped = value
    if hi is not None and clamped > hi:
        clamped = hi
    if lo is not None and clamped < lo:
        clamped = lo
    if clamped != value and chain_delta:
        notes.append("Dial-in: {} pinned at the brewer's limit ({}{}).".format(label, clamped, unit))
    return clamped
