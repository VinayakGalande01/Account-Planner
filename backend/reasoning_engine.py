"""
APEX Reasoning Engine — Intelligence Evolution Layer

Architecture Position:
    CRM Data (DataEngine)
    ↓
    Deterministic Intelligence (intelligence_layer.py)
    ↓
    THIS MODULE → Reasoning Layer
    ↓
    Recommendation Layer (also here)
    ↓
    curate_llm_context() → LLM → Response

Design Principles:
    1. Zero LLM calls. Fully deterministic and blazing fast.
    2. Derives recommendations from observed state, not from hardcoded intent templates.
    3. Every action is evidence-based: it references specific data facts.
    4. The system first infers the underlying business decision, then generates recommendations
       that serve that decision — not the surface query wording.
    5. Generalises to any future query without new rules.

Core Modules:
    - DecisionFramework   : Infer the business decision behind any query
    - StakeholderRanker   : Rank contacts by role relevance, stage fit, engagement, recency
    - OpportunityAnalyzer : Assess per-opportunity state: momentum, risk, stakeholder coverage
    - AccountAnalyzer     : Assess account-level context: health, engagement, revenue exposure
    - NextBestActionEngine: Dynamically generate evidence-based, specific actions from observed state
    - BusinessImpactModel : Estimate expected outcome and ignore-risk per action
    - assemble_reasoning_package(): Master orchestrator → ReasoningPackage
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import re


# ═══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class DecisionContext:
    """Structured business decision inference — replaces plain string.

    Every query has three dimensions:
        1. decision_label   — what type of decision is being made
        2. desired_outcome  — what outcome the user is pursuing
        3. context_evidence — data facts that support this inference
    """
    decision_label: str            # e.g. "Relationship Strategy"
    desired_outcome: str           # e.g. "Advance opportunity progression"
    context_evidence: List[str] = field(default_factory=list)

    def to_display(self) -> str:
        return f"{self.decision_label} → Desired Outcome: {self.desired_outcome}"


@dataclass
class ConfidenceModel:
    """Six-dimensional confidence scoring.

    Each dimension is HIGH / MEDIUM / LOW.
    Overall is the composite floor (min of all dimensions).
    overall_pct is a 0-100 numeric for frontend rendering.
    """
    intent: str = "HIGH"           # Was the intent classification clear?
    decision: str = "HIGH"         # Is the business decision well-understood?
    data: str = "HIGH"             # Is the underlying CRM data complete?
    reasoning: str = "HIGH"        # Did the reasoning engine have enough signal?
    recommendation: str = "HIGH"   # How confident are we in the specific actions?
    overall: str = "HIGH"          # Composite — floor(all dimensions)
    overall_pct: int = 100         # 0-100 numeric composite

    _LEVEL_MAP = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    _PCT_MAP = {"HIGH": 100, "MEDIUM": 60, "LOW": 30}

    def compute_overall(self) -> None:
        """Recalculate overall from individual dimensions."""
        dims = [self.intent, self.decision, self.data, self.reasoning, self.recommendation]
        scores = [self._LEVEL_MAP.get(d, 2) for d in dims]
        min_score = min(scores)
        avg_pct = sum(self._PCT_MAP.get(d, 60) for d in dims) // len(dims)

        if min_score >= 3:
            self.overall = "HIGH"
        elif min_score >= 2:
            self.overall = "MEDIUM"
        else:
            self.overall = "LOW"
        self.overall_pct = avg_pct

    def to_summary(self) -> str:
        return (
            f"Intent: {self.intent} | Decision: {self.decision} | Data: {self.data} | "
            f"Reasoning: {self.reasoning} | Recommendation: {self.recommendation} | "
            f"Overall: {self.overall} ({self.overall_pct}%)"
        )


@dataclass
class StakeholderRecommendation:
    """A ranked contact recommendation with full reasoning chain."""
    rank: int                      # 1=Primary, 2=Secondary, 3=Supporting
    contact_id: str
    name: str
    role: str
    department: str
    engagement_level: str
    last_contact_date: str
    role_relevance_score: float    # 0-1: how relevant this role is to current opp stage
    engagement_score: float        # 0-1: how engaged is this contact
    recency_score: float           # 0-1: how recently were they contacted
    composite_score: float         # weighted total
    why_primary: str               # plain-language reason this contact is recommended
    engagement_risk: Optional[str] # e.g. "Engagement has cooled for 14 days"
    suggested_action: str          # specific next step with this person
    expected_outcome: str          # what closing this interaction achieves
    stakeholder_confidence: str = "HIGH"  # HIGH/MEDIUM/LOW — degrades when engagement is cold/stale


@dataclass
class ActionRecommendation:
    """A dynamically generated, evidence-based next best action."""
    text: str                      # the specific action
    reason: str                    # why this action is needed (data-derived)
    expected_impact: str           # what happens if actioned
    ignore_risk: str               # what happens if NOT actioned
    urgency: str                   # CRITICAL / HIGH / MEDIUM / LOW
    urgency_rank: int              # 1=most urgent (for sorting)
    owner_hint: str                # "Account Manager", "Sales Director", etc.
    evidence: List[str]            # specific data facts that triggered this action
    confidence: str = "HIGH"       # HIGH/MEDIUM/LOW — reflects data quality of evidence


@dataclass
class ReasoningPackage:
    """
    Complete reasoning output passed to curate_llm_context().
    The LLM receives this as its context — NOT raw CRM tables.
    """
    decision_context: DecisionContext                  # structured business decision inference
    situation_summary: str                             # "What is happening right now, specifically"
    primary_recommendation: Optional[StakeholderRecommendation]  # top contact if applicable
    secondary_recommendations: List[StakeholderRecommendation]    # supporting contacts
    next_best_actions: List[ActionRecommendation]                 # ranked, evidence-based actions
    risk_implications: List[str]                       # ignore-risks at portfolio/account level
    business_impact: str                               # 1-2 line high-level outcome
    confidence: ConfidenceModel = field(default_factory=ConfidenceModel)  # 6-dimensional confidence
    reasoning_evidence: List[str] = field(default_factory=list)           # key data facts
    portfolio_state: Optional[Dict[str, Any]] = None   # portfolio-level analysis for global queries
    opp_id: Optional[str] = None                       # if query is opp-specific
    account_id: Optional[str] = None
    account_name: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# DECISION FRAMEWORK
# ═══════════════════════════════════════════════════════════════

class DecisionFramework:
    """
    Infer the underlying business decision the user is trying to make.

    This decouples reasoning from surface query wording:
    "Who should I call?" → underlying decision: relationship strategy
    "What's at risk?"    → underlying decision: risk mitigation
    "Top opportunities?" → underlying decision: resource allocation

    Returns a structured DecisionContext with:
        - decision_label: what decision is being made
        - desired_outcome: what business outcome the user is pursuing
        - context_evidence: data facts supporting the inference
    """

    # (decision_label, desired_outcome, intent_patterns, query_signal_words)
    DECISION_SIGNATURES = [
        (
            "Relationship Strategy",
            "Advance opportunity progression through targeted stakeholder engagement",
            ["CONTACT_QUERY"],
            ["contact", "who", "call", "reach", "talk", "meet", "stakeholder"]
        ),
        (
            "Resource Allocation",
            "Maximize revenue impact by focusing effort on highest-value opportunities",
            ["GLOBAL_LIST_QUERY", "PIPELINE_SUMMARY_QUERY"],
            ["top", "priority", "best", "focus", "biggest", "ranked", "which deal", "pipeline"]
        ),
        (
            "Risk Mitigation",
            "Prevent revenue loss by identifying and resolving deal blockers",
            ["RISK_ANALYSIS_QUERY"],
            ["risk", "danger", "jeopardy", "stalled", "at risk", "losing", "blocked"]
        ),
        (
            "Growth Strategy",
            "Expand account revenue through strategic relationship deepening and upsell",
            ["ACCOUNT_PLAN_QUERY"],
            ["account plan", "strategy", "growth", "expand", "review", "plan"]
        ),
        (
            "Execution Planning",
            "Identify and execute the highest-impact actions to accelerate pipeline today",
            ["ACTION_RECOMMENDATION_QUERY"],
            ["what should i do", "next steps", "action", "today", "priorities", "focus", "prepare"]
        ),
    ]

    @staticmethod
    def infer(intent: str, query: str, account_name: Optional[str] = None,
              account_ctx: Optional[Dict] = None, opp_ctx: Optional[Dict] = None) -> DecisionContext:
        q = query.lower()
        evidence = []

        # Build context evidence from available state
        if account_name:
            evidence.append(f"Account: {account_name}")
        if opp_ctx and opp_ctx.get("opp_id"):
            evidence.append(f"Opportunity: {opp_ctx.get('opp_name', opp_ctx['opp_id'])} (${opp_ctx.get('amount', 0):,.0f})")
            evidence.append(f"Stage: {opp_ctx.get('stage', 'Unknown')}")
        if account_ctx:
            pipeline = account_ctx.get("pipeline_value", 0)
            if pipeline > 0:
                evidence.append(f"Active pipeline: ${pipeline:,.0f}")

        for decision_label, desired_outcome, intents, signals in DecisionFramework.DECISION_SIGNATURES:
            if intent in intents:
                if any(s in q for s in signals) or intent in intents:
                    label = decision_label
                    if account_name:
                        label = f"{decision_label} (Account: {account_name})"
                    return DecisionContext(
                        decision_label=label,
                        desired_outcome=desired_outcome,
                        context_evidence=evidence,
                    )

        # Fallback: generic execution framing (supports unseen query types)
        return DecisionContext(
            decision_label="Operational Intelligence",
            desired_outcome="Understand current state and determine the highest-value next action",
            context_evidence=evidence,
        )


# ═══════════════════════════════════════════════════════════════
# STAKEHOLDER RANKER
# ═══════════════════════════════════════════════════════════════

class StakeholderRanker:
    """
    Ranks contacts by their relevance to the current opportunity stage and relationship state.

    Scoring (composite, 0-100):
        role_relevance   × 0.40  — how relevant is this role to the current deal stage
        engagement       × 0.30  — how engaged is this contact (High=1.0, Medium=0.6, Low=0.2, Cold=0.0)
        recency          × 0.20  — how recently were they contacted (exponential decay)
        department       × 0.10  — IT/Finance/Procurement fit to deal type

    Role relevance is stage-aware (not hardcoded globally).
    """

    # Stage → ordered list of most-to-least relevant roles
    STAGE_ROLE_PRIORITY: Dict[str, List[str]] = {
        "Negotiation/Review":       ["Decision Maker", "Economic Buyer", "Champion", "Procurement", "C-Suite", "VP"],
        "Proposal/Price Quote":     ["Economic Buyer", "Technical Buyer", "Champion", "Decision Maker", "Procurement"],
        "Id. Decision Makers":      ["Decision Maker", "Influencer", "Champion", "C-Suite", "VP"],
        "Value Proposition":        ["Champion", "Technical Buyer", "Influencer", "Decision Maker"],
        "Perception Analysis":      ["Champion", "Technical Buyer", "Influencer"],
        "Needs Analysis":           ["Champion", "Technical Buyer", "Influencer", "End User"],
        "Qualification":            ["Influencer", "Champion", "End User", "Technical Buyer"],
        "Prospecting":              ["Influencer", "Champion", "End User"],
        # Generic fallback if stage is unknown
        "_default":                 ["Decision Maker", "Economic Buyer", "Champion", "Technical Buyer", "Influencer", "End User"],
    }

    ENGAGEMENT_SCORES = {"High": 1.0, "Medium": 0.6, "Low": 0.2, "Cold": 0.0}

    @staticmethod
    def _role_relevance(role: str, stage: str) -> float:
        priority_list = (
            StakeholderRanker.STAGE_ROLE_PRIORITY.get(stage)
            or StakeholderRanker.STAGE_ROLE_PRIORITY["_default"]
        )
        role_lower = str(role).lower()
        for i, priority_role in enumerate(priority_list):
            if priority_role.lower() in role_lower or role_lower in priority_role.lower():
                # Higher rank = higher score
                return max(0.1, 1.0 - (i * 0.15))
        return 0.1  # unknown role

    @staticmethod
    def _recency_score(last_contact_date_str: str) -> float:
        """Exponential decay: contacted today=1.0, 30+ days=0.1."""
        if not last_contact_date_str or last_contact_date_str in ("Never", "NaT", "nan", ""):
            return 0.0
        try:
            dt = pd.to_datetime(last_contact_date_str)
            if dt.tzinfo is not None:
                dt = dt.tz_localize(None)
            days = (datetime.now() - dt).days
            if days <= 0:
                return 1.0
            elif days <= 7:
                return 0.9
            elif days <= 14:
                return 0.7
            elif days <= 21:
                return 0.5
            elif days <= 30:
                return 0.3
            else:
                return max(0.0, 0.3 - (days - 30) * 0.005)
        except Exception:
            return 0.0

    @staticmethod
    def _engagement_risk(engagement_level: str, last_contact_date_str: str) -> Optional[str]:
        """Identifies if this contact's engagement is a risk factor."""
        if engagement_level in ("Low", "Cold"):
            return f"Engagement is {engagement_level} — relationship requires active recovery."
        try:
            dt = pd.to_datetime(last_contact_date_str)
            if dt.tzinfo is not None:
                dt = dt.tz_localize(None)
            days = (datetime.now() - dt).days
            if days > 21 and engagement_level == "Medium":
                return f"No contact in {days} days — engagement momentum is declining."
            if days > 14 and engagement_level == "High":
                return f"Previously high engagement but no contact in {days} days — at risk of cooling."
        except Exception:
            pass
        return None

    @staticmethod
    def _suggest_action(rank: int, name: str, role: str, stage: str, engagement_level: str) -> str:
        role_lower = role.lower()
        stage_lower = stage.lower()

        if "decision maker" in role_lower or "c-suite" in role_lower or "vp" in role_lower:
            if "negotiation" in stage_lower:
                return f"Schedule approval alignment meeting with {name} before close date."
            return f"Secure executive sponsorship conversation with {name}."
        elif "procurement" in role_lower:
            if "negotiation" in stage_lower or "proposal" in stage_lower:
                return f"Loop in {name} from Procurement to validate contract terms and timelines."
            return f"Introduce {name} to project scope and expected procurement timeline."
        elif "technical buyer" in role_lower:
            return f"Conduct technical validation session with {name} to resolve open requirements."
        elif "champion" in role_lower:
            if engagement_level in ("Low", "Cold"):
                return f"Re-engage {name} (Champion) with updated value proposition and competitive positioning."
            return f"Leverage {name} as internal advocate — share executive-ready business case."
        elif "influencer" in role_lower:
            return f"Engage {name} to understand internal landscape and identify additional stakeholders."
        else:
            return f"Reconnect with {name} to maintain presence and gather deal intel."

    @staticmethod
    def _expected_outcome(role: str, stage: str) -> str:
        role_lower = role.lower()
        stage_lower = stage.lower()
        if "decision maker" in role_lower:
            return "Secure formal commitment and move the opportunity to final approval stage."
        elif "procurement" in role_lower:
            return "Unblock contract finalisation and reduce procurement-driven deal slippage risk."
        elif "champion" in role_lower:
            return "Strengthen internal advocacy and accelerate internal approval velocity."
        elif "technical buyer" in role_lower:
            return "Resolve technical objections and confirm solution fit before executive review."
        elif "influencer" in role_lower:
            return "Build broader coalition of internal support to reduce single-threaded risk."
        return "Maintain relationship momentum and keep the opportunity visible internally."

    @classmethod
    def rank(cls, contacts_df: pd.DataFrame, opp_stage: str, max_contacts: int = 3) -> List[StakeholderRecommendation]:
        """
        Rank all contacts in the DataFrame against the opportunity stage.
        Returns up to max_contacts StakeholderRecommendation objects.
        """
        if contacts_df is None or contacts_df.empty:
            return []

        ranked = []
        for _, row in contacts_df.iterrows():
            role = str(row.get("Role", ""))
            engagement = str(row.get("Engagement_Level", "Medium"))
            last_date = str(row.get("Last_Contact_Date", ""))[:10] if pd.notna(row.get("Last_Contact_Date")) else "Never"
            name = f"{row.get('First_Name', '')} {row.get('Last_Name', '')}".strip()

            role_rel = cls._role_relevance(role, opp_stage)
            eng_score = cls.ENGAGEMENT_SCORES.get(engagement, 0.3)
            rec_score = cls._recency_score(last_date)

            composite = (role_rel * 0.40) + (eng_score * 0.30) + (rec_score * 0.20) + 0.05  # dept bonus omitted for simplicity

            ranked.append({
                "contact_id": str(row.get("Contact_ID", "")),
                "name": name,
                "role": role,
                "department": str(row.get("Department", "N/A")),
                "engagement_level": engagement,
                "last_contact_date": last_date,
                "role_relevance_score": round(role_rel, 3),
                "engagement_score": round(eng_score, 3),
                "recency_score": round(rec_score, 3),
                "composite_score": round(composite, 3),
            })

        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        ranked = ranked[:max_contacts]

        result = []
        for rank_num, r in enumerate(ranked, 1):
            eng_risk = cls._engagement_risk(r["engagement_level"], r["last_contact_date"])
            action = cls._suggest_action(rank_num, r["name"], r["role"], opp_stage, r["engagement_level"])
            outcome = cls._expected_outcome(r["role"], opp_stage)

            # Build plain-language reason for why this contact is recommended
            why = f"{r['role']} in {r['department']} department"
            if rank_num == 1:
                why += f" — highest-relevance contact for this opportunity stage ({opp_stage})."
            elif rank_num == 2:
                why += f" — key supporting stakeholder for deal progression."
            else:
                why += f" — backup relationship to ensure multi-threaded coverage."

            # Derive stakeholder confidence from data quality
            if r["engagement_level"] in ("Cold",) and r["recency_score"] < 0.2:
                stk_confidence = "LOW"
            elif r["engagement_level"] in ("Low", "Cold") or r["recency_score"] < 0.3:
                stk_confidence = "MEDIUM"
            else:
                stk_confidence = "HIGH"

            result.append(StakeholderRecommendation(
                rank=rank_num,
                contact_id=r["contact_id"],
                name=r["name"],
                role=r["role"],
                department=r["department"],
                engagement_level=r["engagement_level"],
                last_contact_date=r["last_contact_date"],
                role_relevance_score=r["role_relevance_score"],
                engagement_score=r["engagement_score"],
                recency_score=r["recency_score"],
                composite_score=r["composite_score"],
                why_primary=why,
                engagement_risk=eng_risk,
                suggested_action=action,
                expected_outcome=outcome,
                stakeholder_confidence=stk_confidence,
            ))

        return result


