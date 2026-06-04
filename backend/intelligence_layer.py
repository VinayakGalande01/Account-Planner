"""
APEX Intelligence Layer — Phase 4: Hybrid Intelligence Architecture

Pure-Python analytics module. Zero LLM dependency. Zero network requests.
Fully deterministic. Consumes only pre-computed data from DataEngine.

Architecture Principle:
    Deterministic Engine → Intelligence Layer → Curated Synthesis → (optional) LLM narrative
    LLM NEVER receives raw CRM dumps. Only curated aggregate intelligence.

Modules:
    - SignalClassifier: Typed signal priority hierarchy
    - PortfolioIntelligence: Cross-entity concentration/exposure/momentum analysis
    - TemporalIntelligence: Trajectory awareness (stale, decay, urgency)
    - HumanizedPriority: CRITICAL/HIGH/MEDIUM/LOW bands + compact formatting
    - generate_strategic_synthesis(): Master orchestrator
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


# ═══════════════════════════════════════════════════════════════
# RESPONSE BUDGET — Hard limits per intent (backend owns truncation)
# ═══════════════════════════════════════════════════════════════

RESPONSE_BUDGET = {
    "GLOBAL_LIST_QUERY":            {"max_rows": 10, "max_signals": 4, "max_actions": 3},
    "ACCOUNT_PLAN_QUERY":           {"max_rows": 5,  "max_signals": 5, "max_actions": 5},
    "RISK_ANALYSIS_QUERY":          {"max_rows": 5,  "max_signals": 5, "max_actions": 3},
    "CONTACT_QUERY":                {"max_rows": 15, "max_signals": 3, "max_actions": 3},
    "PIPELINE_SUMMARY_QUERY":       {"max_rows": 10, "max_signals": 4, "max_actions": 3},
    "ACTION_RECOMMENDATION_QUERY":  {"max_rows": 0,  "max_signals": 4, "max_actions": 5},
}


# ═══════════════════════════════════════════════════════════════
# SIGNAL CLASSIFICATION SYSTEM
# ═══════════════════════════════════════════════════════════════

class SignalType(str, Enum):
    REVENUE     = "REVENUE"
    PIPELINE    = "PIPELINE"
    STRATEGIC   = "STRATEGIC"
    RISK        = "RISK"
    ENGAGEMENT  = "ENGAGEMENT"
    TEMPORAL    = "TEMPORAL"
    CRM         = "CRM"


# Business-priority ordering. Revenue first, CRM last.
SIGNAL_PRIORITY = {
    SignalType.REVENUE:    1,
    SignalType.PIPELINE:   2,
    SignalType.STRATEGIC:  3,
    SignalType.RISK:       4,
    SignalType.ENGAGEMENT: 5,
    SignalType.TEMPORAL:   6,
    SignalType.CRM:        7,
}


@dataclass
class ClassifiedSignal:
    """A signal with business-type classification and priority rank."""
    text: str
    signal_type: SignalType
    priority_rank: int = 99

    def to_display(self) -> str:
        """Format for transport. Frontend can optionally parse the [TYPE] prefix for color coding."""
        return f"[{self.signal_type.value}] {self.text}"


class SignalClassifier:
    """Classifies raw signal strings into typed, priority-ranked signals.
    CRM hygiene signals are always deprioritized unless the query is explicitly CRM-focused."""

    # Keyword → SignalType mapping for auto-classification
    _CLASSIFICATION_RULES = [
        (SignalType.REVENUE,    ["revenue", "forecast", "weighted", "close within", "closing soon", "$", "quarter"]),
        (SignalType.PIPELINE,   ["pipeline", "stage", "concentration", "deal count", "conversion"]),
        (SignalType.RISK,       ["risk", "stalled", "overdue", "jeopardy", "critical case", "declining", "past close"]),
        (SignalType.TEMPORAL,   ["days ago", "days since", "aging", "stale", "momentum", "decay", "urgency", "window"]),
        (SignalType.ENGAGEMENT, ["engagement", "activity", "contact", "touch", "outreach", "dormant"]),
        (SignalType.STRATEGIC,  ["strategic", "tier", "key account", "upsell", "growth", "expansion"]),
        (SignalType.CRM,        ["hygiene", "missing", "data completeness", "unmapped", "single-threaded", "competitor"]),
    ]

    @staticmethod
    def classify(text: str) -> SignalType:
        """Auto-classify a signal string by keyword matching."""
        text_lower = text.lower()
        for signal_type, keywords in SignalClassifier._CLASSIFICATION_RULES:
            if any(kw in text_lower for kw in keywords):
                return signal_type
        return SignalType.CRM  # Default fallback

    @staticmethod
    def classify_and_rank(signals: List[str], max_signals: int = 5) -> List[ClassifiedSignal]:
        """Classify, rank by business priority, and truncate to budget."""
        classified = []
        for text in signals:
            signal_type = SignalClassifier.classify(text)
            rank = SIGNAL_PRIORITY.get(signal_type, 99)
            classified.append(ClassifiedSignal(text=text, signal_type=signal_type, priority_rank=rank))

        # Sort by priority (Revenue first, CRM last)
        classified.sort(key=lambda s: s.priority_rank)

        # Truncate to budget
        return classified[:max_signals]


# ═══════════════════════════════════════════════════════════════
# HUMANIZED PRIORITY SYSTEM
# ═══════════════════════════════════════════════════════════════

class HumanizedPriority:
    """Converts raw numerical priority scores into human-readable bands and formats."""

    @staticmethod
    def score_to_band(score: float, all_scores: List[float]) -> str:
        """Convert a raw score to CRITICAL/HIGH/MEDIUM/LOW using percentile bands."""
        if not all_scores:
            return "MEDIUM"
        sorted_scores = sorted(all_scores, reverse=True)
        n = len(sorted_scores)
        if n == 0:
            return "MEDIUM"

        # Percentile-based bands
        p90 = sorted_scores[max(0, int(n * 0.10) - 1)] if n > 1 else sorted_scores[0]
        p75 = sorted_scores[max(0, int(n * 0.25) - 1)] if n > 1 else sorted_scores[0]
        p50 = sorted_scores[max(0, int(n * 0.50) - 1)] if n > 1 else sorted_scores[0]

        if score >= p90:
            return "CRITICAL"
        elif score >= p75:
            return "HIGH"
        elif score >= p50:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def format_currency(amount: float) -> str:
        """Compact currency formatting: $1.2M, $450K, $5K."""
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.0f}K"
        else:
            return f"${amount:,.0f}"

    @staticmethod
    def format_date_relative(date_val) -> str:
        """Humanized date: 'in 5 days', '12 days overdue', 'today'."""
        if pd.isna(date_val):
            return "No date set"
        try:
            dt = pd.to_datetime(date_val)
            if dt.tzinfo is not None:
                dt = dt.tz_localize(None)
            delta = (dt - datetime.now()).days
            if delta == 0:
                return "today"
            elif delta > 0:
                return f"in {delta} days"
            else:
                return f"{abs(delta)} days overdue"
        except Exception:
            return str(date_val)[:10]


# ═══════════════════════════════════════════════════════════════
# PORTFOLIO INTELLIGENCE
# ═══════════════════════════════════════════════════════════════

class PortfolioIntelligence:
    """Cross-entity portfolio analysis. All computations are deterministic.
    Generates strategic insights about concentration, exposure, and momentum."""

    @staticmethod
    def analyze_stage_concentration(engine) -> List[str]:
        """Detect pipeline concentration risk by stage."""
        insights = []
        opps = engine.data.get('opportunity')
        if opps is None or opps.empty:
            return insights

        open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
        if open_opps.empty:
            return insights

        total_pipeline = open_opps['Amount_USD'].sum()
        if total_pipeline == 0:
            return insights

        stage_agg = open_opps.groupby('Stage').agg(
            total=('Amount_USD', 'sum'),
            count=('Opp_ID', 'count')
        )

        for stage, row in stage_agg.iterrows():
            pct = (row['total'] / total_pipeline) * 100
            if pct >= 40:
                insights.append(
                    f"{stage} deals represent {pct:.0f}% of total pipeline value "
                    f"({HumanizedPriority.format_currency(row['total'])}), increasing concentration risk."
                )
            elif pct >= 25 and "Negotiation" in str(stage):
                insights.append(
                    f"Negotiation-stage opportunities account for {pct:.0f}% of projected quarter revenue "
                    f"({HumanizedPriority.format_currency(row['total'])})."
                )

        return insights[:2]  # Max 2 concentration insights

    @staticmethod
    def analyze_revenue_exposure(engine) -> List[str]:
        """Detect revenue concentration on few accounts."""
        insights = []
        opps = engine.data.get('opportunity')
        accounts = engine.data.get('account')
        if opps is None or opps.empty or accounts is None:
            return insights

        open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
        if open_opps.empty:
            return insights

        total_pipeline = open_opps['Amount_USD'].sum()
        if total_pipeline == 0:
            return insights

        acc_pipeline = open_opps.groupby('Account_ID')['Amount_USD'].sum().sort_values(ascending=False)

        # Top 3 accounts concentration
        top_3_value = acc_pipeline.head(3).sum()
        top_3_pct = (top_3_value / total_pipeline) * 100
        if top_3_pct >= 50:
            top_names = []
            for acc_id in acc_pipeline.head(3).index:
                acc_row = accounts[accounts['Account_ID'] == acc_id]
                if not acc_row.empty:
                    top_names.append(acc_row.iloc[0]['Account_Name'])
            if top_names:
                insights.append(
                    f"Top 3 accounts ({', '.join(top_names[:3])}) hold {top_3_pct:.0f}% of total pipeline "
                    f"({HumanizedPriority.format_currency(top_3_value)}) — high account concentration risk."
                )

        return insights[:1]

    @staticmethod
    def analyze_engagement_momentum(engine) -> List[str]:
        """Detect accounts with declining engagement vs rising engagement."""
        insights = []
        accounts = engine.data.get('account')
        activities = engine.data.get('activity')
        if accounts is None or activities is None or activities.empty:
            return insights

        now = datetime.now()
        inactive_strategic = 0
        total_strategic = 0

        for _, acc in accounts.iterrows():
            tier = str(acc.get('Account_Tier', '')).lower()
            if 'strategic' not in tier and 'key' not in tier:
                continue
            total_strategic += 1

            acc_acts = activities[activities['Account_ID'] == acc['Account_ID']]
            if acc_acts.empty:
                inactive_strategic += 1
                continue

            last_date = pd.to_datetime(acc_acts['Activity_Date']).max()
            if pd.notna(last_date):
                try:
                    if last_date.tzinfo is not None:
                        last_date = last_date.tz_localize(None)
                except Exception:
                    pass
                if (now - last_date).days > 30:
                    inactive_strategic += 1

        if total_strategic > 0 and inactive_strategic > 0:
            pct = (inactive_strategic / total_strategic) * 100
            insights.append(
                f"{inactive_strategic} of {total_strategic} strategic/key accounts ({pct:.0f}%) show declining engagement momentum "
                f"(no activity in 30+ days)."
            )

        return insights[:1]

    @staticmethod
    def generate_all(engine) -> List[str]:
        """Run all portfolio analyses and return combined insights."""
        results = []
        results.extend(PortfolioIntelligence.analyze_stage_concentration(engine))
        results.extend(PortfolioIntelligence.analyze_revenue_exposure(engine))
        results.extend(PortfolioIntelligence.analyze_engagement_momentum(engine))
        return results


# ═══════════════════════════════════════════════════════════════
# TEMPORAL INTELLIGENCE
# ═══════════════════════════════════════════════════════════════

class TemporalIntelligence:
    """Trajectory awareness. Detects stale deals, engagement decay,
    close-window urgency, and aging clusters."""

    @staticmethod
    def detect_stale_deals(engine) -> List[str]:
        """Find high-value deals past their close date and still open."""
        insights = []
        opps = engine.data.get('opportunity')
        if opps is None or opps.empty:
            return insights

        now = datetime.now()
        open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])].copy()
        if open_opps.empty:
            return insights

        stale_count = 0
        stale_value = 0

        for _, opp in open_opps.iterrows():
            try:
                close_date = pd.to_datetime(opp.get('Close_Date'))
                if pd.notna(close_date):
                    if close_date.tzinfo is not None:
                        close_date = close_date.tz_localize(None)
                    if close_date < now:
                        amount = float(opp.get('Amount_USD', 0)) if pd.notna(opp.get('Amount_USD')) else 0
                        stale_count += 1
                        stale_value += amount
            except Exception:
                pass

        if stale_count > 0:
            insights.append(
                f"{stale_count} open deals with overdue close dates totaling "
                f"{HumanizedPriority.format_currency(stale_value)} in exposed pipeline value."
            )

        return insights[:1]

    @staticmethod
    def detect_close_window_urgency(engine, days: int = 30) -> List[str]:
        """Find high-value deals closing within the next N days."""
        insights = []
        opps = engine.data.get('opportunity')
        if opps is None or opps.empty:
            return insights

        now = datetime.now()
        window_end = now + timedelta(days=days)
        open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
        if open_opps.empty:
            return insights

        closing_soon_count = 0
        closing_soon_value = 0

        for _, opp in open_opps.iterrows():
            try:
                close_date = pd.to_datetime(opp.get('Close_Date'))
                if pd.notna(close_date):
                    if close_date.tzinfo is not None:
                        close_date = close_date.tz_localize(None)
                    if now <= close_date <= window_end:
                        amount = float(opp.get('Amount_USD', 0)) if pd.notna(opp.get('Amount_USD')) else 0
                        closing_soon_count += 1
                        closing_soon_value += amount
            except Exception:
                pass

        if closing_soon_count > 0:
            insights.append(
                f"{closing_soon_count} deals ({HumanizedPriority.format_currency(closing_soon_value)}) "
                f"are scheduled to close within the next {days} days."
            )

        return insights[:1]

    @staticmethod
    def detect_aging_clusters(engine) -> List[str]:
        """Detect early-stage deals that haven't progressed."""
        insights = []
        opps = engine.data.get('opportunity')
        if opps is None or opps.empty:
            return insights

        early_stages = ['Prospecting', 'Qualification', 'Needs Analysis']
        open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
        early_opps = open_opps[open_opps['Stage'].isin(early_stages)]

        if len(early_opps) > 0 and len(open_opps) > 0:
            pct = (len(early_opps) / len(open_opps)) * 100
            if pct >= 40:
                insights.append(
                    f"{len(early_opps)} deals ({pct:.0f}% of pipeline) remain in early stages "
                    f"({', '.join(early_stages[:2])}), indicating potential progression bottleneck."
                )

        return insights[:1]

    @staticmethod
    def generate_all(engine) -> List[str]:
        """Run all temporal analyses and return combined insights."""
        results = []
        results.extend(TemporalIntelligence.detect_close_window_urgency(engine))
        results.extend(TemporalIntelligence.detect_stale_deals(engine))
        results.extend(TemporalIntelligence.detect_aging_clusters(engine))
        return results


