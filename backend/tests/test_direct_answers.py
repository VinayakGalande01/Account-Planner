"""Deterministic direct answers against the demo dataset (no LLM calls)."""
import datetime
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_dataset import build_demo_sheets
from direct_answers import account_answer, display_id, fmt_usd, portfolio_answer


@pytest.fixture(scope="module")
def data():
    # Same date as conftest's APEX_REFERENCE_DATE so relative close dates line up
    sheets = build_demo_sheets(datetime.date(2026, 7, 14))
    names = {"Accounts": "account", "Opportunities": "opportunity", "Contacts": "contact"}
    return {names.get(k, k.lower()): v for k, v in sheets.items()}


def account(data, name):
    accs = data["account"]
    return accs[accs["Account_Name"] == name].iloc[0]


def test_sheet_names(data):
    assert {"account", "opportunity", "contact"} <= set(data)


def test_expansion_lists_healthy_accounts_with_pipeline(data):
    ans = portfolio_answer("Which accounts have expansion potential?", data)
    names = [r["Account_Name"] for r in ans["table_data"]["rows"]]
    assert names and names[0] == "Brightwater Capital"
    assert all(r["Health_Score"] >= 65 for r in ans["table_data"]["rows"])
    assert not {"Northwind Logistics", "Sablewood Manufacturing", "Halvorsen Retail Co."} & set(names)


def test_closing_this_month_only_open_future_deals(data):
    ans = portfolio_answer("What's closing this month?", data)
    assert ans["table_data"]["rows"]
    for r in ans["table_data"]["rows"]:
        assert r["Stage"] not in ("Closed Won", "Closed Lost")


@pytest.mark.parametrize("query", [
    "Why are we losing Halvorsen?", "Which accounts should I prioritise?", "Give me a plan for expansion",
])
def test_planning_questions_go_to_reasoning(data, query):
    assert portfolio_answer(query, data) is None


def test_revenue(data):
    ans = account_answer("What is the revenue of Brightwater Capital?", account(data, "Brightwater Capital"), data)
    assert "$2.1B" in ans["narrative"] and ans["table_data"] is None


def test_health(data):
    ans = account_answer("What's the health score of Northwind Logistics?", account(data, "Northwind Logistics"), data)
    assert "28/100" in ans["narrative"] and "critical" in ans["narrative"]


def test_contacts(data):
    ans = account_answer("List contacts at Brightwater Capital", account(data, "Brightwater Capital"), data)
    assert "Jamal Wright" in [r["Name"] for r in ans["table_data"]["rows"]]


def test_opportunities_show_ids_without_user_prefix_and_open_total(data):
    ans = account_answer("Show opportunities for Northwind Logistics", account(data, "Northwind Logistics"), data)
    assert "$1.54M" in ans["narrative"] and "plus 1 closed" in ans["narrative"]
    assert ans["table_data"]["rows"][-1]["Stage"] == "Closed Lost"


@pytest.mark.parametrize("query", [
    "Who should I contact at Meridian?", "Give me a 7-day playbook for Northwind Logistics", "Why is health dropping?",
])
def test_account_planning_questions_go_to_reasoning(data, query):
    assert account_answer(query, account(data, "Northwind Logistics"), data) is None


def test_formatting_helpers():
    assert fmt_usd(2_100_000_000) == "$2.1B"
    assert fmt_usd(1_540_000) == "$1.54M"
    assert fmt_usd(2_000_000) == "$2M"
    assert fmt_usd(340_000) == "$340K"
    assert display_id("1_OPP001") == "OPP001"
