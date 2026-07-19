from dataclasses import dataclass
from typing import List, Optional
from patterns.models import Pattern

# --- PATTERN: PIPELINE_CONCENTRATION ---
PIPELINE_CONCENTRATION = Pattern(
    id="PIPELINE_CONCENTRATION",
    version="1.0.0",
    name="Pipeline Concentration Risk",
    category="PIPELINE",
    description="Top 2 opportunities represent over 70% of total pipeline ARR.",
    trigger_conditions=["obs_pipeline_concentration"],
    min_conditions_required=1,
    insight_template=(
        "Over {concentration_pct:.0f}% of active pipeline is concentrated in just "
        "{top_n} opportunities. A delay or loss of any single deal significantly "
        "impacts the entire quarter's forecast."
    ),
    business_impact_template=(
        "If the top deal stalls, ${at_risk_value:,.0f} in pipeline is immediately "
        "at risk with no secondary deals to absorb the miss."
    ),
    severity="HIGH",
    confidence_weight=0.95,
    tags=["pipeline", "concentration", "forecast_risk"]
)

# --- PATTERN: STALLED_DEAL ---
STALLED_DEAL = Pattern(
    id="STALLED_DEAL",
    version="1.0.0",
    name="Stalled Opportunity",
    category="PIPELINE",
    description="Opportunities in negotiation stages with no stage change or no activity for over 30 days.",
    trigger_conditions=["obs_stalled_deal"],
    min_conditions_required=1,
    insight_template="The opportunity '{opp_name}' has stalled in stage '{stage}' for over {days_stalled} days with no sales velocity or active contact engagement.",
    business_impact_template="Forecasted revenue of ${value_usd:,.0f} from this deal is slipping past the projected close date.",
    severity="HIGH",
    confidence_weight=0.90,
    tags=["pipeline", "stalled", "velocity"]
)

# --- PATTERN: CLOSE_DATE_PRESSURE ---
CLOSE_DATE_PRESSURE = Pattern(
    id="CLOSE_DATE_PRESSURE",
    version="1.0.0",
    name="Close Date Pressure Risk",
    category="PIPELINE",
    description="Opportunities closing within 30 days with low probability score.",
    trigger_conditions=["obs_close_date_pressure"],
    min_conditions_required=1,
    insight_template="The opportunity '{opp_name}' is scheduled to close in {days_to_close} days but is currently flagged with low win probability ({probability:.0%}).",
    business_impact_template="Without immediate intervention, the targeted ${value_usd:,.0f} deal is unlikely to close on schedule.",
    severity="HIGH",
    confidence_weight=0.85,
    tags=["pipeline", "close_date", "forecast_risk"]
)

# --- PATTERN: SINGLE_THREADED_RISK ---
SINGLE_THREADED_RISK = Pattern(
    id="SINGLE_THREADED_RISK",
    version="1.0.0",
    name="Single Threaded Risk",
    category="RELATIONSHIP",
    description="Thin relationship coverage on the account with 2 or fewer contacts or lack of key decision maker roles.",
    trigger_conditions=["obs_single_threaded"],
    min_conditions_required=1,
    insight_template="The account has thin relationship coverage ({contact_count} total contacts). Active opportunities are highly vulnerable to key contact departure.",
    business_impact_template="A single point of failure at the client organization threatens the account's pipeline of ${pipeline_value:,.0f}.",
    severity="HIGH",
    confidence_weight=0.95,
    tags=["relationship", "single_threaded", "stakeholders"]
)

# --- PATTERN: EXECUTIVE_BLIND_SPOT ---
EXECUTIVE_BLIND_SPOT = Pattern(
    id="EXECUTIVE_BLIND_SPOT",
    version="1.0.0",
    name="Executive Blind Spot",
    category="RELATIONSHIP",
    description="High ARR or pipeline value on account but no mapped C-suite or VP level relationships.",
    trigger_conditions=["obs_executive_blind_spot"],
    min_conditions_required=1,
    insight_template="We have no mapped C-suite or VP-level executive relationships engaged, despite a significant pipeline of ${pipeline_value:,.0f}.",
    business_impact_template="We lack the top-down corporate buy-in needed to secure renewal or large expansions.",
    severity="HIGH",
    confidence_weight=0.90,
    tags=["relationship", "exec_sponsorship", "stakeholders"]
)