# ═══════════════════════════════════════════════════════════════
# WHY THIS MATTERS ENGINE
# ═══════════════════════════════════════════════════════════════

def generate_why_this_matters(intent: str, engine, account_id: Optional[str] = None) -> Optional[str]:
    """Generate a concise 1-2 sentence 'why this matters' context.
    Purely deterministic — computed from aggregated metrics, not LLM."""

    opps = engine.data.get('opportunity')
    if opps is None or opps.empty:
        return None

    open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
    total_pipeline = open_opps['Amount_USD'].sum() if not open_opps.empty else 0
    weighted = (open_opps['Amount_USD'] * open_opps['Probability_Pct'] / 100.0).sum() if not open_opps.empty else 0

    if intent == "GLOBAL_LIST_QUERY":
        gap = total_pipeline - weighted
        return (
            f"Your portfolio has {HumanizedPriority.format_currency(total_pipeline)} in open pipeline "
            f"but only {HumanizedPriority.format_currency(weighted)} probability-adjusted — "
            f"a {HumanizedPriority.format_currency(gap)} execution gap that requires deal-level focus."
        )
    elif intent == "PIPELINE_SUMMARY_QUERY":
        deal_count = len(open_opps)
        avg_deal = total_pipeline / deal_count if deal_count > 0 else 0
        return (
            f"{deal_count} active deals averaging {HumanizedPriority.format_currency(avg_deal)} each. "
            f"Weighted forecast of {HumanizedPriority.format_currency(weighted)} depends on stage progression velocity."
        )
    elif intent == "RISK_ANALYSIS_QUERY":
        # Count overdue deals
        now = datetime.now()
        overdue = 0
        for _, opp in open_opps.iterrows():
            try:
                cd = pd.to_datetime(opp.get('Close_Date'))
                if pd.notna(cd):
                    if cd.tzinfo is not None:
                        cd = cd.tz_localize(None)
                    if cd < now:
                        overdue += 1
            except Exception:
                pass
        if overdue > 0:
            return f"{overdue} deals have passed their expected close dates, representing unresolved pipeline risk."
        return None
    elif intent == "CONTACT_QUERY":
        contacts = engine.data.get('contact')
        if contacts is not None and not contacts.empty:
            if account_id:
                acct_contacts = contacts[contacts['Account_ID'] == account_id]
                dm_count = len(acct_contacts[acct_contacts['Role'].str.contains('Decision Maker|C-Suite|VP', na=False, case=False)])
                if dm_count == 0:
                    return "No decision-maker contacts mapped — deal progression depends on stakeholder access."
        return None
    elif intent == "ACCOUNT_PLAN_QUERY" and account_id:
        acc_opps = open_opps[open_opps['Account_ID'] == account_id]
        acc_total = acc_opps['Amount_USD'].sum() if not acc_opps.empty else 0
        if total_pipeline > 0:
            pct = (acc_total / total_pipeline) * 100
            return (
                f"This account holds {HumanizedPriority.format_currency(acc_total)} "
                f"({pct:.0f}% of total portfolio pipeline) — prioritize accordingly."
            )
        return None

    return None


