"""
AI-powered roaster recipe search.

Uses AI to find brew recommendations from specific roasters,
returning structured recipe data in the community recipe format.
"""

from .parsing import call_ai_with_prompt

RECIPE_SEARCH_PROMPT = """You are a specialty coffee expert with deep knowledge of roaster brew guides, published recipes, and community brewing techniques.

Given a roaster name, coffee name, and brew method, search your knowledge for the roaster's recommended brew recipe. Return a JSON object matching this exact schema:

{
  "id": "auto_<roaster>_<coffee>",
  "title": "Roaster's recommended recipe name",
  "author": "<roaster name>",
  "source_url": "URL to the roaster's brew guide page, or null if unknown",
  "attribution": "Credit: <roaster name>",
  "brew_method": "<pour_over|immersion|aeropress|drip>",
  "coffee_amount_g": <number>,
  "water_amount_g": <number>,
  "ratio": <number>,
  "water_temp_c": <number>,
  "grind_size": "<description>",
  "total_time_s": <number>,
  "steps": [
    {"order": 1, "action": "<bloom|pour|wait|stir|steep|press|drawdown|swirl|add_water|setup|release>", "water_g": <number or omit>, "duration_s": <number>, "description": "<instruction>"}
  ],
  "notes": "Brief summary of what makes this recipe distinctive",
  "confidence": "<high|medium|low>",
  "confidence_reason": "Explanation of confidence level"
}

Rules:
- confidence "high": You know this roaster publishes a specific brew guide and you can recall its exact parameters
- confidence "medium": You know the roaster's general approach but are estimating specific numbers
- confidence "low": You're inferring a recipe based on the coffee's characteristics and general best practices
- If the roaster has a well-known brew guide page, include the source_url
- If you don't know the specific coffee, still provide a recipe based on the roaster's general style and the brew method
- Temperatures must be in Celsius
- Always return valid JSON, nothing else
- Do NOT hallucinate specific parameters — if uncertain, use standard values and set confidence to "low"
- For the brew_method field, use: "pour_over" for V60/Chemex/Kalita/Stagg, "immersion" for French Press/Clever, "aeropress" for AeroPress, "drip" for automatic brewers"""


def search_roaster_recipe(roaster, coffee_name, brew_method, brewer_name, settings):
    """Search AI knowledge for a roaster's recommended brew recipe.

    Args:
        roaster: roaster name (e.g. "Counter Culture")
        coffee_name: coffee name (e.g. "Hologram"), can be empty
        brew_method: brew method (e.g. "pour_over")
        brewer_name: specific brewer (e.g. "Hario V60 02")
        settings: app settings dict with API keys

    Returns:
        (recipe_dict, error_string) — recipe_dict follows community recipe schema
    """
    parts = [f"Roaster: {roaster}"]
    if coffee_name:
        parts.append(f"Coffee: {coffee_name}")
    parts.append(f"Brew method: {brew_method}")
    if brewer_name:
        parts.append(f"Brewer: {brewer_name}")

    user_prompt = "\n".join(parts)
    user_prompt += "\n\nFind this roaster's recommended brew recipe for this method. If they publish a specific brew guide, use those exact parameters."

    result, err = call_ai_with_prompt(user_prompt, RECIPE_SEARCH_PROMPT, settings)
    if err:
        return None, err

    # Ensure required fields exist
    if result and isinstance(result, dict):
        result.setdefault("confidence", "low")
        result.setdefault("attribution", f"Credit: {roaster}")
        result.setdefault("author", roaster)
        result.setdefault("brew_method", brew_method)

    return result, None
