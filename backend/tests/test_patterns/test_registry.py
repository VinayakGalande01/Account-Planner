import os
import sys
import pytest
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv(override=True)

from intelligence_engine import IntelligenceEngine
from patterns.registry import get_pattern_by_id

def test_pipeline_concentration_triggers():
    data = {
        "account_name": "Concentration Corp",
        "health_score": 80.0,
        "opportunities": [
            {"opp_name": "Massive Deal 1", "amount_usd": 850000.0, "stage": "Negotiation", "close_date": "2026-08-30"},
            {"opp_name": "Massive Deal 2", "amount_usd": 100000.0, "stage": "Negotiation", "close_date": "2026-08-30"},
            {"opp_name": "Tiny Deal", "amount_usd": 50000.0, "stage": "Qualification", "close_date": "2026-09-30"}
        ],
        "contacts": [{"name": "A", "role": "VP Buying", "engagement_level": "High"}],
        "cases": [],
        "activities": [{"date": "2026-07-12", "type": "Email"}]
    }
    brief = IntelligenceEngine.build_intelligence_brief(data)
    assert any(f.pattern_id == "PIPELINE_CONCENTRATION" for f in brief.ranked_findings)

def test_stalled_deal_triggers():
    data = {
        "account_name": "Stalled Inc",
        "health_score": 80.0,
        "opportunities": [
            {"opp_name": "Stalled Opp", "amount_usd": 200000.0, "stage": "Negotiation", "close_date": "2026-05-01"}
        ],
        "contacts": [{"name": "A", "role": "Director", "engagement_level": "High"}],
        "cases": [],
        "activities": [{"date": "2026-05-01", "type": "Email"}]
    }
    brief = IntelligenceEngine.build_intelligence_brief(data)
    assert any(f.pattern_id == "STALLED_DEAL" for f in brief.ranked_findings)

def test_close_date_pressure_triggers():
    data = {
        "account_name": "Pressure Ltd",
        "health_score": 80.0,
        "opportunities": [
            {"opp_name": "Risky Opp", "amount_usd": 200000.0, "stage": "Negotiation", "close_date": "2026-07-28", "probability": 0.3}
        ],
        "contacts": [{"name": "A", "role": "Director", "engagement_level": "High"}],
        "cases": [],
        "activities": [{"date": "2026-07-12", "type": "Email"}]
    }
    brief = IntelligenceEngine.build_intelligence_brief(data)
    assert any(f.pattern_id == "CLOSE_DATE_PRESSURE" for f in brief.ranked_findings)

def test_single_threaded_triggers():
    data = {
        "account_name": "Lonely Co",
        "health_score": 80.0,
        "opportunities": [{"opp_name": "Big Opp", "amount_usd": 50000.0}],
        "contacts": [{"name": "Only One", "role": "Staff Developer"}],
        "cases": [],
        "activities": [{"date": "2026-07-12", "type": "Email"}]
    }
    brief = IntelligenceEngine.build_intelligence_brief(data)
    assert any(f.pattern_id == "SINGLE_THREADED_RISK" for f in brief.ranked_findings)

def test_executive_blind_spot_triggers():
    data = {
        "account_name": "Blind Spot Org",
        "health_score": 80.0,
        "opportunities": [{"opp_name": "Large Opportunity", "amount_usd": 250000.0}],
        "contacts": [{"name": "Dev", "role": "Engineer"}],
        "cases": [],
        "activities": [{"date": "2026-07-12", "type": "Email"}]
    }
    brief = IntelligenceEngine.build_intelligence_brief(data)
    assert any(f.pattern_id == "EXECUTIVE_BLIND_SPOT" for f in brief.ranked_findings)

def test_stakeholder_gap_triggers():
    data = {
        "account_name": "Gap Corp",
        "health_score": 80.0,
        "opportunities": [{"opp_name": "Some Opp", "amount_usd": 50000.0}],
        "contacts": [{"name": "Consultant", "role": "Advisor"}],
        "cases": [],
        "activities": [{"date": "2026-07-12", "type": "Email"}]
    }
    brief = IntelligenceEngine.build_intelligence_brief(data)
    assert any(f.pattern_id == "STAKEHOLDER_GAP" for f in brief.ranked_findings)

def test_activity_cliff_triggers():
    data = {
        "account_name": "Silent Corp",
        "health_score": 80.0,
        "opportunities": [{"opp_name": "Some Opp", "amount_usd": 50000.0}],
        "contacts": [{"name": "A", "role": "Director"}],
        "cases": [],
        "activities": [{"date": "2026-06-01", "type": "Email"}]
    }
    brief = IntelligenceEngine.build_intelligence_brief(data)
    assert any(f.pattern_id == "ACTIVITY_CLIFF" for f in brief.ranked_findings)

def test_support_pressure_triggers():
    data = {
        "account_name": "Hot Support Corp",
        "health_score": 80.0,
        "opportunities": [{"opp_name": "Some Opp", "amount_usd": 50000.0}],
        "contacts": [{"name": "A", "role": "Director"}],
        "cases": [{"case_id": "CS1", "severity": "P1", "status": "New", "subject": "System crash"}],
        "activities": [{"date": "2026-07-12", "type": "Email"}]
    }
    brief = IntelligenceEngine.build_intelligence_brief(data)
    assert any(f.pattern_id == "SUPPORT_PRESSURE" for f in brief.ranked_findings)

def test_expansion_signal_triggers():
    data = {
        "account_name": "Growing Corp",
        "health_score": 95.0,
        "opportunities": [
            {"opp_name": "Opp 1", "amount_usd": 20000.0},
            {"opp_name": "Opp 2", "amount_usd": 30000.0},
            {"opp_name": "Opp 3", "amount_usd": 15000.0}
        ],
        "contacts": [{"name": "Buyer", "role": "Economic Buyer"}],
        "cases": [],
        "activities": [{"date": "2026-07-12", "type": "Email"}]
    }
    brief = IntelligenceEngine.build_intelligence_brief(data)
    assert any(f.pattern_id == "EXPANSION_SIGNAL" for f in brief.ranked_findings)
