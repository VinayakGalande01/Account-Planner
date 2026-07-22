import os
import sys
from dotenv import load_dotenv

# Ensure current directory and backend directory are in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(override=True)

from reasoning_engine import ReasoningEngine

def test():
    print("=== STARTING MULTI-PERSPECTIVE REASONING ENGINE TEST ===")
    
    # Instantiate the reasoning engine
    engine = ReasoningEngine()
    print(f"Using LLM URL: {engine.url}")
    print(f"Using LLM Model: {engine.model}")
    
    account_data = {
        "account": "Infosys",
        "health_score": 0.75,
        "churn_probability": 0.15,
        "engagement_trend": "increasing",
        "historical_data": {
            "past_cases": 12,
            "success_rate": 0.85
        }
    }
    
    market_context = {
        "competitive_threats": ["Competitor A", "Competitor B"],
        "peer_accounts": [
            {"account": "Wipro", "health_score": 0.65},
            {"account": "TCS", "health_score": 0.80}
        ],
        "company_okrs": [
            "Increase retention in enterprise accounts to >95%",
            "Expand ARR in APAC by 20%"
        ],
        "competitive_context": "Competitor A is actively pitching a replacement solution."
    }
    
    print("\nRunning parallel threads and consensus synthesis...")
    try:
        # Run with generous timeout of 30 seconds for test
        consensus = engine.run_reasoning_threads(
            account_data=account_data,
            market_context=market_context,
            timeout_per_thread=20,
            total_timeout=40
        )
        print("\n--- SYNTHESIS COMPLETE ---")
        print(f"Consensus recommendation action: {consensus.consensus_recommendation.get('action')}")
        print(f"Consensus recommendation confidence: {consensus.consensus_recommendation.get('confidence')}")
        print(f"Final confidence: {consensus.final_confidence}")
        print(f"Dissenting views count: {len(consensus.dissenting_views)}")
        for i, dv in enumerate(consensus.dissenting_views):
            print(f"  Dissent {i+1} ({dv.perspective}): {dv.dissent} (Confidence: {dv.confidence})")
        print(f"Confidence limiting factors: {consensus.confidence_limiting_factors}")
        print(f"Agreement Score: {consensus.agreement_score}")
    except Exception as e:
        print(f"Error executing test: {e}")
        
    print("\n=== MULTI-PERSPECTIVE REASONING ENGINE TEST COMPLETE ===")

if __name__ == "__main__":
    test()
