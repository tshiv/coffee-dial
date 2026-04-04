"""
Brew recipe builders — generate method-specific instructions.

Each builder takes (brewer, coffee_data, target_microns, dose_g, water_g)
and returns a recipe dict with type-specific structure.
"""

import math

from .grind import get_origin_temp_offset, get_process_temp_offset


def _compute_temp_c(brewer, coffee_data):
    """Compute brew temperature in Celsius, applying origin/process offsets."""
    params = brewer.get("parameters", {})
    temp_param = params.get("temp_c", {})

    # Fixed temp (e.g., Moccamaster)
    if "fixed" in temp_param:
        return temp_param["fixed"]

    base = temp_param.get("default", 94)
    origin = coffee_data.get("origin", "")
    process = coffee_data.get("process", "")

    offset = get_origin_temp_offset(origin) + get_process_temp_offset(process)
    temp = base + offset

    # Clamp to brewer's range
    temp_min = temp_param.get("min", 85)
    temp_max = temp_param.get("max", 100)
    return round(max(temp_min, min(temp_max, temp)), 1)


def _c_to_f(temp_c):
    return round(temp_c * 9 / 5 + 32, 1)


def _get_ratio(brewer, coffee_data):
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


def _bloom_params(coffee_data):
    """Compute bloom parameters based on roast."""
    roast = coffee_data.get("roast", "medium")
    bloom_table = {
        "light":        {"bloom_ratio": 2.5, "bloom_dur": 45},
        "medium-light": {"bloom_ratio": 2.5, "bloom_dur": 40},
        "medium":       {"bloom_ratio": 2.0, "bloom_dur": 35},
        "medium-dark":  {"bloom_ratio": 2.0, "bloom_dur": 30},
        "dark":         {"bloom_ratio": 1.5, "bloom_dur": 25},
    }
    return bloom_table.get(roast, bloom_table["medium"])


# ─── Recipe Builders ──────────────────────────────────────────────────────────

def build_aiden_profile(brewer, coffee_data, target_microns, dose_g, water_g):
    """Fellow Aiden machine profile with all programmable parameters."""
    roast = coffee_data.get("roast", "medium")
    temp_c = _compute_temp_c(brewer, coffee_data)
    ratio = _get_ratio(brewer, coffee_data)
    bloom = _bloom_params(coffee_data)

    # Pulse count varies by roast
    pulse_table = {
        "light": {"pulses": 3, "pulse_int": 30},
        "medium-light": {"pulses": 3, "pulse_int": 28},
        "medium": {"pulses": 2, "pulse_int": 25},
        "medium-dark": {"pulses": 2, "pulse_int": 22},
        "dark": {"pulses": 1, "pulse_int": 20},
    }
    pulses = pulse_table.get(roast, pulse_table["medium"])

    return {
        "type": "aiden_profile",
        "temp_c": temp_c,
        "temp_f": _c_to_f(temp_c),
        "ratio": ratio,
        "dose_g": round(dose_g, 1),
        "water_g": round(water_g),
        "bloom_dur": bloom["bloom_dur"],
        "bloom_ratio": bloom["bloom_ratio"],
        "pulses": pulses["pulses"],
        "pulse_int": pulses["pulse_int"],
    }


def build_pour_over_steps(brewer, coffee_data, target_microns, dose_g, water_g):
    """Step-by-step pour-over recipe (V60, Chemex, Kalita, Stagg)."""
    temp_c = _compute_temp_c(brewer, coffee_data)
    ratio = _get_ratio(brewer, coffee_data)
    bloom = _bloom_params(coffee_data)
    bloom_water = round(dose_g * bloom["bloom_ratio"])

    total_water = round(water_g)
    remaining = total_water - bloom_water
    pour_1 = round(remaining * 0.55)
    pour_2 = remaining - pour_1

    steps = [
        {"action": "bloom", "water_g": bloom_water, "duration_s": bloom["bloom_dur"],
         "note": f"Pour {bloom_water}g in gentle circles. Wait {bloom['bloom_dur']}s."},
        {"action": "pour", "water_g": pour_1, "duration_s": 30,
         "note": f"Slow spiral pour {pour_1}g (total: {bloom_water + pour_1}g)."},
        {"action": "wait", "duration_s": 15, "note": "Let water draw down slightly."},
        {"action": "pour", "water_g": pour_2, "duration_s": 25,
         "note": f"Final pour {pour_2}g to reach {total_water}g total."},
    ]

    return {
        "type": "pour_over_steps",
        "temp_c": temp_c,
        "temp_f": _c_to_f(temp_c),
        "ratio": ratio,
        "dose_g": round(dose_g, 1),
        "water_g": total_water,
        "steps": steps,
        "target_total_time_s": bloom["bloom_dur"] + 30 + 15 + 25 + 60,
    }