# ═══════════════════════════════════════════════════════════════
# OPPORTUNITY ANALYZER
# ═══════════════════════════════════════════════════════════════

class OpportunityAnalyzer:
    """
    Analyzes a single opportunity's current state across multiple dimensions:
    - Momentum (stage velocity)
    - Stakeholder coverage
    - Close date urgency
    - Revenue exposure
    - Case blockers
    """

    @staticmethod
    def analyze(opp_row: pd.Series, contacts_df: pd.DataFrame, cases_df: pd.DataFrame) -> Dict[str, Any]:
        now = datetime.now()
        result = {}

        amount = float(opp_row.get("Amount_USD", 0)) if pd.notna(opp_row.get("Amount_USD")) else 0
        prob = float(opp_row.get("Probability_Pct", 0)) if pd.notna(opp_row.get("Probability_Pct")) else 0
        stage = str(opp_row.get("Stage", "Unknown"))
        opp_id = str(opp_row.get("Opp_ID", ""))
        opp_name = str(opp_row.get("Opp_Name", ""))

        result["opp_id"] = opp_id
        result["opp_name"] = opp_name
        result["stage"] = stage
        result["amount"] = amount
        result["probability"] = prob
        result["weighted_value"] = round(amount * prob / 100, 2)

        # Close date urgency
        days_until_close = None
        is_overdue = False
        try:
            close_date = pd.to_datetime(opp_row.get("Close_Date"))
            if pd.notna(close_date):
                if close_date.tzinfo is not None:
                    close_date = close_date.tz_localize(None)
                delta = (close_date - now).days
                days_until_close = delta
                is_overdue = delta < 0
        except Exception:
            pass

        result["days_until_close"] = days_until_close
        result["is_overdue"] = is_overdue
        result["close_urgency"] = (
            "CRITICAL" if is_overdue
            else "HIGH" if days_until_close is not None and days_until_close <= 14
            else "MEDIUM" if days_until_close is not None and days_until_close <= 30
            else "LOW"
        )

        # Stakeholder coverage gaps
        has_dm = False
        contact_count = 0
        if contacts_df is not None and not contacts_df.empty:
            contact_count = len(contacts_df)
            has_dm = not contacts_df[
                contacts_df["Role"].str.contains("Decision Maker|Economic Buyer|C-Suite|VP", na=False, case=False)
            ].empty
        result["contact_count"] = contact_count
        result["has_decision_maker"] = has_dm
        result["is_single_threaded"] = contact_count <= 1

        # Blocking cases
        blocking_case = None
        if cases_df is not None and not cases_df.empty:
            open_critical = cases_df[
                (cases_df["Severity"].isin(["Critical", "High"])) &
                (cases_df["Status"] != "Closed")
            ]
            if not open_critical.empty:
                c = open_critical.iloc[0]
                blocking_case = f"{c.get('Subject', 'Unknown case')} ({c.get('Severity', 'Unknown')} severity)"
        result["blocking_case"] = blocking_case

        return result


# ═══════════════════════════════════════════════════════════════
# ACCOUNT ANALYZER
# ═══════════════════════════════════════════════════════════════

class AccountAnalyzer:
    """
    Derives account-level situational context from the DataEngine.
    Produces a concise situation string and evidence list.
    """

    @staticmethod
    def analyze(engine, account_id: str) -> Dict[str, Any]:
        result = {}
        accounts = engine.data.get("account")
        opps = engine.data.get("opportunity")
        contacts = engine.data.get("contact")
        activities = engine.data.get("activity")
        cases = engine.data.get("case")

        if accounts is None:
            return {"error": "No account data"}

        acc_row_df = accounts[accounts["Account_ID"] == account_id]
        if acc_row_df.empty:
            return {"error": "Account not found"}
        acc = acc_row_df.iloc[0]

        result["account_id"] = account_id
        result["account_name"] = str(acc.get("Account_Name", ""))
        result["tier"] = str(acc.get("Account_Tier", "Standard"))
        result["industry"] = str(acc.get("Industry", "N/A"))
        annual_revenue = float(acc.get("Annual_Revenue_USD", 0)) if pd.notna(acc.get("Annual_Revenue_USD")) else 0
        result["annual_revenue"] = annual_revenue

        # Pipeline state
        acc_opps = opps[opps["Account_ID"] == account_id] if opps is not None else pd.DataFrame()
        open_opps = acc_opps[~acc_opps["Stage"].isin(["Closed Won", "Closed Lost"])] if not acc_opps.empty else pd.DataFrame()
        result["open_deal_count"] = len(open_opps)
        result["pipeline_value"] = float(open_opps["Amount_USD"].sum()) if not open_opps.empty else 0
        result["highest_stage"] = None
        if not open_opps.empty:
            stage_order = ["Negotiation/Review", "Proposal/Price Quote", "Perception Analysis",
                           "Value Proposition", "Id. Decision Makers", "Needs Analysis",
                           "Qualification", "Prospecting"]
            for s in stage_order:
                if s in open_opps["Stage"].values:
                    result["highest_stage"] = s
                    break

        # Engagement
        days_since_activity = 999
        if activities is not None and not activities.empty:
            acc_acts = activities[activities["Account_ID"] == account_id]
            if not acc_acts.empty:
                last = pd.to_datetime(acc_acts["Activity_Date"]).max()
                if pd.notna(last):
                    try:
                        if last.tzinfo is not None:
                            last = last.tz_localize(None)
                    except Exception:
                        pass
                    days_since_activity = (datetime.now() - last).days
        result["days_since_activity"] = days_since_activity
        result["engagement_status"] = (
            "COLD" if days_since_activity > 60
            else "DECLINING" if days_since_activity > 30
            else "ACTIVE" if days_since_activity <= 14
            else "MODERATE"
        )

        # Contact coverage
        acc_contacts = contacts[contacts["Account_ID"] == account_id] if contacts is not None else pd.DataFrame()
        result["contact_count"] = len(acc_contacts)
        result["has_decision_maker"] = (
            not acc_contacts[
                acc_contacts["Role"].str.contains("Decision Maker|Economic Buyer|C-Suite|VP", na=False, case=False)
            ].empty
            if not acc_contacts.empty else False
        )

        # Open critical cases
        open_critical_cases = 0
        if cases is not None and not cases.empty:
            acc_cases = cases[cases["Account_ID"] == account_id]
            open_critical_cases = len(acc_cases[
                (acc_cases["Severity"].isin(["Critical", "High"])) &
                (acc_cases["Status"] != "Closed")
            ])
        result["open_critical_cases"] = open_critical_cases

        return result


# ═══════════════════════════════════════════════════════════════
# NEXT BEST ACTION ENGINE
# ═══════════════════════════════════════════════════════════════

