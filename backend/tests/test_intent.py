import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from intent_classifier import IntentClassifier

def run_tests():
    print("=== TESTING LAY 1 INTENT VALIDATION & NORMALIZATION ===")
    
    classifier = IntentClassifier()
    
    test_queries = [
        "Top 5 opportunities in negotiation stage",
        "Show me stalling opportunities",
        "Opportunities closing in next 30 days",
        "Why are we losing to competitor X"
    ]
    
    for i, q in enumerate(test_queries, 1):
        print(f"\nTest {i}: '{q}'")
        res = classifier.classify(q)
        try:
            res_dict = res.model_dump()
        except AttributeError:
            res_dict = res.dict()
            
        # Format enums
        primary_intent_val = res_dict["primary_intent"]
        urgency_val = res_dict["urgency"]
        scope_val = res_dict["scope"]
        
        output = {
            "query": q,
            "primary_intent": primary_intent_val,
            "confidence": res_dict["confidence_primary"],
            "entities": {
                "account": res_dict["extracted_entities"]["account"],
                "stage": res_dict["extracted_entities"]["stage"],
                "metric": res_dict["extracted_entities"]["metric"],
                "timeframe": res_dict["extracted_entities"]["timeframe"],
                "competitor": res_dict["extracted_entities"].get("competitor")
            },
            "urgency": urgency_val,
            "scope": scope_val
        }
        print(json.dumps(output, indent=2))

if __name__ == "__main__":
    run_tests()
