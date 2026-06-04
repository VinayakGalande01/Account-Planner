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
