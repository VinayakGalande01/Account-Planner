"""Account resolution and routing checks against the demo dataset's account names (no LLM calls)."""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from account_resolver import (
    candidate_names, find_account_in_text, is_contact_name, match_account_rows, user_messages,
)
from demo_dataset import ACCOUNTS
import intent_classifier
from intent_classifier import IntentClassifier

KNOWN_ACCOUNTS = [a[1] for a in ACCOUNTS]
ACCOUNTS_DF = pd.DataFrame({"Account_ID": [a[0] for a in ACCOUNTS], "Account_Name": KNOWN_ACCOUNTS})
CONTACTS_DF = pd.DataFrame({"First_Name": ["Marcus", "Sofia"], "Last_Name": ["Hale", "Laurent"]})


@pytest.mark.parametrize("query, expected", [
    ("Who should I contact at Meridian?", "Meridian Health Network"),
    ("Give me a 7-day playbook for Northwind Logistics", "Northwind Logistics"),
    ("What is the revenue of Brightwater Capital?", "Brightwater Capital"),
    ("Why are we losing Halvorsen Retail?", "Halvorsen Retail Co."),
    ("How are support cases affecting Crestline Realty?", "Crestline Realty Group"),
    ("What's wrong with Sablewood Manufacturing?", "Sablewood Manufacturing"),
    ("Tell me about Acme Corp", None),
    ("Which accounts have expansion potential?", None),
    ("I need a plan", None),
])
def test_find_account_in_text(query, expected):
    assert find_account_in_text(query, KNOWN_ACCOUNTS) == expected


def test_candidate_names_drop_filler_words():
    assert candidate_names("Tell me about Acme Corp") == ["Acme Corp"]
    assert candidate_names("Who should I contact at Meridian?") == ["Meridian"]
    assert candidate_names("Which accounts have expansion potential?") == []
    assert candidate_names("hi") == []


@pytest.mark.parametrize("name, expected_id", [
    ("I", None),            # used to substring-match "Northwind Logistics"
    ("Tell", None),
    ("in", None),
    ("Acme Corp", None),
    ("Meridian", "ACC002"),
    ("northwind logistics", "ACC001"),
    ("ACC006", "ACC006"),
])
def test_match_account_rows_is_whole_word(name, expected_id):
    rows = match_account_rows(ACCOUNTS_DF, name)
    assert (rows.iloc[0]["Account_ID"] if not rows.empty else None) == expected_id


def test_contact_name_detection():
    assert is_contact_name(CONTACTS_DF, "Marcus")
    assert is_contact_name(CONTACTS_DF, "Sofia Laurent")
    assert not is_contact_name(CONTACTS_DF, "Acme Corp")


def test_user_messages_excludes_assistant_text():
    history = [
        {"sender": "user", "text": "Tell me about Meridian"},
        {"sender": "assistant", "text": "Northwind Logistics renewal at risk"},
        {"role": "user", "content": "thanks"},
    ]
    assert user_messages(history) == ["Tell me about Meridian", "thanks"]


@pytest.fixture
def classifier(monkeypatch):
    # Skip the embedding fast-lane and the LLM router; account resolution runs before both.
    monkeypatch.setattr(IntentClassifier, "_init_embeddings", lambda self: None)
    monkeypatch.setattr(IntentClassifier, "_call_llm", lambda self, *a, **k: (_ for _ in ()).throw(TimeoutError("offline")))
    return IntentClassifier(known_accounts=KNOWN_ACCOUNTS)


@pytest.mark.parametrize("query, active_account, history, expected", [
    ("Who should I contact at Meridian?", "Northwind Logistics", None, "Meridian Health Network"),
    ("Tell me about Acme Corp", "Northwind Logistics", None, "Acme Corp"),
    ("Which accounts have expansion potential?", None,
     [{"sender": "assistant", "text": "Northwind Logistics is at risk"}], None),
    ("What are the next steps?", None,
     [{"sender": "user", "text": "Tell me about Crestline Realty Group"},
      {"sender": "assistant", "text": "Northwind Logistics renewal"}], "Crestline Realty Group"),
    ("What are the next steps?", "Orion BioLabs", None, "Orion BioLabs"),
])
def test_classifier_target_account(classifier, query, active_account, history, expected):
    result = classifier.classify(query, history=history, active_account=active_account)
    assert result.extracted_entities.account == expected