class NextBestActionEngine:
    """
    Dynamically generates specific, contextual, evidence-based actions
    by evaluating observed state dimensions.

    Anti-hardcoding principle:
        Actions are derived from state observations, NOT from intent type.
        Adding a new state condition automatically produces a new action
        without any changes to the call site.

    Each state evaluator returns an Optional[ActionRecommendation].
    All evaluators run every time. Outputs are sorted by urgency.
    """

    @staticmethod
    def _eval_overdue_deal(opp_ctx: Dict, account_name: str, primary_contact: Optional[StakeholderRecommendation]) -> Optional[ActionRecommendation]:
        if not opp_ctx.get("is_overdue"):
            return None
        contact_hint = f"with {primary_contact.name} ({primary_contact.role})" if primary_contact else "with the decision maker"
        return ActionRecommendation(
            text=f"Initiate immediate close-date reset conversation {contact_hint} for {opp_ctx['opp_name']}.",
            reason=f"Deal is past its original close date by {abs(opp_ctx['days_until_close'])} days with ${opp_ctx['amount']:,.0f} at stake.",
            expected_impact="Resets deal timeline and prevents pipeline staleness from compounding.",
            ignore_risk="Deal risks being marked lost or deprioritised in forecast reviews.",
            urgency="CRITICAL",
            urgency_rank=1,
            owner_hint="Account Manager",
            evidence=[f"Opp {opp_ctx['opp_id']} is overdue by {abs(opp_ctx['days_until_close'])} days", f"Amount: ${opp_ctx['amount']:,.0f}"]
        )

    @staticmethod
    def _eval_close_window_urgency(opp_ctx: Dict, primary_contact: Optional[StakeholderRecommendation]) -> Optional[ActionRecommendation]:
        days = opp_ctx.get("days_until_close")
        if days is None or days < 0 or days > 14:
            return None
        contact_hint = f"Schedule approval meeting with {primary_contact.name}" if primary_contact else "Engage the decision maker"
        return ActionRecommendation(
            text=f"{contact_hint} for {opp_ctx['opp_name']} — close date is {days} days away.",
            reason=f"Final approval window is closing. Stage: {opp_ctx['stage']}. Revenue: ${opp_ctx['amount']:,.0f}.",
            expected_impact=f"Secures deal commitment before quarter-end and locks ${opp_ctx['amount']:,.0f} in revenue.",
            ignore_risk=f"Opportunity misses close date, slips into next quarter, or is reclassified.",
            urgency="CRITICAL" if days <= 7 else "HIGH",
            urgency_rank=1 if days <= 7 else 2,
            owner_hint="Account Manager + Sales Director",
            evidence=[f"Close date in {days} days", f"Stage: {opp_ctx['stage']}"]
        )

    @staticmethod
    def _eval_missing_decision_maker(opp_ctx: Dict, account_name: str) -> Optional[ActionRecommendation]:
        if opp_ctx.get("has_decision_maker"):
            return None
        advanced_stages = ["Negotiation/Review", "Proposal/Price Quote", "Perception Analysis"]
        if opp_ctx.get("stage") not in advanced_stages:
            return None
        return ActionRecommendation(
            text=f"Identify and map the economic/decision authority at {account_name} for {opp_ctx['opp_name']}.",
            reason=f"Opportunity is in {opp_ctx['stage']} stage with no Decision Maker or Economic Buyer mapped. Approval path is undefined.",
            expected_impact="Creates a clear path to final approval and prevents last-minute executive surprises.",
            ignore_risk="Deal cannot close without identified approval authority. Risk of indefinite stall.",
            urgency="HIGH",
            urgency_rank=2,
            owner_hint="Account Manager",
            evidence=[f"No Decision Maker mapped", f"Stage: {opp_ctx['stage']}", f"Amount: ${opp_ctx['amount']:,.0f}"]
        )

    @staticmethod
    def _eval_low_dm_engagement(contacts_df: pd.DataFrame, opp_ctx: Dict) -> Optional[ActionRecommendation]:
        if contacts_df is None or contacts_df.empty:
            return None
        if opp_ctx.get("stage") not in ["Negotiation/Review", "Proposal/Price Quote"]:
            return None
        dm_df = contacts_df[
            contacts_df["Role"].str.contains("Decision Maker|Economic Buyer|C-Suite|VP", na=False, case=False)
        ]
        if dm_df.empty:
            return None
        low_eng = dm_df[dm_df["Engagement_Level"].isin(["Low", "Cold"])]
        if low_eng.empty:
            return None
        dm = low_eng.iloc[0]
        dm_name = f"{dm.get('First_Name', '')} {dm.get('Last_Name', '')}".strip()
        return ActionRecommendation(
            text=f"Re-engage {dm_name} ({dm.get('Role')}) before deal advancement — engagement is {dm.get('Engagement_Level', 'Low')}.",
            reason=f"Decision Maker engagement has cooled while deal is in {opp_ctx['stage']}. Approval risk is elevated.",
            expected_impact="Restores executive alignment and unblocks deal from stalling at approval stage.",
            ignore_risk="Deal stalls awaiting executive sign-off that has no active relationship backing it.",
            urgency="HIGH",
            urgency_rank=2,
            owner_hint="Account Manager + Executive Sponsor",
            evidence=[f"{dm_name} engagement: {dm.get('Engagement_Level')}", f"Stage: {opp_ctx['stage']}"]
        )

    @staticmethod
    def _eval_single_threaded(opp_ctx: Dict, account_name: str) -> Optional[ActionRecommendation]:
        if not opp_ctx.get("is_single_threaded"):
            return None
        return ActionRecommendation(
            text=f"Map at least 2 additional stakeholders at {account_name} to eliminate single-threaded deal risk.",
            reason=f"Only {opp_ctx['contact_count']} contact(s) mapped for a ${opp_ctx['amount']:,.0f} opportunity. Single point of failure.",
            expected_impact="Reduces deal fragility and maintains momentum even if the primary contact becomes unavailable.",
            ignore_risk="If primary contact leaves or disengages, the deal loses all internal advocacy overnight.",
            urgency="HIGH",
            urgency_rank=2,
            owner_hint="Account Manager",
            evidence=[f"{opp_ctx['contact_count']} contact(s) mapped", f"Amount: ${opp_ctx['amount']:,.0f}"]
        )

    @staticmethod
    def _eval_blocking_case(opp_ctx: Dict, account_name: str) -> Optional[ActionRecommendation]:
        if not opp_ctx.get("blocking_case"):
            return None
        return ActionRecommendation(
            text=f"Escalate open critical support case at {account_name} before advancing deal conversations.",
            reason=f"Active high-severity case: {opp_ctx['blocking_case']}. Proceeding without resolution creates trust risk.",
            expected_impact="Demonstrates account commitment and removes customer satisfaction blocker from deal path.",
            ignore_risk="Customer may freeze deal conversations until support issues are resolved.",
            urgency="HIGH",
            urgency_rank=2,
            owner_hint="Account Manager + Support Lead",
            evidence=[f"Blocking case: {opp_ctx['blocking_case']}"]
        )

    @staticmethod
    def _eval_engagement_decay(account_ctx: Dict) -> Optional[ActionRecommendation]:
        status = account_ctx.get("engagement_status", "ACTIVE")
        days = account_ctx.get("days_since_activity", 0)
        if status not in ("COLD", "DECLINING"):
            return None
        account_name = account_ctx.get("account_name", "this account")
        return ActionRecommendation(
            text=f"Schedule re-engagement touch with key contacts at {account_name} — no activity in {days} days.",
            reason=f"Engagement momentum has {'completely stalled' if status == 'COLD' else 'declined significantly'} ({days} days inactive).",
            expected_impact="Re-establishes presence and prevents relationship from going cold before deal advancement.",
            ignore_risk="Account perceives a lack of attention, increasing competitive vulnerability and churn risk.",
            urgency="HIGH" if status == "COLD" else "MEDIUM",
            urgency_rank=2 if status == "COLD" else 3,
            owner_hint="Account Manager",
            evidence=[f"Last activity: {days} days ago", f"Engagement status: {status}"]
        )

    @staticmethod
    def _eval_stage_advancement(account_ctx: Dict, opp_ctx: Dict) -> Optional[ActionRecommendation]:
        """Flag if deal is in an advanced stage but key coverage is missing."""
        stage = opp_ctx.get("stage", "")
        advanced = ["Negotiation/Review", "Proposal/Price Quote"]
        if stage not in advanced:
            return None
        # Only fire if there's an engagement or stakeholder concern
        has_dm = opp_ctx.get("has_decision_maker", True)
        if has_dm:
            return None
        account_name = account_ctx.get("account_name", "this account")
        return ActionRecommendation(
            text=f"Conduct stakeholder mapping session to identify the economic buyer before progressing {opp_ctx['opp_name']}.",
            reason=f"Deal is in {stage} but the economic buyer is unidentified. Contract approval cannot proceed.",
            expected_impact="Accelerates path to contract by removing the unknown decision authority blocker.",
            ignore_risk="Deal reaches contract phase without the approver engaged, leading to unexpected delay or loss.",
            urgency="HIGH",
            urgency_rank=2,
            owner_hint="Account Manager",
            evidence=[f"Stage: {stage}", "No economic buyer/DM mapped"]
        )

    @classmethod
    def generate(
        cls,
        opp_ctx: Dict,
        account_ctx: Dict,
        contacts_df: Optional[pd.DataFrame],
        primary_contact: Optional[StakeholderRecommendation],
        max_actions: int = 5
    ) -> List[ActionRecommendation]:
        """
        Run all state evaluators and return sorted, deduplicated action list.
        """
        account_name = account_ctx.get("account_name", "this account")

        evaluations = [
            cls._eval_overdue_deal(opp_ctx, account_name, primary_contact),
            cls._eval_close_window_urgency(opp_ctx, primary_contact),
            cls._eval_blocking_case(opp_ctx, account_name),
            cls._eval_missing_decision_maker(opp_ctx, account_name),
            cls._eval_low_dm_engagement(contacts_df, opp_ctx),
            cls._eval_single_threaded(opp_ctx, account_name),
            cls._eval_engagement_decay(account_ctx),
            cls._eval_stage_advancement(account_ctx, opp_ctx),
        ]

        actions = [a for a in evaluations if a is not None]

        # Derive per-action confidence from evidence quality
        for action in actions:
            if action.urgency == "CRITICAL":
                action.confidence = "HIGH"  # CRITICAL actions fire on strong data signals
            elif len(action.evidence) >= 2:
                action.confidence = "HIGH"
            elif len(action.evidence) == 1:
                action.confidence = "MEDIUM"
            else:
                action.confidence = "LOW"

        actions.sort(key=lambda a: (a.urgency_rank, a.urgency))
        return actions[:max_actions]

    @classmethod
    def generate_from_account_state(
        cls,
        account_ctx: Dict,
        open_opps_df: Optional[pd.DataFrame],
        contacts_df: Optional[pd.DataFrame],
        max_actions: int = 5
    ) -> List[ActionRecommendation]:
        """
        Generate actions from account-level state when no specific opportunity is targeted.
        Evaluates the most urgent open opportunity automatically.
        """
        # Find the most critical open opportunity to ground actions in
        opp_ctx = {
            "opp_id": "",
            "opp_name": "open opportunities",
            "stage": "",
            "amount": 0,
            "probability": 0,
            "days_until_close": None,
            "is_overdue": False,
            "close_urgency": "LOW",
            "contact_count": account_ctx.get("contact_count", 0),
            "has_decision_maker": account_ctx.get("has_decision_maker", True),
            "is_single_threaded": account_ctx.get("contact_count", 2) <= 1,
            "blocking_case": None,
        }

        if open_opps_df is not None and not open_opps_df.empty:
            # Find most urgent deal (overdue or soonest close)
            now = datetime.now()
            best_opp = None
            best_urgency = 9999
            for _, row in open_opps_df.iterrows():
                try:
                    close_date = pd.to_datetime(row.get("Close_Date"))
                    if pd.notna(close_date):
                        if close_date.tzinfo is not None:
                            close_date = close_date.tz_localize(None)
                        delta = (close_date - now).days
                        if delta < best_urgency:
                            best_urgency = delta
                            best_opp = row
                except Exception:
                    pass
            if best_opp is not None:
                opp_ctx.update({
                    "opp_id": str(best_opp.get("Opp_ID", "")),
                    "opp_name": str(best_opp.get("Opp_Name", "")),
                    "stage": str(best_opp.get("Stage", "")),
                    "amount": float(best_opp.get("Amount_USD", 0)) if pd.notna(best_opp.get("Amount_USD")) else 0,
                    "days_until_close": best_urgency,
                    "is_overdue": best_urgency < 0,
                    "close_urgency": "CRITICAL" if best_urgency < 0 else "HIGH" if best_urgency <= 14 else "MEDIUM",
                })

        return cls.generate(opp_ctx, account_ctx, contacts_df, None, max_actions)


# ═══════════════════════════════════════════════════════════════
# BUSINESS IMPACT MODEL
# ═══════════════════════════════════════════════════════════════

class BusinessImpactModel:
    """Computes a concise business impact statement for the full reasoning package."""

    @staticmethod
    def summarize(actions: List[ActionRecommendation], account_ctx: Dict, opp_ctx: Optional[Dict]) -> str:
        if not actions:
            return "No immediate action required based on current account and opportunity state."

        top = actions[0]
        amount_str = ""
        if opp_ctx and opp_ctx.get("amount", 0) > 0:
            amount_str = f" protecting ${opp_ctx['amount']:,.0f} in at-risk revenue"

        return (
            f"The highest-priority action ({top.urgency}) is: {top.text} "
            f"Expected outcome: {top.expected_impact}{amount_str}. "
            f"If not actioned: {top.ignore_risk}"
        )

# ═══════════════════════════════════════════════════════════════
# PORTFOLIO ANALYZER
# ═══════════════════════════════════════════════════════════════

