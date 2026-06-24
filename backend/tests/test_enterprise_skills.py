import os
import sys

# Ensure backend directory is in the path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_path)

from intent_classifier import IntentClassifier

def run_enterprise_tests():
    print("=========================================================")
    print("[RUN] APEX INTENT CLASSIFIER - PHASE 1 MANUAL VERIFICATION")
    print("=========================================================\n")
    
    queries = [
        "Give me the top 5 opportunities stalling in the negotiation stage.",
        "Who are the key decision makers at Accenture and when was the last time we contacted them?",
        "Show me the highest risk accounts with critical open support cases",
        "What opportunities are closing in the next 30 days and what is our weighted forecast?",
        "Give me a strategic account plan for Accenture.",
        "What are my top priority actions for today?",
        "Who is the primary decision maker at ServiceNow and are there any unmapped key influencers we need to engage?",
        "Which stakeholders at Accenture are acting as blockers, and what is our action plan to align them?",
        "What is our total value-at-risk for opportunities stalling in the perception stage, and what is the expected revenue impact of resolving them?",
        "Show me the deal velocity and estimated risk reduction percentage for our active pipeline.",
        "Provide a complete strategic review of our opportunity with Grab Holdings, tracing our key observations to next recommended steps.",
        "What is the strategic focus for Deloitte India, and what observations from the raw cases database support this?",
        "Evaluate our pipeline confidence. Are there accounts with stale activity notes (>30 days) where we need to downgrade our reasoning confidence?",
        "Who is the decision maker at accenture?",
        "is servicenow stalling in proposal?",
        "hello",
        "anyone there",
        "hey, what's up?"
    ]
    
    known_accounts = ["Accenture", "ServiceNow", "Deloitte India", "Grab Holdings"]
    classifier = IntentClassifier(known_accounts=known_accounts)
    
    for idx, q in enumerate(queries, 1):
        res = classifier.classify(q)
        print(f"[{idx}] Query: \"{q}\"")
        print(f"    |- Scope:      {res.scope}")
        print(f"    |- Complexity: {res.complexity}")
        print(f"    |- Intent:     {res.intent}")
        print(f"    |- Entities:   {res.target_entities}")
        print("-" * 65)

if __name__ == "__main__":
    run_enterprise_tests()
