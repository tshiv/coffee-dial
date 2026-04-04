"""
Fetch and convert Fellow Aiden shared brew profiles from brew.link URLs.

Uses Fellow's shared profile API. Tries unauthenticated first,
falls back to authenticated if Fellow credentials are configured.
"""

import json
import re
import urllib.request

FELLOW_API_BASE = "https://l8qtmnc692.execute-api.us-west-2.amazonaws.com/v1"
BREWLINK_REGEX = r'(?:.*?/p/)?([a-zA-Z0-9]+)/?$'

# Fields added by the server that we strip from imported profiles
SERVER_FIELDS = [
    "id", "createdAt", "deletedAt", "lastUsedTime", "sharedFrom",
    "isDefaultProfile", "instantBrew", "folder", "duration",
    "lastGBQuantity", "deviceId", "synced", "updatedAt",
    "overallTemperature", "lastGBQuantity",
]


def _extract_brew_id(link):
    """Extract the brew ID from a brew.link URL or raw ID string."""
    match = re.search(BREWLINK_REGEX, link.strip())
    if not match:
        return None
    return match.group(1)


def fetch_brewlink_profile(link, settings=None):
    """Fetch a shared Aiden profile from a brew.link URL.

    Tries unauthenticated request first. If 401 and Fellow credentials
    are available in settings, retries with authentication.

    Returns:
        (profile_dict, error_string)
    """
    brew_id = _extract_brew_id(link)
    if not brew_id:
        return None, "Invalid brew.link URL format."

    url = f"{FELLOW_API_BASE}/shared/{brew_id}"

    # Try unauthenticated first
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Fellow/5 CFNetwork/1568.300.101 Darwin/24.2.0"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            profile = json.loads(resp.read())
            # Strip server-side fields
            for field in SERVER_FIELDS:
                profile.pop(field, None)
            return profile, None
    except urllib.error.HTTPError as e:
        if e.code != 401:
            return None, f"Fellow API error: HTTP {e.code}"
    except Exception as e:
        return None, f"Error fetching brew.link: {str(e)}"

    # 401 — try authenticated with Fellow credentials
    if not settings:
        return None, "Brew.link requires authentication. Add Fellow credentials in Settings."

    email = settings.get("fellow_email")
    password = settings.get("fellow_password")
    if not email or not password:
        return None, "Brew.link requires authentication. Add Fellow credentials in Settings."

    try:
        # Authenticate
        auth_url = f"{FELLOW_API_BASE}/auth/login"
        auth_payload = json.dumps({"email": email, "password": password}).encode()
        auth_req = urllib.request.Request(auth_url, data=auth_payload, headers={
            "Content-Type": "application/json",
            "User-Agent": "Fellow/5 CFNetwork/1568.300.101 Darwin/24.2.0"
        }, method="POST")
        with urllib.request.urlopen(auth_req, timeout=10) as auth_resp:
            auth_data = json.loads(auth_resp.read())

        token = auth_data.get("accessToken")
        if not token:
            return None, "Fellow authentication failed."

        # Retry with auth token
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Fellow/5 CFNetwork/1568.300.101 Darwin/24.2.0"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            profile = json.loads(resp.read())
            for field in SERVER_FIELDS:
                profile.pop(field, None)
            return profile, None

    except Exception as e:
        return None, f"Error fetching brew.link (authenticated): {str(e)}"


def brewlink_to_community_recipe(profile):
    """Convert a Fellow Aiden shared profile to the community recipe format.

    Maps Fellow fields to the community recipe schema and preserves
    the raw Aiden profile for direct push to the Aiden brewer.

    Returns a community recipe dict.
    """
    title = profile.get("title", "Imported Aiden Profile")
    ratio = profile.get("ratio", 16)
    temp_c = profile.get("bloomTemperature", 94)

    # Compute approximate coffee and water amounts from ratio (assuming 20oz default)
    water_g = 590  # ~20oz
    coffee_g = round(water_g / ratio, 1)

    # Build steps from Aiden profile parameters
    steps = []
    step_order = 1

    if profile.get("bloomEnabled", True):
        bloom_dur = profile.get("bloomDuration", 40)
        bloom_ratio = profile.get("bloomRatio", 2.5)
        steps.append({
            "order": step_order,
            "action": "bloom",
            "duration_s": bloom_dur,
            "description": f"Machine blooms with {bloom_ratio}x coffee weight at {temp_c}\u00b0C."
        })
        step_order += 1

    pulses_enabled = profile.get("ssPulsesEnabled", False)
    pulses_num = profile.get("ssPulsesNumber", 1)
    pulses_int = profile.get("ssPulsesInterval", 25)
    pulse_temps = profile.get("ssPulseTemperatures", [temp_c])

    if pulses_enabled and pulses_num > 1:
        steps.append({
            "order": step_order,
            "action": "pour",
            "duration_s": pulses_num * pulses_int,
            "description": f"{pulses_num} single-serve pulses at {pulses_int}s intervals."
        })
    else:
        steps.append({
            "order": step_order,
            "action": "pour",
            "duration_s": 180,
            "description": f"Single brew pulse at {temp_c}\u00b0C."
        })

    # Build the community recipe
    recipe = {
        "id": f"brewlink_{title.lower().replace(' ', '_')[:30]}",
        "title": title,
        "author": "Shared via brew.link",
        "source_url": None,
        "attribution": "Imported from Fellow Aiden brew.link",
        "brew_method": "drip",
        "compatible_brewers": ["fellow_aiden"],
        "coffee_amount_g": coffee_g,
        "water_amount_g": water_g,
        "ratio": ratio,
        "water_temp_c": temp_c,
        "grind_size": "medium",
        "total_time_s": sum(s.get("duration_s", 0) for s in steps),
        "steps": steps,
        "notes": f"Imported Aiden profile: {title}",
    }

    # Preserve the raw Aiden profile for direct push
    aiden_profile = {}
    aiden_fields = [
        "profileType", "ratio", "bloomEnabled", "bloomRatio", "bloomDuration",
        "bloomTemperature", "ssPulsesEnabled", "ssPulsesNumber", "ssPulsesInterval",
        "ssPulseTemperatures", "batchPulsesEnabled", "batchPulsesNumber",
        "batchPulsesInterval", "batchPulseTemperatures",
    ]
    for field in aiden_fields:
        if field in profile:
            aiden_profile[field] = profile[field]

    if aiden_profile:
        recipe["aiden_profile"] = aiden_profile

    return recipe
