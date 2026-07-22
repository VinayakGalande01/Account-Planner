import os
import sys
from dotenv import load_dotenv

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(override=True)

from pre_reasoning_layer import (
    EvidenceSelectorAgent, IntelligenceBriefAgent,
    ReasoningPlannerAgent, build_consensus_from_plan
)

def test_pre_reasoning():
    print("=== STARTING PRE-REASONING LAYER RESILIENCY & AGENTS TEST ===")
    
    # 1. Dummy retrieved CRM context
    retrieved_context = {
        "account_id": "ACC001",
        "account_name": "Infosys Ltd",
        "health_score": 85.0,
        "opportunities": [
            {
                "opp_id": "OPP001",
                "opp_name": "Infosys Cloud Migration",
                "amount_usd": 450000.0,
                "stage": "Negotiation",
                "close_date": "2026-08-30",
                "probability": 65
            }
        ],
        "contacts": [
            {
                "contact_id": "CON001",
                "name": "Nandan Nilekani",
                "role": "Executive Chairman",
                "title": "Chairman",
                "engagement_level": "High",
                "last_contact_date": "2026-07-10"
            }
        ],
        "cases": [
            {
                "case_id": "CASE001",
                "subject": "SLA breach on portal access",
                "severity": "High",
                "status": "In Progress"
            }
        ],
        "activities": [
            {
                "activity_id": "ACT001",
                "type": "Meeting",
                "description": "Reviewed cloud migration architecture.",
                "date": "2026-07-12"
            }
        ]
    }
    
    intent_json = {
        "primary_intent": "PIPELINE_ANALYSIS",
        "confidence_primary": 0.95,
        "extracted_entities": {
            "account": "Infosys",
            "stage": "Negotiation"
        },
        "urgency": "medium",
        "scope": "ENTITY",
        "complexity": "STRATEGIC"
    }

    # 2. Test Fallbacks (No Gemini Key)
    # We temporarily unset GEMINI_API_KEY to force fallback pathway
    orig_key = os.environ.get("GEMINI_API_KEY")
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]

    print("\n[Test 1] Verifying Fallback Pathway (when GEMINI_API_KEY is unset)...")
    try:
        evidence_bundle, ev_telemetry = EvidenceSelectorAgent().run(
            user_query="Analyze Infosys pipeline and open support cases",
            intent_json=intent_json,
            retrieved_context_json=retrieved_context,
            semantic_activities_json=[],
            data_sufficiency_score=0.85
        )
        print("  - Evidence Bundle generated successfully.")
        print(f"  - Fallback used: {ev_telemetry['fallback_used']}")
        print(f"  - Scope: {evidence_bundle.scope}")
        print(f"  - Relevant Opportunities count: {len(evidence_bundle.relevant_opportunities)}")

        brief, ib_telemetry = IntelligenceBriefAgent().run(
            user_query="Analyze Infosys pipeline and open support cases",
            intent_json=intent_json,
            evidence_bundle=evidence_bundle,
            intelligence_signals={},
            data_sufficiency_score=0.85
        )
        print("  - Intelligence Brief generated successfully.")
        print(f"  - Fallback used: {ib_telemetry['fallback_used']}")
        print(f"  - Maturity assessment: {brief.account_maturity}")
        print(f"  - Findings count: {len(brief.top_findings)}")

        plan, rp_telemetry = ReasoningPlannerAgent().run(
            user_query="Analyze Infosys pipeline and open support cases",
            response_mode="executive",
            intent_json=intent_json,
            intelligence_brief=brief
        )
        print("  - Reasoning Plan generated successfully.")
        print(f"  - Fallback used: {rp_telemetry['fallback_used']}")
        print(f"  - Answer mode: {plan.answer_mode}")
        print(f"  - Persona focus: {plan.persona_focus}")

        consensus = build_consensus_from_plan(plan, brief)
        print("  - Consensus constructed from plan successfully.")
        print(f"  - Consensus action: {consensus.consensus_recommendation.get('action')}")
        
    finally:
        # Restore key
        if orig_key:
            os.environ["GEMINI_API_KEY"] = orig_key

    # 3. Test LLM Pathway (If Gemini Key is configured in environment)
    if orig_key:
        print("\n[Test 2] Verifying Cloud Gemini Pathway...")
        try:
            evidence_bundle, ev_telemetry = EvidenceSelectorAgent().run(
                user_query="Analyze Infosys pipeline and open support cases",
                intent_json=intent_json,
                retrieved_context_json=retrieved_context,
                semantic_activities_json=[],
                data_sufficiency_score=0.85
            )
            print("  - Evidence Bundle successfully parsed from Gemini!")
            print(f"  - Latency: {ev_telemetry['latency_ms']} ms")
            print(f"  - Schema Valid: {ev_telemetry['schema_valid']}")
            print(f"  - Strategy Selected: {evidence_bundle.answer_strategy}")

            brief, ib_telemetry = IntelligenceBriefAgent().run(
                user_query="Analyze Infosys pipeline and open support cases",
                intent_json=intent_json,
                evidence_bundle=evidence_bundle,
                intelligence_signals={},
                data_sufficiency_score=0.85
            )
            print("  - Intelligence Brief successfully parsed from Gemini!")
            print(f"  - Severity of top finding: {brief.top_findings[0].severity if brief.top_findings else 'N/A'}")
            print(f"  - Dominant risk theme: {brief.dominant_risk_theme}")

            plan, rp_telemetry = ReasoningPlannerAgent().run(
                user_query="Analyze Infosys pipeline and open support cases",
                response_mode="executive",
                intent_json=intent_json,
                intelligence_brief=brief
            )
            print("  - Reasoning Plan successfully parsed from Gemini!")
            print(f"  - Answer Mode: {plan.answer_mode}")
            print(f"  - Candidate Conclusion: {plan.candidate_conclusion}")

        except Exception as e:
            print(f"  - Gemini pathway failed with error: {e}")
    else:
        print("\n[Test 2] Gemini API key not present in dotenv, skipping cloud pathway test.")

    print("\n=== PRE-REASONING LAYER TESTS COMPLETED ===")

if __name__ == "__main__":
    test_pre_reasoning()
