"""
APEX Phase 2 — Data Retrieval Layer

Pipeline Position:
    Phase 1 (Planner LLM) → extract_query_context() → JSON
    ↓
    THIS MODULE → Phase 2: Data Retrieval Layer
    ↓
    Phase 3 (Reasoner LLM) → Structured Intelligence Package

Purpose:
    Takes the structured JSON output from Phase 1 (intent, decision context,
    query parameters), queries the in-memory Pandas DataEngine, and formats
    a clean consolidated data payload string ready for Phase 3 injection.

Design Principles:
    1. Zero LLM calls. Purely deterministic. Blazing fast.
    2. Consumes ONLY the Phase 1 JSON contract — no raw user query parsing.
    3. Outputs a single consolidated text string — the Phase 3 prompt payload.
    4. Every data section is labelled with a tag (e.g. [ACCOUNTS], [OPPORTUNITIES])
       so the Phase 3 Reasoner can parse it reliably.
    5. Applies parameter-driven filtering (limit, time_window, stage_filter)
       before formatting — the Reasoner never sees irrelevant rows.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import json


# ═══════════════════════════════════════════════════════════════
# PHASE 1 CONTRACT SCHEMA
# ═══════════════════════════════════════════════════════════════

@dataclass
class Phase1Output:
    """Parsed representation of the Phase 1 Planner LLM JSON output."""
    extracted_intent: str
    decision_context_label: str
    decision_context_outcome: str
    limit: Optional[int] = None
    target_accounts: Optional[List[str]] = None
    target_opportunities: Optional[List[str]] = None
    target_contacts: Optional[List[str]] = None
    time_window: Optional[str] = None
    stage_filter: Optional[str] = None
    sort_by: Optional[str] = None
    secondary_intents: Optional[List[str]] = None
    confidence: str = "HIGH"

    @classmethod
    def from_json(cls, raw: dict) -> "Phase1Output":
        """Parse the raw Phase 1 JSON into a typed dataclass.
        Supports both verbose and ultra-compact low-latency schemas."""
        params = raw.get("query_parameters") or raw.get("params") or {}
        dc = raw.get("decision_context") or {}

        # Handle decision_context as either a dict, string, or plain fields
        if isinstance(dc, dict):
            label = dc.get("label") or raw.get("decision") or "Operational Intelligence"
            outcome = dc.get("desired_outcome") or raw.get("outcome") or ""
        else:
            label = str(dc)
            outcome = ""

        intent = raw.get("extracted_intent") or raw.get("intent") or "ACTION_RECOMMENDATION"
        confidence = raw.get("confidence", "HIGH")

        return cls(
            extracted_intent=intent,
            decision_context_label=label,
            decision_context_outcome=outcome,
            limit=params.get("limit"),
            target_accounts=params.get("target_accounts") or params.get("accounts") or [],
            target_opportunities=params.get("target_opportunities") or params.get("opportunities") or [],
            target_contacts=params.get("target_contacts") or params.get("contacts") or [],
            time_window=params.get("time_window") or params.get("window"),
            stage_filter=params.get("stage_filter") or params.get("stage"),
            sort_by=params.get("sort_by") or params.get("sort"),
            secondary_intents=raw.get("secondary_intents", []),
            confidence=confidence,
        )


# ═══════════════════════════════════════════════════════════════
# HELPER UTILITIES
# ═══════════════════════════════════════════════════════════════

def _safe_date(val) -> Optional[str]:
    """Safely convert a date value to YYYY-MM-DD string."""
    if pd.isna(val):
        return None
    try:
        return str(pd.to_datetime(val))[:10]
    except Exception:
        return str(val)[:10] if val else None


def _safe_float(val) -> float:
    """Safely convert to float, defaulting to 0."""
    if pd.isna(val):
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val) -> int:
    """Safely convert to int, defaulting to 0."""
    if pd.isna(val):
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _parse_time_window(time_window: Optional[str]) -> Optional[datetime]:
    """Convert a natural-language time window string into a cutoff datetime.

    Supported formats from Phase 1:
        "next 30 days", "30 days", "this quarter", "this month",
        "next week", "today", "next 7 days", "60 days"
    """
    if not time_window:
        return None

    tw = time_window.lower().strip()
    now = datetime.now()

    # Direct day extraction: "next N days" or "N days"
    for prefix in ("next ", ""):
        for suffix in (" days", " day"):
            candidate = tw.replace(prefix, "").replace(suffix, "").strip()
            if candidate.isdigit():
                return now + timedelta(days=int(candidate))

    if "this week" in tw or "next week" in tw:
        return now + timedelta(days=7)
    if "this month" in tw:
        return now + timedelta(days=30)
    if "this quarter" in tw:
        return now + timedelta(days=90)
    if "today" in tw:
        return now + timedelta(days=1)

    return None


def normalize_stage_name(stage_str: Optional[str]) -> Optional[str]:
    """Normalize common stage names/phrases extracted by Phase 1 Planner
    to match valid substrings of CRM database Stage values."""
    if not stage_str:
        return None
    s = stage_str.lower().strip()
    if "negotiation" in s:
        return "Negotiation"
    if "perception" in s:
        return "Perception"
    if "proposal" in s:
        return "Proposal"
    if "proposition" in s:
        return "Proposition"
    if "decision" in s:
        return "Decision"
    if "needs" in s:
        return "Needs"
    if "qualification" in s:
        return "Qualification"
    if "prospecting" in s:
        return "Prospecting"
    return stage_str


def _resolve_account_ids(engine, target_names: List[str]) -> List[str]:
    """Fuzzy-resolve account names from Phase 1 to actual Account_IDs.

    Performs case-insensitive substring matching against the Account_Name column.
    """
    accounts = engine.data.get("account")
    if accounts is None or accounts.empty or not target_names:
        return []

    resolved = []
    for name in target_names:
        name_lower = name.lower().strip()
        for _, row in accounts.iterrows():
            db_name = str(row.get("Account_Name", "")).lower()
            if name_lower in db_name or db_name in name_lower:
                resolved.append(str(row["Account_ID"]))
                break
    return resolved


def _resolve_opportunity_ids(engine, target_opps: List[str]) -> List[str]:
    """Resolve opportunity ID strings to validated IDs that exist in the data."""
    opps = engine.data.get("opportunity")
    if opps is None or opps.empty or not target_opps:
        return []

    valid_ids = set(opps["Opp_ID"].astype(str).str.upper().tolist())
    resolved = []
    for opp_id in target_opps:
        normalized = opp_id.strip().upper()
        if normalized in valid_ids:
            resolved.append(normalized)
    return resolved


# ═══════════════════════════════════════════════════════════════
# CORE FORMATTER — Converts a DataFrame subset into tagged text
# ═══════════════════════════════════════════════════════════════

def _format_dataframe_as_text(df: pd.DataFrame, tag: str, columns: List[str],
                               limit: Optional[int] = None) -> str:
    """Format a filtered DataFrame into a pipe-delimited text block.

    Output format:
        [TAG]
        Col1 | Col2 | Col3
        val1 | val2 | val3
        ...
    """
    if df is None or df.empty:
        return f"[{tag}]\nNo records found.\n"

    # Filter to only requested columns that exist
    available = [c for c in columns if c in df.columns]
    if not available:
        return f"[{tag}]\nNo matching columns.\n"

    subset = df[available]
    if limit and limit > 0:
        subset = subset.head(limit)

    lines = [f"[{tag}]"]
    lines.append(" | ".join(available))
    for _, row in subset.iterrows():
        vals = []
        for c in available:
            v = row[c]
            if pd.isna(v):
                vals.append("")
            elif isinstance(v, float):
                vals.append(f"{v:,.2f}")
            else:
                vals.append(str(v)[:50])  # Truncate long strings
        lines.append(" | ".join(vals))

    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# INTENT-SPECIFIC DATA RETRIEVERS
# ═══════════════════════════════════════════════════════════════

def _retrieve_contact_data(engine, p1: Phase1Output, account_ids: List[str]) -> str:
    """Retrieve contact + activity data for stakeholder intelligence."""
    sections = []
    contacts = engine.data.get("contact")
    activities = engine.data.get("activity")
    opps = engine.data.get("opportunity")

    if contacts is None or contacts.empty:
        return "[CONTACTS]\nNo contact data available.\n"

    df = contacts.copy()

    # Filter by resolved accounts
    if account_ids:
        df = df[df["Account_ID"].isin(account_ids)]

    # Enrich with account name
    accounts = engine.data.get("account")
    if accounts is not None:
        df = df.merge(accounts[["Account_ID", "Account_Name"]], on="Account_ID", how="left")

    contact_cols = ["Contact_ID", "Account_ID", "Account_Name", "First_Name", "Last_Name",
                    "Role", "Department", "Engagement_Level", "Last_Contact_Date"]
    sections.append(_format_dataframe_as_text(df, "CONTACTS", contact_cols, p1.limit))

    # Append activity context for these accounts
    if activities is not None and not activities.empty and account_ids:
        act_df = activities[activities["Account_ID"].isin(account_ids)].copy()
        # Sort by most recent first
        act_df["Activity_Date"] = pd.to_datetime(act_df["Activity_Date"], errors="coerce")
        act_df = act_df.sort_values("Activity_Date", ascending=False)
        act_cols = ["Activity_ID", "Account_ID", "Contact_ID", "Activity_Type",
                    "Activity_Date", "Subject"]
        sections.append(_format_dataframe_as_text(act_df, "RECENT_ACTIVITIES", act_cols, limit=15))

    # Append open opportunity context for stakeholder-to-deal mapping
    if opps is not None and not opps.empty and account_ids:
        opp_df = opps[(opps["Account_ID"].isin(account_ids)) &
                      (~opps["Stage"].isin(["Closed Won", "Closed Lost"]))].copy()
        opp_cols = ["Opp_ID", "Opp_Name", "Stage", "Amount_USD", "Probability_Pct", "Close_Date"]
        sections.append(_format_dataframe_as_text(opp_df, "RELATED_OPPORTUNITIES", opp_cols))

    return "\n".join(sections)


def _retrieve_pipeline_data(engine, p1: Phase1Output, account_ids: List[str]) -> str:
    """Retrieve opportunity pipeline data with filters applied."""
    sections = []
    opps = engine.data.get("opportunity")
    accounts = engine.data.get("account")

    if opps is None or opps.empty:
        return "[OPPORTUNITIES]\nNo opportunity data available.\n"

    df = opps.copy()

    # Filter: open deals only
    df = df[~df["Stage"].isin(["Closed Won", "Closed Lost"])]

    # Filter: by account
    if account_ids:
        df = df[df["Account_ID"].isin(account_ids)]

    # Filter: by stage
    if p1.stage_filter:
        stage_norm = normalize_stage_name(p1.stage_filter)
        if stage_norm:
            df = df[df["Stage"].str.lower().str.contains(stage_norm.lower(), na=False)]

    # Filter: by time window (close date within window)
    cutoff = _parse_time_window(p1.time_window)
    if cutoff:
        df["_close_dt"] = pd.to_datetime(df["Close_Date"], errors="coerce")
        # Strip timezone
        try:
            df["_close_dt"] = df["_close_dt"].dt.tz_localize(None)
        except Exception:
            pass
        now = datetime.now()
        df = df[(df["_close_dt"] >= now) & (df["_close_dt"] <= cutoff)]
        df = df.drop(columns=["_close_dt"], errors="ignore")

    # Enrich with account name + tier
    if accounts is not None:
        df = df.merge(accounts[["Account_ID", "Account_Name", "Account_Tier"]],
                      on="Account_ID", how="left")

    # Sort: by amount descending (default), or by Phase 1 sort parameter
    sort_col = "Amount_USD"
    if p1.sort_by:
        sb = p1.sort_by.lower()
        if "probability" in sb:
            sort_col = "Probability_Pct"
        elif "close" in sb or "date" in sb:
            sort_col = "Close_Date"
        elif "stage" in sb:
            sort_col = "Stage"
    df = df.sort_values(by=sort_col, ascending=False)

    opp_cols = ["Opp_ID", "Account_Name", "Account_Tier", "Opp_Name", "Stage",
                "Amount_USD", "Probability_Pct", "Close_Date", "Competitor", "Owner"]
    sections.append(_format_dataframe_as_text(df, "OPPORTUNITIES", opp_cols, p1.limit))

    # Append aggregate metrics
    total_value = _safe_float(df["Amount_USD"].sum())
    weighted = _safe_float((df["Amount_USD"] * df["Probability_Pct"] / 100.0).sum())
    deal_count = len(df)

    sections.append("[PIPELINE_METRICS]")
    sections.append(f"Total Open Pipeline: ${total_value:,.2f}")
    sections.append(f"Weighted Forecast: ${weighted:,.2f}")
    sections.append(f"Active Deal Count: {deal_count}")
    sections.append(f"Execution Gap: ${total_value - weighted:,.2f}")
    sections.append("")

    # Stage breakdown
    if not df.empty:
        sections.append("[STAGE_BREAKDOWN]")
        sections.append("Stage | Count | Total_Amount")
        stage_agg = df.groupby("Stage").agg(
            count=("Opp_ID", "count"),
            total=("Amount_USD", "sum"),
        )
        for stage, row in stage_agg.iterrows():
            sections.append(f"{stage} | {int(row['count'])} | ${float(row['total']):,.2f}")
        sections.append("")

    return "\n".join(sections)


def _retrieve_health_data(engine, p1: Phase1Output, account_ids: List[str]) -> str:
    """Retrieve risk, health, and support case data."""
    sections = []
    accounts = engine.data.get("account")
    opps = engine.data.get("opportunity")
    contacts = engine.data.get("contact")
    cases = engine.data.get("case")
    activities = engine.data.get("activity")

    if accounts is None or accounts.empty:
        return "[HEALTH_DATA]\nNo account data available.\n"

    # Scope to target accounts or all
    acc_df = accounts.copy()
    if account_ids:
        acc_df = acc_df[acc_df["Account_ID"].isin(account_ids)]

    # Build a per-account health/risk summary
    rows = []
    for _, acc in acc_df.iterrows():
        aid = acc["Account_ID"]
        row = {
            "Account_ID": aid,
            "Account_Name": acc.get("Account_Name", ""),
            "Account_Tier": acc.get("Account_Tier", ""),
            "Industry": acc.get("Industry", ""),
            "Annual_Revenue_USD": _safe_float(acc.get("Annual_Revenue_USD")),
        }

        # Open pipeline
        if opps is not None and not opps.empty:
            acc_opps = opps[(opps["Account_ID"] == aid) &
                            (~opps["Stage"].isin(["Closed Won", "Closed Lost"]))]
            row["Open_Pipeline_USD"] = _safe_float(acc_opps["Amount_USD"].sum())
            row["Open_Deal_Count"] = len(acc_opps)

            # Overdue deals
            now = datetime.now()
            overdue_count = 0
            overdue_value = 0
            for _, opp in acc_opps.iterrows():
                try:
                    cd = pd.to_datetime(opp.get("Close_Date"))
                    if pd.notna(cd):
                        if cd.tzinfo is not None:
                            cd = cd.tz_localize(None)
                        if cd < now:
                            overdue_count += 1
                            overdue_value += _safe_float(opp.get("Amount_USD"))
                except Exception:
                    pass
            row["Overdue_Deals"] = overdue_count
            row["Overdue_Value_USD"] = overdue_value
        else:
            row["Open_Pipeline_USD"] = 0
            row["Open_Deal_Count"] = 0
            row["Overdue_Deals"] = 0
            row["Overdue_Value_USD"] = 0

        # Contact coverage
        if contacts is not None and not contacts.empty:
            acc_contacts = contacts[contacts["Account_ID"] == aid]
            row["Contact_Count"] = len(acc_contacts)
            row["Has_Decision_Maker"] = not acc_contacts[
                acc_contacts["Role"].str.contains("Decision Maker|Economic Buyer|C-Suite|VP",
                                                  na=False, case=False)
            ].empty
        else:
            row["Contact_Count"] = 0
            row["Has_Decision_Maker"] = False

        # Engagement recency
        if activities is not None and not activities.empty:
            acc_acts = activities[activities["Account_ID"] == aid]
            if not acc_acts.empty:
                last = pd.to_datetime(acc_acts["Activity_Date"]).max()
                if pd.notna(last):
                    try:
                        if last.tzinfo is not None:
                            last = last.tz_localize(None)
                    except Exception:
                        pass
                    row["Days_Since_Activity"] = (datetime.now() - last).days
                else:
                    row["Days_Since_Activity"] = 999
            else:
                row["Days_Since_Activity"] = 999
        else:
            row["Days_Since_Activity"] = 999

        # Open critical cases
        if cases is not None and not cases.empty:
            acc_cases = cases[cases["Account_ID"] == aid]
            open_critical = acc_cases[
                (acc_cases["Severity"].isin(["Critical", "High"])) &
                (acc_cases["Status"] != "Closed")
            ]
            row["Open_Critical_Cases"] = len(open_critical)
        else:
            row["Open_Critical_Cases"] = 0

        rows.append(row)

    # Format the health summary table
    health_df = pd.DataFrame(rows)
    health_cols = ["Account_ID", "Account_Name", "Account_Tier", "Annual_Revenue_USD",
                   "Open_Pipeline_USD", "Open_Deal_Count", "Overdue_Deals", "Overdue_Value_USD",
                   "Contact_Count", "Has_Decision_Maker", "Days_Since_Activity",
                   "Open_Critical_Cases"]
    sections.append(_format_dataframe_as_text(health_df, "ACCOUNT_HEALTH_MATRIX", health_cols, p1.limit))

    # Append raw case data for critical/high severity
    if cases is not None and not cases.empty:
        case_scope = cases.copy()
        if account_ids:
            case_scope = case_scope[case_scope["Account_ID"].isin(account_ids)]
        critical_cases = case_scope[
            (case_scope["Severity"].isin(["Critical", "High"])) &
            (case_scope["Status"] != "Closed")
        ]
        if accounts is not None:
            critical_cases = critical_cases.merge(accounts[["Account_ID", "Account_Name"]],
                                                  on="Account_ID", how="left")
        case_cols = ["Case_ID", "Account_Name", "Subject", "Severity", "Status",
                     "Open_Date", "CSAT_Score"]
        sections.append(_format_dataframe_as_text(critical_cases, "OPEN_CRITICAL_CASES", case_cols))

    return "\n".join(sections)


def _retrieve_account_plan_data(engine, p1: Phase1Output, account_ids: List[str]) -> str:
    """Retrieve full cross-entity data for a specific account strategy review."""
    sections = []
    accounts = engine.data.get("account")
    opps = engine.data.get("opportunity")
    contacts = engine.data.get("contact")
    activities = engine.data.get("activity")
    cases = engine.data.get("case")

    if not account_ids:
        return "[ACCOUNT_PLAN]\nNo target account specified.\n"

    # Use the first resolved account
    aid = account_ids[0]

    # Account profile
    if accounts is not None:
        acc_row = accounts[accounts["Account_ID"] == aid]
        acc_cols = list(accounts.columns)
        sections.append(_format_dataframe_as_text(acc_row, "ACCOUNT_PROFILE", acc_cols))

    # All opportunities (open + closed for historical context)
    if opps is not None:
        acc_opps = opps[opps["Account_ID"] == aid].copy()
        acc_opps = acc_opps.sort_values("Amount_USD", ascending=False)
        opp_cols = ["Opp_ID", "Opp_Name", "Stage", "Amount_USD", "Probability_Pct",
                    "Close_Date", "Competitor", "Owner"]
        sections.append(_format_dataframe_as_text(acc_opps, "OPPORTUNITIES", opp_cols))

    # Contacts
    if contacts is not None:
        acc_contacts = contacts[contacts["Account_ID"] == aid].copy()
        contact_cols = ["Contact_ID", "First_Name", "Last_Name", "Role", "Department",
                        "Engagement_Level", "Last_Contact_Date"]
        sections.append(_format_dataframe_as_text(acc_contacts, "CONTACTS", contact_cols))

    # Activities (most recent first, capped at 20)
    if activities is not None:
        acc_acts = activities[activities["Account_ID"] == aid].copy()
        acc_acts["Activity_Date"] = pd.to_datetime(acc_acts["Activity_Date"], errors="coerce")
        acc_acts = acc_acts.sort_values("Activity_Date", ascending=False)
        act_cols = ["Activity_ID", "Contact_ID", "Activity_Type", "Activity_Date", "Subject"]
        sections.append(_format_dataframe_as_text(acc_acts, "ACTIVITIES", act_cols, limit=20))

    # Cases
    if cases is not None:
        acc_cases = cases[cases["Account_ID"] == aid].copy()
        case_cols = ["Case_ID", "Subject", "Severity", "Status", "Open_Date", "CSAT_Score"]
        sections.append(_format_dataframe_as_text(acc_cases, "CASES", case_cols))

    return "\n".join(sections)


def _retrieve_action_data(engine, p1: Phase1Output, account_ids: List[str]) -> str:
    """Retrieve cross-cutting data for action recommendation generation.

    Pulls the broadest useful context: overdue deals, declining engagement,
    open critical cases, and unmapped stakeholders — across all accounts
    or scoped to target accounts.
    """
    sections = []

    # Get health matrix (reuse the health retriever for consistency)
    sections.append(_retrieve_health_data(engine, p1, account_ids))

    # Add pipeline data as supplementary
    opps = engine.data.get("opportunity")
    if opps is not None and not opps.empty:
        df = opps[~opps["Stage"].isin(["Closed Won", "Closed Lost"])].copy()
        if account_ids:
            df = df[df["Account_ID"].isin(account_ids)]

        # Overdue deals specifically
        now = datetime.now()
        overdue_rows = []
        for _, opp in df.iterrows():
            try:
                cd = pd.to_datetime(opp.get("Close_Date"))
                if pd.notna(cd):
                    if cd.tzinfo is not None:
                        cd = cd.tz_localize(None)
                    if cd < now:
                        overdue_rows.append(opp)
            except Exception:
                pass

        if overdue_rows:
            overdue_df = pd.DataFrame(overdue_rows)
            accounts = engine.data.get("account")
            if accounts is not None:
                overdue_df = overdue_df.merge(accounts[["Account_ID", "Account_Name"]],
                                              on="Account_ID", how="left")
            overdue_df = overdue_df.sort_values("Amount_USD", ascending=False)
            od_cols = ["Opp_ID", "Account_Name", "Opp_Name", "Stage", "Amount_USD", "Close_Date"]
            sections.append(_format_dataframe_as_text(overdue_df, "OVERDUE_DEALS", od_cols, limit=10))

    return "\n".join(sections)


def _retrieve_pipeline_summary_data(engine, p1: Phase1Output, account_ids: List[str]) -> str:
    """Retrieve aggregate pipeline summary with stage breakdown."""
    # This is a superset of pipeline data with extra aggregate focus
    return _retrieve_pipeline_data(engine, p1, account_ids)


# ═══════════════════════════════════════════════════════════════
# INTENT → RETRIEVER DISPATCH TABLE
# ═══════════════════════════════════════════════════════════════

_INTENT_RETRIEVER_MAP = {
    "CONTACT_QUERY":          _retrieve_contact_data,
    "PIPELINE_QUERY":         _retrieve_pipeline_data,
    "PIPELINE_SUMMARY":       _retrieve_pipeline_summary_data,
    "RISK_ANALYSIS":          _retrieve_health_data,
    "HEALTH_QUERY":           _retrieve_health_data,
    "ACCOUNT_PLAN":           _retrieve_account_plan_data,
    "ACTION_RECOMMENDATION":  _retrieve_action_data,
}


# ═══════════════════════════════════════════════════════════════
# MASTER ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

def execute_data_retrieval(engine, phase1_json: dict) -> str:
    """Master entry point for Phase 2.

    Args:
        engine: DataEngine instance with loaded Excel data.
        phase1_json: Raw JSON dict from Phase 1 Planner LLM.

    Returns:
        A consolidated text payload string formatted for Phase 3 injection.
        Contains:
            - [QUERY_CONTEXT] header with decision metadata
            - Intent-specific data sections ([CONTACTS], [OPPORTUNITIES], etc.)
            - [DATA_RETRIEVAL_METADATA] footer with retrieval stats
    """
    import time
    start = time.perf_counter()

    # 1. Parse the Phase 1 contract
    p1 = Phase1Output.from_json(phase1_json)

    # 2. Resolve entity references to actual IDs in the database
    account_ids = _resolve_account_ids(engine, p1.target_accounts or [])
    opp_ids = _resolve_opportunity_ids(engine, p1.target_opportunities or [])

    # If opportunity IDs were resolved but no account IDs, derive account from opp
    if opp_ids and not account_ids:
        opps = engine.data.get("opportunity")
        if opps is not None:
            for oid in opp_ids:
                match = opps[opps["Opp_ID"].str.upper() == oid.upper()]
                if not match.empty:
                    account_ids.append(str(match.iloc[0]["Account_ID"]))

    # 3. Build the consolidated payload
    payload_sections = []

    # ── Section 1: Query Context Header ───────────────────────────
    payload_sections.append("=" * 60)
    payload_sections.append("[QUERY_CONTEXT]")
    payload_sections.append(f"Intent: {p1.extracted_intent}")
    payload_sections.append(f"Decision: {p1.decision_context_label}")
    payload_sections.append(f"Desired Outcome: {p1.decision_context_outcome}")
    if account_ids:
        # Resolve names for readability
        accounts = engine.data.get("account")
        if accounts is not None:
            names = []
            for aid in account_ids:
                match = accounts[accounts["Account_ID"] == aid]
                if not match.empty:
                    names.append(f"{match.iloc[0]['Account_Name']} ({aid})")
            payload_sections.append(f"Target Accounts: {', '.join(names)}")
    if opp_ids:
        payload_sections.append(f"Target Opportunities: {', '.join(opp_ids)}")
    if p1.time_window:
        payload_sections.append(f"Time Window: {p1.time_window}")
    if p1.stage_filter:
        payload_sections.append(f"Stage Filter: {p1.stage_filter}")
    if p1.limit:
        payload_sections.append(f"Result Limit: {p1.limit}")
    payload_sections.append(f"Planner Confidence: {p1.confidence}")
    payload_sections.append("=" * 60)
    payload_sections.append("")

    # ── Section 2: Intent-Specific Data ───────────────────────────
    retriever = _INTENT_RETRIEVER_MAP.get(p1.extracted_intent)

    if retriever:
        data_payload = retriever(engine, p1, account_ids)
    else:
        # Fallback: retrieve broad action-recommendation data
        data_payload = _retrieve_action_data(engine, p1, account_ids)

    payload_sections.append(data_payload)

    # ── Section 3: Secondary Intent Data (if any) ─────────────────
    if p1.secondary_intents:
        for sec_intent in p1.secondary_intents:
            sec_retriever = _INTENT_RETRIEVER_MAP.get(sec_intent)
            if sec_retriever and sec_retriever != retriever:
                payload_sections.append(f"\n[SECONDARY_CONTEXT — {sec_intent}]")
                payload_sections.append(sec_retriever(engine, p1, account_ids))

    # ── Section 4: Retrieval Metadata Footer ──────────────────────
    elapsed_ms = (time.perf_counter() - start) * 1000
    payload_sections.append("=" * 60)
    payload_sections.append("[DATA_RETRIEVAL_METADATA]")
    payload_sections.append(f"Retrieval Latency: {elapsed_ms:.1f}ms")
    payload_sections.append(f"Resolved Accounts: {len(account_ids)}")
    payload_sections.append(f"Resolved Opportunities: {len(opp_ids)}")
    payload_sections.append(f"Primary Retriever: {p1.extracted_intent}")
    payload_sections.append(f"Secondary Retrievers: {', '.join(p1.secondary_intents) if p1.secondary_intents else 'None'}")
    payload_sections.append(f"Timestamp: {datetime.now().isoformat()}")
    payload_sections.append("=" * 60)

    return "\n".join(payload_sections)
