"""
Load and search community brew recipes from the curated JSON catalog.
"""

import copy
import json
import os

_DIR = os.path.dirname(__file__)
_recipes = None


def get_community_recipes():
    """Load all community recipes from recipes.json. Cached after first load."""
    global _recipes
    if _recipes is None:
        path = os.path.join(_DIR, "recipes.json")
        with open(path) as f:
            _recipes = json.load(f)
    return _recipes


def search_recipes(brewer_id=None, brew_method=None):
    """Return community recipes matching the given brewer or method.

    Matching logic:
      1. If brewer_id provided, include recipes where brewer_id is in compatible_brewers
      2. Also include recipes matching the brewer's brew_method
      3. Sort: exact brewer match first, then method match
      4. Deduplicate (a recipe might match both)

    Returns list of recipe dicts.
    """
    recipes = get_community_recipes()
    brewer_matches = []
    method_matches = []
    seen = set()

    for r in recipes:
        is_brewer_match = brewer_id and brewer_id in r.get("compatible_brewers", [])
        is_method_match = brew_method and r.get("brew_method") == brew_method

        if is_brewer_match:
            brewer_matches.append(r)
            seen.add(r["id"])
        elif is_method_match and r["id"] not in seen:
            method_matches.append(r)

    return brewer_matches + method_matches


def get_recipe_by_id(recipe_id):
    """Return a single recipe by its ID, or None."""
    recipes = get_community_recipes()
    for r in recipes:
        if r["id"] == recipe_id:
            return r
    return None


def scale_recipe(recipe, target_water_g):
    """Scale a community recipe to a target water amount.

    Adjusts: coffee_amount_g, water_amount_g, and each step's water_g.
    Preserves: ratio, water_temp_c, grind_size, step durations, notes.

    Returns a new dict (does not mutate original).
    """
    orig_water = recipe.get("water_amount_g", 250)
    if orig_water <= 0:
        return copy.deepcopy(recipe)

    factor = target_water_g / orig_water
    scaled = copy.deepcopy(recipe)

    scaled["water_amount_g"] = round(target_water_g)
    scaled["coffee_amount_g"] = round(recipe.get("coffee_amount_g", 15) * factor, 1)

    # Scale water amounts in steps
    for step in scaled.get("steps", []):
        if "water_g" in step:
            step["water_g"] = round(step["water_g"] * factor)

    # Mark as scaled
    scaled["_scaled"] = True
    scaled["_original_water_g"] = orig_water

    return scaled
