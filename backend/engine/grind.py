"""
Universal grind mapping engine.

Converts between target microns and grinder-specific settings.
Determines base grind targets per brew method and roast level.

NOTE: Micron values are approximate and based on manufacturer specs
and community measurements. They vary by burr wear, alignment, and
bean hardness. Contributions and corrections are welcome.
"""

# Base target microns by (roast_level, extraction_type)
# These are starting points before origin/process/volume adjustments.
GRIND_TARGETS = {
    # Percolation (V60, Kalita, drip machines, Chemex)
    ("light", "percolation"):        550,
    ("medium-light", "percolation"): 625,
    ("medium", "percolation"):       700,
    ("medium-dark", "percolation"):  775,
    ("dark", "percolation"):         850,

    # Immersion (French Press)
    ("light", "immersion"):        850,
    ("medium-light", "immersion"): 925,
    ("medium", "immersion"):       1000,
    ("medium-dark", "immersion"):  1050,
    ("dark", "immersion"):         1100,

    # Immersion-fine (AeroPress — pressure immersion, finer grind)
    ("light", "immersion_fine"):        400,
    ("medium-light", "immersion_fine"): 430,
    ("medium", "immersion_fine"):       460,
    ("medium-dark", "immersion_fine"):  500,
    ("dark", "immersion_fine"):         540,

    # Immersion-filtered (Clever Dripper — paper-filtered immersion, medium grind)
    ("light", "immersion_filtered"):        550,
    ("medium-light", "immersion_filtered"): 600,
    ("medium", "immersion_filtered"):       650,
    ("medium-dark", "immersion_filtered"):  700,
    ("dark", "immersion_filtered"):         750,
}

# Micron offsets for origin (replaces the old grind_bias system)
ORIGIN_MICRON_OFFSETS = {
    "ethiopia":   0,
    "kenya":      0,
    "rwanda":     0,
    "burundi":    0,
    "colombia":   0,
    "brazil":     +50,
    "guatemala":  0,
    "sumatra":    +50,
    "indonesia":  +50,
    "panama":     0,
    "costa rica": 0,
    "honduras":   0,
    "peru":       0,
}

# Micron offsets for processing method
PROCESS_MICRON_OFFSETS = {
    "washed":     0,
    "natural":    +30,
    "honey":      +30,
    "anaerobic":  +60,
    "wet-hulled": +60,
}

# Temperature adjustments remain in Celsius (applied to brew temp)
ORIGIN_TEMP_OFFSETS = {
    "ethiopia": +1, "kenya": +1, "brazil": -2, "sumatra": -2,
    "indonesia": -2, "honduras": -1,
}

PROCESS_TEMP_OFFSETS = {
    "washed": +1, "natural": -1, "anaerobic": -1, "wet-hulled": -1,
}


def get_base_target_microns(roast, extraction_type):
    """Get the base grind target in microns for a roast + extraction type."""
    key = (roast or "medium", extraction_type or "percolation")
    return GRIND_TARGETS.get(key, GRIND_TARGETS[("medium", "percolation")])


def get_origin_micron_offset(origin):
    """Return micron offset for the given origin."""
    origin_lower = (origin or "").lower()
    for key, offset in ORIGIN_MICRON_OFFSETS.items():
        if key in origin_lower:
            return offset
    return 0


def get_process_micron_offset(process):
    """Return micron offset for the given process."""
    process_lower = (process or "").lower()
    for key, offset in PROCESS_MICRON_OFFSETS.items():
        if key in process_lower:
            return offset
    return 0


def get_volume_micron_offset(oz):
    """Larger batches need slightly coarser grinds."""
    if oz <= 10:
        return -30
    if oz <= 16:
        return 0
    if oz <= 22:
        return +30
    return +50


def get_origin_temp_offset(origin):
    origin_lower = (origin or "").lower()
    for key, offset in ORIGIN_TEMP_OFFSETS.items():
        if key in origin_lower:
            return offset
    return 0


def get_process_temp_offset(process):
    process_lower = (process or "").lower()
    for key, offset in PROCESS_TEMP_OFFSETS.items():
        if key in process_lower:
            return offset
    return 0


def microns_to_setting(grinder, target_microns):
    """Convert a target micron value to a grinder-specific setting.

    Uses linear interpolation on micron_map or micron_formula.
    Returns the setting as a number (int for stepped, float for stepless).
    """
    if "micron_formula" in grinder:
        formula = grinder["micron_formula"]
        base = formula["base_microns"]
        per_step = formula["microns_per_step"]
        raw = (target_microns - base) / per_step
        setting = round(raw)
        return max(grinder["settings"]["min"], min(grinder["settings"]["max"], setting))

    if "micron_map" in grinder:
        mmap = grinder["micron_map"]
        # mmap is [[setting, microns], ...] sorted by setting

        # Exact or beyond range
        if target_microns <= mmap[0][1]:
            return mmap[0][0]
        if target_microns >= mmap[-1][1]:
            return mmap[-1][0]

        # Linear interpolation between two nearest points
        for i in range(len(mmap) - 1):
            s1, m1 = mmap[i]
            s2, m2 = mmap[i + 1]
            if m1 <= target_microns <= m2:
                frac = (target_microns - m1) / (m2 - m1)
                raw = s1 + frac * (s2 - s1)
                step = grinder["settings"].get("step", 1)
                return round(raw / step) * step

    # Fallback: return midpoint
    return (grinder["settings"]["min"] + grinder["settings"]["max"]) // 2


def format_grind_setting(grinder, setting):
    """Format a grind setting for display (e.g., 'Setting 4' or '26 clicks')."""
    unit = grinder["settings"]["unit"]
    if unit == "clicks":
        return f"{setting} clicks"
    return f"Setting {setting}"
