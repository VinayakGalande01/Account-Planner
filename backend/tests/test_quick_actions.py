import os
import sys
import pytest
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(override=True)

from quick_actions_handler import StakeholderHandler, RiskReviewHandler, dispatch_quick_action

# Mock CRM data to test deterministic handlers without DB dependencies
MOCK_ACCOUNT_DATA = {
    "account_id": "ACC123",
    "account_name": "Acme Corp",
    "health_score": 35.0, # Low health to trigger competitor threat
    "opportunities": [
        {
            "opp_id": "OPP001",
            "opp_name": "Acme Enterprise Deal",
            "amount_usd": 1500000.0,
            "stage": "Commercial Negotiation",
            "close_date": "2026-06-30",  # 14 days overdue relative to 2026-07-14
            "competitor": "Competitor A"
        }
    ],
    "contacts": [
        {
            "contact_id": "CON001",
            "name": "Alice Johnson",
            "role": "VP of Operations",
            "engagement_level": "High",
            "last_contact_date": "2026-07-10" # Recent
        },
        {
            "contact_id": "CON002",
            "name": "Bob Smith",
            "role": "Procurement Manager",
            "engagement_level": "Low",
            "last_contact_date": "2026-05-14" # COLD (> 30 days relative to 2026-07-14)
        }
    ],
    "cases": [
        {
            "case_id": "CASE001",
            "subject": "System integration issue",
            "status": "New",
            "priority": "P1", # Critical case
            "open_date": "2026-07-04"
        }
    ]
}

def test_stakeholder_handler():
    """Verify that StakeholderHandler correctly maps sentiment, calculates days since, and groups by influence."""
    res = StakeholderHandler.handle(MOCK_ACCOUNT_DATA, "show stakeholders")
    
    assert res["type"] == "STAKEHOLDERS"
    assert res["total_count"] == 2
    
    # Alice: High -> Champion, is_dm -> True
    alice = next(s for s in res["stakeholders"] if s["name"] == "Alice Johnson")
    assert alice["sentiment"] == "Champion"
    assert alice["is_decision_maker"] is True
    assert alice["risk_flag"] == "NONE"
    
    # Bob: Low -> Detractor, cold (> 30 days)
    bob = next(s for s in res["stakeholders"] if s["name"] == "Bob Smith")
    assert bob["sentiment"] == "Detractor"
    assert bob["risk_flag"] == "COLD_CONTACT"
    assert bob["days_since_contact"] > 30

    # Influence map
    influence = res["influence_map"]
    assert "Alice Johnson" in influence["high_influence_champions"]
    assert "Bob Smith" in influence["cold_stakeholders"]

def test_risk_review_handler():
    """Verify that RiskReviewHandler correctly triages single-threaded, stalling, critical support cases and competitor threats."""
    res = RiskReviewHandler.handle(MOCK_ACCOUNT_DATA, "review risks")
    
    assert res["type"] == "RISK_REVIEW"
    assert res["revenue_at_risk_usd"] > 0
    
    buckets = res["risk_buckets"]
    
    # Single-threaded (since total contacts <= 2)
    assert len(buckets["single_threaded"]) == 1
    assert buckets["single_threaded"][0]["opp_name"] == "Acme Enterprise Deal"
    
    # Stalling (Commercial Negotiation)
    assert len(buckets["stalling_deals"]) == 1
    assert buckets["stalling_deals"][0]["opp_name"] == "Acme Enterprise Deal"
    assert buckets["stalling_deals"][0]["days_stalled"] == 14
    
    # Critical cases
    assert len(buckets["critical_cases"]) == 1
    assert buckets["critical_cases"][0]["case_id"] == "CASE001"
    assert buckets["critical_cases"][0]["age_days"] == 10
    
    # Competitor threat (health score < 50)
    assert len(buckets["competitor_threat"]) == 1
    assert buckets["competitor_threat"][0]["opp_name"] == "Acme Enterprise Deal"
    assert buckets["competitor_threat"][0]["competitor"] == "Competitor A"

    # One deal in several buckets is counted once
    assert res["revenue_at_risk_usd"] == 1500000.0


def test_risk_review_excludes_closed_deals():
    data = dict(MOCK_ACCOUNT_DATA, opportunities=MOCK_ACCOUNT_DATA["opportunities"] + [
        {"opp_id": "OPP002", "opp_name": "Lost Pilot", "amount_usd": 900000.0, "stage": "Closed Lost",
         "close_date": "2026-01-01", "competitor": "Competitor B"},
    ])
    res = RiskReviewHandler.handle(data, "review risks")
    names = {o["opp_name"] for bucket in res["risk_buckets"].values() for o in bucket if "opp_name" in o}
    assert "Lost Pilot" not in names
    assert res["revenue_at_risk_usd"] == 1500000.0


def test_risk_review_portfolio_counts_only_unhealthy_accounts():
    data = {
        "account_id": None,
        "account_name": "Global Portfolio View",
        "health_score": 60.0,
        "contacts": [],
        "cases": [],
        "portfolio_health": {"A1": 20.0, "A2": 88.0},
        "opportunities": [
            {"opp_id": "O1", "opp_name": "Weak account renewal", "account_id": "A1", "amount_usd": 500000.0,
             "stage": "Negotiation/Review", "close_date": "2026-07-01", "competitor": None},
            {"opp_id": "O2", "opp_name": "Healthy account expansion", "account_id": "A2", "amount_usd": 2000000.0,
             "stage": "Negotiation/Review", "close_date": "2026-07-01", "competitor": "Competitor A"},
        ],
    }
    res = RiskReviewHandler.handle(data, "which accounts are at risk")
    assert res["risk_buckets"]["single_threaded"] == []
    assert [d["opp_name"] for d in res["risk_buckets"]["stalling_deals"]] == ["Weak account renewal"]
    assert res["revenue_at_risk_usd"] == 500000.0

def test_dispatch_quick_action():
    """Verify that dispatcher correctly routes types and returns structured responses."""
    # Deterministic test
    sh_res = dispatch_quick_action("SHOW_STAKEHOLDERS", MOCK_ACCOUNT_DATA, "show contacts")
    assert sh_res["type"] == "STAKEHOLDERS"
    
    rr_res = dispatch_quick_action("REVIEW_RISKS", MOCK_ACCOUNT_DATA, "show risks")
    assert rr_res["type"] == "RISK_REVIEW"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