def build_immersion_steps(brewer, coffee_data, target_microns, dose_g, water_g):
    """Immersion brew recipe (French Press, Clever Dripper)."""
    temp_c = _compute_temp_c(brewer, coffee_data)
    ratio = _get_ratio(brewer, coffee_data)

    params = brewer.get("parameters", {})
    steep_param = params.get("steep_time", {})
    steep_time = steep_param.get("default", 240)

    method = brewer.get("method", "immersion")
    is_clever = "clever" in brewer.get("name", "").lower()

    if is_clever:
        steps = [
            {"action": "add_water", "water_g": round(water_g),
             "note": f"Pour all {round(water_g)}g of water over grounds."},
            {"action": "stir", "duration_s": 10,
             "note": "Gentle stir to saturate all grounds."},
            {"action": "steep", "duration_s": steep_time,
             "note": f"Cover and steep for {steep_time // 60} min {steep_time % 60}s."},
            {"action": "release", "note": "Place on cup/server to release the valve and drain."},
        ]
    else:
        steps = [
            {"action": "add_water", "water_g": round(water_g),
             "note": f"Pour all {round(water_g)}g of water over grounds."},
            {"action": "stir", "duration_s": 10,
             "note": "Gentle stir to saturate all grounds."},
            {"action": "steep", "duration_s": steep_time,
             "note": f"Cover and steep for {steep_time // 60} minutes."},
            {"action": "press", "note": "Press plunger slowly and evenly."},
        ]

    return {
        "type": "immersion_steps",
        "temp_c": temp_c,
        "temp_f": _c_to_f(temp_c),
        "ratio": ratio,
        "dose_g": round(dose_g, 1),
        "water_g": round(water_g),
        "steep_time_s": steep_time,
        "steps": steps,
    }


def build_aeropress_steps(brewer, coffee_data, target_microns, dose_g, water_g):
    """AeroPress recipe — standard method."""
    temp_c = _compute_temp_c(brewer, coffee_data)
    ratio = _get_ratio(brewer, coffee_data)

    params = brewer.get("parameters", {})
    steep_time = params.get("steep_time", {}).get("default", 90)

    steps = [
        {"action": "setup", "note": "Place filter in cap, rinse with hot water, attach to chamber on mug."},
        {"action": "add_coffee", "note": f"Add {round(dose_g, 1)}g of ground coffee."},
        {"action": "add_water", "water_g": round(water_g),
         "note": f"Pour {round(water_g)}g of water at {_c_to_f(temp_c)}°F."},
        {"action": "stir", "duration_s": 10, "note": "Stir gently for 10 seconds."},
        {"action": "steep", "duration_s": steep_time,
         "note": f"Wait {steep_time} seconds total."},
        {"action": "press", "duration_s": 30,
         "note": "Press steadily for ~30 seconds. Stop when you hear a hiss."},
    ]

    return {
        "type": "aeropress_steps",
        "temp_c": temp_c,
        "temp_f": _c_to_f(temp_c),
        "ratio": ratio,
        "dose_g": round(dose_g, 1),
        "water_g": round(water_g),
        "steep_time_s": steep_time,
        "steps": steps,
    }


def build_simple_drip(brewer, coffee_data, target_microns, dose_g, water_g):
    """Simple automatic brewer — grind + dose is all you control."""
    temp_c = _compute_temp_c(brewer, coffee_data)
    ratio = _get_ratio(brewer, coffee_data)

    return {
        "type": "simple_drip",
        "temp_c": temp_c,
        "temp_f": _c_to_f(temp_c),
        "ratio": ratio,
        "dose_g": round(dose_g, 1),
        "water_g": round(water_g),
        "water_oz": round(water_g / 29.5735, 1),
        "note": "Grind size and dose are your main variables. Temperature is set by the machine.",
    }


def build_precision_drip(brewer, coffee_data, target_microns, dose_g, water_g):
    """Precision automatic brewer with temp/bloom control (e.g., Breville Precision Brewer)."""
    temp_c = _compute_temp_c(brewer, coffee_data)
    ratio = _get_ratio(brewer, coffee_data)
    bloom = _bloom_params(coffee_data)

    return {
        "type": "precision_drip",
        "temp_c": temp_c,
        "temp_f": _c_to_f(temp_c),
        "ratio": ratio,
        "dose_g": round(dose_g, 1),
        "water_g": round(water_g),
        "bloom_dur": bloom["bloom_dur"],
        "flow_rate": "medium",
        "note": "Use 'My Brew' mode. Set temperature and bloom time. Medium flow rate for most coffees.",
    }


# ─── Recipe Builder Dispatch ──────────────────────────────────────────────────

RECIPE_BUILDERS = {
    "aiden_profile": build_aiden_profile,
    "pour_over_steps": build_pour_over_steps,
    "immersion_steps": build_immersion_steps,
    "aeropress_steps": build_aeropress_steps,
    "simple_drip": build_simple_drip,
    "precision_drip": build_precision_drip,
}


def build_recipe(brewer, coffee_data, target_microns, dose_g, water_g):
    """Dispatch to the correct recipe builder based on brewer type."""
    recipe_type = brewer.get("recipe_type", "simple_drip")
    builder = RECIPE_BUILDERS.get(recipe_type, build_simple_drip)
    return builder(brewer, coffee_data, target_microns, dose_g, water_g)