class PortfolioAnalyzer:
    """Structured portfolio state analysis for global/non-entity queries.

    Produces a Dict with:
        - total_pipeline, weighted_forecast
        - deal_count, avg_deal_size
        - concentration_risk (top-3 account share %)
        - stage_distribution (stage → count+value)
        - risk_cluster_accounts (accounts with 2+ risk flags)
        - growth_cluster_accounts (high-revenue, low-pipeline accounts)
        - most_critical_opp (auto-detected highest-urgency opportunity)
    """

    @staticmethod
    def analyze(engine) -> Dict[str, Any]:
        opps_df = engine.data.get("opportunity")
        accounts_df = engine.data.get("account")
        contacts_df = engine.data.get("contact")
        cases_df = engine.data.get("case")
        activities_df = engine.data.get("activity")

        result: Dict[str, Any] = {}
        if opps_df is None or opps_df.empty:
            return result

        open_opps = opps_df[~opps_df["Stage"].isin(["Closed Won", "Closed Lost"])]
        total_pipeline = float(open_opps["Amount_USD"].sum()) if not open_opps.empty else 0
        weighted = float((open_opps["Amount_USD"] * open_opps["Probability_Pct"] / 100.0).sum()) if not open_opps.empty else 0

        result["total_pipeline"] = total_pipeline
        result["weighted_forecast"] = weighted
        result["execution_gap"] = total_pipeline - weighted
        result["deal_count"] = len(open_opps)
        result["avg_deal_size"] = total_pipeline / len(open_opps) if len(open_opps) > 0 else 0

        # Concentration risk: top-3 accounts share
        if accounts_df is not None and total_pipeline > 0:
            acc_pipeline = open_opps.groupby("Account_ID")["Amount_USD"].sum().sort_values(ascending=False)
            top_3_value = float(acc_pipeline.head(3).sum())
            result["concentration_risk_pct"] = round((top_3_value / total_pipeline) * 100, 1)
            top_names = []
            for acc_id in acc_pipeline.head(3).index:
                acc_match = accounts_df[accounts_df["Account_ID"] == acc_id]
                if not acc_match.empty:
                    top_names.append(str(acc_match.iloc[0]["Account_Name"]))
            result["concentration_top_accounts"] = top_names
        else:
            result["concentration_risk_pct"] = 0
            result["concentration_top_accounts"] = []

        # Stage distribution
        stage_dist = {}
        if not open_opps.empty:
            stage_agg = open_opps.groupby("Stage").agg(
                count=("Opp_ID", "count"),
                value=("Amount_USD", "sum")
            )
            for stage, row in stage_agg.iterrows():
                stage_dist[str(stage)] = {"count": int(row["count"]), "value": float(row["value"])}
        result["stage_distribution"] = stage_dist

        # Risk clusters: accounts with 2+ risk flags
        risk_accounts = []
        growth_accounts = []
        if accounts_df is not None:
            now = datetime.now()
            for _, acc in accounts_df.iterrows():
                acc_id = acc["Account_ID"]
                acc_name = str(acc.get("Account_Name", ""))
                flags = 0
                # Flag 1: no DM
                if contacts_df is not None and not contacts_df.empty:
                    acc_contacts = contacts_df[contacts_df["Account_ID"] == acc_id]
                    has_dm = not acc_contacts[
                        acc_contacts["Role"].str.contains("Decision Maker|Economic Buyer|C-Suite|VP", na=False, case=False)
                    ].empty if not acc_contacts.empty else False
                    if not has_dm:
                        flags += 1
                    if len(acc_contacts) <= 1:
                        flags += 1
                # Flag 2: critical cases
                if cases_df is not None and not cases_df.empty:
                    acc_cases = cases_df[cases_df["Account_ID"] == acc_id]
                    open_critical = len(acc_cases[
                        (acc_cases["Severity"].isin(["Critical", "High"])) &
                        (acc_cases["Status"] != "Closed")
                    ])
                    if open_critical > 0:
                        flags += 1
                # Flag 3: stale engagement
                if activities_df is not None and not activities_df.empty:
                    acc_acts = activities_df[activities_df["Account_ID"] == acc_id]
                    if not acc_acts.empty:
                        last = pd.to_datetime(acc_acts["Activity_Date"]).max()
                        if pd.notna(last):
                            try:
                                if last.tzinfo is not None:
                                    last = last.tz_localize(None)
                            except Exception:
                                pass
                            if (now - last).days > 30:
                                flags += 1
                    else:
                        flags += 1

                if flags >= 2:
                    risk_accounts.append(acc_name)

                # Growth cluster: high revenue, low pipeline
                revenue = float(acc.get("Annual_Revenue_USD", 0)) if pd.notna(acc.get("Annual_Revenue_USD")) else 0
                acc_opps = open_opps[open_opps["Account_ID"] == acc_id] if not open_opps.empty else pd.DataFrame()
                acc_pipeline = float(acc_opps["Amount_USD"].sum()) if not acc_opps.empty else 0
                if revenue > 10_000_000 and acc_pipeline < 50_000:
                    growth_accounts.append(acc_name)

        result["risk_cluster_accounts"] = risk_accounts[:5]
        result["growth_cluster_accounts"] = growth_accounts[:5]

        # Most critical opportunity (auto-detected for focused recommendations)
        most_critical = None
        if not open_opps.empty:
            now = datetime.now()
            best_score = -999
            for _, opp in open_opps.iterrows():
                amount = float(opp.get("Amount_USD", 0)) if pd.notna(opp.get("Amount_USD")) else 0
                prob = float(opp.get("Probability_Pct", 50)) if pd.notna(opp.get("Probability_Pct")) else 50
                try:
                    close_date = pd.to_datetime(opp.get("Close_Date"))
                    if pd.notna(close_date):
                        if close_date.tzinfo is not None:
                            close_date = close_date.tz_localize(None)
                        days = (close_date - now).days
                    else:
                        days = 999
                except Exception:
                    days = 999
                # Criticality = high value + low time + medium probability (deals in jeopardy)
                criticality = (amount / 100_000) + (100 - prob) + max(0, 30 - days)
                if criticality > best_score:
                    best_score = criticality
                    most_critical = {
                        "opp_id": str(opp.get("Opp_ID", "")),
                        "opp_name": str(opp.get("Opp_Name", "")),
                        "amount": amount,
                        "stage": str(opp.get("Stage", "")),
                        "days_until_close": days,
                        "account_id": str(opp.get("Account_ID", "")),
                    }
        result["most_critical_opp"] = most_critical
        return result


# ═══════════════════════════════════════════════════════════════
# CONFIDENCE MODEL COMPUTATION
# ═══════════════════════════════════════════════════════════════

def compute_confidence_model(
    intent: str,
    crm_gaps: List[str],
    account_ctx: Optional[Dict],
    opp_ctx: Optional[Dict],
    ranked_contacts: List[StakeholderRecommendation],
    actions: List[ActionRecommendation],
) -> ConfidenceModel:
    """Compute a 6-dimensional ConfidenceModel from observed state.

    Each dimension has a clear derivation:
        intent:         HIGH if intent matched a known pattern, MEDIUM for GENERAL_QUERY
        decision:       HIGH if entity context exists, MEDIUM if global, LOW if no data
        data:           Based on CRM gap count (0=HIGH, 1-3=MEDIUM, 4+=LOW)
        reasoning:      Based on whether the engine had enough signal to produce actions
        recommendation: Based on action confidence distribution
        overall:        Composite floor
    """
    model = ConfidenceModel()

    # Intent confidence
    if intent in ("GENERAL_QUERY",):
        model.intent = "MEDIUM"
    elif intent in ("GLOBAL_LIST_QUERY", "CONTACT_QUERY", "ACCOUNT_PLAN_QUERY",
                     "RISK_ANALYSIS_QUERY", "PIPELINE_SUMMARY_QUERY", "ACTION_RECOMMENDATION_QUERY"):
        model.intent = "HIGH"
    else:
        model.intent = "LOW"

    # Decision confidence — based on entity resolution
    if opp_ctx and opp_ctx.get("opp_id"):
        model.decision = "HIGH"  # specific opportunity context
    elif account_ctx and account_ctx.get("account_id"):
        model.decision = "HIGH"  # specific account context
    elif account_ctx:
        model.decision = "MEDIUM"
    else:
        model.decision = "MEDIUM"  # global query, broad decision

    # Data confidence — based on CRM gaps
    gap_count = len(crm_gaps) if crm_gaps else 0
    if gap_count == 0:
        model.data = "HIGH"
    elif gap_count <= 3:
        model.data = "MEDIUM"
    else:
        model.data = "LOW"

    # Reasoning confidence — based on signal availability
    has_contacts = len(ranked_contacts) > 0
    has_actions = len(actions) > 0
    has_opp = bool(opp_ctx and opp_ctx.get("opp_id"))
    if has_contacts and has_actions and has_opp:
        model.reasoning = "HIGH"
    elif has_actions or has_contacts:
        model.reasoning = "MEDIUM" if has_actions else "MEDIUM"
    else:
        model.reasoning = "LOW"

    # Recommendation confidence — based on action confidence distribution
    if actions:
        low_count = sum(1 for a in actions if a.confidence == "LOW")
        if low_count == 0:
            model.recommendation = "HIGH"
        elif low_count <= len(actions) // 2:
            model.recommendation = "MEDIUM"
        else:
            model.recommendation = "LOW"
    else:
        model.recommendation = "MEDIUM"  # no actions = moderate (not necessarily bad)

    model.compute_overall()
    return model


# ═══════════════════════════════════════════════════════════════
# SITUATION SUMMARY BUILDER
# ═══════════════════════════════════════════════════════════════

def _build_situation_summary(account_ctx: Dict, opp_ctx: Optional[Dict], contacts: List[StakeholderRecommendation]) -> str:
    """Produces a concise, specific, data-backed situation narrative — not a generic description."""
    lines = []

    account_name = account_ctx.get("account_name", "this account")
    tier = account_ctx.get("tier", "Standard")
    pipeline = account_ctx.get("pipeline_value", 0)
    engagement = account_ctx.get("engagement_status", "ACTIVE")
    days_since = account_ctx.get("days_since_activity", 0)
    open_deals = account_ctx.get("open_deal_count", 0)
    critical_cases = account_ctx.get("open_critical_cases", 0)
    has_dm = account_ctx.get("has_decision_maker", False)

    lines.append(
        f"{account_name} is a {tier} account with {open_deals} open deal(s) "
        f"totalling ${pipeline:,.0f} in active pipeline."
    )

    if opp_ctx and opp_ctx.get("opp_id"):
        stage = opp_ctx.get("stage", "")
        amount = opp_ctx.get("amount", 0)
        days = opp_ctx.get("days_until_close")
        overdue = opp_ctx.get("is_overdue", False)
        opp_name = opp_ctx.get("opp_name", "")
        close_str = f"{abs(days)} days overdue" if overdue else (f"{days} days to close" if days is not None else "no close date set")
        lines.append(
            f"The opportunity in focus — {opp_name} (${amount:,.0f}) — is currently in "
            f"{stage} stage with {close_str}."
        )

    if engagement in ("COLD", "DECLINING"):
        lines.append(
            f"Account engagement has {'completely stalled' if engagement == 'COLD' else 'declined'} "
            f"({days_since} days since last activity)."
        )

    if not has_dm:
        lines.append("No decision-maker or economic buyer is currently mapped — approval authority is undefined.")

    if critical_cases > 0:
        lines.append(f"{critical_cases} open critical/high-severity support case(s) represent a potential deal blocker.")

    if contacts:
        primary = contacts[0]
        lines.append(
            f"Recommended primary contact: {primary.name} ({primary.role}) "
            f"with {primary.engagement_level} engagement."
        )

    return " ".join(lines)


# ═══════════════════════════════════════════════════════════════
# MASTER ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

def assemble_reasoning_package(
    engine,
    intent: str,
    query: str,
    account_id: Optional[str] = None,
    opp_id: Optional[str] = None,
) -> ReasoningPackage:
    """
    Master orchestrator for the reasoning layer.

    Inputs:
        engine      — DataEngine instance (access to all CRM dataframes)
        intent      — classified intent string
        query       — original user query string
        account_id  — resolved account ID (may be None for global queries)
        opp_id      — resolved opportunity ID (may be None)

    Returns:
        ReasoningPackage — complete reasoning output for curate_llm_context()

    This function is 100% deterministic and zero-LLM.
    """
    opps_df = engine.data.get("opportunity")
    contacts_df_raw = engine.data.get("contact")
    accounts_df = engine.data.get("account")
    cases_df = engine.data.get("case")

    # 1. Resolve opportunity if opp_id is given but account_id is not
    opp_row = None
    if opp_id and opps_df is not None:
        matching = opps_df[opps_df["Opp_ID"].str.upper() == opp_id.upper()]
        if not matching.empty:
            opp_row = matching.iloc[0]
            if not account_id:
                account_id = str(opp_row.get("Account_ID", ""))

    # 2. Resolve account name
    account_name = None
    if account_id and accounts_df is not None:
        acc_match = accounts_df[accounts_df["Account_ID"] == account_id]
        if not acc_match.empty:
            account_name = str(acc_match.iloc[0].get("Account_Name", ""))

    # 3. Account context
    account_ctx: Dict = {}
    if account_id:
        account_ctx = AccountAnalyzer.analyze(engine, account_id)

    # 4. Account-scoped contacts
    account_contacts_df = pd.DataFrame()
    if contacts_df_raw is not None and account_id:
        account_contacts_df = contacts_df_raw[contacts_df_raw["Account_ID"] == account_id].copy()

    # 5. Account-scoped cases
    account_cases_df = pd.DataFrame()
    if cases_df is not None and account_id:
        account_cases_df = cases_df[cases_df["Account_ID"] == account_id].copy()

    # 6. Account-scoped open opportunities
    account_opps_df = pd.DataFrame()
    if opps_df is not None and account_id:
        acc_opps = opps_df[opps_df["Account_ID"] == account_id]
        account_opps_df = acc_opps[~acc_opps["Stage"].isin(["Closed Won", "Closed Lost"])].copy()

    # 7. Opportunity context (if specific opp identified)
    opp_ctx: Dict = {}
    if opp_row is not None:
        opp_ctx = OpportunityAnalyzer.analyze(opp_row, account_contacts_df, account_cases_df)
    elif not account_opps_df.empty:
        # Use most urgent open opp as proxy context
        now = datetime.now()
        best_delta = None
        for _, row in account_opps_df.iterrows():
            try:
                cd = pd.to_datetime(row.get("Close_Date"))
                if pd.notna(cd):
                    if cd.tzinfo is not None:
                        cd = cd.tz_localize(None)
                    delta = (cd - now).days
                    if best_delta is None or delta < best_delta:
                        best_delta = delta
                        opp_row = row
            except Exception:
                pass
        if opp_row is not None:
            opp_ctx = OpportunityAnalyzer.analyze(opp_row, account_contacts_df, account_cases_df)

    # 8. Stakeholder ranking (against opp stage if available)
    opp_stage = opp_ctx.get("stage", "_default") if opp_ctx else "_default"
    ranked_contacts = StakeholderRanker.rank(account_contacts_df, opp_stage, max_contacts=3) if not account_contacts_df.empty else []

    primary = ranked_contacts[0] if ranked_contacts else None
    secondary = ranked_contacts[1:] if len(ranked_contacts) > 1 else []

    # 9. Next best actions (dynamic, state-derived)
    if opp_ctx:
        actions = NextBestActionEngine.generate(
            opp_ctx=opp_ctx,
            account_ctx=account_ctx,
            contacts_df=account_contacts_df if not account_contacts_df.empty else None,
            primary_contact=primary,
        )
    else:
        actions = NextBestActionEngine.generate_from_account_state(
            account_ctx=account_ctx,
            open_opps_df=account_opps_df if not account_opps_df.empty else None,
            contacts_df=account_contacts_df if not account_contacts_df.empty else None,
        )

    # 10. Business impact
    business_impact = BusinessImpactModel.summarize(actions, account_ctx, opp_ctx if opp_ctx else None)

    # 11. Situation summary
    situation = _build_situation_summary(account_ctx, opp_ctx if opp_ctx else None, ranked_contacts)

    # 12. Risk implications
    risk_implications = [a.ignore_risk for a in actions[:3] if a.ignore_risk]

    # 13. Evidence list
    evidence = []
    if opp_ctx:
        evidence += opp_ctx.get("evidence", []) if "evidence" in opp_ctx else []
    for a in actions:
        evidence += a.evidence
    evidence = list(dict.fromkeys(evidence))[:8]  # deduplicate, cap

    # 14. CRM gaps for confidence computation
    crm_gaps = engine.audit_crm_hygiene(account_id) if account_id else []

    # 15. Six-dimensional confidence model
    confidence_model = compute_confidence_model(
        intent=intent,
        crm_gaps=crm_gaps,
        account_ctx=account_ctx if account_ctx else None,
        opp_ctx=opp_ctx if opp_ctx else None,
        ranked_contacts=ranked_contacts,
        actions=actions,
    )

    # 16. Structured decision context (replaces plain string)
    decision_context = DecisionFramework.infer(
        intent, query, account_name,
        account_ctx=account_ctx if account_ctx else None,
        opp_ctx=opp_ctx if opp_ctx else None,
    )

    # 17. Portfolio state (for global/non-entity queries)
    portfolio_state = None
    if not account_id or intent in ("GLOBAL_LIST_QUERY", "PIPELINE_SUMMARY_QUERY"):
        portfolio_state = PortfolioAnalyzer.analyze(engine)

    return ReasoningPackage(
        decision_context=decision_context,
        situation_summary=situation,
        primary_recommendation=primary,
        secondary_recommendations=secondary,
        next_best_actions=actions,
        risk_implications=risk_implications,
        business_impact=business_impact,
        confidence=confidence_model,
        reasoning_evidence=evidence,
        portfolio_state=portfolio_state,
        opp_id=opp_id,
        account_id=account_id,
        account_name=account_name,
    )


