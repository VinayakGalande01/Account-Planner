import json
from reasoning_engine import repair_json_string

def run_tests():
    print("=== STARTING JSON REPAIR TEST SUITE ===")
    
    test_cases = [
        # Case 1: Missing comma between objects
        (
            """{
  "dissenting_views": [
    {
      "perspective": "VP|Data",
      "dissent": "Proceed with default operational plan."
    }
    {
      "perspective": "SVP",
      "dissent": "Invest in keeping this relationship."
    }
  ]
}""",
            True
        ),
        # Case 2: Python literals and single quotes
        (
            """{
  'am_perspective': 'The immediate risk is None',
  'playbook_7day': [
    {'day': True, 'action': False}
  ]
}""",
            True
        ),
        # Case 3: Raw newlines inside quotes
        (
            """{
  "rationale": "High risk of deal closure.
We need immediate action to resolve this issue.
Please coordinate with sales."
}""",
            True
        ),
        # Case 4: Missing comma between key-values
        (
            """{
  "action": "Schedule a call"
  "confidence": 0.6
  "rationale": "High risk"
}""",
            True
        ),
        # Case 5: Unbalanced brackets/braces (truncated JSON)
        (
            """{
  "consensus_recommendation": {
    "action": "Schedule a call",
    "confidence": 0.6""",
            True
        ),
        # Case 6: Truncated JSON ending inside a string value (unclosed double quote)
        (
            """{
  "playbook_7day": [{"day": 1}],
  "why_this_matters": "Data quality issues may impact account plan effectiveness""",
            True
        )
    ]
    
    all_passed = True
    for i, (raw_json, expected_success) in enumerate(test_cases, 1):
        print(f"\n--- Testing Case {i} ---")
        print(f"Raw text:\n{raw_json}")
        
        repaired = repair_json_string(raw_json)
        print(f"Repaired text:\n{repaired}")
        
        try:
            parsed = json.loads(repaired)
            print(f"Success! Parsed JSON: {parsed}")
        except Exception as e:
            print(f"Failed to parse! Error: {e}")
            all_passed = False
            
    if all_passed:
        print("\n=== ALL REPAIR TESTS PASSED SUCCESSFULLY ===")
    else:
        print("\n=== SOME REPAIR TESTS FAILED ===")

if __name__ == "__main__":
    run_tests()