# ═══════════════════════════════════════════════════════════════
# STRATEGIC SYNTHESIS ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

@dataclass
class SynthesisResult:
    """Output of generate_strategic_synthesis(). Contains all computed intelligence."""
    classified_signals: List[ClassifiedSignal] = field(default_factory=list)
    portfolio_insights: List[str] = field(default_factory=list)
    temporal_insights: List[str] = field(default_factory=list)
    why_this_matters: Optional[str] = None
    actions: List[str] = field(default_factory=list)
    synthesis_latency_ms: float = 0.0
    reasoning_package: Optional[Any] = None  # ReasoningPackage from reasoning_engine

    def get_all_signals_for_display(self, max_signals: int = 4) -> List[str]:
        """Return pre-classified, pre-ranked signals formatted for transport.
        classified_signals already contains portfolio + temporal + CRM inputs
        ranked by business priority (Revenue > Pipeline > ... > CRM).
        No re-addition needed — just format and truncate."""
        return [s.to_display() for s in self.classified_signals[:max_signals]]



def generate_strategic_synthesis(
    engine,
    intent: str,
    account_id: Optional[str] = None,
    mode: str = "operational",
    crm_gaps: Optional[List[str]] = None,
) -> SynthesisResult:
    """Master orchestrator for the intelligence synthesis layer.

    Receives ONLY:
        - engine: DataEngine instance (for computed data access)
        - intent: classified query intent
        - account_id: optional account filter
        - mode: executive/operational/analyst
        - crm_gaps: pre-computed CRM hygiene gaps

    Returns:
        SynthesisResult with classified signals, portfolio insights,
        temporal insights, why-this-matters, and curated actions.

    This function is 100% deterministic. No LLM calls.
    """
    import time
    start = time.perf_counter()

    result = SynthesisResult()
    budget = RESPONSE_BUDGET.get(intent, {"max_signals": 4, "max_actions": 3})

    # 1. Portfolio Intelligence (cross-entity)
    result.portfolio_insights = PortfolioIntelligence.generate_all(engine)

    # 2. Temporal Intelligence (trajectory)
    result.temporal_insights = TemporalIntelligence.generate_all(engine)

    # 3. Classify and rank CRM hygiene gaps (always deprioritized)
    raw_signals = []
    if crm_gaps:
        # Strip the ⚠️ prefix for classification
        raw_signals.extend([g.replace("⚠️ ", "").strip() for g in crm_gaps])

    # Add portfolio + temporal insights as raw signals for unified ranking
    raw_signals.extend(result.portfolio_insights)
    raw_signals.extend(result.temporal_insights)

    result.classified_signals = SignalClassifier.classify_and_rank(
        raw_signals, budget.get("max_signals", 4)
    )

    # 4. "Why This Matters" engine
    result.why_this_matters = generate_why_this_matters(intent, engine, account_id)

    # Actions are now generated by NextBestActionEngine in reasoning_engine.py
    # and surfaced via the ReasoningPackage. The synthesis result preserves a
    # backward-compatible list for deterministic renderers that still use it.
    if result.reasoning_package and result.reasoning_package.next_best_actions:
        result.actions = [a.text for a in result.reasoning_package.next_best_actions]
    else:
        # Fallback: derive actions from classified signals only (no hardcoding)
        result.actions = [
            f"Address: {cs.text[:80]}" for cs in result.classified_signals
            if cs.signal_type in (SignalType.REVENUE, SignalType.RISK)
        ][:budget.get("max_actions", 3)]

    result.synthesis_latency_ms = (time.perf_counter() - start) * 1000
    return result