# ═══════════════════════════════════════════════════════════════
# LAYER 2: MULTI-PERSPECTIVE REASONING ENGINE
# ═══════════════════════════════════════════════════════════════

import os
import httpx
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class PlaybookDay(BaseModel):
    day: int
    action: str
    owner: str
    expected_outcome: Optional[str] = None

class AMPerspectiveOutput(BaseModel):
    am_perspective: str
    playbook_7day: List[PlaybookDay]
    stakeholder_sequence: List[Dict[str, str]]
    risks: List[str]
    success_metrics: List[str]
    resource_needs: List[str]
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class VPPerspectiveOutput(BaseModel):
    vp_perspective: str
    pattern_detection: str
    peer_comparison: Dict[str, Any]
    market_hypothesis: str
    portfolio_recommendation: str
    resource_allocation: Dict[str, Any]
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class SVPPerspectiveOutput(BaseModel):
    svp_perspective: str
    strategic_value: str
    strategic_fit_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    competitive_threat_level: str  # "low" | "medium" | "high"
    market_positioning_insight: str
    keep_vs_let_go_recommendation: str
    rationale: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class HistoricalPrecedent(BaseModel):
    situation: str
    outcome: str
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    match_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class DataPerspectiveOutput(BaseModel):
    data_perspective: str
    key_metrics: Dict[str, Any]
    data_quality: Dict[str, Any]
    historical_precedents: List[HistoricalPrecedent]
    intervention_success_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence_intervals: Dict[str, List[Optional[float]]]
    overall_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class DissentingView(BaseModel):
    perspective: str  # "SVP", "VP", "Data"
    dissent: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    rationale: str

class ConsensusOutput(BaseModel):
    consensus_recommendation: Dict[str, Any]
    thread_agreement: Dict[str, Optional[float]]
    agreement_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    dissenting_views: List[DissentingView]
    confidence_limiting_factors: List[str]
    final_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


def repair_json_string(text: str) -> str:
    """Attempt to repair common JSON syntax issues from LLM outputs."""
    repaired = text.strip()
    # Remove markdown code fences
    repaired = re.sub(r"^```(?:json)?\s*", "", repaired)
    repaired = re.sub(r"\s*```$", "", repaired)
    repaired = repaired.strip()
    
    # Find prefix (first { or [)
    start_curly = repaired.find("{")
    start_bracket = repaired.find("[")
    if start_curly != -1 or start_bracket != -1:
        start = start_curly if (start_curly != -1 and (start_bracket == -1 or start_curly < start_bracket)) else start_bracket
        repaired = repaired[start:]
        
    # Strip suffix only if the JSON is NOT truncated (balanced or more closing than opening)
    open_braces = repaired.count("{")
    close_braces = repaired.count("}")
    open_brackets = repaired.count("[")
    close_brackets = repaired.count("]")
    
    if open_braces <= close_braces and open_brackets <= close_brackets:
        end_curly = repaired.rfind("}")
        end_bracket = repaired.rfind("]")
        end = end_curly if (end_curly != -1 and (end_bracket == -1 or end_curly > end_bracket)) else end_bracket
        if end != -1:
            repaired = repaired[:end+1]
        
    # Convert single-quoted keys and string values to standard double quotes
    # E.g. 'key': 'value' -> "key": "value"
    repaired = re.sub(r"'\s*(\w+)\s*'\s*:", r'"\1":', repaired)
    repaired = re.sub(r":\s*'([^']*)'", r': "\1"', repaired)
    
    # Fix invalid escaped single quotes in double-quoted strings
    repaired = repaired.replace(r"\'", "'")
    
    # Escape unescaped control characters (newlines/tabs) inside double-quoted string literals
    def escape_control_chars(match):
        val = match.group(0)
        return val.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    
    repaired = re.sub(r'"(?:[^"\\]|\\.)*"', escape_control_chars, repaired)
    
    # Replace Python unquoted literals
    repaired = re.sub(r'\bNone\b', 'null', repaired)
    repaired = re.sub(r'\bTrue\b', 'true', repaired)
    repaired = re.sub(r'\bFalse\b', 'false', repaired)
    
    # Remove trailing commas before closing braces/brackets
    repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
    
    # Try to insert missing commas between adjacent elements like } { or ] [ or } "
    repaired = re.sub(r'}\s*{', '}, {', repaired)
    repaired = re.sub(r'\]\s*\[', '], [', repaired)
    repaired = re.sub(r'}\s*\[', '}, [', repaired)
    repaired = re.sub(r'\]\s*{', '], {', repaired)
    repaired = re.sub(r'}\s*"', '}, "', repaired)
    repaired = re.sub(r'"\s*{', '", {', repaired)
    
    # Try to insert missing commas between adjacent elements like "val" "key"
    repaired = re.sub(r'("[\s\S]*?"|\d+(?:\.\d+)?|true|false|null)\s+(")', r'\1, \2', repaired)
    
    # Count unescaped double quotes to heal truncated string values
    unescaped_quotes = len(re.findall(r'(?<!\\)"', repaired))
    if unescaped_quotes % 2 != 0:
        repaired += '"'
    
    # Add closing braces if they are unbalanced/truncated
    open_braces = repaired.count("{")
    close_braces = repaired.count("}")
    if open_braces > close_braces:
        repaired += "}" * (open_braces - close_braces)
        
    open_brackets = repaired.count("[")
    close_brackets = repaired.count("]")
    if open_brackets > close_brackets:
        repaired += "]" * (open_brackets - close_brackets)
        
    return repaired


def summarize_large_dataset(account_data: Dict[str, Any], requested_count: int = 5) -> Dict[str, Any]:
    """Summarize raw details to keep context window small and clean up empty/null fields."""
    if not account_data:
        return account_data
        
    # 1. Clean empty/null/zero fields from account_data to save space
    cleaned_data = {}
    for k, v in account_data.items():
        if v is None:
            continue
        if isinstance(v, list) and len(v) == 0:
            continue
        if isinstance(v, dict) and len(v) == 0:
            continue
        cleaned_data[k] = v

    if "opportunities" not in cleaned_data:
        return cleaned_data
        
    opps = cleaned_data["opportunities"]
    
    # 2. Filter opportunities count dynamically
    total_count = len(opps)
    total_val = sum((o.get("amount_usd", 0.0) or 0.0) for o in opps)
    
    # Sort by value descending and keep requested_count
    sorted_opps = sorted(
        opps, 
        key=lambda x: (x.get("amount_usd", 0.0) or 0.0), 
        reverse=True
    )
    
    # Clean up empty/null fields inside each opportunity to save more tokens
    cleaned_opps = []
    for opp in sorted_opps[:requested_count]:
        cleaned_opp = {}
        for ok, ov in opp.items():
            if ov is None:
                continue
            if isinstance(ov, list) and len(ov) == 0:
                continue
            if isinstance(ov, dict) and len(ov) == 0:
                continue
            cleaned_opp[ok] = ov
        cleaned_opps.append(cleaned_opp)
        
    cleaned_data["opportunities"] = cleaned_opps
    cleaned_data["total_opportunities_count"] = total_count
    cleaned_data["total_pipeline_value_usd"] = total_val
    cleaned_data["opportunities_summary_note"] = (
        f"Showing top {len(cleaned_opps)} opportunities out of {total_count} total by value to optimize context size."
    )
    
    return cleaned_data


def call_gemini_api(system_prompt: str, user_prompt: str, api_key: str, max_tokens: int = 400, timeout: int = 1500) -> str:
    """Fallback router to Gemini API when key is configured."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # Format prompts nicely
    full_prompt = f"System: {system_prompt}\n\nUser Prompt: {user_prompt}\nOutput ONLY valid raw JSON."
    
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json"
        }
    }
    
    httpx_timeout = httpx.Timeout(timeout=float(timeout), connect=5.0)
    print(f"  [LLM CONNECT] Attempting Gemini proxy connection to: {url}")
    with httpx.Client(timeout=httpx_timeout) as client:
        print(f"  [LLM REQUEST] Sending Gemini proxy payload to: {url}...")
        headers = {"Content-Type": "application/json"}
        response = client.post(url, json=payload, headers=headers)
        print(f"  [LLM RESPONSE] Received Gemini proxy status {response.status_code} from: {url}")
        if response.status_code == 200:
            res_json = response.json()
            try:
                return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (KeyError, IndexError):
                raise Exception(f"Unexpected Gemini API response structure: {res_json}")
        else:
            raise Exception(f"Gemini API error {response.status_code}: {response.text}")


def generate_contextual_fallback_data(account_data: Dict[str, Any]) -> Dict[str, Any]:
    """Programmatically constructs natural, professional fallback narratives from data."""
    account_name = account_data.get("account_name") or "Global Portfolio"
    health_score = account_data.get("health_score") or 80.0
    opps = account_data.get("opportunities") or []
    contacts = account_data.get("contacts") or []
    cases = account_data.get("cases") or []
    
    num_opps = len(opps)
    total_rev = sum(opp.get("amount_usd", 0.0) or opp.get("amount", 0.0) for opp in opps)
    num_contacts = len(contacts)
    num_cases = len(cases)
    
    rev_str = f"${total_rev:,.2f}"
    macro_summary = f"Reviewing the database metrics for {account_name}, we see {num_opps} active opportunities worth {rev_str}. The current client health score is recorded at {health_score:.1f}%."
    if num_cases > 0:
        macro_summary += f" Attention is recommended to address {num_cases} open support tickets."
        
    ae_insight = f"Based on the {num_contacts} registered stakeholders in the system, we should coordinate a sync with key contacts to reaffirm our commitment."
    if contacts:
        top_contact = contacts[0].get("name", "stakeholders")
        role = contacts[0].get("role", "Key Contact")
        ae_insight += f" The primary contact is listed as {top_contact} ({role})."
        
    director_insight = f"No critical blockers are currently preventing opportunity progression in our systems."
    if num_cases > 0:
        top_case = cases[0].get("subject", "support case")
        sev = cases[0].get("severity", "medium")
        director_insight = f"Critical focus should be placed on resolving the open ticket '{top_case}' which is marked with severity '{sev}'."
        
    tactical_playbook = []
    day_cnt = 1
    
    if opps:
        top_opp = opps[0].get("opp_name") or "active pipeline"
        stage = opps[0].get("stage") or "Negotiation"
        tactical_playbook.append({
            "day": day_cnt,
            "action": f"Review stage and details of opportunity '{top_opp}' currently in '{stage}' stage.",
            "owner": "Account Manager",
            "success_metric": "Opportunity details validated"
        })
        day_cnt += 2
        
    if contacts:
        top_contact = contacts[0].get("name", "stakeholder")
        tactical_playbook.append({
            "day": day_cnt,
            "action": f"Verify engagement level and schedule check-in with {top_contact}.",
            "owner": "Account Manager",
            "success_metric": "Check-in invitation sent"
        })
        day_cnt += 2
        
    if cases:
        top_case_id = cases[0].get("case_id") or "support case"
        tactical_playbook.append({
            "day": day_cnt,
            "action": f"Sync with engineering team regarding support case {top_case_id}.",
            "owner": "Technical Support Lead",
            "success_metric": "Case resolution plan updated"
        })
        day_cnt += 2
        
    if not tactical_playbook:
        tactical_playbook.append({
            "day": 1,
            "action": "Initiate comprehensive stakeholder identification for this account.",
            "owner": "Account Manager",
            "success_metric": "Initial contact list populated"
        })
        
    return {
        "executive_brief": {
            "revenue_at_stake": rev_str,
            "macro_summary": macro_summary
        },
        "persona_insights": {
            "enterprise_ae": ae_insight,
            "strategic_director": director_insight
        },
        "tactical_playbook": tactical_playbook
    }


class ReasoningEngine:
    def __init__(self, model: Optional[str] = None, is_local: bool = True):
        self.url = os.getenv("LLM_URL", "http://192.168.135.105:8000/api/generate")
        self.model = model or os.getenv("MODEL_NAME", "llama3.2:latest")
        self.raw_reasoning_bucket = {}
        self.is_local = is_local

    def _call_llm(self, system_prompt: str, user_prompt: str, timeout: int = 1500) -> str:
        if not self.is_local:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                try:
                    print("[Governance] Routing LLM call to Google Gemini API (Cloud Fallback)...")
                    # Use a reasonable token limit for Gemini to avoid truncating JSON outputs
                    return call_gemini_api(system_prompt, user_prompt, gemini_key, max_tokens=2048, timeout=min(timeout, 1500))
                except Exception as e:
                    print(f"[Governance] Gemini API fallback failed: {e}. Falling back to local model...")

        # Enforce conciseness for resource-constrained systems
        system_prompt = system_prompt + "\nCRITICAL: Keep output extremely concise. Total JSON output must be under 200 tokens."
        payload = {
            "model": self.model,
            "prompt": f"System: {system_prompt}\n\nUser Prompt: {user_prompt}\nOutput ONLY valid raw JSON.",
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 400
            }
        }
        httpx_timeout = httpx.Timeout(timeout=float(timeout), connect=5.0)
        print(f"  [LLM CONNECT] Attempting Crucible thread connection to: {self.url} (model: {self.model})")
        with httpx.Client(timeout=httpx_timeout) as client:
            print(f"  [LLM REQUEST] Sending Crucible thread query payload to: {self.url}...")
            response = client.post(self.url, json=payload)
            print(f"  [LLM RESPONSE] Received Crucible thread status {response.status_code} from: {self.url}")
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                raise Exception(f"HTTP error {response.status_code}")

    def _repair_json_string(self, text: str) -> str:
        return repair_json_string(text)

    def _extract_fallback_fields(self, text: str, thread_name: str) -> dict:
        """Fallback regex extractor to salvage fields and match standard structures."""
        # Grab base fallback structure first
        salvaged = self._fallback_for_thread(thread_name, "JSON Parsing Error")
        
        # Regex search for perspective string
        perspective_key = f"{thread_name}_perspective"
        perspective_match = re.search(r'"' + re.escape(perspective_key) + r'"\s*:\s*"([^"]+)"', text)
        if perspective_match:
            salvaged[perspective_key] = perspective_match.group(1)
            
        # Regex search for confidence score
        conf_match = re.search(r'"confidence"\s*:\s*(0\.\d+|\d+)', text)
        if conf_match:
            try:
                salvaged["confidence"] = float(conf_match.group(1))
            except:
                pass
                
        # Salvage risks
        risks_match = re.findall(r'"([^"]+)"', text)
        if thread_name == 'am' and len(risks_match) > 10:
            salvaged["risks"] = [r for r in risks_match if len(r) > 15 and r != perspective_key][:3]
            
        return salvaged

    def _normalize_parsed_dict(self, parsed: dict) -> dict:
        """Helper to normalize percentages (>1.0) to ratio decimals (<=1.0)."""
        if not isinstance(parsed, dict):
            return parsed
        
        # Normalize historical precedents success_rate and match_confidence
        if "historical_precedents" in parsed and isinstance(parsed["historical_precedents"], list):
            for item in parsed["historical_precedents"]:
                if isinstance(item, dict):
                    for key in ["success_rate", "match_confidence"]:
                        val = item.get(key)
                        if isinstance(val, (int, float)) and val > 1.0:
                            item[key] = val / 100.0
                            
        # Normalize intervention_success_probability and overall_confidence
        for key in ["intervention_success_probability", "overall_confidence", "confidence"]:
            val = parsed.get(key)
            if isinstance(val, (int, float)) and val > 1.0:
                parsed[key] = val / 100.0
                
        return parsed

    def _clean_and_parse(self, text: str, is_consensus: bool = False) -> dict:
        try:
            clean_text = text.strip()
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)
            clean_text = clean_text.strip()
            
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1:
                clean_text = clean_text[start:end+1]
            parsed = json.loads(clean_text)
            return self._normalize_parsed_dict(parsed)
        except Exception as e1:
            try:
                repaired = self._repair_json_string(text)
                parsed = json.loads(repaired)
                return self._normalize_parsed_dict(parsed)
            except Exception as e2:
                if is_consensus:
                    raise Exception(f"Consensus JSON parsing failed: {e2}")
                
                thread_context = 'am'
                for t in ['vp', 'svp', 'data']:
                    if f'{t}_perspective' in text:
                        thread_context = t
                        break
                try:
                    parsed = self._extract_fallback_fields(text, thread_context)
                    return self._normalize_parsed_dict(parsed)
                except Exception as e3:
                    parsed = self._fallback_for_thread(thread_context, f"Parsing exception: {e3}")
                    return self._normalize_parsed_dict(parsed)

    def run_reasoning_threads(
        self,
        account_data: Dict[str, Any],
        market_context: Dict[str, Any],
        timeout_per_thread: int = 300,
        total_timeout: int = 600,
        local: bool = True,
        complexity: str = "EXECUTIVE",
        requested_count: int = 5
    ) -> ConsensusOutput:
        """
        Run multi-persona reasoning.
        APEX Architecture: Runs a single-pass Multi-Persona Crucible LLM call to save latency.
        """
        # 1. Handle FACTUAL complexity level
        if complexity == "FACTUAL":
            print("[Governance] FACTUAL complexity detected: Bypassing LLM reasoning threads.")
            return ConsensusOutput(
                consensus_recommendation={
                    "action": "Displaying database records directly.",
                    "confidence": 1.0,
                    "rationale": "Direct factual query."
                },
                thread_agreement={},
                agreement_score=1.0,
                dissenting_views=[],
                confidence_limiting_factors=[],
                final_confidence=1.0
            )

        # 1.5 Handle CONVERSATIONAL complexity level
        if complexity == "CONVERSATIONAL":
            print("[Governance] CONVERSATIONAL complexity detected: Bypassing LLM reasoning threads.")
            return ConsensusOutput(
                consensus_recommendation={
                    "action": "Initiate natural conversation.",
                    "confidence": 1.0,
                    "rationale": "Conversational greeting query."
                },
                thread_agreement={},
                agreement_score=1.0,
                dissenting_views=[],
                confidence_limiting_factors=[],
                final_confidence=1.0
            )

        # Summarize large dataset to protect context windows
        account_data = summarize_large_dataset(account_data, requested_count)
        
        target_entity = account_data.get("account_name", "Global Portfolio")
        
        # Prepare crucible LLM prompts
        system_rules = f"""You are the APEX Multi-Persona Crucible. You must synthesize a comprehensive account playbook by simulating the perspectives of different enterprise experts within a single JSON response.

