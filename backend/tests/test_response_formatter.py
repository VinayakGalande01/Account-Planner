"""Formatter guards: skip rules, data-driven urgency and removal of invented content (no LLM calls)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import response_formatter
from response_formatter import _ground_to_source, compute_urgency, format_response_for_user, should_skip_formatting

RAW = (
    "__SECTION_HEADLINE__\nNorthwind Logistics renewal at risk\n"
    "__SECTION_SUMMARY__\nMarcus Hale is the champion. 1_OPP001 Northwind - Fleet Analytics Renewal $1,200,000\n"
)


@pytest.mark.parametrize("raw, complexity, expected", [
    ('{"type": "clarification", "message": "Which account?"}', None, True),
    ("__SECTION_HEADLINE__\nHello!", "CONVERSATIONAL", True),
    ("__SECTION_HEADLINE__\nContacts", "FACTUAL", True),
    (RAW, "STRATEGIC", False),
])
def test_should_skip_formatting(raw, complexity, expected):
    assert should_skip_formatting(raw, complexity) is expected


@pytest.mark.parametrize("account_data, expected", [
    (None, None),
    ({"account_name": "Global Portfolio View"}, None),
    ({"account_id": "1_ACC006", "health_score": 88, "cases": []}, "P3"),
    ({"account_id": "1_ACC006", "health_score": 88, "cases": [{"severity": "High", "status": "Open"}]}, "P2"),
    ({"account_id": "1_ACC003", "health_score": 50, "cases": []}, "P2"),
    ({"account_id": "1_ACC001", "health_score": 28, "cases": []}, "P1"),
    ({"account_id": "1_ACC006", "health_score": 88, "cases": [{"severity": "Critical", "status": "Escalated"}]}, "P1"),
    ({"account_id": "1_ACC006", "health_score": 88, "cases": [{"severity": "Critical", "status": "Closed"}]}, "P3"),
])
def test_compute_urgency(account_data, expected):
    assert compute_urgency(account_data) == expected


def test_ground_to_source_drops_invented_items():
    parsed = {
        "headline": "Contact [Insert Decision Maker Name Here] today",
        "summary": "s", "flag": "f", "closing_question": "q",
        "opportunities": [
            {"id": "1_OPP001", "name": "Northwind - Fleet Analytics Renewal"},
            {"id": "X1", "name": "Acme Corp Expansion"},
        ],
        "risks": [
            {"type": "Stalled", "account": "Northwind Logistics", "action": "Call Marcus"},
            {"type": "Stalled", "account": "Acme Corp", "action": "Call John Smith"},
        ],
        "recommended_actions": [
            {"priority": 1, "action": "Call Marcus Hale"},
            {"priority": 2, "action": "Run the test_to_disambiguate call from the Strategic Narrative Builder"},
        ],
        "next_steps_suggestions": ["Call Marcus", "Review Crucible output"],
    }
    out = _ground_to_source(parsed, RAW)
    assert [o["id"] for o in out["opportunities"]] == ["1_OPP001"]
    assert [r["account"] for r in out["risks"]] == ["Northwind Logistics"]
    assert [a["action"] for a in out["recommended_actions"]] == ["Call Marcus Hale"]
    assert out["next_steps_suggestions"] == ["Call Marcus"]
    assert "[Insert" not in out["headline"]


def test_urgency_override_replaces_llm_value(monkeypatch):
    llm_reply = {
        "headline": "h", "urgency": "P1", "summary": "s", "opportunities": [], "risks": [], "flag": "f",
        "recommended_actions": [], "closing_question": "q", "next_steps_suggestions": [],
    }
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    import reasoning_engine
    monkeypatch.setattr(reasoning_engine, "call_gemini_api", lambda **kwargs: json.dumps(llm_reply))
    import asyncio
    out = json.loads(asyncio.run(format_response_for_user(RAW, urgency="P3")))
    assert out["urgency"] == "P3"


def test_storage_prefixes_hidden_from_users():
    from response_formatter import strip_storage_prefixes
    assert strip_storage_prefixes("escalate 26_CASE002 and 1_OPP004") == "escalate CASE002 and OPP004"
    assert strip_storage_prefixes("ACC001, v1_2, 2_CASEX") == "ACC001, v1_2, 2_CASEX"


def test_failed_formatting_returns_raw_output_unchanged(monkeypatch):
    # main.py treats "result != raw_output" as success, so a failure must not alter the text
    import reasoning_engine
    monkeypatch.setattr(reasoning_engine, "call_gemini_api", lambda **kwargs: "not json at all")
    import asyncio
    raw = RAW + " Linked case 26_CASE002."
    assert asyncio.run(format_response_for_user(raw, urgency="P3")) == raw
