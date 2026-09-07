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


# ─── Web-search-backed calls ─────────────────────────────────────────────────

WEB_SEARCH_MODEL = "claude-opus-5"
WEB_SEARCH_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 4},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 3},
]
# A lookup, not a hard reasoning problem: medium effort keeps the searched
# turn to a minute or two instead of several.
WEB_SEARCH_EFFORT = "medium"
# Searched turns are slow (several round trips on Anthropic's side); a first
# live run took longer than two minutes and timed out at the old 120s.
WEB_SEARCH_TIMEOUT_S = 300
# The server-side search loop can pause after its iteration limit; resume a
# bounded number of times rather than returning a half-finished answer.
MAX_CONTINUATIONS = 3


def call_anthropic_with_web_search(prompt, api_key, system_prompt, timeout_s=WEB_SEARCH_TIMEOUT_S):
    """Ask Claude to answer with real web searches behind it.

    Returns (parsed_json, sources, error_string). `sources` is the list of
    {url, title} the model actually searched or fetched, so the caller can
    show where an answer came from rather than trusting the model's own
    claim of a source.
    """
    messages = [{"role": "user", "content": prompt}]
    sources = []
    try:
        for _ in range(MAX_CONTINUATIONS + 1):
            data = _post_anthropic({
                "model": WEB_SEARCH_MODEL,
                "max_tokens": 16000,
                "system": system_prompt,
                "tools": WEB_SEARCH_TOOLS,
                "output_config": {"effort": WEB_SEARCH_EFFORT},
                "messages": messages,
                # Re-run on a substitute model if a safety classifier declines
                # the request, instead of surfacing the refusal.
                "fallbacks": "default",
            }, api_key, timeout_s, betas="server-side-fallback-2026-07-01")

            sources.extend(_sources_from_content(data.get("content") or []))
            stop = data.get("stop_reason")
            if stop == "pause_turn":
                # Echo the paused assistant turn back unchanged; the server
                # picks up where it left off.
                messages = messages + [{"role": "assistant", "content": data["content"]}]
                continue
            if stop == "refusal":
                return None, sources, "The model declined this request."
            text = "".join(
                b.get("text", "") for b in data.get("content") or [] if b.get("type") == "text"
            )
            parsed = extract_json_object(text)
            if parsed is None:
                return None, sources, "Search finished but returned no recipe JSON."
            return parsed, _dedupe_sources(sources), None
        return None, sources, "Search did not finish after several continuations."
    except Exception as e:
        return None, sources, f"Anthropic API error: {str(e)}"


def _post_anthropic(payload, api_key, timeout_s, betas=None):
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    if betas:
        headers["anthropic-beta"] = betas
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read())


def _sources_from_content(content):
    """URLs the model actually touched, from web search and fetch result blocks.

    A search error comes back as a single object in `content` instead of a
    list of results; skip those rather than indexing into them.
    """
    found = []
    for block in content:
        kind = block.get("type")
        inner = block.get("content")
        if kind == "web_search_tool_result" and isinstance(inner, list):
            for r in inner:
                if isinstance(r, dict) and r.get("url"):
                    found.append({"url": r["url"], "title": r.get("title") or ""})
        elif kind == "web_fetch_tool_result" and isinstance(inner, dict) and inner.get("url"):
            doc = inner.get("content") or {}
            found.append({"url": inner["url"], "title": (doc.get("title") if isinstance(doc, dict) else "") or ""})
    return found


def _dedupe_sources(sources):
    seen, out = set(), []
    for s in sources:
        if s["url"] not in seen:
            seen.add(s["url"])
            out.append(s)
    return out


def extract_json_object(text):
    """The first complete JSON object in a block of prose, or None.

    A search-backed answer often wraps its JSON in a sentence or a code
    fence; take the outermost braces and parse what is inside.
    """
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


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