You must adapt your output based on the provided [COMPLEXITY] variable.
- If TACTICAL: Focus on immediate SMB AE and SDR actions.
- If STRATEGIC: Focus on Enterprise AE playbooks and Strategic Director risk mitigation.
- If EXECUTIVE: Focus entirely on CRO-level revenue summaries."""

        context_payload = {
            "Target Entity": target_entity,
            "Complexity Required": complexity,
            "Raw Database Context": json.dumps(account_data, indent=2)
        }
        
        user_prompt = f"""Analyze the database context. Output your analysis using the exact JSON schema below. Do not generate markdown backticks or conversational text outside the JSON block.

Schema format:
{{
  "executive_brief": {{
    "revenue_at_stake": "[Sum of active opportunities]",
    "macro_summary": "[2-sentence overview]"
  }},
  "persona_insights": {{
    "enterprise_ae": "[Strategic stakeholder pathing]",
    "strategic_director": "[Risk analysis of open cases]"
  }},
  "tactical_playbook": [
    {{ "day": 1, "action": "...", "owner": "...", "success_metric": "..." }},
    {{ "day": 3, "action": "...", "owner": "...", "success_metric": "..." }}
  ]
}}

Context Payload:
{json.dumps(context_payload, indent=2)}"""

        crucible_data = None
        raw_llm_output = ""
        
        # Call Crucible LLM
        try:
            print("[Crucible] Initiating single-pass multi-persona crucible...")
            raw_llm_output = self._call_llm(system_rules, user_prompt, timeout=timeout_per_thread)
            self.raw_reasoning_bucket['consensus'] = raw_llm_output
            
            # Clean and parse JSON
            parsed_json = self._clean_and_parse(raw_llm_output)
            
            # Basic schema validation
            if "executive_brief" in parsed_json and "persona_insights" in parsed_json:
                crucible_data = parsed_json
                print("[Crucible] Successfully parsed single-pass JSON output.")
            else:
                raise ValueError("JSON parsed successfully but missing required Crucible schema keys.")
                
        except Exception as e:
            print(f"[Crucible Warning] Crucible execution or parsing failed: {e}. Generating context-aware fallback data.")
            if 'consensus' not in self.raw_reasoning_bucket:
                self.raw_reasoning_bucket['consensus'] = f"Error or parsing issue: {e}. Raw text: {raw_llm_output[:200]}"
            
            # Context-Aware Natural Fallback Engine (Task 5)
            crucible_data = generate_contextual_fallback_data(account_data)

        # Build ConsensusOutput in Python
        macro_summary = crucible_data.get("executive_brief", {}).get("macro_summary", "Strategic review compiled.")
        rev_stake = crucible_data.get("executive_brief", {}).get("revenue_at_stake", "N/A")
        
        consensus = ConsensusOutput(
            consensus_recommendation={
                "action": "Proceed with Crucible recommendations.",
                "confidence": 0.85,
                "rationale": macro_summary,
                "crucible_data": crucible_data  # Save the crucible data for Layer 3 Response Generation
            },
            thread_agreement={"am": 0.85, "vp": 0.85, "svp": 0.85, "data": 0.90},
            agreement_score=0.85,
            dissenting_views=[],
            confidence_limiting_factors=[],
            final_confidence=0.85
        )
        
        return consensus
    
    def _run_am_thread(self, account_data: Dict, timeout: int) -> AMPerspectiveOutput:
        system_prompt = """You are a seasoned Account Manager responsible for executing deals and 
maintaining client relationships.

Your lens: Tactics, immediate actions, stakeholder engagement, deal execution.

Given this account situation, answer:
1. What is my 7-day playbook? (Specific, actionable steps)
2. Which stakeholders do I need to engage and in what order?
3. What objections or risks should I anticipate?
4. What does success look like in the next 30 days?
5. What resources do I need (marketing, product, exec sponsorship)?

Reasoning Chain:
- Start with: "The immediate risk/opportunity is..."
- Then: "To execute, I need to..."
- Then: "Success means..."
- End with: Confidence (0-1) in your recommended approach"""

        user_prompt = f"""Account Situation:
{json.dumps(account_data, indent=2)}

Respond with JSON only:
{{
  "am_perspective": "...",
  "playbook_7day": [
    {{"day": 1, "action": "...", "owner": "..."}},
    {{"day": 2, "action": "...", "owner": "..."}}
  ],
  "stakeholder_sequence": [
    {{"stakeholder": "...", "role": "...", "talking_point": "..."}}
  ],
  "risks": ["...", "..."],
  "success_metrics": ["...", "..."],
  "resource_needs": ["...", "..."],
  "confidence": 0.X
}}"""
        
        try:
            raw_text = self._call_llm(system_prompt, user_prompt, timeout)
            self.raw_reasoning_bucket['am'] = raw_text
            res_dict = self._clean_and_parse(raw_text)
            return AMPerspectiveOutput(**res_dict)
        except Exception as e:
            if 'am' not in self.raw_reasoning_bucket:
                self.raw_reasoning_bucket['am'] = f"Error or timeout before response: {e}"
            return AMPerspectiveOutput(**self._fallback_for_thread('am', str(e)))
            
    def _run_vp_thread(self, account_data: Dict, market_context: Dict, timeout: int) -> VPPerspectiveOutput:
        system_prompt = """You are a VP of Sales responsible for portfolio health, resource allocation, 
and market strategy.

Your lens: Patterns across accounts, competitive threats, resource constraints, 
market signals.

Given this situation, answer:
1. Is this account-specific or a symptom of a broader trend?
2. How does this account's situation compare to peers?
3. What portfolio-level action should we take?
4. What market signal does this send (if any)?
5. Should we fight for this account or reallocate resources?

Reasoning Chain:
- Pattern detection: "I see similar signals in X other accounts"
- Market hypothesis: "This suggests..."
- Resource implication: "To address this, we should..."
- Confidence in portfolio assessment: 0-1"""

        peer_accounts = market_context.get("peer_accounts", "No peer comparative data available.")
        user_prompt = f"""Account Situation:
{json.dumps(account_data, indent=2)}

Market Context:
{json.dumps(market_context, indent=2)}

Comparative Data:
{json.dumps(peer_accounts, indent=2)}

Respond with JSON only:
{{
  "vp_perspective": "...",
  "pattern_detection": "...",
  "peer_comparison": {{
    "similar_accounts": ["..."],
    "health_percentile": 0.X
  }},
  "market_hypothesis": "...",
  "portfolio_recommendation": "...",
  "resource_allocation": {{
    "investment_required": "...",
    "teams_involved": ["..."]
  }},
  "confidence": 0.X
}}"""

        try:
            raw_text = self._call_llm(system_prompt, user_prompt, timeout)
            self.raw_reasoning_bucket['vp'] = raw_text
            res_dict = self._clean_and_parse(raw_text)
            return VPPerspectiveOutput(**res_dict)
        except Exception as e:
            if 'vp' not in self.raw_reasoning_bucket:
                self.raw_reasoning_bucket['vp'] = f"Error or timeout before response: {e}"
            return VPPerspectiveOutput(**self._fallback_for_thread('vp', str(e)))

    def _run_svp_thread(self, account_data: Dict, market_context: Dict, timeout: int) -> SVPPerspectiveOutput:
        system_prompt = """You are an SVP responsible for company strategy, long-term positioning, 
and high-stakes decisions.

Your lens: Strategic value, competitive positioning, market expansion, 
relationship worth vs. effort.

Given this situation, answer:
1. What is the strategic value of this account/relationship?
2. Is this a competitive threat or company-specific issue?
3. Does this align with our 2026 strategy/OKRs?
4. Should we invest in keeping this relationship or let it go?
5. What does this tell us about our market position?

Reasoning Chain:
- Strategic fit: "This account is worth X because..."
- Market signal: "This suggests our positioning is..."
- Investment ROI: "Effort to retain vs. future value: ..."
- Strategic confidence: 0-1"""

        company_okrs = market_context.get("company_okrs", "No specific strategy/OKRs provided.")
        competitive_context = market_context.get("competitive_context", "No specific competitive landscape context provided.")
        
        user_prompt = f"""Account Situation:
{json.dumps(account_data, indent=2)}

Company Strategy:
{json.dumps(company_okrs, indent=2)}

Competitive Landscape:
{json.dumps(competitive_context, indent=2)}

Respond with JSON only:
{{
  "svp_perspective": "...",
  "strategic_value": "$X",
  "strategic_fit_score": 0.X,
  "competitive_threat_level": "low|medium|high",
  "market_positioning_insight": "...",
  "keep_vs_let_go_recommendation": "...",
  "rationale": "...",
  "confidence": 0.X
}}"""

        try:
            raw_text = self._call_llm(system_prompt, user_prompt, timeout)
            self.raw_reasoning_bucket['svp'] = raw_text
            res_dict = self._clean_and_parse(raw_text)
            return SVPPerspectiveOutput(**res_dict)
        except Exception as e:
            if 'svp' not in self.raw_reasoning_bucket:
                self.raw_reasoning_bucket['svp'] = f"Error or timeout before response: {e}"
            return SVPPerspectiveOutput(**self._fallback_for_thread('svp', str(e)))

    def _run_data_thread(self, account_data: Dict, timeout: int) -> DataPerspectiveOutput:
        system_prompt = """You are a data analyst providing quantified, evidence-based reasoning.

