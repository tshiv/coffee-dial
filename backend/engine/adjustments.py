"""
Origin, process, and volume adjustments for brew recommendations.
These are applied as offsets to the base grind target and temperature.
"""

ORIGIN_ADJUSTMENTS = {
    "ethiopia":   {"temp_bias": +1, "grind_bias": 0},
    "kenya":      {"temp_bias": +1, "grind_bias": 0},
    "rwanda":     {"temp_bias": 0,  "grind_bias": 0},
    "burundi":    {"temp_bias": 0,  "grind_bias": 0},
    "colombia":   {"temp_bias": 0,  "grind_bias": 0},
    "brazil":     {"temp_bias": -2, "grind_bias": +1},
    "guatemala":  {"temp_bias": 0,  "grind_bias": 0},
    "sumatra":    {"temp_bias": -2, "grind_bias": +1},
    "indonesia":  {"temp_bias": -2, "grind_bias": +1},
    "panama":     {"temp_bias": 0,  "grind_bias": 0},
    "costa rica": {"temp_bias": 0,  "grind_bias": 0},
    "honduras":   {"temp_bias": -1, "grind_bias": 0},
    "peru":       {"temp_bias": 0,  "grind_bias": 0},
}

PROCESS_ADJUSTMENTS = {
    "washed":     {"temp_bias": +1, "grind_bias": 0},
    "natural":    {"temp_bias": -1, "grind_bias": +0.5},
    "honey":      {"temp_bias": 0,  "grind_bias": +0.5},
    "anaerobic":  {"temp_bias": -1, "grind_bias": +1},
    "wet-hulled": {"temp_bias": -1, "grind_bias": +1},
}


def get_origin_adjustment(origin):
    """Return (temp_bias, grind_bias) for the given origin string."""
    origin_lower = (origin or "").lower()
    for key, adj in ORIGIN_ADJUSTMENTS.items():
        if key in origin_lower:
            return adj["temp_bias"], adj["grind_bias"]
    return 0, 0


def get_process_adjustment(process):
    """Return (temp_bias, grind_bias) for the given process string."""
    process_lower = (process or "").lower()
    for key, adj in PROCESS_ADJUSTMENTS.items():
        if key in process_lower:
            return adj["temp_bias"], adj["grind_bias"]
    return 0, 0


def get_volume_grind_offset(oz):
    """Larger batches need slightly coarser grinds."""
    if oz <= 10:
        return -0.5
    if oz <= 16:
        return 0
    if oz <= 22:
        return +0.5
    return +1.0