# --- PATTERN: STAKEHOLDER_GAP ---
STAKEHOLDER_GAP = Pattern(
    id="STAKEHOLDER_GAP",
    version="1.0.0",
    name="Decision Maker Gap",
    category="RELATIONSHIP",
    description="No contact with mapped roles such as decision maker or economic buyer.",
    trigger_conditions=["obs_stakeholder_gap"],
    min_conditions_required=1,
    insight_template="No contacts are mapped to core purchasing roles such as 'Decision Maker' or 'Economic Buyer'.",
    business_impact_template="We are running sales cycles without direct alignment to the person with budget authority.",
    severity="MEDIUM",
    confidence_weight=0.85,
    tags=["relationship", "stakeholders", "buyer_mapping"]
)

# --- PATTERN: ACTIVITY_CLIFF ---
ACTIVITY_CLIFF = Pattern(
    id="ACTIVITY_CLIFF",
    version="1.0.0",
    name="Engagement Activity Cliff",
    category="ACTIVITY",
    description="Sudden drop in client engagement with zero logged activities in the last 14 days.",
    trigger_conditions=["obs_activity_cliff"],
    min_conditions_required=1,
    insight_template="Customer communication has completely paused with zero logged activities in the last {days_since_activity} days.",
    business_impact_template="This sudden drop in engagement velocity indicates potential relationship cooling or silent dissatisfaction.",
    severity="HIGH",
    confidence_weight=0.90,
    tags=["activity", "engagement", "relationship_cooling"]
)

# --- PATTERN: MOMENTUM_DROP ---
MOMENTUM_DROP = Pattern(
    id="MOMENTUM_DROP",
    version="1.0.0",
    name="Activity Momentum Drop",
    category="ACTIVITY",
    description="Significant drop in activity count compared to previous averages.",
    trigger_conditions=["obs_momentum_drop"],
    min_conditions_required=1,
    insight_template="Activity volume has dropped by {drop_pct:.0f}% compared to the previous month, signaling decreasing sales velocity.",
    business_impact_template="Reduced activity momentum threatens ongoing negotiations and deal progression.",
    severity="MEDIUM",
    confidence_weight=0.80,
    tags=["activity", "momentum", "engagement"]
)

# --- PATTERN: SUPPORT_PRESSURE ---
SUPPORT_PRESSURE = Pattern(
    id="SUPPORT_PRESSURE",
    version="1.0.0",
    name="Support Case Escalation Pressure",
    category="SUPPORT",
    description="Presence of high severity open support tickets threatening customer experience.",
    trigger_conditions=["obs_support_pressure"],
    min_conditions_required=1,
    insight_template="There are currently {case_count} open Critical or High severity support tickets unresolved.",
    business_impact_template="Outstanding technical issues are damaging customer experience and putting renewal at risk.",
    severity="HIGH",
    confidence_weight=0.95,
    tags=["support", "tickets", "csat"]
)

# --- PATTERN: EXPANSION_SIGNAL ---
EXPANSION_SIGNAL = Pattern(
    id="EXPANSION_SIGNAL",
    version="1.0.0",
    name="Expansion Opportunity Signal",
    category="REVENUE",
    description="High health score combined with healthy activity and multiple opportunities indicates upsell potential.",
    trigger_conditions=["obs_expansion_ready"],
    min_conditions_required=1,
    insight_template="Account demonstrates high health ({health_score:.0f}%) and solid engagement momentum with no active escalations.",
    business_impact_template="The account is prime for expansion and upsell motions.",
    severity="POSITIVE",
    confidence_weight=0.85,
    tags=["revenue", "upsell", "growth"]
)

ALL_PATTERNS: List[Pattern] = [
    PIPELINE_CONCENTRATION,
    STALLED_DEAL,
    CLOSE_DATE_PRESSURE,
    SINGLE_THREADED_RISK,
    EXECUTIVE_BLIND_SPOT,
    STAKEHOLDER_GAP,
    ACTIVITY_CLIFF,
    MOMENTUM_DROP,
    SUPPORT_PRESSURE,
    EXPANSION_SIGNAL,
]

def get_pattern_by_id(pattern_id: str) -> Optional[Pattern]:
    return next((p for p in ALL_PATTERNS if p.id == pattern_id), None)
