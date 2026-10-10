import os
import sys
from dotenv import load_dotenv

# Ensure current directory and backend directory are in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(override=True)

from intent_classifier import IntentClassifier, IntentClassificationOutput
from reasoning_engine import ReasoningEngine

def test_intent_classification():
    print("=== STARTING SKILLS INTENT CLASSIFICATION TEST ===")
    classifier = IntentClassifier()
    print(f"Classifier URL: {getattr(classifier, 'url', 'N/A')}")
    
    # 1. Test Factual / Contact Lookup
    q1 = "Who is the decision maker at Deloitte?"
    res1 = classifier.classify(q1)
    print(f"Query: '{q1}'")
    print(f"  Intent: {res1.intent}")
    print(f"  Scope: {res1.scope}")
    print(f"  Complexity: {res1.complexity}")
    print(f"  Target Entities: {res1.target_entities}")
    assert res1.complexity == "FACTUAL"
    assert res1.intent == "CONTACT_LOOKUP"
    assert "Deloitte" in res1.target_entities
    
    # 2. Test Operational / Pipeline Review
    q2 = "Show me the top opportunities stalling in negotiation"
    res2 = classifier.classify(q2)
    print(f"\nQuery: '{q2}'")
    print(f"  Intent: {res2.intent}")
    print(f"  Scope: {res2.scope}")
    print(f"  Complexity: {res2.complexity}")
    assert res2.complexity == "OPERATIONAL"
    assert res2.intent in ("OPPORTUNITY_RANKING", "RISK_ANALYSIS")
    
    # 3. Test Strategic / Playbook
    q3 = "What is the 7-day playbook for Deloitte?"
    res3 = classifier.classify(q3)
    print(f"\nQuery: '{q3}'")
    print(f"  Intent: {res3.intent}")
    print(f"  Scope: {res3.scope}")
    print(f"  Complexity: {res3.complexity}")
    assert res3.complexity == "STRATEGIC"
    assert res3.intent == "ACCOUNT_PLAN"

    # 4. Test Executive / Board Narrative
    q4 = "Give me an executive briefing for the portfolio"
    res4 = classifier.classify(q4)
    print(f"\nQuery: '{q4}'")
    print(f"  Intent: {res4.intent}")
    print(f"  Scope: {res4.scope}")
    print(f"  Complexity: {res4.complexity}")
    assert res4.complexity == "EXECUTIVE"
    assert res4.intent == "EXECUTIVE_BRIEFING"
    
    print("\n[OK] Intent Classification skills tests passed!")

def test_reasoning_engine_factual():
    print("\n=== STARTING SKILLS REASONING ENGINE BYPASS TEST ===")
    engine = ReasoningEngine()
    
    # Factual complexity bypass test
    res = engine.run_reasoning_threads(
        account_data={},
        market_context={},
        complexity="FACTUAL"
    )
    print("Factual Consensus Output:")
    print(f"  Recommendation action: {res.consensus_recommendation.get('action')}")
    print(f"  Final Confidence: {res.final_confidence}")
    assert res.final_confidence == 1.0
    assert res.consensus_recommendation.get("action") == "Displaying database records directly."
    
    # Operational complexity bypass test
    res_op = engine.run_reasoning_threads(
        account_data={"opportunities": []},
        market_context={},
        complexity="OPERATIONAL"
    )
    print("Operational Consensus Output:")
    print(f"  Recommendation action: {res_op.consensus_recommendation.get('action')}")
    print(f"  Final Confidence: {res_op.final_confidence}")
    assert res_op.final_confidence == 0.9  # deterministic data display, no LLM synthesis
    assert res_op.consensus_recommendation.get("action") == "Displaying data quality and core metrics."
    
    print("\n[OK] Reasoning Engine Governance tests passed!")

def test():
    test_intent_classification()
    test_reasoning_engine_factual()
    print("\n=== ALL SKILLS ARCHITECTURE TESTS COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    test()
