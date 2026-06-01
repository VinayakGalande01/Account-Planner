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

    # 5. Curated actions (intent-specific, deterministic)
    result.actions = _generate_curated_actions(engine, intent, account_id, budget.get("max_actions", 3))

    result.synthesis_latency_ms = (time.perf_counter() - start) * 1000
    return result


def _generate_curated_actions(engine, intent: str, account_id: Optional[str], max_actions: int) -> List[str]:
    """Generate operationally relevant actions based on intent + data state."""
    actions = []
    opps = engine.data.get('opportunity')
    now = datetime.now()

    if intent == "GLOBAL_LIST_QUERY":
        # Check for overdue deals
        if opps is not None and not opps.empty:
            open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
            overdue = []
            for _, opp in open_opps.iterrows():
                try:
                    cd = pd.to_datetime(opp.get('Close_Date'))
                    if pd.notna(cd):
                        if cd.tzinfo is not None:
                            cd = cd.tz_localize(None)
                        if cd < now:
                            overdue.append(opp)
                except Exception:
                    pass
            if overdue:
                actions.append(f"Revisit {len(overdue)} opportunities with overdue close dates — update timelines or escalate.")
            actions.append("Focus deal execution on top-ranked opportunities to maximize probability-adjusted revenue.")
            actions.append("Conduct CRM hygiene audit on deals missing competitor or timeline details.")

    elif intent == "PIPELINE_SUMMARY_QUERY":
        actions.append("Verify close-date accuracy for deals in Negotiation/Review stage.")
        actions.append("Accelerate early-stage deals through qualification to reduce pipeline aging.")
        actions.append("Review stage-concentration risk and diversify deal progression.")

    elif intent == "CONTACT_QUERY":
        actions.append("Prioritize outreach to Decision Maker contacts with Low or Cold engagement.")
        actions.append("Map additional stakeholders for single-threaded accounts.")
        actions.append("Schedule executive engagement for strategic accounts with declining activity.")

    elif intent == "RISK_ANALYSIS_QUERY":
        actions.append("Escalate deals with overdue close dates and high revenue exposure.")
        actions.append("Re-engage dormant strategic accounts with zero recent activity.")
        actions.append("Resolve open critical-severity support cases blocking deal progression.")

    elif intent == "ACCOUNT_PLAN_QUERY":
        actions.append("Review open opportunity pipeline and validate close-date accuracy.")
        actions.append("Map decision-maker contacts and assess engagement depth.")
        actions.append("Address active CRM hygiene gaps and support case backlog.")
        actions.append("Identify upsell/cross-sell opportunities based on account revenue profile.")
        actions.append("Schedule strategic review meeting with key stakeholders.")

    elif intent == "ACTION_RECOMMENDATION_QUERY":
        actions.append("Focus on highest-priority deals closing within 30 days.")
        actions.append("Re-engage dormant strategic accounts with zero recent activity.")
        actions.append("Resolve critical support cases impacting key account relationships.")
        actions.append("Audit CRM data completeness for deals in advanced stages.")
        actions.append("Prepare executive briefing on portfolio health and forecast confidence.")

    return actions[:max_actions]


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
    """Curate the context sent to the LLM.

    The LLM receives ONLY:
        - Aggregated metrics (pipeline totals, deal counts, weighted forecast)
        - Classified signals (pre-ranked)
        - Portfolio insights (concentration, exposure, momentum)
        - Temporal insights (stale, urgency, decay)
        - Synthesis metadata

    The LLM NEVER receives:
        - Raw CRM records
        - Full opportunity tables
        - Raw contact lists
        - Activity logs
    """
    sections = []

    # 1. Curated portfolio metrics
    opps = engine.data.get('opportunity')
    if opps is not None and not opps.empty:
        open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
        total = open_opps['Amount_USD'].sum() if not open_opps.empty else 0
        weighted = (open_opps['Amount_USD'] * open_opps['Probability_Pct'] / 100.0).sum() if not open_opps.empty else 0
        deal_count = len(open_opps)

        sections.append("[Portfolio Metrics]")
        sections.append(f"Total Open Pipeline: {HumanizedPriority.format_currency(total)}")
        sections.append(f"Weighted Forecast: {HumanizedPriority.format_currency(weighted)}")
        sections.append(f"Active Deals: {deal_count}")
        sections.append(f"Execution Gap: {HumanizedPriority.format_currency(total - weighted)}")
        sections.append("")

    # 2. Account-specific metrics (if applicable)
    if account_id:
        accounts = engine.data.get('account')
        if accounts is not None:
            acc_row = accounts[accounts['Account_ID'] == account_id]
            if not acc_row.empty:
                acc = acc_row.iloc[0]
                sections.append(f"[Account: {acc['Account_Name']}]")
                sections.append(f"Tier: {acc.get('Account_Tier', 'Standard')}")
                sections.append(f"Industry: {acc.get('Industry', 'N/A')}")
                sections.append(f"Annual Revenue: {HumanizedPriority.format_currency(float(acc.get('Annual_Revenue_USD', 0)))}")

                # Account-level health
                try:
                    health = engine.calculate_health_score(account_id)
                    if 'error' not in health:
                        sections.append(f"Health Score: {health['overall_score']}/100 ({health['tier']})")
                except Exception:
                    pass

                # Account pipeline
                if opps is not None:
                    acc_opps = opps[(opps['Account_ID'] == account_id) & ~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
                    acc_pipe = acc_opps['Amount_USD'].sum() if not acc_opps.empty else 0
                    sections.append(f"Account Pipeline: {HumanizedPriority.format_currency(acc_pipe)} ({len(acc_opps)} deals)")

                sections.append("")

    # 3. Table summary (row count + top entries, NOT full dump)
    if table_data and table_data.get('rows'):
        rows = table_data['rows']
        sections.append(f"[Data Table: {len(rows)} records provided]")
        # Provide only top 5 for LLM context (it doesn't need all rows)
        for i, row in enumerate(rows[:5]):
            row_summary = " | ".join([f"{k}: {v}" for k, v in row.items()])
            sections.append(f"  #{i+1}: {row_summary}")
        if len(rows) > 5:
            sections.append(f"  ... and {len(rows) - 5} more records")
        sections.append("")

    # 4. Pre-computed intelligence signals
    if synthesis.classified_signals:
        sections.append("[Classified Intelligence Signals]")
        for cs in synthesis.classified_signals:
            sections.append(f"  [{cs.signal_type.value}] {cs.text}")
        sections.append("")

    # 5. Portfolio insights
    if synthesis.portfolio_insights:
        sections.append("[Portfolio Intelligence]")
        for ins in synthesis.portfolio_insights:
            sections.append(f"  • {ins}")
        sections.append("")

    # 6. Temporal insights
    if synthesis.temporal_insights:
        sections.append("[Temporal Intelligence]")
        for ins in synthesis.temporal_insights:
            sections.append(f"  • {ins}")
        sections.append("")

    # 7. Why this matters
    if synthesis.why_this_matters:
        sections.append("[Strategic Context]")
        sections.append(f"  {synthesis.why_this_matters}")
        sections.append("")

    return "\n".join(sections)
