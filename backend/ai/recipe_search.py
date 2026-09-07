"""
AI-powered roaster recipe search.

Uses AI to find brew recommendations from specific roasters,
returning structured recipe data in the community recipe format.
"""

from .parsing import call_ai_with_prompt, call_anthropic_with_web_search

# How a recipe was obtained. Shown to the brewer next to the confidence, so
# "high" from a real page and "high" from memory never look the same.
SOURCE_WEB = "roaster_web"       # searched the web, ideally the roaster's own guide
SOURCE_RECALL = "model_recall"   # the model's memory only, no search

WEB_SEARCH_PROMPT = """You are a specialty coffee expert helping a home brewer find the brew recipe a roaster actually publishes for their coffee.

You have web search and web fetch. Use them. Priority order:
1. The roaster's own brew guide for this exact coffee (product page, brew guide, blog post, recipe card).
2. The roaster's general brew guide for this brew method or brewer.
3. A reputable third-party recipe for this specific coffee or roaster (a well-known coffee YouTuber, a community profile site such as brew.link or brewshare.coffee).
Only if none of those exist, fall back to a sensible recipe for this coffee's style and say so.

Return ONE JSON object and nothing else after it, matching this schema:
{
  "id": "auto_<roaster>_<coffee>",
  "title": "Recipe name as the roaster calls it",
  "author": "<roaster or author name>",
  "source_url": "URL of the page the recipe came from, or null",
  "attribution": "Credit: <roaster or author>",
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
  "notes": "What makes this recipe distinctive, and which page it came from",
  "confidence": "<high|medium|low>",
  "confidence_reason": "One sentence on what you found and did not find"
}

Confidence rules, strictly:
- "high": you fetched a page from the roaster (or the named author) that gives this recipe's numbers for this coffee or this brew method. source_url must be that page.
- "medium": you found the roaster's general guidance or a third-party recipe for this coffee, and adapted it. source_url is the page you adapted from.
- "low": you found nothing specific and are proposing a recipe from the coffee's style. source_url must be null.
- Never report a source_url you did not actually open.
- Temperatures in Celsius. Numbers, not strings, for numeric fields."""

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

    # A real search beats recall whenever an Anthropic key is available; the
    # OpenAI path here is chat-completions only and cannot browse.
    if settings.get("anthropic_key"):
        result, sources, err = call_anthropic_with_web_search(
            user_prompt, settings["anthropic_key"], WEB_SEARCH_PROMPT)
        source_kind = SOURCE_WEB
    else:
        result, err = call_ai_with_prompt(user_prompt, RECIPE_SEARCH_PROMPT, settings)
        sources = []
        source_kind = SOURCE_RECALL
    if err:
        return None, err
    if not isinstance(result, dict):
        return None, "Recipe search returned something that was not a recipe."

    result.setdefault("confidence", "low")
    result.setdefault("confidence_reason", "")
    result.setdefault("attribution", f"Credit: {roaster}")
    result.setdefault("author", roaster)
    result.setdefault("brew_method", brew_method)
    result["source_kind"] = source_kind
    result["sources"] = sources
    # A source_url the model never opened is a claim, not a source.
    if source_kind == SOURCE_WEB and result.get("source_url"):
        opened = {s["url"] for s in sources}
        if result["source_url"] not in opened:
            result["source_url_unverified"] = True
    return result, None
