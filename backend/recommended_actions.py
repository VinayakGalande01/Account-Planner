"""
RECOMMENDED ACTIONS ENGINE (recommended_actions.py)
Generates context-aware Next-Best-Actions (Copilot Action Chips) for the frontend UI
based on intent, risk signals, health scores, and pipeline stages with zero LLM latency.
"""

# --- SECTION 1: Base Imports & Recommended Action Schema ---
# Imports dataclass builders and defines the copilot RecommendedAction metadata structure.
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import json

@dataclass
class RecommendedAction:
    title: str
    action: str
    description: str = ""
    priority: str = "medium"  # "high" | "medium" | "low"
    # action_type: maps directly to the quick-action backend dispatcher.
    # When set, chip clicks bypass the intent classifier entirely.
    # Values: EXEC_EMAIL | MEETING_AGENDA | SHOW_STAKEHOLDERS | REVIEW_RISKS | None
    action_type: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# INTENT-BASED DEFAULT ACTION SETS
# ═══════════════════════════════════════════════════════════════

_INTENT_ACTIONS: Dict[str, List[RecommendedAction]] = {
    "ACCOUNT_PLAN_QUERY": [
        RecommendedAction("Generate Executive Email", "generate_email", "Draft an email for executive outreach", "high", action_type="EXEC_EMAIL"),
        RecommendedAction("Show Stakeholders", "show_stakeholders", "View key contacts and engagement levels", "high", action_type="SHOW_STAKEHOLDERS"),
        RecommendedAction("Create Meeting Agenda", "meeting_agenda", "Build an agenda for the next account review", "medium", action_type="MEETING_AGENDA"),
        RecommendedAction("Review Risks", "review_risks", "Analyze risk factors for this account", "medium", action_type="REVIEW_RISKS"),
        RecommendedAction("Predict Renewal", "predict_renewal", "Forecast renewal probability and timeline", "low"),
    ],
    "RISK_ANALYSIS_QUERY": [
        RecommendedAction("Create Recovery Plan", "create_recovery_plan", "Build a structured risk mitigation strategy", "high"),
        RecommendedAction("Review Risk Factors", "review_risk_factors", "Deep dive into risk drivers", "high"),
        RecommendedAction("Run Root Cause Analysis", "root_cause_analysis", "Identify underlying causes of risk", "medium"),
        RecommendedAction("Review Engagement History", "review_engagement", "Check past interactions for patterns", "medium"),
        RecommendedAction("Schedule Executive Outreach", "executive_outreach", "Plan outreach to senior stakeholders", "low"),
    ],
    "CONTACT_QUERY": [
        RecommendedAction("Map Decision Makers", "map_decision_makers", "Identify key decision-making stakeholders", "high"),
        RecommendedAction("Draft Engagement Email", "draft_engagement_email", "Create outreach email for key contacts", "high"),
        RecommendedAction("Show Engagement Gaps", "show_engagement_gaps", "Reveal contacts with declining engagement", "medium"),
        RecommendedAction("Build Stakeholder Map", "build_stakeholder_map", "Visualize organizational relationships", "medium"),
    ],
    "PIPELINE_SUMMARY_QUERY": [
        RecommendedAction("Review Top Deals", "review_top_deals", "Focus on highest-value opportunities", "high"),
        RecommendedAction("Show Pipeline Risks", "show_pipeline_risks", "Identify deals at risk of slipping", "high"),
        RecommendedAction("Forecast Revenue Impact", "forecast_revenue", "Estimate weighted revenue for current quarter", "medium"),
        RecommendedAction("Create Deal Strategy", "create_deal_strategy", "Build strategy for priority deals", "medium"),
    ],
    "GLOBAL_LIST_QUERY": [
        RecommendedAction("Analyze Top Opportunity", "analyze_top_opportunity", "Deep dive into the highest-priority deal", "high"),
        RecommendedAction("Show Pipeline Risks", "show_pipeline_risks", "Review deals at risk of slipping", "high"),
        RecommendedAction("Compare Deal Velocity", "compare_velocity", "Benchmark deal progression speed", "medium"),
        RecommendedAction("Build Priority Action Plan", "priority_action_plan", "Create action plan for top deals", "medium"),
    ],
    "ACTION_RECOMMENDATION_QUERY": [
        RecommendedAction("Generate Executive Email", "generate_email", "Draft executive outreach email", "high"),
        RecommendedAction("Show Stakeholders", "show_stakeholders", "View key contacts and engagement levels", "high"),
        RecommendedAction("Create Meeting Agenda", "meeting_agenda", "Build an agenda for the next touchpoint", "medium"),
        RecommendedAction("Review Risks", "review_risks", "Analyze risk factors across accounts", "medium"),
    ],
}