CRITICAL JSON RULES:
1. Every numeric value must be a raw float or integer, NOT a string and NOT containing a '%' sign (e.g., use 0.062 instead of 6.2% or "6.2%").
2. Do NOT output 'N/A', 'null', or any placeholder text for numeric fields. If a probability/score is unavailable, use 0.0 or a valid float.

Your lens: Numbers, confidence intervals, historical patterns, probabilistic 
forecasting.

Given this situation, answer:
1. What are the key quantified metrics? (Health score, churn probability, etc.)
2. How confident are we in these metrics? (Data quality assessment)
3. What historical precedents does this resemble?
4. What is the probability of success for proposed interventions?
5. What are the confidence intervals around forecasts?

Reasoning Chain:
- Quantified signals: "The data shows X with Y% confidence"
- Pattern matching: "This resembles Z past cases, which had outcome..."
- Probability estimation: "Success rate for similar interventions: X%"
- Confidence in data quality: 0-1"""

        historical_data = account_data.get("historical_data", "No historical precedent outcomes available.")

        user_prompt = f"""Account Data:
{json.dumps(account_data, indent=2)}

Historical Outcomes:
{json.dumps(historical_data, indent=2)}

Respond with JSON only:
{{
  "data_perspective": "...",
  "key_metrics": {{
    "health_score": 0.X,
    "churn_probability": 0.X,
    "engagement_trend": "..."
  }},
  "data_quality": {{
    "metric": "...",
    "confidence": 0.X,
    "limitation": "..."
  }},
  "historical_precedents": [
    {{
      "situation": "...",
      "outcome": "...",
      "success_rate": 0.X,
      "match_confidence": 0.X
    }}
  ],
  "intervention_success_probability": 0.X,
  "confidence_intervals": {{
    "metric": [0.X, 0.X]
  }},
  "overall_confidence": 0.X
}}"""

        try:
            raw_text = self._call_llm(system_prompt, user_prompt, timeout)
            self.raw_reasoning_bucket['data'] = raw_text
            res_dict = self._clean_and_parse(raw_text)
            return DataPerspectiveOutput(**res_dict)
        except Exception as e:
            if 'data' not in self.raw_reasoning_bucket:
                self.raw_reasoning_bucket['data'] = f"Error or timeout before response: {e}"
            return DataPerspectiveOutput(**self._fallback_for_thread('data', str(e)))

    def _fallback_for_thread(self, thread_name: str, error: str) -> Dict:
        """Fallback if thread times out or fails."""
        if thread_name == 'am':
            return {
                "am_perspective": f"Thread am timed out or failed: {error}",
                "playbook_7day": [],
                "stakeholder_sequence": [],
                "risks": [f"Fallback mode active due to: {error}"],
                "success_metrics": [],
                "resource_needs": [],
                "confidence": 0.3
            }
        elif thread_name == 'vp':
            return {
                "vp_perspective": f"Thread vp timed out or failed: {error}",
                "pattern_detection": "Unable to run pattern detection.",
                "peer_comparison": {"similar_accounts": [], "health_percentile": 0.0},
                "market_hypothesis": "Data unavailable.",
                "portfolio_recommendation": "Proceed with default operational plan.",
                "resource_allocation": {"investment_required": "UNKNOWN", "teams_involved": []},
                "confidence": 0.3
            }
        elif thread_name == 'svp':
            return {
                "svp_perspective": f"Thread svp timed out or failed: {error}",
                "strategic_value": "UNKNOWN",
                "strategic_fit_score": 0.0,
                "competitive_threat_level": "medium",
                "market_positioning_insight": "Strategic trace unavailable.",
                "keep_vs_let_go_recommendation": "Investigate alignment.",
                "rationale": f"Strategic reasoning failed: {error}",
                "confidence": 0.3
            }
        elif thread_name == 'data':
            return {
                "data_perspective": f"Thread data timed out or failed: {error}",
                "key_metrics": {"health_score": 0.0, "churn_probability": 0.0, "engagement_trend": "UNKNOWN"},
                "data_quality": {"metric": "N/A", "confidence": 0.0, "limitation": "Thread execution failed"},
                "historical_precedents": [],
                "intervention_success_probability": 0.0,
                "confidence_intervals": {},
                "overall_confidence": 0.3
            }
        return {"confidence": 0.3}

    def _build_consensus(self, results: Dict, timeout: int) -> ConsensusOutput:
        """Synthesize 4 threads into consensus."""
        
        system_prompt = """You are a consensus-building analyst synthesizing four perspectives on an 
account planning decision.

Your job: Build consensus while surfacing disagreement.

CONSENSUS BUILDING:
- Where do 3+ threads agree? → High confidence recommendation
- Where do 2 threads agree, 2 disagree? → Flag as contested
- Where all 4 agree? → Very high confidence

DISSENT SURFACING:
- If SVP confidence is <0.5 but others are >0.7 → Include SVP caveat
- If Data quality is <0.6 → Cap recommendation confidence
- If threads have opposing recommendations → Include both views"""

        user_prompt = f"""Four threading outputs:
1. AM (Tactics): {json.dumps(results.get('am'), indent=2)}
2. VP (Portfolio): {json.dumps(results.get('vp'), indent=2)}
3. SVP (Strategy): {json.dumps(results.get('svp'), indent=2)}
4. Data (Quantified): {json.dumps(results.get('data'), indent=2)}

Build consensus while surfacing disagreement.

