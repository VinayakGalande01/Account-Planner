import os
import sys
import pytest
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(override=True)

from intelligence_engine import IntelligenceEngine

MOCK_HEALTHY_ACCOUNT = {
    "account_name": "Tesla",
    "health_score": 90.0,
    "opportunities": [
        {
            "opp_name": "Model 3 Fleet Purchase",
            "amount_usd": 500000.0,
            "stage": "Negotiation",
            "close_date": "2026-08-30" # Future close date
        }
    ],
    "contacts": [
        {"name": "Elon Musk", "role": "CEO", "engagement_level": "High"},
        {"name": "Gwynne Shotwell", "role": "COO", "engagement_level": "High"},
        {"name": "JB Straubel", "role": "CTO", "engagement_level": "Medium"}
    ],
    "cases": [],
    "activities": [
        {"date": "2026-07-12", "type": "Email", "description": "Discussed delivery terms"}
    ]
}

MOCK_RISKY_ACCOUNT = {
    "account_name": "Ford",
    "health_score": 45.0, # Low health
    "opportunities": [
        {
            "opp_name": "Mustang Mach-E Deal",
            "amount_usd": 2000000.0,
            "stage": "Contract Review",
            "close_date": "2026-05-10" # Past close date (stale)
        }
    ],
    "contacts": [
        {"name": "Jim Farley", "role": "CEO", "engagement_level": "Low"} # Single-threaded
    ],
    "cases": [
        {"case_id": "CASE99", "subject": "Charging station compatibility issue", "severity": "P1", "status": "New"} # Overlapping critical support ticket
    ],
    "activities": [
        {"date": "2026-05-01", "type": "Call", "description": "Intro call"}
    ]
}

def test_healthy_account_signals():
    signals = IntelligenceEngine.compute(MOCK_HEALTHY_ACCOUNT)
    
    assert len(signals["stale_deals"]) == 0
    assert signals["churn_risk_index"] == 0.0
    assert len(signals["single_threaded_opps"]) == 0
    assert len(signals["case_opp_overlap"]) == 0
    assert "account status healthy" in signals["narrative_bullets"][0]

def test_risky_account_signals():
    signals = IntelligenceEngine.compute(MOCK_RISKY_ACCOUNT)
    
    assert len(signals["stale_deals"]) == 1
    assert signals["stale_deals"][0]["opp_name"] == "Mustang Mach-E Deal"
    assert signals["stale_deals"][0]["days_stalled"] > 30
    
    assert len(signals["single_threaded_opps"]) == 1
    assert signals["single_threaded_opps"][0]["primary_contact"] == "Jim Farley"
    
    assert len(signals["case_opp_overlap"]) == 1
    assert signals["case_opp_overlap"][0]["case_id"] == "CASE99"
    
    assert signals["churn_risk_index"] == 1.0 # 0.4 (low health) + 0.4 (P1 case) + 0.2 (stale deal)
    
    # Verify narrative bullet warnings exist
    bullets = "".join(signals["narrative_bullets"])
    assert "pipeline stagnation" in bullets
    assert "single-threaded risk" in bullets
    assert "critical ticket overlap" in bullets
    assert "account health warning" in bullets

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