# ═══════════════════════════════════════════════════════════════
# LLM CONTEXT CURATOR
# ═══════════════════════════════════════════════════════════════

def curate_llm_context(
    engine,
    intent: str,
    account_id: Optional[str],
    synthesis: SynthesisResult,
    table_data: Optional[dict] = None,
) -> str:
    """
    Curate the context sent to the LLM.

    When a ReasoningPackage is present on the synthesis result, it takes priority
    and provides the LLM with pre-computed recommendations, ranked contacts,
    evidence-based actions, and business impact analysis.

    The LLM NEVER receives raw CRM records or full contact/opportunity tables.
    It receives ONLY curated intelligence outputs from the reasoning layer.
    """
    sections = []
    pkg = synthesis.reasoning_package  # May be None for global/non-entity queries

    # ── Section 1: Business Decision Context ──────────────────────────────────
    if pkg and pkg.decision_context:
        dc = pkg.decision_context
        sections.append("[Business Decision Context]")
        sections.append(f"  Decision: {dc.decision_label}")
        sections.append(f"  Desired Outcome: {dc.desired_outcome}")
        if dc.context_evidence:
            sections.append(f"  Evidence: {' | '.join(dc.context_evidence)}")
        sections.append("")

    # ── Section 2: Situation (specific, data-backed) ──────────────────────────
    if pkg and pkg.situation_summary:
        sections.append("[Current Situation]")
        sections.append(f"  {pkg.situation_summary}")
        sections.append("")
    else:
        # Fallback: portfolio-level metrics when no entity is scoped
        opps = engine.data.get('opportunity')
        if opps is not None and not opps.empty:
            open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
            total = open_opps['Amount_USD'].sum() if not open_opps.empty else 0
            weighted = (open_opps['Amount_USD'] * open_opps['Probability_Pct'] / 100.0).sum() if not open_opps.empty else 0
            deal_count = len(open_opps)
            sections.append("[Portfolio Metrics]")
            sections.append(f"  Total Open Pipeline: {HumanizedPriority.format_currency(total)}")
            sections.append(f"  Weighted Forecast: {HumanizedPriority.format_currency(weighted)}")
            sections.append(f"  Active Deals: {deal_count}")
            sections.append(f"  Execution Gap: {HumanizedPriority.format_currency(total - weighted)}")
            sections.append("")

    # ── Section 3: Stakeholder Recommendations ────────────────────────────────
    if pkg and pkg.primary_recommendation:
        pc = pkg.primary_recommendation
        sections.append("[Primary Contact Recommendation]")
        sections.append(f"  Name: {pc.name}")
        sections.append(f"  Role: {pc.role} | Department: {pc.department}")
        sections.append(f"  Engagement: {pc.engagement_level} | Last Contact: {pc.last_contact_date}")
        sections.append(f"  Confidence: {pc.stakeholder_confidence}")
        sections.append(f"  Why Primary: {pc.why_primary}")
        sections.append(f"  Suggested Action: {pc.suggested_action}")
        sections.append(f"  Expected Outcome: {pc.expected_outcome}")
        if pc.engagement_risk:
            sections.append(f"  Engagement Risk: {pc.engagement_risk}")
        sections.append("")

        if pkg.secondary_recommendations:
            sections.append("[Secondary Contact Recommendations]")
            for sc in pkg.secondary_recommendations:
                sections.append(f"  #{sc.rank}: {sc.name} | {sc.role} | {sc.engagement_level} engagement | Confidence: {sc.stakeholder_confidence}")
                sections.append(f"       Action: {sc.suggested_action}")
                if sc.engagement_risk:
                    sections.append(f"       Risk: {sc.engagement_risk}")
            sections.append("")

    # ── Section 4: Next Best Actions ──────────────────────────────────────────
    if pkg and pkg.next_best_actions:
        sections.append("[Next Best Actions — Evidence-Based]")
        for i, action in enumerate(pkg.next_best_actions, 1):
            sections.append(f"  {i}. [{action.urgency}] [{action.confidence} confidence] {action.text}")
            sections.append(f"     Why: {action.reason}")
            sections.append(f"     Expected Impact: {action.expected_impact}")
            sections.append(f"     Owner: {action.owner_hint}")
        sections.append("")

    # ── Section 5: Consequences of Inaction (prominent, not buried) ───────────
    if pkg and pkg.next_best_actions:
        inaction_risks = [a.ignore_risk for a in pkg.next_best_actions if a.ignore_risk]
        if inaction_risks:
            sections.append("[⚠ CONSEQUENCES OF INACTION]")
            for i, risk in enumerate(inaction_risks[:3], 1):
                sections.append(f"  {i}. {risk}")
            sections.append("")

    # ── Section 6: Risk Implications ──────────────────────────────────────────
    if pkg and pkg.risk_implications:
        sections.append("[Risk Implications]")
        for r in pkg.risk_implications:
            sections.append(f"  • {r}")
        sections.append("")

    # ── Section 7: Business Impact ────────────────────────────────────────────
    if pkg and pkg.business_impact:
        sections.append("[Business Impact]")
        sections.append(f"  {pkg.business_impact}")
        sections.append("")

    # ── Section 8: Reasoning Evidence ────────────────────────────────────────
    if pkg and pkg.reasoning_evidence:
        sections.append("[Data Evidence Driving Recommendations]")
        for ev in pkg.reasoning_evidence:
            sections.append(f"  • {ev}")
        sections.append("")

    # ── Section 9: Portfolio State (global queries) ───────────────────────────
    if pkg and pkg.portfolio_state:
        ps = pkg.portfolio_state
        sections.append("[Portfolio State]")
        if ps.get("total_pipeline"):
            sections.append(f"  Total Pipeline: ${ps['total_pipeline']:,.0f} | Weighted: ${ps.get('weighted_forecast', 0):,.0f}")
            sections.append(f"  Execution Gap: ${ps.get('execution_gap', 0):,.0f} | Deals: {ps.get('deal_count', 0)}")
        if ps.get("concentration_risk_pct", 0) >= 40:
            sections.append(f"  ⚠ Concentration Risk: Top 3 accounts hold {ps['concentration_risk_pct']}% of pipeline ({', '.join(ps.get('concentration_top_accounts', []))})")
        if ps.get("risk_cluster_accounts"):
            sections.append(f"  Risk Clusters: {', '.join(ps['risk_cluster_accounts'])}")
        if ps.get("growth_cluster_accounts"):
            sections.append(f"  Growth Opportunities: {', '.join(ps['growth_cluster_accounts'])}")
        if ps.get("most_critical_opp"):
            mc = ps["most_critical_opp"]
            sections.append(f"  Most Critical Deal: {mc.get('opp_name', '')} (${mc.get('amount', 0):,.0f}) — {mc.get('stage', '')} — {mc.get('days_until_close', '?')} days to close")
        sections.append("")

    # ── Section 10: Classified Intelligence Signals (from synthesis) ──────────
    if synthesis.classified_signals:
        sections.append("[Portfolio Intelligence Signals]")
        for cs in synthesis.classified_signals:
            sections.append(f"  [{cs.signal_type.value}] {cs.text}")
        sections.append("")

    # ── Section 11: Table hint (LLM never re-generates the table) ────────────
    if table_data and table_data.get('rows'):
        rows = table_data['rows']
        sections.append(f"[Data Table: {len(rows)} records pre-rendered for the user]")
        sections.append("  (Do NOT re-generate this table. It is already displayed to the user.)")
        sections.append("")

    # ── Section 12: Strategic context (why this matters) ─────────────────────
    if synthesis.why_this_matters:
        sections.append("[Strategic Context]")
        sections.append(f"  {synthesis.why_this_matters}")
        sections.append("")

    # ── Section 13: Confidence Assessment ────────────────────────────────────
    if pkg and pkg.confidence:
        sections.append("[Confidence Assessment]")
        sections.append(f"  {pkg.confidence.to_summary()}")
        sections.append("")

    return "\n".join(sections)