# ═══════════════════════════════════════════════════════════════
# CONTEXTUAL OVERLAY ACTIONS (added based on detected signals)
# ═══════════════════════════════════════════════════════════════

_RENEWAL_RISK_ACTIONS = [
    RecommendedAction("Create Renewal Plan", "create_renewal_plan", "Build a structured renewal strategy", "high"),
    RecommendedAction("Generate Renewal Email", "generate_renewal_email", "Draft outreach for renewal discussion", "high"),
    RecommendedAction("Show Renewal Risks", "show_renewal_risks", "Analyze factors affecting renewal", "medium"),
    RecommendedAction("Identify Decision Makers", "identify_decision_makers", "Map key stakeholders for renewal", "medium"),
]

_EXPANSION_ACTIONS = [
    RecommendedAction("Build Expansion Strategy", "build_expansion_strategy", "Plan cross-sell or upsell approach", "high"),
    RecommendedAction("Estimate Revenue Impact", "estimate_revenue_impact", "Project revenue from expansion", "high"),
    RecommendedAction("Draft Expansion Proposal", "draft_expansion_proposal", "Create business case for growth", "medium"),
    RecommendedAction("Find Additional Stakeholders", "find_stakeholders", "Identify new contacts for expansion", "medium"),
]

_POOR_HEALTH_ACTIONS = [
    RecommendedAction("Run Root Cause Analysis", "root_cause_analysis", "Identify underlying health issues", "high"),
    RecommendedAction("Review Risk Factors", "review_risk_factors", "Examine drivers of low health score", "high"),
    RecommendedAction("Create Recovery Plan", "create_recovery_plan", "Build a structured remediation plan", "medium"),
    RecommendedAction("Review Engagement History", "review_engagement", "Check past interaction patterns", "medium"),
]

_HIGH_CHURN_ACTIONS = [
    RecommendedAction("Analyze Churn Drivers", "analyze_churn_drivers", "Identify causes of churn risk", "high"),
    RecommendedAction("Prepare Retention Plan", "prepare_retention_plan", "Create strategy to retain the account", "high"),
    RecommendedAction("Schedule Executive Outreach", "executive_outreach", "Plan senior stakeholder engagement", "medium"),
]

_STALLED_DEAL_ACTIONS = [
    RecommendedAction("Identify Blockers", "identify_blockers", "Find what's stalling deal progression", "high"),
    RecommendedAction("Re-engage Decision Maker", "reengage_dm", "Plan outreach to key approver", "high"),
    RecommendedAction("Create Deal Acceleration Plan", "deal_acceleration", "Build strategy to unstick the deal", "medium"),
]

_CLOSING_SOON_ACTIONS = [
    RecommendedAction("Prepare Close Plan", "prepare_close_plan", "Build a step-by-step closing strategy", "high"),
    RecommendedAction("Draft Contract Summary", "draft_contract_summary", "Prepare contract key points", "high"),
    RecommendedAction("Verify Stakeholder Alignment", "verify_alignment", "Confirm all approvers are aligned", "medium"),
]


# ═══════════════════════════════════════════════════════════════
# SIGNAL DETECTION HELPERS
# ═══════════════════════════════════════════════════════════════

