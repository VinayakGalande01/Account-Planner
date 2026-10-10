
import os
import sys
from dotenv import load_dotenv

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(override=True)

from database import SessionLocal
from data_engine import DataEngine
from agent_orchestrator import AccountPlanningAgent

def test():
    print("=== STARTING AGENT ORCHESTRATOR TEST ===")
    
    # Initialize live DataEngine with database session
    db_session = SessionLocal()
    engine = DataEngine(db_session, user_id=1)

    
    # Instantiate the planning agent
    agent = AccountPlanningAgent(data_engine=engine)
    
    query = "Show me top 5 opportunities stalling in negotiation at Accenture and what to do"
    print(f"\nProcessing query: '{query}'")
    
    try:
        result = agent.process_query(
            query=query,
            user_role="Account Manager",
            recipient_roles=["am", "vp"]
        )
        
        print("\n--- PROCESS QUERY SUCCESSFUL ---")
        print(f"Status: {result['status']}")
        print(f"Intent classified: {result['intent'].primary_intent.value} (Confidence: {result['intent'].confidence_primary})")
        print(f"Entities: {result['intent'].extracted_entities.dict(exclude_none=True)}")
        print(f"Data Quality: {result.get('data_quality_score')}")
        print(f"Consensus recommendation action: {result['consensus'].consensus_recommendation.get('action')}")
        print(f"Overall Confidence: {result['confidence']}")
        print(f"AM Response narrative: {result['responses']['am'].narrative}")
        print(f"VP Response narrative: {result['responses']['vp'].narrative}")
        
    except Exception as e:
        print(f"Failed to process query: {e}")
        
    print("\n=== AGENT ORCHESTRATOR TEST COMPLETE ===")

if __name__ == "__main__":
    test()