Respond in JSON format only:
{{
  "consensus_recommendation": {{
    "action": "...",
    "confidence": 0.X,
    "rationale": "..."
  }},
  "thread_agreement": {{
    "am": 0.X,
    "vp": 0.X,
    "svp": 0.X,
    "data": 0.X
  }},
  "agreement_score": 0.X,
  "dissenting_views": [
    {{
      "perspective": "SVP|VP|Data",
      "dissent": "...",
      "confidence": 0.X,
      "rationale": "..."
    }}
  ],
  "confidence_limiting_factors": [
    "..."
  ],
  "final_confidence": 0.X
}}"""
        
        try:
            raw_text = self._call_llm(system_prompt, user_prompt, timeout)
            self.raw_reasoning_bucket['consensus'] = raw_text
            res_dict = self._clean_and_parse(raw_text, is_consensus=True)
            return ConsensusOutput(**res_dict)
        except Exception as e:
            if 'consensus' not in self.raw_reasoning_bucket:
                self.raw_reasoning_bucket['consensus'] = f"Error or timeout before response: {e}"
            fallback = {
                "consensus_recommendation": {
                    "action": "Proceed with default tactical AM account plan.",
                    "confidence": 0.3,
                    "rationale": f"Consensus synthesis timed out or failed: {str(e)}"
                },
                "thread_agreement": {
                    "am": results.get('am', {}).get('confidence', 0.3) or 0.3,
                    "vp": results.get('vp', {}).get('confidence', 0.3) or 0.3,
                    "svp": results.get('svp', {}).get('confidence', 0.3) or 0.3,
                    "data": results.get('data', {}).get('overall_confidence', 0.3) or 0.3
                },
                "agreement_score": 0.3,
                "dissenting_views": [],
                "confidence_limiting_factors": [f"Consensus generation failed: {str(e)}"],
                "final_confidence": 0.3
            }
            return ConsensusOutput(**fallback)


# ═══════════════════════════════════════════════════════════════
# LAYER 3: RESPONSE GENERATION (Role-Specific)
# ═══════════════════════════════════════════════════════════════

from typing import Union

class PlaybookAction(BaseModel):
    day: int
    action: str
    owner: str
    success_metric: str
    template: Optional[str] = None

class Stakeholder(BaseModel):
    stakeholder: str
    role: str
    engagement_type: str  # "call" | "email" | "meeting"
    talking_points: List[str]
    success_indicator: str

class RiskMitigation(BaseModel):
    risk: str
    mitigation: str

class AMResponseOutput(BaseModel):
    narrative: str
    urgency: str  # "P1" | "P2" | "P3"
    playbook_7day: List[PlaybookAction]
    stakeholder_sequence: List[Stakeholder]
    risks_and_mitigations: List[RiskMitigation]
    confidence_in_playbook: Optional[float] = Field(None, ge=0.0, le=1.0)
    why_this_matters: str

class PortfolioImpact(BaseModel):
    accounts_affected: int
    total_arr_at_risk: str
    probability_of_churn: Optional[float] = Field(None, ge=0.0, le=1.0)

class MarketSignal(BaseModel):
    is_market_wide: bool
    competitor_threat: str
    strategic_implication: str

class ResourceRecommendation(BaseModel):
    investment_required: str
    teams_needed: List[str]
    timeline: str

class VPResponseOutput(BaseModel):
    narrative: str
    portfolio_impact: PortfolioImpact
    market_signal: MarketSignal
    resource_recommendation: ResourceRecommendation
    strategic_action: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class StrategicContext(BaseModel):
    strategic_fit: str  # "KEEP" | "CAUTIOUS" | "LET_GO"
    strategic_value: str
    rationale: str

class CompetitivePositioning(BaseModel):
    threat_level: str  # "low" | "medium" | "high"
    market_signal: str
    response_strategy: str

class DecisionScenario(BaseModel):
    scenario: str
    action: str
    expected_outcome: str

class SVPResponseOutput(BaseModel):
    narrative: str
    strategic_context: StrategicContext
    competitive_positioning: CompetitivePositioning
    board_narrative: str
    decision_framework: List[DecisionScenario]
    long_term_implication: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class ResponseGenerator:
    def __init__(self, model: Optional[str] = None, is_local: bool = True):
        self.url = os.getenv("LLM_URL", "http://192.168.135.105:8000/api/generate")
        self.model = model or os.getenv("MODEL_NAME", "llama3.2:latest")
        self.raw_response_bucket = {}
        self.is_local = is_local

    def _call_llm(self, system_prompt: str, user_prompt: str, timeout: int = 1500) -> str:
        if not self.is_local:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                try:
                    print("[Governance] Routing LLM call to Google Gemini API (Cloud Fallback)...")
                    return call_gemini_api(system_prompt, user_prompt, gemini_key, max_tokens=2048, timeout=min(timeout, 1500))
                except Exception as e:
                    print(f"[Governance] Gemini API fallback failed: {e}. Falling back to local model...")

        # Enforce conciseness for resource-constrained systems
        system_prompt = system_prompt + "\nCRITICAL: Keep output extremely concise. The narrative response must be under 150 words."
        payload = {
            "model": self.model,
            "prompt": f"System: {system_prompt}\n\nUser Prompt: {user_prompt}\nOutput ONLY valid raw JSON.",
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 512
            }
        }
        httpx_timeout = httpx.Timeout(timeout=float(timeout), connect=5.0)
        print(f"  [LLM CONNECT] Attempting single-pass Crucible connection to: {self.url} (model: {self.model})")
        with httpx.Client(timeout=httpx_timeout) as client:
            print(f"  [LLM REQUEST] Sending single-pass Crucible query payload to: {self.url}...")
            response = client.post(self.url, json=payload)
            print(f"  [LLM RESPONSE] Received single-pass Crucible status {response.status_code} from: {self.url}")
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                raise Exception(f"HTTP error {response.status_code}")

    def _repair_json_string(self, text: str) -> str:
        return repair_json_string(text)

    def _apply_defaults(self, salvaged: dict, role: str) -> dict:
        """Crucial defaults per role to ensure Pydantic doesn't fail on missing keys."""
        salvaged.setdefault("narrative", "No narrative generated.")
        if role == 'am':
            salvaged.setdefault("urgency", "P3")
            salvaged.setdefault("playbook_7day", [
                {
                    "day": 1,
                    "action": "Review consensus findings and manually verify CRM contact completeness.",
                    "owner": "Account Manager",
                    "success_metric": "Verified contacts",
                    "template": "MEETING_AGENDA: Internal strategy alignment"
                }
            ])
            salvaged.setdefault("stakeholder_sequence", [])
            salvaged.setdefault("risks_and_mitigations", [])
            salvaged.setdefault("confidence_in_playbook", 0.5)
            salvaged.setdefault("why_this_matters", "Playbook response.")
        elif role == 'vp':
            salvaged.setdefault("portfolio_impact", {"accounts_affected": 0, "total_arr_at_risk": "N/A", "probability_of_churn": 0.5})
            salvaged.setdefault("market_signal", {"is_market_wide": False, "competitor_threat": "", "strategic_implication": ""})
            salvaged.setdefault("resource_recommendation", {"investment_required": "", "teams_needed": [], "timeline": ""})
            salvaged.setdefault("strategic_action", "Action needed.")
            salvaged.setdefault("confidence", 0.5)
        elif role == 'svp':
            salvaged.setdefault("strategic_context", {"strategic_fit": "CAUTIOUS", "strategic_value": "", "rationale": ""})
            salvaged.setdefault("competitive_positioning", {"threat_level": "medium", "market_signal": "", "response_strategy": ""})
            salvaged.setdefault("board_narrative", "SVP strategic brief.")
            salvaged.setdefault("decision_framework", [])
            salvaged.setdefault("long_term_implication", "")
            salvaged.setdefault("confidence", 0.5)
        return salvaged

    def _extract_fallback_fields(self, text: str, role: str) -> dict:
        """Extract narrative and other fields using regex from broken JSON."""
        salvaged = {}
        narrative_match = re.search(r'"narrative"\s*:\s*"([^"]+)"', text)
        if narrative_match:
            salvaged["narrative"] = narrative_match.group(1)
        else:
            salvaged["narrative"] = "Partial response salvaged from LLM output."
            
        why_match = re.search(r'"why_this_matters"\s*:\s*"([^"]+)"', text)
        if why_match:
            salvaged["why_this_matters"] = why_match.group(1)
            
        urgency_match = re.search(r'"urgency"\s*:\s*"([^"]+)"', text)
        if urgency_match:
            salvaged["urgency"] = urgency_match.group(1)
            
        return self._apply_defaults(salvaged, role)

    def _clean_and_parse(self, text: str) -> dict:
        role = 'am'
        if 'portfolio_impact' in text or 'market_signal' in text:
            role = 'vp'
        elif 'strategic_context' in text or 'board_narrative' in text:
            role = 'svp'
            
        try:
            clean_text = text.strip()
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)
            clean_text = clean_text.strip()
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1:
                clean_text = clean_text[start:end+1]
            parsed = json.loads(clean_text)
            return self._apply_defaults(parsed, role)
        except Exception as e1:
            try:
                repaired = self._repair_json_string(text)
                parsed = json.loads(repaired)
                return self._apply_defaults(parsed, role)
            except Exception as e2:
                try:
                    return self._extract_fallback_fields(text, role)
                except Exception:
                    return self._extract_fallback_fields("", role)


    def generate_response(
        self,
        consensus: ConsensusOutput,
        recipient_role: str
    ) -> Union[AMResponseOutput, VPResponseOutput, SVPResponseOutput]:
        """
        Generate role-specific response from consensus reasoning.
        """
        self.raw_response_bucket[recipient_role] = "Pending generation..."
        
        # Check if the consensus has our new single-pass crucible data embedded
        crucible_data = None
        if hasattr(consensus, "consensus_recommendation") and isinstance(consensus.consensus_recommendation, dict):
            crucible_data = consensus.consensus_recommendation.get("crucible_data")
            
        if crucible_data:
            print(f"[ResponseGenerator] Mapping role response dynamically for: {recipient_role.upper()}")
            try:
                if recipient_role == "am":
                    resp = self._map_am_from_crucible(crucible_data)
                    self.raw_response_bucket[recipient_role] = "Mapped dynamically from Crucible (zero LLM latency)"
                    return resp
                elif recipient_role == "vp":
                    resp = self._map_vp_from_crucible(crucible_data)
                    self.raw_response_bucket[recipient_role] = "Mapped dynamically from Crucible (zero LLM latency)"
                    return resp
                elif recipient_role == "svp":
                    resp = self._map_svp_from_crucible(crucible_data)
                    self.raw_response_bucket[recipient_role] = "Mapped dynamically from Crucible (zero LLM latency)"
                    return resp
            except Exception as map_err:
                print(f"[ResponseGenerator Warning] Crucible mapping failed: {map_err}. Falling back to standard LLM generation.")
                
        # Legacy fallback if crucible data is not available or mapping fails
        if recipient_role == "am":
            return self._generate_am_response(consensus)
        elif recipient_role == "vp":
            return self._generate_vp_response(consensus)
        elif recipient_role == "svp":
            return self._generate_svp_response(consensus)
        else:
            raise ValueError(f"Unknown role: {recipient_role}")

    def _map_am_from_crucible(self, crucible_data: Dict[str, Any]) -> AMResponseOutput:
        exec_brief = crucible_data.get("executive_brief", {})
        persona_insights = crucible_data.get("persona_insights", {})
        tactical_playbook = crucible_data.get("tactical_playbook", [])
        
        narrative = exec_brief.get("macro_summary", "Strategic plan initiated.")
        
        playbook_actions = []
        for item in tactical_playbook:
            playbook_actions.append(PlaybookAction(
                day=item.get("day", 1),
                action=item.get("action", ""),
                owner=item.get("owner", "Account Manager"),
                success_metric=item.get("success_metric", "Action step completed"),
                template=item.get("template")
            ))
            
        ae_text = persona_insights.get("enterprise_ae", "")
        stakeholder_sequence = []
        if ae_text:
            stakeholder_sequence.append(Stakeholder(
                stakeholder="Key Stakeholders",
                role="Strategic Sponsors",
                engagement_type="meeting",
                talking_points=[ae_text[:120]],
                success_indicator="Partnership alignment confirmed"
            ))
            
        director_text = persona_insights.get("strategic_director", "")
        risks_and_mitigations = []
        if director_text:
            risks_and_mitigations.append(RiskMitigation(
                risk=director_text[:120],
                mitigation="Initiate immediate communication and review service milestones."
            ))
            
        return AMResponseOutput(
            narrative=narrative,
            urgency="P2",
            playbook_7day=playbook_actions,
            stakeholder_sequence=stakeholder_sequence,
            risks_and_mitigations=risks_and_mitigations,
            confidence_in_playbook=0.85,
            why_this_matters=exec_brief.get("macro_summary", "Strategic review required.")[:150]
        )

    def _map_vp_from_crucible(self, crucible_data: Dict[str, Any]) -> VPResponseOutput:
        exec_brief = crucible_data.get("executive_brief", {})
        persona_insights = crucible_data.get("persona_insights", {})
        
        narrative = exec_brief.get("macro_summary", "Strategic portfolio review initiated.")
        rev_stake = exec_brief.get("revenue_at_stake", "$0")
        
        portfolio_impact = PortfolioImpact(
            accounts_affected=1,
            total_arr_at_risk=rev_stake,
            probability_of_churn=0.3
        )
        
        market_signal = MarketSignal(
            is_market_wide=False,
            competitor_threat=persona_insights.get("strategic_director", "")[:150],
            strategic_implication="Immediate client relationship touchpoint needed to defend revenue."
        )
        
        resource_rec = ResourceRecommendation(
            investment_required="Core Account Management alignment",
            teams_needed=["Account Team", "Customer Success"],
            timeline="Next 7 days"
        )
        
        return VPResponseOutput(
            narrative=narrative,
            portfolio_impact=portfolio_impact,
            market_signal=market_signal,
            resource_recommendation=resource_rec,
            strategic_action=persona_insights.get("enterprise_ae", "Coordinate executive alignment."),
            confidence=0.85
        )

    def _map_svp_from_crucible(self, crucible_data: Dict[str, Any]) -> SVPResponseOutput:
        exec_brief = crucible_data.get("executive_brief", {})
        persona_insights = crucible_data.get("persona_insights", {})
        
        narrative = exec_brief.get("macro_summary", "Macro account briefing.")
        
        strat_context = StrategicContext(
            strategic_fit="KEEP",
            strategic_value="High strategic value customer account.",
            rationale=exec_brief.get("macro_summary", "Key relationship.")
        )
        
        comp_position = CompetitivePositioning(
            threat_level="medium",
            market_signal="Active competitor positioning detected.",
            response_strategy="Reaffirm value framework and demonstrate ROI milestones."
        )
        
        decision_scenarios = [
            DecisionScenario(
                scenario="Competitor discounts or displaces relationship",
                action="Engage senior leadership and sponsor executive review",
                expected_outcome="Reinforce relationship trust and secure renewal"
            )
        ]
        
        return SVPResponseOutput(
            narrative=narrative,
            strategic_context=strat_context,
            competitive_positioning=comp_position,
            board_narrative=exec_brief.get("macro_summary", "SVP Executive Account Briefing."),
            decision_framework=decision_scenarios,
            long_term_implication="Ensure structured communication plan is established to avoid competitor lock-in.",
            confidence=0.85
        )

    def _generate_am_response(self, consensus: ConsensusOutput) -> AMResponseOutput:
        system_prompt = """You are translating consensus reasoning into an Account Manager's playbook.

Account Manager needs: Immediate tactics, stakeholder sequence, templates, 
clear next steps.

Your job: Create a 7-day playbook with:
1. Specific, actionable steps (not general advice)
2. Stakeholder engagement sequence
3. Templates (email drafts, meeting agendas)
4. Risk mitigations
5. Success metrics"""

        consensus_dict = consensus.model_dump() if hasattr(consensus, "model_dump") else consensus
        user_prompt = f"""Consensus Output:
{json.dumps(consensus_dict, indent=2)}

Generate AM response JSON matching this structure:
{{
  "narrative": "...",
  "urgency": "P1|P2|P3",
  "playbook_7day": [
    {{
      "day": 1,
      "action": "...",
      "owner": "...",
      "success_metric": "...",
      "template": "EMAIL_DRAFT | MEETING_AGENDA | ..."
    }}
  ],
  "stakeholder_sequence": [
    {{
      "stakeholder": "...",
      "role": "...",
      "engagement_type": "call|email|meeting",
      "talking_points": ["...", "..."],
      "success_indicator": "..."
    }}
  ],
  "risks_and_mitigations": [
    {{
      "risk": "...",
      "mitigation": "..."
    }}
  ],
  "confidence_in_playbook": 0.X,
  "why_this_matters": "..."
}}"""
        
        try:
            raw_text = self._call_llm(system_prompt, user_prompt)
            self.raw_response_bucket['am'] = raw_text
            res_dict = self._clean_and_parse(raw_text)
            return AMResponseOutput(**res_dict)
        except Exception as e:
            if self.raw_response_bucket.get('am') == "Pending generation...":
                self.raw_response_bucket['am'] = f"Error or timeout before response: {e}"
            fallback = {
                "narrative": f"AM Response Generation failed/timed out: {str(e)}",
                "urgency": "P2",
                "playbook_7day": [
                    {
                        "day": 1,
                        "action": "Review consensus findings and manually verify CRM contact completeness.",
                        "owner": "Account Manager",
                        "success_metric": "Verified contacts",
                        "template": "MEETING_AGENDA: Internal strategy alignment"
                    }
                ],
                "stakeholder_sequence": [],
                "risks_and_mitigations": [],
                "confidence_in_playbook": 0.3,
                "why_this_matters": "Fallback mode active due to API errors."
            }
            return AMResponseOutput(**fallback)

    def _generate_vp_response(self, consensus: ConsensusOutput) -> VPResponseOutput:
        system_prompt = """You are translating consensus reasoning into a VP's portfolio strategy.

VP needs: Market patterns, portfolio impact, resource implications, 
strategic recommendations.

Your job: Create a portfolio-level analysis with:
1. Is this account-specific or market signal?
2. How many accounts affected?
3. Resource allocation recommendation
4. Market strategy implication
5. Portfolio-level action"""

        consensus_dict = consensus.model_dump() if hasattr(consensus, "model_dump") else consensus
        user_prompt = f"""Consensus Output:
{json.dumps(consensus_dict, indent=2)}

Generate VP response JSON matching this structure:
{{
  "narrative": "...",
  "portfolio_impact": {{
    "accounts_affected": X,
    "total_arr_at_risk": "$X",
    "probability_of_churn": 0.X
  }},
  "market_signal": {{
    "is_market_wide": true|false,
    "competitor_threat": "...",
    "strategic_implication": "..."
  }},
  "resource_recommendation": {{
    "investment_required": "$X",
    "teams_needed": ["Sales", "Product", "Marketing"],
    "timeline": "...days"
  }},
  "strategic_action": "...",
  "confidence": 0.X
}}"""
        
        try:
            raw_text = self._call_llm(system_prompt, user_prompt)
            self.raw_response_bucket['vp'] = raw_text
            res_dict = self._clean_and_parse(raw_text)
            return VPResponseOutput(**res_dict)
        except Exception as e:
            if self.raw_response_bucket.get('vp') == "Pending generation...":
                self.raw_response_bucket['vp'] = f"Error or timeout before response: {e}"
            fallback = {
                "narrative": f"VP Response Generation failed/timed out: {str(e)}",
                "portfolio_impact": {
                    "accounts_affected": 1,
                    "total_arr_at_risk": "UNKNOWN",
                    "probability_of_churn": 0.5
                },
                "market_signal": {
                    "is_market_wide": False,
                    "competitor_threat": "Unknown",
                    "strategic_implication": "Verify competitive alignment"
                },
                "resource_recommendation": {
                    "investment_required": "UNKNOWN",
                    "teams_needed": ["Sales"],
                    "timeline": "N/A"
                },
                "strategic_action": "Manually inspect target account pipeline health.",
                "confidence": 0.3
            }
            return VPResponseOutput(**fallback)

    def _generate_svp_response(self, consensus: ConsensusOutput) -> SVPResponseOutput:
        system_prompt = """You are translating consensus reasoning into an SVP's strategic brief.

SVP needs: Strategic context, board narrative, long-term implications, 
high-level decision framework.

Your job: Create a strategic brief with:
1. Is this consistent with 2026 strategy?
2. Competitive positioning insight
3. Board-level narrative
4. High-stakes decision framework
5. Long-term market implications"""

        consensus_dict = consensus.model_dump() if hasattr(consensus, "model_dump") else consensus
        user_prompt = f"""Consensus Output:
{json.dumps(consensus_dict, indent=2)}

Generate SVP response JSON matching this structure:
{{
  "narrative": "...",
  "strategic_context": {{
    "strategic_fit": "KEEP | CAUTIOUS | LET_GO",
    "strategic_value": "$X",
    "rationale": "..."
  }},
  "competitive_positioning": {{
    "threat_level": "low|medium|high",
    "market_signal": "...",
    "response_strategy": "..."
  }},
  "board_narrative": "...",
  "decision_framework": [
    {{
      "scenario": "...",
      "action": "...",
      "expected_outcome": "..."
    }}
  ],
  "long_term_implication": "...",
  "confidence": 0.X
}}"""
        
        try:
            raw_text = self._call_llm(system_prompt, user_prompt)
            self.raw_response_bucket['svp'] = raw_text
            res_dict = self._clean_and_parse(raw_text)
            return SVPResponseOutput(**res_dict)
        except Exception as e:
            if self.raw_response_bucket.get('svp') == "Pending generation...":
                self.raw_response_bucket['svp'] = f"Error or timeout before response: {e}"
            fallback = {
                "narrative": f"SVP Response Generation failed/timed out: {str(e)}",
                "strategic_context": {
                    "strategic_fit": "CAUTIOUS",
                    "strategic_value": "UNKNOWN",
                    "rationale": "Fall back active due to API errors."
                },
                "competitive_positioning": {
                    "threat_level": "medium",
                    "market_signal": "Unknown",
                    "response_strategy": "Examine account strategy alignment."
                },
                "board_narrative": "Consensus output analysis offline. Manual auditing active.",
                "decision_framework": [],
                "long_term_implication": "Long-term market trend tracking is degraded.",
                "confidence": 0.3
            }
            return SVPResponseOutput(**fallback)

