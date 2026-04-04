"""
Load grinder and brewer definitions from JSON catalogs.
"""

import json
import os

_DIR = os.path.dirname(__file__)
_grinders = None
_brewers = None


def _load_json(filename):
    path = os.path.join(_DIR, filename)
    with open(path) as f:
        return json.load(f)


def get_grinders():
    global _grinders
    if _grinders is None:
        _grinders = _load_json("grinders.json")
    return _grinders


def get_brewers():
    global _brewers
    if _brewers is None:
        _brewers = _load_json("brewers.json")
    return _brewers


def get_grinder(grinder_id):
    grinders = get_grinders()
    return grinders.get(grinder_id)


def get_brewer(brewer_id):
    brewers = get_brewers()
    return brewers.get(brewer_id)


def list_equipment():
    """Return a summary of all available equipment for the API."""
    grinders = get_grinders()
    brewers = get_brewers()

    return {
        "grinders": [
            {
                "id": gid,
                "name": g["name"],
                "type": g["type"],
                "unit": g["settings"]["unit"],
                "range": f"{g['settings']['min']}-{g['settings']['max']}",
            }
            for gid, g in grinders.items()
        ],
        "brewers": [
            {
                "id": bid,
                "name": b["name"],
                "type": b["type"],
                "method": b["method"],
                "capacity_oz": b.get("capacity_oz"),
            }
            for bid, b in brewers.items()
        ],
    }
