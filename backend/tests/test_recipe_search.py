"""Roaster recipe search: provenance, JSON extraction, and the cache route.
No network — the AI calls are stubbed."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai import parsing, recipe_search  # noqa: E402


# ─── Pulling a recipe out of a searched answer ────────────────────────────────

def test_extract_json_object_ignores_prose_and_fences():
    text = 'Here is what I found:\n```json\n{"ratio": 16, "steps": []}\n```\nHope that helps.'
    assert parsing.extract_json_object(text) == {"ratio": 16, "steps": []}


def test_extract_json_object_rejects_non_objects_and_garbage():
    assert parsing.extract_json_object("[1, 2]") is None
    assert parsing.extract_json_object("no json here") is None
    assert parsing.extract_json_object("{not json}") is None
    assert parsing.extract_json_object("") is None


def test_sources_come_from_search_and_fetch_blocks_only():
    content = [
        {"type": "text", "text": "thinking..."},
        {"type": "server_tool_use", "name": "web_search", "input": {"query": "x"}},
        {"type": "web_search_tool_result", "content": [
            {"type": "web_search_result", "url": "https://roaster.example/guide", "title": "Brew Guide"},
            {"type": "web_search_result", "url": "https://other.example", "title": ""},
        ]},
        # An errored search is an object, not a list — must not blow up.
        {"type": "web_search_tool_result", "content": {"type": "web_search_tool_result_error",
                                                       "error_code": "max_uses_exceeded"}},
        {"type": "web_fetch_tool_result", "content": {
            "type": "web_fetch_result", "url": "https://roaster.example/guide",
            "content": {"type": "document", "title": "Brew Guide"}}},
    ]
    found = parsing._sources_from_content(content)
    assert [s["url"] for s in found] == [
        "https://roaster.example/guide", "https://other.example", "https://roaster.example/guide"]
    assert [s["url"] for s in parsing._dedupe_sources(found)] == [
        "https://roaster.example/guide", "https://other.example"]


# ─── Provenance on the returned recipe ────────────────────────────────────────

def test_web_search_path_marks_source_and_flags_unopened_urls(monkeypatch):
    def fake_search(prompt, key, system):
        return ({"title": "Guide", "confidence": "high",
                 "source_url": "https://never-opened.example"},
                [{"url": "https://roaster.example/guide", "title": "Guide"}], None)
    monkeypatch.setattr(recipe_search, "call_anthropic_with_web_search", fake_search)

    r, err = recipe_search.search_roaster_recipe(
        "Roaster", "Coffee", "drip", "Fellow Aiden", {"anthropic_key": "k"})
    assert err is None
    assert r["source_kind"] == recipe_search.SOURCE_WEB
    assert r["sources"][0]["url"] == "https://roaster.example/guide"
    assert r["source_url_unverified"] is True


def test_web_search_path_trusts_a_url_it_opened(monkeypatch):
    monkeypatch.setattr(recipe_search, "call_anthropic_with_web_search",
                        lambda p, k, s: ({"source_url": "https://r.example/g"},
                                         [{"url": "https://r.example/g", "title": ""}], None))
    r, _ = recipe_search.search_roaster_recipe("R", "C", "drip", "", {"anthropic_key": "k"})
    assert "source_url_unverified" not in r
    assert r["confidence"] == "low"          # defaulted, never missing
    assert r["author"] == "R"


def test_recall_path_is_labelled_as_memory(monkeypatch):
    monkeypatch.setattr(recipe_search, "call_ai_with_prompt",
                        lambda p, s, settings: ({"confidence": "high"}, None))
    r, _ = recipe_search.search_roaster_recipe("R", "C", "drip", "", {"openai_key": "k"})
    assert r["source_kind"] == recipe_search.SOURCE_RECALL
    assert r["sources"] == []


def test_search_error_is_returned_not_swallowed(monkeypatch):
    monkeypatch.setattr(recipe_search, "call_anthropic_with_web_search",
                        lambda p, k, s: (None, [], "boom"))
    r, err = recipe_search.search_roaster_recipe("R", "C", "drip", "", {"anthropic_key": "k"})
    assert r is None and err == "boom"