def _safe_get(obj, key, default=None):
    """Safely get attribute from dict or Pydantic model."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _detect_renewal_risk(query: str, intent_str: str, response_obj: Any) -> bool:
    """Check if renewal risk is a factor in the current context."""
    q = query.lower() if query else ""
    if any(kw in q for kw in ["renewal", "renew", "contract end", "expiring"]):
        return True
    narrative = _safe_get(response_obj, "narrative", "")
    if isinstance(narrative, str) and any(kw in narrative.lower() for kw in ["renewal", "renew"]):
        return True
    return False


def _detect_expansion(query: str, response_obj: Any) -> bool:
    """Check if expansion opportunity is relevant."""
    q = query.lower() if query else ""
    if any(kw in q for kw in ["expand", "expansion", "upsell", "cross-sell", "growth"]):
        return True
    return False


def _detect_poor_health(consensus: Any, response_obj: Any) -> bool:
    """Check if health score signals are poor."""
    # Check data perspective key_metrics
    key_metrics = _safe_get(response_obj, "key_metrics", {})
    health = _safe_get(key_metrics, "health_score")
    if health is not None and isinstance(health, (int, float)) and health < 60:
        return True
    # Check consensus confidence as proxy
    final_conf = _safe_get(consensus, "final_confidence")
    if final_conf is not None and isinstance(final_conf, (int, float)) and final_conf < 0.5:
        return True
    return False


def _detect_high_churn(response_obj: Any) -> bool:
    """Check if churn probability is elevated."""
    key_metrics = _safe_get(response_obj, "key_metrics", {})
    churn = _safe_get(key_metrics, "churn_probability")
    if churn is not None and isinstance(churn, (int, float)):
        threshold = 0.5 if churn <= 1 else 50
        if churn >= threshold:
            return True
    return False


def _detect_stalled_deals(query: str, response_obj: Any) -> bool:
    """Check if stalled or blocked deals are a concern."""
    q = query.lower() if query else ""
    if any(kw in q for kw in ["stalled", "stuck", "blocked", "stalling", "blocker"]):
        return True
    return False


def _detect_closing_soon(query: str, response_obj: Any) -> bool:
    """Check if near-term deal closing is the focus."""
    q = query.lower() if query else ""
    if any(kw in q for kw in ["closing", "close date", "close soon", "this week", "this month", "30 days"]):
        return True
    return False


# ═══════════════════════════════════════════════════════════════
# MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_recommended_actions(
    intent: Any,
    query: str = "",
    account_data: Optional[Dict] = None,
    consensus: Any = None,
    response_obj: Any = None,
    max_actions: int = 5
) -> List[Dict]:
    """
    Generate contextual recommended actions based on intent, query context,
    and response signals.

    Returns a list of action dicts ready for JSON serialization.

    Args:
        intent: The intent classification object (has .primary_intent, .intent, .complexity)
        query: The original user query string
        account_data: Account data dict from the orchestrator
        consensus: ConsensusOutput from reasoning engine
        response_obj: The role-specific response object
        max_actions: Maximum number of actions to return (default 5)

    Returns:
        List of action dicts with title, action, description, priority
    """
    # Resolve intent string
    intent_str = ""
    if intent is not None:
        if hasattr(intent, "intent"):
            intent_str = str(intent.intent)
        elif hasattr(intent, "primary_intent"):
            pi = intent.primary_intent
            intent_str = pi.value if hasattr(pi, "value") else str(pi)
        elif isinstance(intent, str):
            intent_str = intent

    # Map various intent formats to our standard keys
    intent_map = {
        "risk_assessment": "RISK_ANALYSIS_QUERY",
        "relationship_analysis": "CONTACT_QUERY",
        "pipeline_summary": "PIPELINE_SUMMARY_QUERY",
        "opportunity_expansion": "GLOBAL_LIST_QUERY",
        "action_recommendation": "ACTION_RECOMMENDATION_QUERY",
        "opportunity_ranking": "GLOBAL_LIST_QUERY",
        "pipeline_review": "PIPELINE_SUMMARY_QUERY",
        "executive_briefing": "GLOBAL_LIST_QUERY",
        "portfolio_analysis": "RISK_ANALYSIS_QUERY",
        "account_plan": "ACCOUNT_PLAN_QUERY",
        "contact_lookup": "CONTACT_QUERY",
    }
    mapped_intent = intent_map.get(intent_str.lower(), intent_str.upper()) if intent_str else "ACTION_RECOMMENDATION_QUERY"

    # Start with intent-based defaults
    base_actions = list(_INTENT_ACTIONS.get(mapped_intent, _INTENT_ACTIONS["ACTION_RECOMMENDATION_QUERY"]))

    # Contextual overlays — prepend high-priority contextual actions
    contextual_actions: List[RecommendedAction] = []

    if _detect_renewal_risk(query, intent_str, response_obj):
        contextual_actions = _RENEWAL_RISK_ACTIONS
    elif _detect_high_churn(response_obj):
        contextual_actions = _HIGH_CHURN_ACTIONS
    elif _detect_poor_health(consensus, response_obj):
        contextual_actions = _POOR_HEALTH_ACTIONS
    elif _detect_expansion(query, response_obj):
        contextual_actions = _EXPANSION_ACTIONS
    elif _detect_stalled_deals(query, response_obj):
        contextual_actions = _STALLED_DEAL_ACTIONS
    elif _detect_closing_soon(query, response_obj):
        contextual_actions = _CLOSING_SOON_ACTIONS

    # Merge: contextual actions first (they override), then fill from base
    if contextual_actions:
        # Use contextual as primary, backfill from base (avoid duplicates)
        seen_actions = {a.action for a in contextual_actions}
        merged = list(contextual_actions)
        for a in base_actions:
            if a.action not in seen_actions:
                merged.append(a)
                seen_actions.add(a.action)
        final_actions = merged
    else:
        final_actions = base_actions

    # Priority sort: high first, then medium, then low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    final_actions.sort(key=lambda a: priority_order.get(a.priority, 1))

    # Cap at max_actions
    final_actions = final_actions[:max_actions]

    return [a.to_dict() for a in final_actions]


def serialize_recommended_actions(actions: List[Dict]) -> str:
    """Serialize recommended actions list to JSON string for streaming."""
    return json.dumps(actions, ensure_ascii=False)
