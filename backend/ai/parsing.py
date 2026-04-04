"""
AI-powered coffee bag parsing using Anthropic or OpenAI.
"""

import json
import re
import urllib.request

SYSTEM_PROMPT = """You are an expert specialty coffee consultant with deep knowledge of coffee origins, processing methods, roast levels, and brewing science.

When given coffee bag text or a coffee name, extract and infer the following as JSON:
{
  "coffee_name": "short name for this coffee",
  "roaster": "roaster name if mentioned",
  "origin": "country or region",
  "process": "washed | natural | honey | anaerobic | wet-hulled | other",
  "roast": "light | medium-light | medium | medium-dark | dark",
  "altitude_m": number or null,
  "variety": "coffee variety if mentioned",
  "flavor_notes": ["array", "of", "tasting", "notes"],
  "confidence": "high | medium | low",
  "reasoning": "1-2 sentence explanation of how you determined the roast level and key parameters"
}

Rules:
- If the text mentions specific flavor notes (jasmine, citrus, blueberry = light; chocolate, caramel = medium; smoky, earthy = dark), use those to infer roast if not stated
- Specialty coffee from Africa (Ethiopia, Kenya, Rwanda) defaults to light unless stated otherwise
- Bottomless subscriptions default to specialty/light-medium unless stated otherwise
- Natural process coffees are slightly more soluble than washed; account for this in your reasoning
- Be conservative — if uncertain between light and medium-light, say medium-light
- Always return valid JSON, nothing else"""


def call_ai_with_prompt(user_prompt, system_prompt, settings):
    """Generic AI call with a custom system prompt. Returns (parsed_json, error_string)."""
    provider = settings.get("ai_provider", "anthropic")

    if provider == "openai" and settings.get("openai_key"):
        return _call_openai(user_prompt, settings["openai_key"], system_prompt)
    elif settings.get("anthropic_key"):
        return _call_anthropic(user_prompt, settings["anthropic_key"], system_prompt)
    elif settings.get("openai_key"):
        return _call_openai(user_prompt, settings["openai_key"], system_prompt)
    else:
        return None, "No AI API key configured. Add one in Settings."


def call_ai(prompt, settings):
    """Parse coffee bag text using the coffee parsing system prompt."""
    return call_ai_with_prompt(prompt, SYSTEM_PROMPT, settings)


def _call_anthropic(prompt, api_key, system_prompt=SYSTEM_PROMPT):
    try:
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            text = data["content"][0]["text"].strip()
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            return json.loads(text), None
    except Exception as e:
        return None, f"Anthropic API error: {str(e)}"


def _call_openai(prompt, api_key, system_prompt=SYSTEM_PROMPT):
    try:
        payload = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 1024,
        }).encode()

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            text = data["choices"][0]["message"]["content"].strip()
            return json.loads(text), None
    except Exception as e:
        return None, f"OpenAI API error: {str(e)}"
