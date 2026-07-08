import json
from reasoning_engine import generate_contextual_fallback_data, ResponseGenerator, ConsensusOutput

def test_contextual_fallback_content():
    # Mock account data
    mock_account = {
        "account_name": "Acme Corp",
        "health_score": 75.5,
        "opportunities": [
            {"opp_name": "Cloud Expansion", "amount_usd": 150000.0, "stage": "Proposal"}
        ],
        "contacts": [
            {"name": "Alice Smith", "role": "VP of IT"}
        ],
        "cases": [
            {"case_id": "CS-101", "subject": "Billing discrepancy", "severity": "medium"}
        ]
    }
    
    fallback_data = generate_contextual_fallback_data(mock_account)
    
    # 1. Verify schema keys exist
    assert "executive_brief" in fallback_data
    assert "persona_insights" in fallback_data
    assert "tactical_playbook" in fallback_data
    
    # 2. Verify natural wording (should NOT contain technical fallback indicators)
    macro_summary = fallback_data["executive_brief"]["macro_summary"]
    assert "Acme Corp" in macro_summary
    assert "$150,000.00" in macro_summary
    assert "75.5%" in macro_summary
    assert "fallback" not in macro_summary.lower()
    assert "error" not in macro_summary.lower()
    assert "default" not in macro_summary.lower()
    
    ae_insight = fallback_data["persona_insights"]["enterprise_ae"]
    assert "Alice Smith" in ae_insight
    assert "VP of IT" in ae_insight
    
    director_insight = fallback_data["persona_insights"]["strategic_director"]
    assert "Billing discrepancy" in director_insight
    
    # 3. Test Response Mapping (Zero LLM Latency path)
    consensus = ConsensusOutput(
        consensus_recommendation={
            "action": "Proceed with Crucible recommendations.",
            "confidence": 0.85,
            "rationale": macro_summary,
            "crucible_data": fallback_data
        },
        thread_agreement={"am": 0.85, "vp": 0.85, "svp": 0.85, "data": 0.90},
        agreement_score=0.85,
        dissenting_views=[],
        confidence_limiting_factors=[],
        final_confidence=0.85
    )
    
    generator = ResponseGenerator(is_local=True)
    
    # Generate for AM
    am_res = generator.generate_response(consensus, "am")
    assert am_res.narrative == macro_summary
    assert len(am_res.playbook_7day) == 3
    assert am_res.playbook_7day[0].action.startswith("Review stage and details of opportunity 'Cloud Expansion'")
    
    # Generate for VP
    vp_res = generator.generate_response(consensus, "vp")
    assert vp_res.narrative == macro_summary
    assert vp_res.portfolio_impact.total_arr_at_risk == "$150,000.00"
    
    # Generate for SVP
    svp_res = generator.generate_response(consensus, "svp")
    assert svp_res.narrative == macro_summary
    assert svp_res.strategic_context.strategic_fit == "KEEP"

    print("Success: Fallback and Crucible mapping validation test passed successfully!")
