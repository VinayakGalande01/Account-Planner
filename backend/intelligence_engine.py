"""
DETERMINISTIC INTELLIGENCE ENGINE (intelligence_engine.py)
Analyzes CRM account data to compute pipeline risks, stale deal alerts,
stakeholder engagement gaps, and composite Intelligence Briefs with zero LLM calls.
"""

# --- SECTION 1: Dependencies & Class Definition ---
# Imports JSON, datetime tools, and dictionary type hints for rule-based analysis.
import json
import datetime
import os
from typing import Dict, Any, List


CLOSED_STAGES = {"Closed Won", "Closed Lost", "Dead/Lost"}


def open_opportunities(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Closed deals are history, not active pipeline."""
    return [o for o in opportunities if o.get("stage", "") not in CLOSED_STAGES]


def reference_date() -> datetime.date:
    """Date that deal staleness is measured against: today, or APEX_REFERENCE_DATE (YYYY-MM-DD) for reproducible tests."""
    override = os.getenv("APEX_REFERENCE_DATE")
    return datetime.date.fromisoformat(override) if override else datetime.date.today()

# --- SECTION 2: Intelligence Computation Engine ---
# Evaluates account data against deterministic heuristics for deal velocity and risk analysis.
class IntelligenceEngine:
    @staticmethod
    def compute(account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes CRM account data deterministically and generates strategic alerts & insights.
        Zero LLM calls. Extremely fast and robust.
        """
        opportunities = open_opportunities(account_data.get("opportunities", []))
        contacts = account_data.get("contacts", [])
        cases = account_data.get("cases", [])
        activities = account_data.get("activities", [])
        health_score = account_data.get("health_score", 80.0)
        account_name = account_data.get("account_name", "Global Portfolio")

        # Configuration constants
        anchor_date = reference_date()
        
        # 1. Stale Deals Analysis
        stale_deals = []
        total_pipeline = sum(o.get("amount_usd", 0.0) for o in opportunities)
        
        for o in opportunities:
            stage = o.get("stage", "")
            val = o.get("amount_usd", 0.0)
            
            # Simple heuristic: if opportunity is in commercial/negotiation stage and close date is past anchor_date
            close_date_str = o.get("close_date", "")
            days_past = 0
            is_past_close = False
            if close_date_str:
                try:
                    close_date = datetime.datetime.strptime(close_date_str[:10], "%Y-%m-%d").date()
                    if close_date < anchor_date:
                        is_past_close = True
                        days_past = (anchor_date - close_date).days
                except ValueError:
                    pass
            
            # Check latest activity for this opportunity/account
            days_since_activity = 999
            for act in activities:
                act_date_str = act.get("date", "")
                if act_date_str:
                    try:
                        act_date = datetime.datetime.strptime(act_date_str[:10], "%Y-%m-%d").date()
                        diff = (anchor_date - act_date).days
                        if diff < days_since_activity:
                            days_since_activity = diff
                    except ValueError:
                        pass
            
            # Flag as stale if past close date or no activity for > 30 days in advanced stages
            if is_past_close or (days_since_activity > 30 and stage in ["Negotiation", "Proposal", "Contract Review", "Signed & Activated"]):
                stale_deals.append({
                    "opp_name": o.get("opp_name", "Unknown Deal"),
                    "value_usd": val,
                    "stage": stage,
                    "days_stalled": max(days_past, days_since_activity if days_since_activity != 999 else 30)
                })

        # 2. Single-Threaded Risk
        dm_roles = ["director", "vp", "cxo", "chief", "head", "manager", "ceo", "coo", "cto", "cfo", "president", "officer", "lead"]
        dm_count = sum(1 for c in contacts if any(r in c.get("role", "").lower() for r in dm_roles))
        is_single_threaded = len(contacts) <= 2 or dm_count == 0
        
        single_threaded_opps = []
        if is_single_threaded and opportunities:
            for o in opportunities:
                single_threaded_opps.append({
                    "opp_name": o.get("opp_name", ""),
                    "value_usd": o.get("amount_usd", 0.0),
                    "primary_contact": contacts[0].get("name", "None") if contacts else "None"
                })

        # 3. Case-Opportunity Overlap
        critical_cases = [c for c in cases if c.get("severity") in ["P1", "Critical", "High"] and c.get("status") != "Closed"]
        case_opp_overlap = []
        if critical_cases and opportunities:
            for cc in critical_cases:
                for o in opportunities:
                    case_opp_overlap.append({
                        "case_id": cc.get("case_id"),
                        "case_subject": cc.get("subject"),
                        "opp_name": o.get("opp_name"),
                        "value_usd": o.get("amount_usd", 0.0)
                    })

        # 4. Revenue Concentration
        revenue_concentration_pct = 0.0
        if total_pipeline > 0 and len(opportunities) > 0:
            sorted_opps = sorted(opportunities, key=lambda x: x.get("amount_usd", 0.0), reverse=True)
            top_2_sum = sum(o.get("amount_usd", 0.0) for o in sorted_opps[:2])
            revenue_concentration_pct = (top_2_sum / total_pipeline) * 100.0

        # 5. Churn Risk Index (0.0 to 1.0)
        churn_score = 0.0
        if health_score < 60:
            churn_score += 0.4
        elif health_score < 80:
            churn_score += 0.2
            
        if critical_cases:
            churn_score += 0.4
        if len(stale_deals) > 0:
            churn_score += 0.2
            
        churn_risk_index = min(churn_score, 1.0)

        # 6. Generate narrative bullets
        narrative_bullets = []
        
        if stale_deals:
            stale_sum = sum(d["value_usd"] for d in stale_deals)
            stale_names = ", ".join([f"'{d['opp_name']}'" for d in stale_deals[:2]])
            narrative_bullets.append(
                f"⚠️ pipeline stagnation: {len(stale_deals)} deal(s) totaling ${stale_sum:,.0f} (including {stale_names}) have had no activity for over 30 days."
            )
            
        if is_single_threaded and opportunities:
            narrative_bullets.append(
                f"📌 single-threaded risk: Thin relationship coverage detected ({len(contacts)} contacts). Flagship deals are vulnerable to single-point-of-failure if contacts change roles."
            )
            
        if case_opp_overlap:
            overlap_names = ", ".join(f"'{name}'" for name in list(dict.fromkeys(c['case_subject'] for c in case_opp_overlap))[:2])
            narrative_bullets.append(
                f"🔴 critical ticket overlap: Open escalation ({overlap_names}) is directly threatening active pipeline value of ${total_pipeline:,.0f}."
            )
            
        if revenue_concentration_pct > 70.0 and len(opportunities) >= 3:
            narrative_bullets.append(
                f"📊 revenue concentration: {revenue_concentration_pct:.1f}% of active pipeline is concentrated in just the top 2 deals, posing a portfolio imbalance threat."
            )
            
        if health_score < 70.0:
            narrative_bullets.append(
                f"⚡ account health warning: Health score is critically low at {health_score:.1f}%, indicating a high risk of churn unless active support tickets are resolved."
            )

        if not narrative_bullets:
            narrative_bullets.append(
                f"✅ account status healthy: Active pipeline of ${total_pipeline:,.0f} across {len(opportunities)} deals is well-diversified with normal stakeholder engagement and no unresolved escalations."
            )

        return {
            "stale_deals": stale_deals,
            "single_threaded_opps": single_threaded_opps,
            "case_opp_overlap": case_opp_overlap,
            "revenue_concentration_pct": revenue_concentration_pct,
            "churn_risk_index": churn_risk_index,
            "narrative_bullets": narrative_bullets
        }

    @staticmethod
    def build_intelligence_brief(
        account_data: Dict[str, Any],
        data_quality_score: float = 0.7
    ) -> Any:
        """
        New primary intelligence pipeline.
        Returns a structured IntelligenceBrief from the Pattern Registry.
        """
        # Lazy imports to avoid circular reference issues if any
        from patterns.models import IntelligenceBrief, Finding
        from patterns.registry import ALL_PATTERNS

        opportunities = account_data.get("opportunities", [])
        contacts = account_data.get("contacts", [])
        cases = account_data.get("cases", [])
        activities = account_data.get("activities", [])
        health_score = account_data.get("health_score", 80.0)
        account_name = account_data.get("account_name", "Global Portfolio")

        # Config anchor date matching the rest of the file
        anchor_date = reference_date()

        # Observations mapping
        observations = {}
        evidence_store = {}
        param_store = {}

        # obs_pipeline_concentration
        total_pipeline = sum(o.get("amount_usd", 0.0) for o in opportunities)
        if total_pipeline > 0 and len(opportunities) >= 3:
            sorted_opps = sorted(opportunities, key=lambda x: x.get("amount_usd", 0.0), reverse=True)
            top_2_sum = sum(o.get("amount_usd", 0.0) for o in sorted_opps[:2])
            concentration_pct = (top_2_sum / total_pipeline) * 100.0
            triggered = concentration_pct > 70.0
            observations["obs_pipeline_concentration"] = triggered
            evidence_store["obs_pipeline_concentration"] = [
                f"Top 2 opportunities constitute {concentration_pct:.1f}% of pipeline."
            ]
            param_store["obs_pipeline_concentration"] = {
                "concentration_pct": concentration_pct,
                "top_n": 2,
                "at_risk_value": top_2_sum
            }
        else:
            observations["obs_pipeline_concentration"] = False

        # obs_stalled_deal
        stalled_list = []
        for o in opportunities:
            stage = o.get("stage", "")
            val = o.get("amount_usd", 0.0)
            close_date_str = o.get("close_date", "")
            days_past = 0
            is_past_close = False
            if close_date_str:
                try:
                    close_date = datetime.datetime.strptime(close_date_str[:10], "%Y-%m-%d").date()
                    if close_date < anchor_date:
                        is_past_close = True
                        days_past = (anchor_date - close_date).days
                except ValueError:
                    pass
            days_since_activity = 999
            for act in activities:
                act_date_str = act.get("date", "")
                if act_date_str:
                    try:
                        act_date = datetime.datetime.strptime(act_date_str[:10], "%Y-%m-%d").date()
                        diff = (anchor_date - act_date).days
                        if diff < days_since_activity:
                            days_since_activity = diff
                    except ValueError:
                        pass
            if is_past_close or (days_since_activity > 30 and stage in ["Negotiation", "Proposal", "Contract Review", "Signed & Activated"]):
                stalled_list.append((o, max(days_past, days_since_activity if days_since_activity != 999 else 30)))

        if stalled_list:
            observations["obs_stalled_deal"] = True
            evidence_store["obs_stalled_deal"] = [
                f"Deal '{item[0].get('opp_name')}' stalled for {item[1]} days in stage '{item[0].get('stage')}'"
                for item in stalled_list
            ]
            # Primary parameters from the top stalled item
            param_store["obs_stalled_deal"] = {
                "opp_name": stalled_list[0][0].get("opp_name", "Unknown Deal"),
                "stage": stalled_list[0][0].get("stage", "Unknown"),
                "days_stalled": stalled_list[0][1],
                "value_usd": stalled_list[0][0].get("amount_usd", 0.0)
            }
        else:
            observations["obs_stalled_deal"] = False

        # obs_close_date_pressure
        closing_soon_risky = []
        for o in opportunities:
            close_date_str = o.get("close_date", "")
            if close_date_str:
                try:
                    close_date = datetime.datetime.strptime(close_date_str[:10], "%Y-%m-%d").date()
                    days_to_close = (close_date - anchor_date).days
                    prob = o.get("probability", 1.0)
                    if 0 < days_to_close <= 30 and prob < 0.50:
                        closing_soon_risky.append((o, days_to_close, prob))
                except ValueError:
                    pass
        if closing_soon_risky:
            observations["obs_close_date_pressure"] = True
            evidence_store["obs_close_date_pressure"] = [
                f"Deal '{item[0].get('opp_name')}' closing in {item[1]} days with low probability {item[2]:.0%}"
                for item in closing_soon_risky
            ]
            param_store["obs_close_date_pressure"] = {
                "opp_name": closing_soon_risky[0][0].get("opp_name", ""),
                "days_to_close": closing_soon_risky[0][1],
                "probability": closing_soon_risky[0][2],
                "value_usd": closing_soon_risky[0][0].get("amount_usd", 0.0)
            }
        else:
            observations["obs_close_date_pressure"] = False

        # obs_single_threaded
        dm_roles = ["director", "vp", "cxo", "chief", "head", "manager", "ceo", "coo", "cto", "cfo", "president", "officer", "lead"]
        dm_count = sum(1 for c in contacts if any(r in c.get("role", "").lower() for r in dm_roles))
        is_single_threaded = len(contacts) <= 2 or dm_count == 0
        observations["obs_single_threaded"] = is_single_threaded
        if is_single_threaded:
            evidence_store["obs_single_threaded"] = [f"Only {len(contacts)} contacts mapped. Decision makers count: {dm_count}."]
            param_store["obs_single_threaded"] = {
                "contact_count": len(contacts),
                "pipeline_value": total_pipeline
            }

        # obs_executive_blind_spot
        has_exec_contact = any(any(r in c.get("role", "").lower() for r in ["vp", "cxo", "chief", "director", "officer"]) for c in contacts)
        is_blind_spot = total_pipeline > 100000 and not has_exec_contact
        observations["obs_executive_blind_spot"] = is_blind_spot
        if is_blind_spot:
            evidence_store["obs_executive_blind_spot"] = ["Pipeline exceeds $100K but no executive-level contacts mapped."]
            param_store["obs_executive_blind_spot"] = {
                "pipeline_value": total_pipeline
            }

        # obs_stakeholder_gap
        has_dm_role = any(any(r in c.get("role", "").lower() for r in ["decision maker", "economic buyer", "champion"]) for c in contacts)
        is_gap = len(contacts) > 0 and not has_dm_role
        observations["obs_stakeholder_gap"] = is_gap
        if is_gap:
            evidence_store["obs_stakeholder_gap"] = ["No mapped contact plays a designated Decision Maker, Champion, or Economic Buyer role."]

        # obs_activity_cliff
        days_since_any_activity = 999
        for act in activities:
            act_date_str = act.get("date", "")
            if act_date_str:
                try:
                    act_date = datetime.datetime.strptime(act_date_str[:10], "%Y-%m-%d").date()
                    diff = (anchor_date - act_date).days
                    if diff < days_since_any_activity:
                        days_since_any_activity = diff
                except ValueError:
                    pass
        is_cliff = days_since_any_activity > 14
        observations["obs_activity_cliff"] = is_cliff
        if is_cliff:
            evidence_store["obs_activity_cliff"] = [f"No activities recorded in the last {days_since_any_activity} days."]
            param_store["obs_activity_cliff"] = {
                "days_since_activity": days_since_any_activity
            }

        # obs_momentum_drop
        # Compute dynamic activity drop
        current_month_count = sum(1 for act in activities if act.get("date", "") and "2026-07" in act.get("date"))
        prev_month_count = sum(1 for act in activities if act.get("date", "") and "2026-06" in act.get("date"))
        is_momentum_drop = prev_month_count > 0 and (current_month_count / prev_month_count) < 0.5
        observations["obs_momentum_drop"] = is_momentum_drop
        if is_momentum_drop:
            drop_pct = (1.0 - (current_month_count / prev_month_count)) * 100.0
            evidence_store["obs_momentum_drop"] = [f"Logged activities dropped from {prev_month_count} in June to {current_month_count} in July."]
            param_store["obs_momentum_drop"] = {
                "drop_pct": drop_pct
            }

        # obs_support_pressure
        critical_cases = [c for c in cases if c.get("severity") in ["P1", "Critical", "High"] and c.get("status") != "Closed"]
        observations["obs_support_pressure"] = len(critical_cases) > 0
        if critical_cases:
            evidence_store["obs_support_pressure"] = [f"Open escalation ticket: '{c.get('subject')}' ({c.get('severity')})" for c in critical_cases]
            param_store["obs_support_pressure"] = {
                "case_count": len(critical_cases)
            }

        # obs_expansion_ready
        is_expansion = health_score > 80.0 and len(opportunities) >= 3 and days_since_any_activity < 14
        observations["obs_expansion_ready"] = is_expansion
        if is_expansion:
            evidence_store["obs_expansion_ready"] = [f"Account health is high at {health_score}%, with {len(opportunities)} active opportunities."]
            param_store["obs_expansion_ready"] = {
                "health_score": health_score
            }

        # Step 2: Pattern Match Pass & Find matching findings
        findings = []
        for pattern in ALL_PATTERNS:
            match = True
            for cond in pattern.trigger_conditions:
                if not observations.get(cond, False):
                    match = False
                    break
            if match:
                evidence = []
                for cond in pattern.trigger_conditions:
                    evidence.extend(evidence_store.get(cond, []))

                # Render templates safely
                params = {}
                for cond in pattern.trigger_conditions:
                    params.update(param_store.get(cond, {}))
                
                try:
                    insight = pattern.insight_template.format(**params)
                    impact = pattern.business_impact_template.format(**params)
                except Exception:
                    insight = pattern.insight_template
                    impact = pattern.business_impact_template

                # Calculate confidence score
                obs_confidence = data_quality_score
                # Let's say evidence weight contribution
                pattern_conf = obs_confidence * pattern.confidence_weight
                confidence = round(min(pattern_conf, 1.0), 3)

                # Priority Score calculation
                sev_map = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3, "POSITIVE": 0.2}
                sev_weight = sev_map.get(pattern.severity, 0.5)
                
                rev_band = 0.1
                if total_pipeline > 500000:
                    rev_band = 1.0
                elif total_pipeline > 100000:
                    rev_band = 0.6
                
                urgency = 0.3
                if pattern.id in ["STALLED_DEAL", "CLOSE_DATE_PRESSURE", "SUPPORT_PRESSURE"]:
                    urgency = 1.0
                
                priority = (sev_weight * 0.35) + (rev_band * 0.25) + (urgency * 0.20) + (confidence * 0.20)

                finding = Finding(
                    id=f"{pattern.id}_{account_name.replace(' ', '_').lower()}",
                    pattern_id=pattern.id,
                    pattern_version=pattern.version,
                    category=pattern.category,
                    observation=pattern.description,
                    insight=insight,
                    business_impact=impact,
                    severity=pattern.severity,
                    evidence=evidence,
                    priority_score=round(priority, 3),
                    confidence=confidence
                )
                findings.append(finding)

        # Sort findings descending
        findings.sort(key=lambda f: f.priority_score, reverse=True)

        # Maturing status
        high_findings = [f for f in findings if f.severity == "HIGH"]
        if health_score < 60.0 or len(critical_cases) >= 2:
            maturity = "CHURNING"
        elif len(high_findings) >= 2:
            maturity = "AT_RISK"
        elif not high_findings and health_score > 80.0 and any(f.pattern_id == "EXPANSION_SIGNAL" for f in findings):
            maturity = "STRATEGIC"
        elif high_findings or (70.0 <= health_score <= 80.0):
            maturity = "GROWTH"
        else:
            maturity = "ACQUISITION"

        # Risk score calculation
        max_priority = findings[0].priority_score if findings else 0.0
        risk_score = min(max_priority * 1.2, 1.0) if maturity in ["CHURNING", "AT_RISK"] else max_priority * 0.8
        risk_score = round(min(risk_score, 1.0), 3)

        # Brief confidence (mean of top 3 finding confidence scores)
        top_confidences = [f.confidence for f in findings[:3]]
        brief_conf = round(sum(top_confidences) / len(top_confidences), 3) if top_confidences else 0.5

        top_finding_text = findings[0].insight if findings else "No critical findings detected. Account status is stable."
        expansion_signals_list = [f.insight for f in findings if f.severity == "POSITIVE"]

        return IntelligenceBrief(
            account_name=account_name,
            account_risk_score=risk_score,
            top_finding=top_finding_text,
            ranked_findings=findings,
            expansion_signals=expansion_signals_list,
            critical_count=len(high_findings),
            confidence=brief_conf,
            account_maturity=maturity,
            data_quality_score=data_quality_score,
            is_empty=len(findings) == 0
        )

