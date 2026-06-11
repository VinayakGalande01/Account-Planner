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
        response_obj: Union[AMResponseOutput, VPResponseOutput, SVPResponseOutput, dict],
        consensus: ConsensusOutput,
        data_sufficiency_score: float,
        intent: str = "ACTION_RECOMMENDATION_QUERY",
        complexity: str = "EXECUTIVE"
    ) -> str:
        """
        Maps the structured output and consensus into the exact section tags 
        the frontend parser expects based on the complexity level.
        """
        parts = []

        # 0. Intent (Common to all)
        parts.append(f"__SECTION_INTENT__\n{intent}")

        is_dict = isinstance(response_obj, dict)
        narrative = response_obj.get("narrative", "") if is_dict else getattr(response_obj, "narrative", "")
        why_this_matters = response_obj.get("why_this_matters", "") if is_dict else getattr(response_obj, "why_this_matters", "")
        urgency = response_obj.get("urgency", "P2") if is_dict else getattr(response_obj, "urgency", "P2")

        # 1. FACTUAL Blueprint: [Direct Answer, Confidence]
        if complexity == "FACTUAL":
            direct_answer = narrative or why_this_matters or "Factual data retrieved successfully."
            parts.append(f"__SECTION_DIRECT_ANSWER__\n{direct_answer}")

        # 2. OPERATIONAL Blueprint: [Headline, Table, Signals, Actions]
        elif complexity == "OPERATIONAL":
            headline = f"Operational Metrics Overview"
            parts.append(f"__SECTION_HEADLINE__\n{headline}")
            
            signals = []
            if is_dict:
                signals.append(f"• QUANTIFIED SUMMARY: {response_obj.get('data_perspective', 'Operational metrics loaded.')}")
            else:
                signals.append("• STATUS: Active pipeline metrics and quality audits are current.")
            parts.append(f"__SECTION_SIGNALS__\n" + "\n".join(signals))
            
            actions = ["• Action: Review operational metrics table shown below."]
            parts.append(f"__SECTION_ACTIONS__\n" + "\n".join(actions))

        # 3. STRATEGIC / EXECUTIVE Blueprint: [Summary, Signals, Risks, Actions]
        else:
            # Headline
            headline = ""
            if isinstance(response_obj, AMResponseOutput):
                headline = f"Urgency {urgency}: {narrative}"
            elif isinstance(response_obj, VPResponseOutput):
                headline = f"Portfolio Impact: {narrative}"
            elif isinstance(response_obj, SVPResponseOutput):
                headline = f"Strategic Brief: {narrative}"
            elif is_dict:
                headline = response_obj.get("headline", "Strategic Synthesis")
            parts.append(f"__SECTION_HEADLINE__\n{headline}")

            # Summary
            summary = ""
            if isinstance(response_obj, AMResponseOutput):
                summary = why_this_matters
            elif isinstance(response_obj, VPResponseOutput):
                summary = f"Strategic Action: {response_obj.strategic_action}"
            elif isinstance(response_obj, SVPResponseOutput):
                summary = f"Board Narrative: {response_obj.board_narrative}"
            elif is_dict:
                summary = response_obj.get("summary", "")
            parts.append(f"__SECTION_SUMMARY__\n{summary}")

            # Signals (Risks / Positioning / Market)
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

            # Actions (Playbooks / Sequences)
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

            # Dissent
            dissenting = [d for d in consensus.dissenting_views if d.confidence >= 0.5]
            if dissenting:
                dissent_texts = [f"• {d.perspective} VIEW: {d.dissent} (Rationale: {d.rationale})" for d in dissenting]
                parts.append(f"__SECTION_DISSENT__\n" + "\n".join(dissent_texts))

        # 6. CRM Hygiene (Common validation check)
        hygiene = []
        if data_sufficiency_score < 0.4:
            hygiene.append("⚠️ WARNING: CRM data sufficiency is critically low. Please update opportunities and contacts.")
            for clf in consensus.confidence_limiting_factors:
                hygiene.append(f"⚠️ {clf}")
        if hygiene:
            parts.append(f"__SECTION_CRM_HYGIENE__\n" + "\n".join(hygiene))

        # 7. Confidence (Common to all)
        confidence_json = json.dumps({
            "score": f"{consensus.final_confidence * 100:.0f}%",
            "status": "Factual Grounding" if complexity == "FACTUAL" else "Consensus Formed",
            "sources": [f"Agreement: {consensus.agreement_score * 100:.0f}%"] if complexity != "FACTUAL" else ["CRM Database Engine"]
        })
        parts.append(f"__SECTION_CONFIDENCE__\n{confidence_json}")

        # 8. End Tag
        parts.append("__SECTION_END__")

        return "\n".join(parts)
