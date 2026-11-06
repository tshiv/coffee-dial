"""Bag parsing request shape and response handling. No network."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai import parsing  # noqa: E402

PARSED = {"coffee_name": "Ardi", "roaster": "Blossom", "origin": "Ethiopia",
          "process": "natural", "roast": "light", "altitude_m": None, "variety": None,
          "flavor_notes": ["blueberry"], "confidence": "high", "reasoning": "Stated."}


def _stub(monkeypatch, response):
    sent = {}

    def fake_post(payload, api_key, timeout_s, betas=None):
        sent["payload"] = payload
        return response
    monkeypatch.setattr(parsing, "_post_anthropic", fake_post)
    return sent


def test_bag_parse_uses_haiku_55_with_the_schema(monkeypatch):
    import json
    sent = _stub(monkeypatch, {"stop_reason": "end_turn",
                               "content": [{"type": "text", "text": json.dumps(PARSED)}]})
    result, err = parsing.call_ai("Blossom Ardi natural", {"anthropic_key": "k"})
    assert err is None and result == PARSED
    p = sent["payload"]
    assert p["model"] == "claude-haiku-5-5"
    assert p["output_config"]["effort"] == "low"
    assert p["output_config"]["format"] == {"type": "json_schema", "schema": parsing.BAG_SCHEMA}
    assert "temperature" not in p and "thinking" not in p


def test_answer_after_a_thinking_block_is_still_read(monkeypatch):
    """Haiku 5.5 thinks by default; content[0] is a thinking block."""
    import json
    _stub(monkeypatch, {"stop_reason": "end_turn", "content": [
        {"type": "thinking", "thinking": "", "signature": "sig"},
        {"type": "text", "text": json.dumps(PARSED)},
    ]})
    result, err = parsing.call_ai("x", {"anthropic_key": "k"})
    assert err is None and result["roast"] == "light"


def test_refusal_and_truncation_are_errors_not_crashes(monkeypatch):
    _stub(monkeypatch, {"stop_reason": "refusal", "content": []})
    assert parsing.call_ai("x", {"anthropic_key": "k"})[1] == "The model declined this request."
    _stub(monkeypatch, {"stop_reason": "max_tokens",
                        "content": [{"type": "thinking", "thinking": "", "signature": "s"}]})
    assert "ran out of room" in parsing.call_ai("x", {"anthropic_key": "k"})[1]


def test_recall_prompts_get_no_schema(monkeypatch):
    sent = _stub(monkeypatch, {"stop_reason": "end_turn",
                               "content": [{"type": "text", "text": '{"ratio": 16}'}]})
    result, err = parsing.call_ai_with_prompt("x", "system", {"anthropic_key": "k"})
    assert err is None and result == {"ratio": 16}
    assert "format" not in sent["payload"]["output_config"]


def test_bag_schema_follows_structured_output_rules():
    """Every object needs additionalProperties false and every field required."""
    s = parsing.BAG_SCHEMA
    assert s["additionalProperties"] is False
    assert set(s["required"]) == set(s["properties"])


def test_web_search_uses_opus_55():
    assert parsing.WEB_SEARCH_MODEL == "claude-opus-5-5"
