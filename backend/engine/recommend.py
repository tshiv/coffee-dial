"""
Recommendation engine — computes grind settings and brew profiles.

Pipeline:
  1. Determine target microns (roast + brew method + adjustments)
  2. Translate to grinder-specific setting
  3. Build brew recipe for the selected brewer
  4. Apply history-based learning
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
            learning below, which stays as the prior for a coffee you have not
            brewed yet.

    Returns:
        dict with grinder_setting, grinder_display, target_microns, recipe, bias_notes
    """
    roast = coffee_data.get("roast", "medium")
    origin = coffee_data.get("origin", "")
    process = coffee_data.get("process", "")
    extraction_type = brewer.get("extraction_type", "percolation")

    bias_notes = []

    # Step 1: Target microns
    base_microns = get_base_target_microns(roast, extraction_type)
    micron_offset = 0

    origin_offset = get_origin_micron_offset(origin)
    if origin_offset != 0:
        micron_offset += origin_offset
        origin_name = origin.split(",")[0].strip().title() if origin else ""
        bias_notes.append(f"{origin_name} origin: {'coarser' if origin_offset > 0 else 'finer'}")

    process_offset = get_process_micron_offset(process)
    if process_offset != 0:
        micron_offset += process_offset
        bias_notes.append(f"{process} process: coarser grind")

    volume_offset = get_volume_micron_offset(oz)
    if volume_offset != 0:
        micron_offset += volume_offset
        bias_notes.append(f"{oz}oz volume adjustment")

    # Step 2: Dial-in chain for this coffee, else aggregate history learning.
    # Both work in micron space, so either survives a change of grinder.
    has_chain = bool(chain) and any(
        chain.get(k) for k in ("micron_delta", "temp_delta_c", "ratio_delta")
    )

    if has_chain:
        micron_delta = chain.get("micron_delta") or 0
        if micron_delta:
            micron_offset += micron_delta
            bias_notes.append(
                "Dial-in: {} microns {}".format(
                    abs(round(micron_delta)),
                    "coarser" if micron_delta > 0 else "finer",
                )
            )

    similar = [b for b in history_rows if b["roast"] == roast]
    if similar and not has_chain:
        bitter_count = sum(1 for b in similar if b["rating"] == "bitter")
        bright_count = sum(1 for b in similar if b["rating"] == "bright")
        flat_count = sum(1 for b in similar if b["rating"] == "flat")
        if bitter_count > bright_count + flat_count:
            micron_offset += 30
            bias_notes.append(f"History: {bitter_count} bitter brews → coarser")
        elif bright_count + flat_count > bitter_count:
            micron_offset -= 30
            bias_notes.append(f"History: {bright_count + flat_count} bright/flat brews → finer")

    target_microns = base_microns + micron_offset

    # Clamp to brewer's suitable range
    grind_range = brewer.get("target_grind_microns", {"min": 300, "max": 1200})
    target_microns = max(grind_range["min"], min(grind_range["max"], target_microns))

    # Step 3: Translate to grinder setting
    grinder_setting = microns_to_setting(grinder, target_microns)
    grinder_display = format_grind_setting(grinder, grinder_setting)

    # Step 4: Compute dose from ratio
    water_g = oz * 29.5735
    ratio = _get_recipe_ratio(brewer, coffee_data)

    if has_chain:
        ratio_delta = chain.get("ratio_delta") or 0
        if ratio_delta:
            ratio = round(ratio + ratio_delta, 1)
            bias_notes.append(
                "Dial-in: ratio {} to 1:{}".format(
                    "stronger" if ratio_delta < 0 else "weaker", ratio
                )
            )

    dose_g = water_g / ratio

    # Step 5: Build brew recipe
    recipe = build_recipe(brewer, coffee_data, target_microns, dose_g, water_g)

    # Temperature is decided inside the recipe builder, so the chain's
    # temperature delta is applied to the finished recipe rather than threaded
    # through every brewer-specific builder.
    if has_chain:
        temp_delta = chain.get("temp_delta_c") or 0
        if temp_delta and recipe.get("temp_c") is not None:
            recipe["temp_c"] = round(recipe["temp_c"] + temp_delta, 1)
            recipe["temp_f"] = round(recipe["temp_c"] * 9 / 5 + 32, 1)
            bias_notes.append(
                "Dial-in: {} {}°C".format(
                    "+" if temp_delta > 0 else "-", abs(round(temp_delta, 1))
                )
            )

    return {
        "grinder_name": grinder["name"],
        "grinder_setting": grinder_setting,
        "grinder_display": grinder_display,
        "target_microns": round(target_microns),
        "brewer_name": brewer["name"],
        "dose_g": round(dose_g, 1),
        "water_g": round(water_g),
        "water_oz": oz,
        "ratio": ratio,
        "recipe": recipe,
        "bias_notes": bias_notes,
    }


def _get_recipe_ratio(brewer, coffee_data):
    """Determine brew ratio based on brewer defaults and roast level."""
    params = brewer.get("parameters", {})
    ratio_param = params.get("ratio", {})
    base_ratio = ratio_param.get("default", 16)

    roast = coffee_data.get("roast", "medium")
    roast_adjustments = {
        "light": +0.5,
        "medium-light": +0.25,
        "medium": 0,
        "medium-dark": -0.25,
        "dark": -0.5,
    }
    return round(base_ratio + roast_adjustments.get(roast, 0), 1)
