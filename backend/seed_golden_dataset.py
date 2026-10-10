"""
GOLDEN DATASET SEEDER (seed_golden_dataset.py)
Seeds evaluation benchmark records (32 gold-standard query cases across 8 intent categories)
into PostgreSQL or SQLite databases for evaluation testing and accuracy benchmarking.
"""

# --- SECTION 1: Dependencies & Import Setup ---
# Imports database engines, environment variables, and evaluation model schemas.
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from database import SessionLocal, get_engine, DATABASE_URL
from models.eval_models import GoldenDataset

# --- SECTION 2: Gold-Standard Seed Benchmark Cases ---
# Defines ground-truth test cases for risk assessment, expansion, competitive, and relationship queries.
SEED_CASES = [
    # ─── 1. RISK_ASSESSMENT ───
    {
        "query": "TCS stale activity notes and blockers",
        "expected_intent": "risk_assessment",
        "expected_entities": {"account": "TCS", "metric": "stale activity"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["risk", "activity", "TCS"],
        "expected_recommendation_type": "RISK_MITIGATION"
    },
    {
        "query": "What is the account risk for Wipro?",
        "expected_intent": "risk_assessment",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "CRITICAL",
        "tags": ["risk", "account_health", "Wipro"],
        "expected_recommendation_type": "RISK_MITIGATION"
    },
    {
        "query": "Critical support tickets open for TCS",
        "expected_intent": "risk_assessment",
        "expected_entities": {"account": "TCS", "metric": "support tickets"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["risk", "support", "TCS"],
        "expected_recommendation_type": "RISK_MITIGATION"
    },
    {
        "query": "List the risk factors in Wipro's pipeline",
        "expected_intent": "risk_assessment",
        "expected_entities": {"account": "Wipro", "metric": "pipeline risk"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["risk", "pipeline", "Wipro"],
        "expected_recommendation_type": "RISK_MITIGATION"
    },

    # ─── 2. OPPORTUNITY_EXPANSION ───
    {
        "query": "Identify upsell opportunities for Wipro",
        "expected_intent": "opportunity_expansion",
        "expected_entities": {"account": "Wipro", "metric": "upsell"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["opportunity", "upsell", "Wipro"],
        "expected_recommendation_type": "GROWTH_STRATEGY"
    },
    {
        "query": "Where can we expand in the TCS account?",
        "expected_intent": "opportunity_expansion",
        "expected_entities": {"account": "TCS"},
        "expected_confidence": "HIGH",
        "priority": "CRITICAL",
        "tags": ["opportunity", "expansion", "TCS"],
        "expected_recommendation_type": "GROWTH_STRATEGY"
    },
    {
        "query": "Wipro expansion strategies for IT infrastructure",
        "expected_intent": "opportunity_expansion",
        "expected_entities": {"account": "Wipro", "metric": "IT infrastructure"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["opportunity", "expansion", "Wipro"],
        "expected_recommendation_type": "GROWTH_STRATEGY"
    },
    {
        "query": "What is the expansion potential for TCS Q3?",
        "expected_intent": "opportunity_expansion",
        "expected_entities": {"account": "TCS", "timeframe": "Q3"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["opportunity", "expansion", "TCS", "Q3"],
        "expected_recommendation_type": "GROWTH_STRATEGY"
    },

    # ─── 3. COMPETITIVE_INTELLIGENCE ───
    {
        "query": "Who is the competitor in Wipro deals?",
        "expected_intent": "competitive_intelligence",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["competitive", "competitors", "Wipro"],
        "expected_recommendation_type": "COMPETITIVE_DEFENSE"
    },
    {
        "query": "How is TCS positioning against competitor X?",
        "expected_intent": "competitive_intelligence",
        "expected_entities": {"account": "TCS", "competitor": "X"},
        "expected_confidence": "HIGH",
        "priority": "CRITICAL",
        "tags": ["competitive", "positioning", "TCS"],
        "expected_recommendation_type": "COMPETITIVE_DEFENSE"
    },
    {
        "query": "What competitive threats do we see at Wipro?",
        "expected_intent": "competitive_intelligence",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["competitive", "threats", "Wipro"],
        "expected_recommendation_type": "COMPETITIVE_DEFENSE"
    },
    {
        "query": "Competitor analysis for the TCS account",
        "expected_intent": "competitive_intelligence",
        "expected_entities": {"account": "TCS"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["competitive", "analysis", "TCS"],
        "expected_recommendation_type": "COMPETITIVE_DEFENSE"
    },

    # ─── 4. RELATIONSHIP_ANALYSIS ───
    {
        "query": "Who are the key stakeholders in Wipro?",
        "expected_intent": "relationship_analysis",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["relationship", "stakeholders", "Wipro"],
        "expected_recommendation_type": "RELATIONSHIP_BUILDING"
    },
    {
        "query": "CIO contact details and engagement level for TCS",
        "expected_intent": "relationship_analysis",
        "expected_entities": {"account": "TCS", "metric": "CIO"},
        "expected_confidence": "HIGH",
        "priority": "CRITICAL",
        "tags": ["relationship", "CIO", "TCS"],
        "expected_recommendation_type": "RELATIONSHIP_BUILDING"
    },
    {
        "query": "Wipro executive relationship health",
        "expected_intent": "relationship_analysis",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["relationship", "executive", "Wipro"],
        "expected_recommendation_type": "RELATIONSHIP_BUILDING"
    },
    {
        "query": "Who are the decision makers in the TCS opportunity?",
        "expected_intent": "relationship_analysis",
        "expected_entities": {"account": "TCS"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["relationship", "decision_makers", "TCS"],
        "expected_recommendation_type": "RELATIONSHIP_BUILDING"
    },

    # ─── 5. ACTION_RECOMMENDATION ───
    {
        "query": "Action plan to unblock Wipro stuck deal",
        "expected_intent": "action_recommendation",
        "expected_entities": {"account": "Wipro", "stage": "stuck"},
        "expected_confidence": "HIGH",
        "priority": "CRITICAL",
        "tags": ["action", "stuck_deal", "Wipro", "regression"],
        "expected_recommendation_type": "ACTION_PLAN"
    },
    {
        "query": "What is the recommended playbook for TCS?",
        "expected_intent": "action_recommendation",
        "expected_entities": {"account": "TCS"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["action", "playbook", "TCS", "regression"],
        "expected_recommendation_type": "ACTION_PLAN"
    },
    {
        "query": "How to mitigate risk for Wipro pipeline?",
        "expected_intent": "action_recommendation",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["action", "mitigation", "Wipro", "regression"],
        "expected_recommendation_type": "ACTION_PLAN"
    },
    {
        "query": "Next steps for Wipro stakeholder alignment",
        "expected_intent": "action_recommendation",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["action", "stakeholder", "Wipro", "regression"],
        "expected_recommendation_type": "ACTION_PLAN"
    },

    # ─── 6. PIPELINE_SUMMARY ───
    {
        "query": "Show me the Wipro pipeline summary",
        "expected_intent": "pipeline_summary",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["pipeline", "summary", "Wipro", "regression"],
        "expected_recommendation_type": "PIPELINE_REVIEW"
    },
    {
        "query": "Weighted forecast review for TCS Q3",
        "expected_intent": "pipeline_summary",
        "expected_entities": {"account": "TCS", "timeframe": "Q3"},
        "expected_confidence": "HIGH",
        "priority": "CRITICAL",
        "tags": ["pipeline", "forecast", "TCS", "Q3", "regression"],
        "expected_recommendation_type": "PIPELINE_REVIEW"
    },
    {
        "query": "Active opportunities list for Wipro",
        "expected_intent": "pipeline_summary",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["pipeline", "opportunities", "Wipro", "regression"],
        "expected_recommendation_type": "PIPELINE_REVIEW"
    },
    {
        "query": "High value opportunities in negotiation for TCS",
        "expected_intent": "pipeline_summary",
        "expected_entities": {"account": "TCS", "stage": "negotiation"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["pipeline", "negotiation", "TCS", "regression"],
        "expected_recommendation_type": "PIPELINE_REVIEW"
    },

    # ─── 7. DRAFT_EMAIL ───
    {
        "query": "Draft an email to the Wipro CIO about their open ticket",
        "expected_intent": "draft_email",
        "expected_entities": {"account": "Wipro", "metric": "CIO"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["email", "draft", "Wipro", "regression"],
        "expected_recommendation_type": "EMAIL_DRAFT"
    },
    {
        "query": "Write an email to TCS stakeholder proposing a meeting",
        "expected_intent": "draft_email",
        "expected_entities": {"account": "TCS"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["email", "draft", "TCS", "regression"],
        "expected_recommendation_type": "EMAIL_DRAFT"
    },
    {
        "query": "Draft a follow-up email for the Wipro expansion deal",
        "expected_intent": "draft_email",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["email", "draft", "Wipro", "regression"],
        "expected_recommendation_type": "EMAIL_DRAFT"
    },
    {
        "query": "Write an introductory email to the new TCS contact",
        "expected_intent": "draft_email",
        "expected_entities": {"account": "TCS"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["email", "draft", "TCS", "regression"],
        "expected_recommendation_type": "EMAIL_DRAFT"
    },

    # ─── 8. MEETING_AGENDA ───
    {
        "query": "Prepare a meeting agenda for Wipro Q3 review",
        "expected_intent": "meeting_agenda",
        "expected_entities": {"account": "Wipro", "timeframe": "Q3"},
        "expected_confidence": "HIGH",
        "priority": "HIGH",
        "tags": ["agenda", "meeting", "Wipro", "regression"],
        "expected_recommendation_type": "AGENDA_PREP"
    },
    {
        "query": "Create an agenda for the TCS opportunity alignment meeting",
        "expected_intent": "meeting_agenda",
        "expected_entities": {"account": "TCS"},
        "expected_confidence": "HIGH",
        "priority": "CRITICAL",
        "tags": ["agenda", "meeting", "TCS", "regression"],
        "expected_recommendation_type": "AGENDA_PREP"
    },
    {
        "query": "Generate a stakeholder meeting agenda for Wipro",
        "expected_intent": "meeting_agenda",
        "expected_entities": {"account": "Wipro"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["agenda", "meeting", "Wipro", "regression"],
        "expected_recommendation_type": "AGENDA_PREP"
    },
    {
        "query": "TCS account review meeting agenda",
        "expected_intent": "meeting_agenda",
        "expected_entities": {"account": "TCS"},
        "expected_confidence": "HIGH",
        "priority": "MEDIUM",
        "tags": ["agenda", "meeting", "TCS", "regression"],
        "expected_recommendation_type": "AGENDA_PREP"
    }
]

def main():
    print("=== SEEDING APEX GOLDEN DATASET ===")
    
    # Check if target is postgres and use admin_url if so, similar to rebuild_db.py
    if DATABASE_URL.startswith("postgresql") or "aws-1-ap-southeast-2.pooler.supabase.com" in DATABASE_URL:
        admin_url = os.getenv("ADMIN_DATABASE_URL", DATABASE_URL)
        print("[INFO] PostgreSQL detected. Using admin credentials for seeding...")
        engine = create_engine(admin_url)
        Session = sessionmaker(bind=engine)
        db = Session()
    else:
        db = SessionLocal()
        
    try:
        # Check if table already contains data
        existing_count = db.query(GoldenDataset).count()
        if existing_count > 0:
            print(f"[INFO] Golden dataset already contains {existing_count} records. Clearing table first...")
            db.query(GoldenDataset).delete()
            db.commit()
            
        print(f"[INFO] Seeding {len(SEED_CASES)} cases...")
        for case in SEED_CASES:
            # owner_id is set to 1 for bootstrap/default owner
            db_case = GoldenDataset(
                query=case["query"],
                expected_intent=case["expected_intent"],
                expected_entities=case["expected_entities"],
                expected_confidence=case["expected_confidence"],
                priority=case["priority"],
                tags=case["tags"],
                expected_recommendation_type=case["expected_recommendation_type"],
                owner_id=1,
                source="MANUAL",
                status="ACTIVE"
            )
            db.add(db_case)
        db.commit()
        print(f"[SUCCESS] Golden dataset seeded with {len(SEED_CASES)} records!")
    except Exception as e:
        print(f"[ERROR] Failed to seed dataset: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
