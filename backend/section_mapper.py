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
        complexity: str = "EXECUTIVE",
        pipeline_breakdown: Optional[dict] = None
    ) -> str:
        """
        Maps the structured output and consensus into the exact section tags 
        the frontend parser expects based on the complexity level.
        """
        parts = []

        if pipeline_breakdown and pipeline_breakdown.get("breakdown"):
            breakdown_str = json.dumps(pipeline_breakdown)
            parts.append(f"__SECTION_BREAKDOWN__\n{breakdown_str}")

        # 0. Intent (Common to all)
        parts.append(f"__SECTION_INTENT__\n{intent}")

        def safe_get(item, key, default=None):
            if item is None:
                return default
            if isinstance(item, dict):
                return item.get(key, default)
            return getattr(item, key, default)

        is_am = isinstance(response_obj, AMResponseOutput) or (isinstance(response_obj, dict) and "playbook_7day" in response_obj)
        is_vp = isinstance(response_obj, VPResponseOutput) or (isinstance(response_obj, dict) and "portfolio_impact" in response_obj)
        is_svp = isinstance(response_obj, SVPResponseOutput) or (isinstance(response_obj, dict) and "board_narrative" in response_obj)

        is_role_specific = is_am or is_vp or is_svp

        narrative = safe_get(response_obj, "narrative", "")
        why_this_matters = safe_get(response_obj, "why_this_matters", "")
        urgency = safe_get(response_obj, "urgency", "P2")

        if is_role_specific:
            # Headline
            headline = narrative
            parts.append(f"__SECTION_HEADLINE__\n{headline}")

            # Summary
            summary = ""
            if is_am:
                summary = why_this_matters
            elif is_vp:
                summary = f"Strategic Action: {safe_get(response_obj, 'strategic_action', '')}"
            elif is_svp:
                summary = f"Board Narrative: {safe_get(response_obj, 'board_narrative', '')}"
            parts.append(f"__SECTION_SUMMARY__\n{summary}")

            # Signals
            signals = []
            if is_am:
                risks = safe_get(response_obj, "risks_and_mitigations", [])
                for rm in risks:
                    r = safe_get(rm, "risk", "")
                    m = safe_get(rm, "mitigation", "")
                    signals.append(f"• RISK: {r} -> MITIGATION: {m}")
            elif is_vp:
                ms = safe_get(response_obj, "market_signal")
                comp = safe_get(ms, "competitor_threat", "")
                imp = safe_get(ms, "strategic_implication", "")
                signals.append(f"• MARKET THREAT: {comp}")
                signals.append(f"• IMPLICATION: {imp}")
            elif is_svp:
                cp = safe_get(response_obj, "competitive_positioning")
                tl = safe_get(cp, "threat_level", "")
                ms = safe_get(cp, "market_signal", "")
                signals.append(f"• THREAT LEVEL: {tl.upper()}")
                signals.append(f"• MARKET SIGNAL: {ms}")
            if signals:
                parts.append(f"__SECTION_SIGNALS__\n" + "\n".join(signals))

            # Actions
            actions = []
            if is_am:
                pb = safe_get(response_obj, "playbook_7day", [])
                for act in pb:
                    day = safe_get(act, "day", 1)
                    owner = safe_get(act, "owner", "")
                    txt = safe_get(act, "action", "")
                    actions.append(f"• Day {day} [{owner}]: {txt}")
                sh_seq = safe_get(response_obj, "stakeholder_sequence", [])
                for sh in sh_seq:
                    sh_role = safe_get(sh, "role", "")
                    sh_name = safe_get(sh, "stakeholder", "")
                    et = safe_get(sh, "engagement_type", "")
                    actions.append(f"• ENGAGE {sh_role} ({sh_name}) via {et}")
            elif is_vp:
                rr = safe_get(response_obj, "resource_recommendation")
                inv = safe_get(rr, "investment_required", "")
                teams = safe_get(rr, "teams_needed", [])
                timeline = safe_get(rr, "timeline", "")
                actions.append(f"• ALLOCATE: {inv}")
                actions.append(f"• MOBILIZE TEAMS: {', '.join(teams)} (Timeline: {timeline})")
            elif is_svp:
                df = safe_get(response_obj, "decision_framework", [])
                for item in df:
                    sc = safe_get(item, "scenario", "")
                    txt = safe_get(item, "action", "")
                    actions.append(f"• SCENARIO ({sc}): {txt}")
            if actions:
                parts.append(f"__SECTION_ACTIONS__\n" + "\n".join(actions))

            # Dissent
            dissenting = [d for d in consensus.dissenting_views if d.confidence >= 0.5]
            if dissenting:
                dissent_texts = [f"• {d.perspective} VIEW: {d.dissent} (Rationale: {d.rationale})" for d in dissenting]
                parts.append(f"__SECTION_DISSENT__\n" + "\n".join(dissent_texts))

        else:
            # 1. FACTUAL Blueprint: [Direct Answer, Confidence]
            if complexity == "FACTUAL":
                direct_answer = narrative or why_this_matters or "Factual data retrieved successfully."
                parts.append(f"__SECTION_DIRECT_ANSWER__\n{direct_answer}")

            # 1.5 CONVERSATIONAL Blueprint: [Direct Answer, Confidence]
            elif complexity == "CONVERSATIONAL":
                direct_answer = narrative or why_this_matters or "Hello! How can I help you today?"
                parts.append(f"__SECTION_DIRECT_ANSWER__\n{direct_answer}")

            # 2. OPERATIONAL Blueprint: [Headline, Summary, Table, Signals, Actions]
            elif complexity == "OPERATIONAL":
                # --- Contextual Headline ---
                data_perspective = safe_get(response_obj, "data_perspective", "")
                headline = data_perspective if data_perspective else "Pipeline Analysis"
                parts.append(f"__SECTION_HEADLINE__\n📊 {headline}")

                # --- Contextual Summary (warm framing above the table) ---
                summary_parts = []
                km = safe_get(response_obj, "key_metrics", {})
                health = safe_get(km, "health_score")
                churn = safe_get(km, "churn_probability")
                trend = safe_get(km, "engagement_trend", "")
                if health is not None:
                    summary_parts.append(f"Portfolio health score is **{health}%**")
                if churn is not None:
                    summary_parts.append(f"churn probability at **{churn * 100 if churn < 1 else churn}%**")
                if trend:
                    summary_parts.append(f"with a **{trend.lower()}** engagement trend")
                dq = safe_get(response_obj, "data_quality", {})
                dq_confidence = safe_get(dq, "confidence")
                if dq_confidence is not None:
                    summary_parts.append(f"Data quality confidence: **{dq_confidence * 100 if dq_confidence < 1 else dq_confidence}%**")
                if summary_parts:
                    parts.append(f"__SECTION_SUMMARY__\n" + ". ".join(summary_parts) + ".")
                else:
                    parts.append(f"__SECTION_SUMMARY__\nHere's the ranked operational view based on your current CRM data.")

                # --- Contextual Signals ---
                signals = []
                km = safe_get(response_obj, "key_metrics", {})
                health = safe_get(km, "health_score")
                if health is not None:
                    if health >= 80:
                        signals.append("• [PIPELINE] Portfolio health is strong — maintain current engagement cadence")
                    elif health >= 60:
                        signals.append(f"• [PIPELINE] Portfolio health at {health}% — moderate attention needed on at-risk deals")
                    else:
                        signals.append(f"• [RISK] Portfolio health at {health}% — immediate intervention recommended")
                
                intervention = safe_get(response_obj, "intervention_success_probability")
                if intervention is not None:
                    pct = int(intervention * 100) if intervention < 1 else int(intervention)
                    signals.append(f"• [STRATEGIC] Intervention success probability: {pct}%")
                
                # Historical context
                precedents = safe_get(response_obj, "historical_precedents", [])
                for p in precedents[:1]:
                    situation = safe_get(p, "situation", "")
                    success_rate = safe_get(p, "success_rate")
                    if situation and success_rate is not None:
                        signals.append(f"• [TEMPORAL] Historical pattern: {situation} (success rate: {int(success_rate * 100)}%)")
                
                dq = safe_get(response_obj, "data_quality", {})
                dq_metric = safe_get(dq, "metric", "")
                if dq_metric:
                    signals.append(f"• [CRM] Data quality check: {dq_metric}")
                
                if not signals:
                    signals.append("• [PIPELINE] Active pipeline metrics and quality audits are current")
                
                parts.append(f"__SECTION_SIGNALS__\n" + "\n".join(signals))
                
                # --- Contextual Actions ---
                actions = []
                km = safe_get(response_obj, "key_metrics", {})
                health = safe_get(km, "health_score")
                intervention = safe_get(response_obj, "intervention_success_probability")
                
                if health is not None and health < 70:
                    actions.append("• **Priority**: Review the deals flagged below and schedule executive check-ins for the top 3 by value")
                elif health is not None:
                    actions.append("• Review the ranked opportunities below and validate close dates for deals in the current quarter")
                
                if intervention is not None and intervention < 0.5:
                    actions.append("• Consider re-engaging with champions on stalled deals — success probability is below 50%")
                
                dq = safe_get(response_obj, "data_quality", {})
                limitation = safe_get(dq, "limitation", "")
                if limitation:
                    actions.append(f"• Data gap to address: {limitation}")
                
                if not actions:
                    actions.append("• Review the ranked data table and prioritize follow-up on top opportunities")
                
                parts.append(f"__SECTION_ACTIONS__\n" + "\n".join(actions))

            # 3. STRATEGIC / EXECUTIVE Blueprint: [Summary, Signals, Risks, Actions]
            else:
                # Headline
                headline = safe_get(response_obj, "headline", "Strategic Synthesis")
                parts.append(f"__SECTION_HEADLINE__\n{headline}")

                # Summary
                summary = safe_get(response_obj, "summary", "")
                parts.append(f"__SECTION_SUMMARY__\n{summary}")

                # Signals (Risks / Positioning / Market)
                signals = []
                parts.append(f"__SECTION_SIGNALS__\n" + "\n".join(signals))

                # Actions (Playbooks / Sequences)
                actions = []
                parts.append(f"__SECTION_ACTIONS__\n" + "\n".join(actions))

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
