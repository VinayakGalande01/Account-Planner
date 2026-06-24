import os
import sys
from dotenv import load_dotenv

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(override=True)

from reasoning_engine import (
    ConsensusOutput, ResponseGenerator, DissentingView
)

def test():
    print("=== STARTING RESPONSE GENERATOR TEST ===")
    
    # Mock a ConsensusOutput object
    mock_consensus = ConsensusOutput(
        consensus_recommendation={
            "action": "Initiate multi-threading strategy immediately to engage economic buyer.",
            "confidence": 0.85,
            "rationale": "High-value deal stalling at Proposal stage with only 1 contact mapped."
        },
        thread_agreement={
            "am": 0.9,
            "vp": 0.8,
            "svp": 0.7,
            "data": 0.85
        },
        agreement_score=0.81,
        dissenting_views=[
            DissentingView(
                perspective="SVP",
                dissent="Expressed concern on resource constraints for customer success.",
                confidence=0.5,
                rationale="CS team is at capacity."
            )
        ],
        confidence_limiting_factors=["High churn risk based on historical cases"],
        final_confidence=0.8
    )
    
    generator = ResponseGenerator()
    print(f"Using LLM URL: {generator.url}")
    print(f"Using LLM Model: {generator.model}")
    
    roles = ["am", "vp", "svp"]
    for role in roles:
        print(f"\nGenerating response for role: '{role.upper()}'...")
        try:
            res = generator.generate_response(mock_consensus, role)
            print(f"[{role.upper()} Narrative Summary]: {res.narrative}")
            print(f"[{role.upper()} Confidence]: {res.confidence if hasattr(res, 'confidence') else res.confidence_in_playbook}")
            if role == "am":
                print(f"AM Urgency: {res.urgency}")
                print(f"Playbook steps count: {len(res.playbook_7day)}")
            elif role == "vp":
                print(f"VP Strategic Action: {res.strategic_action}")
            elif role == "svp":
                print(f"SVP Board Narrative: {res.board_narrative}")
        except Exception as e:
            print(f"Failed to generate response for role '{role}': {e}")
            
    print("\n=== RESPONSE GENERATOR TEST COMPLETE ===")

if __name__ == "__main__":
    test()
