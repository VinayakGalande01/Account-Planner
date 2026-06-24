import os
import sys
from dotenv import load_dotenv

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(override=True)

from intent_classifier import IntentClassifier

def test():
    print("=== STARTING INTENT CLASSIFIER TEST ===")
    classifier = IntentClassifier()
    print(f"Using LLM URL: {getattr(classifier, 'url', 'N/A')}")
    print(f"Using LLM Model: {getattr(classifier, 'model', 'N/A')}")
    
    queries = [
        "Show me the top 5 opportunities stalling in negotiation",
        "Is Accenture at risk of churn?",
        "Who is the decision maker at Infosys?",
        "Where can we expand with Salesforce?"
    ]
    
    for q in queries:
        print(f"\nQuery: '{q}'")
        try:
            output = classifier.classify(q)
            print(f"Primary Intent: {output.primary_intent.value}")
            print(f"Confidence: {output.confidence_primary}")
            print(f"Scope: {output.scope.value}")
            print(f"Entities: {output.extracted_entities.dict(exclude_none=True)}")
            print(f"Summary: {output.context_summary}")
        except Exception as e:
            print(f"Failed to classify query: {e}")
            
    print("\n=== INTENT CLASSIFIER TEST COMPLETE ===")

if __name__ == "__main__":
    test()
