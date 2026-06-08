import json
from typing import Union, List, Optional
from reasoning_engine import AMResponseOutput, VPResponseOutput, SVPResponseOutput, ConsensusOutput

class SectionContractMapper:
    """
    Translates Pydantic Layer 3 role-specific outputs into the legacy streaming 
    string contract format expected by the frontend.
    """
    
    @staticmethod
    def map_to_stream(
        response_obj: Union[AMResponseOutput, VPResponseOutput, SVPResponseOutput],
        consensus: ConsensusOutput,
        data_sufficiency_score: float,
        intent: str = "ACTION_RECOMMENDATION_QUERY"
    ) -> str:
        """
        Maps the structured output and consensus into the exact section tags 
        the frontend parser expects.
        """
        parts = []

        # 0. Intent
        parts.append(f"__SECTION_INTENT__\n{intent}")

        # 1. Headline
        headline = ""
        if isinstance(response_obj, AMResponseOutput):
            headline = f"Urgency {response_obj.urgency}: {response_obj.narrative}"
        elif isinstance(response_obj, VPResponseOutput):
            headline = f"Portfolio Impact: {response_obj.narrative}"
        elif isinstance(response_obj, SVPResponseOutput):
            headline = f"Strategic Brief: {response_obj.narrative}"
        parts.append(f"__SECTION_HEADLINE__\n{headline}")

        # 2. Summary
        summary = ""
        if isinstance(response_obj, AMResponseOutput):
            summary = response_obj.why_this_matters
        elif isinstance(response_obj, VPResponseOutput):
            summary = f"Strategic Action: {response_obj.strategic_action}"
        elif isinstance(response_obj, SVPResponseOutput):
            summary = f"Board Narrative: {response_obj.board_narrative}"
        parts.append(f"__SECTION_SUMMARY__\n{summary}")

        # 3. Signals (Risks / Positioning / Market)
        signals = []
        if isinstance(response_obj, AMResponseOutput):
            for rm in response_obj.risks_and_mitigations:
                signals.append(f"• RISK: {rm.risk} -> MITIGATION: {rm.mitigation}")
        elif isinstance(response_obj, VPResponseOutput):
            ms = response_obj.market_signal
            signals.append(f"• MARKET THREAT: {ms.competitor_threat}")
            signals.append(f"• IMPLICATION: {ms.strategic_implication}")
        elif isinstance(response_obj, SVPResponseOutput):
            cp = response_obj.competitive_positioning
            signals.append(f"• THREAT LEVEL: {cp.threat_level.upper()}")
            signals.append(f"• MARKET SIGNAL: {cp.market_signal}")
        
        if signals:
            parts.append(f"__SECTION_SIGNALS__\n" + "\n".join(signals))

        # 4. Actions (Playbooks / Sequences)
        actions = []
        if isinstance(response_obj, AMResponseOutput):
            for action in response_obj.playbook_7day:
                actions.append(f"• Day {action.day} [{action.owner}]: {action.action}")
            for sh in response_obj.stakeholder_sequence:
                actions.append(f"• ENGAGE {sh.role} ({sh.stakeholder}) via {sh.engagement_type}")
        elif isinstance(response_obj, VPResponseOutput):
            rr = response_obj.resource_recommendation
            actions.append(f"• ALLOCATE: {rr.investment_required}")
            actions.append(f"• MOBILIZE TEAMS: {', '.join(rr.teams_needed)} (Timeline: {rr.timeline})")
        elif isinstance(response_obj, SVPResponseOutput):
            for df in response_obj.decision_framework:
                actions.append(f"• SCENARIO ({df.scenario}): {df.action}")
                
        if actions:
            parts.append(f"__SECTION_ACTIONS__\n" + "\n".join(actions))

        # 5. Dissent (if any threads disagreed)
        dissenting = [d for d in consensus.dissenting_views if d.confidence >= 0.5]
        if dissenting:
            dissent_texts = [f"• {d.perspective} VIEW: {d.dissent} (Rationale: {d.rationale})" for d in dissenting]
            parts.append(f"__SECTION_DISSENT__\n" + "\n".join(dissent_texts))

        # 6. CRM Hygiene (if data sufficiency is low)
        hygiene = []
        if data_sufficiency_score < 40.0:
            hygiene.append("⚠️ WARNING: CRM data sufficiency is critically low. AI reasoning confidence has been capped to prevent hallucinations. Please update opportunities and contacts.")
            for clf in consensus.confidence_limiting_factors:
                hygiene.append(f"⚠️ {clf}")
        if hygiene:
            parts.append(f"__SECTION_CRM_HYGIENE__\n" + "\n".join(hygiene))

        # 7. Confidence
        confidence_json = json.dumps({
            "score": f"{consensus.final_confidence * 100:.0f}%",
            "status": "Consensus Formed",
            "sources": [f"Agreement: {consensus.agreement_score * 100:.0f}%"]
        })
        parts.append(f"__SECTION_CONFIDENCE__\n{confidence_json}")

        # 8. End Tag
        parts.append("__SECTION_END__")

        return "\n".join(parts)
