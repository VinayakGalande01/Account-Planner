"""
Deterministic answers for questions that need data, not reasoning.

- Portfolio questions with no account named: expansion candidates, deals closing soon.
- Factual questions about one account: revenue, health score, contacts, opportunities.

Built straight from the CRM tables: instant, and nothing can be invented. Questions with
planning or causal words ("why", "should", "plan", "strategy") return None and go through
the reasoning pipeline instead.
"""
import datetime
import re
from typing import Any, Dict, List, Optional

import pandas as pd

from intelligence_engine import CLOSED_STAGES, reference_date

PLANNING_WORDS = [
    "why", "should", "plan", "playbook", "strategy", "strategic", "recommend", "next steps", "how do", "how can",
    "how should", "brief", "briefing", "approach", "prioritize", "prioritise", "improve", "risk", "losing", "wrong",
]
EXPANSION_WORDS = ["expansion", "expand", "upsell", "up-sell", "cross-sell", "grow", "growth", "whitespace"]
CLOSING_PATTERN = re.compile(r"\bclos(e|ing)\b.*\b(this|next)\s+(week|month|quarter)\b|\bclosing soon\b")
HEALTHY_MIN = 65.0


def _has_any(text: str, words: List[str]) -> bool:
    return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)


def fmt_usd(value: float) -> str:
    value = float(value or 0)
    if value >= 1e9:
        return f"${value / 1e9:.1f}B"
    if value >= 1e6:
        return f"${value / 1e6:.2f}M".replace(".00M", "M")
    if value >= 1e3:
        return f"${value / 1e3:.0f}K"
    return f"${value:,.0f}"


def display_id(raw_id: Any) -> str:
    """Strip the per-user storage prefix ("1_OPP001" -> "OPP001")."""
    return re.sub(r"^\d+_", "", str(raw_id or ""))


def _open_opps(opps: Optional[pd.DataFrame]) -> pd.DataFrame:
    if opps is None or opps.empty:
        return pd.DataFrame()
    return opps[~opps["Stage"].isin(CLOSED_STAGES)]


def _answer(narrative: str, table: Optional[dict], kind: str) -> Dict[str, Any]:
    return {"narrative": narrative, "table_data": table, "kind": kind}


# ── Portfolio ────────────────────────────────────────────────────────────────

def portfolio_answer(query: str, data: Dict[str, pd.DataFrame]) -> Optional[Dict[str, Any]]:
    q = query.lower()
    if _has_any(q, [w for w in PLANNING_WORDS if w not in ("risk",)]):
        return None
    if _has_any(q, EXPANSION_WORDS):
        return _expansion_candidates(data)
    match = CLOSING_PATTERN.search(q)
    if match:
        return _closing_soon(data, match.group(3) if match.group(3) else "month")
    return None


def _expansion_candidates(data: Dict[str, pd.DataFrame]) -> Optional[Dict[str, Any]]:
    accounts, opps = data.get("account"), _open_opps(data.get("opportunity"))
    if accounts is None or accounts.empty:
        return None
    rows = []
    for _, acc in accounts.iterrows():
        health = float(acc.get("Health_Score", 0)) if pd.notna(acc.get("Health_Score")) else 0.0
        acc_opps = opps[opps["Account_ID"] == acc["Account_ID"]] if not opps.empty else pd.DataFrame()
        if health < HEALTHY_MIN or acc_opps.empty:
            continue
        top = acc_opps.sort_values("Amount_USD", ascending=False).iloc[0]
        rows.append({
            "Account_Name": acc["Account_Name"],
            "Health_Score": int(health),
            "Open_Pipeline_USD": float(acc_opps["Amount_USD"].sum()),
            "Largest_Open_Deal": top["Opp_Name"],
            "Stage": top["Stage"],
            "Probability_Pct": int(top["Probability_Pct"]) if pd.notna(top.get("Probability_Pct")) else None,
        })
    if not rows:
        return _answer("No account is both healthy (health 65+) and carrying open pipeline right now.", None, "PORTFOLIO_EXPANSION")
    rows.sort(key=lambda r: r["Open_Pipeline_USD"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["Rank"] = i
    columns = ["Rank", "Account_Name", "Health_Score", "Open_Pipeline_USD", "Largest_Open_Deal", "Stage", "Probability_Pct"]
    top3 = ", ".join(f"{r['Account_Name']} ({fmt_usd(r['Open_Pipeline_USD'])}, health {r['Health_Score']})" for r in rows[:3])
    total = sum(r["Open_Pipeline_USD"] for r in rows)
    narrative = (
        f"{len(rows)} accounts show expansion potential: healthy (health {int(HEALTHY_MIN)}+) with "
        f"{fmt_usd(total)} of open pipeline between them. Strongest: {top3}."
    )
    return _answer(narrative, {"columns": columns, "rows": rows}, "PORTFOLIO_EXPANSION")


def _closing_soon(data: Dict[str, pd.DataFrame], window: str) -> Optional[Dict[str, Any]]:
    accounts, opps = data.get("account"), _open_opps(data.get("opportunity"))
    if opps.empty:
        return None
    today = reference_date()
    days = {"week": 7, "month": 30, "quarter": 90}.get(window, 30)
    end = today + datetime.timedelta(days=days)
    close = pd.to_datetime(opps["Close_Date"], errors="coerce").dt.date
    due = opps[(close >= today) & (close <= end)].copy()
    names = dict(zip(accounts["Account_ID"], accounts["Account_Name"])) if accounts is not None else {}
    if due.empty:
        return _answer(f"No open deals are due to close in the next {days} days.", None, "PORTFOLIO_CLOSING")
    due["_close"] = pd.to_datetime(due["Close_Date"], errors="coerce")
    rows = []
    for i, (_, o) in enumerate(due.sort_values("_close").iterrows(), 1):
        rows.append({
            "Rank": i,
            "Opp_ID": display_id(o["Opp_ID"]),
            "Opp_Name": o["Opp_Name"],
            "Account_Name": names.get(o["Account_ID"], ""),
            "Stage": o["Stage"],
            "Amount_USD": float(o["Amount_USD"]),
            "Probability_Pct": int(o["Probability_Pct"]) if pd.notna(o.get("Probability_Pct")) else None,
            "Close_Date": str(o["Close_Date"])[:10],
        })
    total = sum(r["Amount_USD"] for r in rows)
    weighted = sum(r["Amount_USD"] * (r["Probability_Pct"] or 0) / 100 for r in rows)
    narrative = (
        f"{len(rows)} open deals worth {fmt_usd(total)} are due to close in the next {days} days "
        f"({fmt_usd(weighted)} probability-weighted). Earliest: {rows[0]['Opp_Name']} on {rows[0]['Close_Date']}."
    )
    columns = ["Rank", "Opp_ID", "Opp_Name", "Account_Name", "Stage", "Amount_USD", "Probability_Pct", "Close_Date"]
    return _answer(narrative, {"columns": columns, "rows": rows}, "PORTFOLIO_CLOSING")


# ── Single account ───────────────────────────────────────────────────────────

def account_answer(query: str, account: pd.Series, data: Dict[str, pd.DataFrame]) -> Optional[Dict[str, Any]]:
    q = query.lower()
    if _has_any(q, PLANNING_WORDS):
        return None
    name = account["Account_Name"]
    acc_id = account["Account_ID"]

    if re.search(r"\b(annual )?revenue\b", q) and not re.search(r"revenue at risk|pipeline", q):
        revenue = account.get("Annual_Revenue_USD")
        if pd.isna(revenue):
            return _answer(f"{name} has no annual revenue recorded in the CRM.", None, "ACCOUNT_REVENUE")
        details = ", ".join(str(account.get(k)) for k in ("Industry", "Account_Tier", "Territory") if pd.notna(account.get(k)))
        return _answer(f"{name}'s annual revenue is {fmt_usd(revenue)} ({details}).", None, "ACCOUNT_REVENUE")

    if re.search(r"\bhealth( score)?\b", q):
        health = account.get("Health_Score")
        if pd.isna(health):
            return _answer(f"{name} has no health score recorded.", None, "ACCOUNT_HEALTH")
        band = "critical" if health < 30 else "at risk" if health < 45 else "fair" if health < 65 else "healthy"
        return _answer(f"{name}'s health score is {int(health)}/100 ({band}).", None, "ACCOUNT_HEALTH")

    if re.search(r"\b(contacts?|stakeholders?|people)\b", q) and re.search(r"\b(list|show|who are|all|contacts? (at|for|of))\b", q):
        contacts = data.get("contact")
        acc_contacts = contacts[contacts["Account_ID"] == acc_id] if contacts is not None and not contacts.empty else pd.DataFrame()
        if acc_contacts.empty:
            return _answer(f"No contacts are recorded for {name}.", None, "ACCOUNT_CONTACTS")
        rows = [{
            "Name": f"{c['First_Name']} {c['Last_Name']}".strip(),
            "Role": c.get("Role", ""),
            "Department": c.get("Department", ""),
            "Engagement": c.get("Engagement_Level", ""),
            "Last_Contacted": str(c.get("Last_Contact_Date", ""))[:10] if pd.notna(c.get("Last_Contact_Date")) else "Never",
        } for _, c in acc_contacts.iterrows()]
        roles = ", ".join(f"{r['Name']} ({r['Role']})" for r in rows)
        return _answer(f"{len(rows)} contacts at {name}: {roles}.",
                       {"columns": ["Name", "Role", "Department", "Engagement", "Last_Contacted"], "rows": rows},
                       "ACCOUNT_CONTACTS")

    if re.search(r"\b(opportunities|opportunity|deals?|opps)\b", q) and re.search(r"\b(list|show|what are|all|open)\b", q):
        opps = data.get("opportunity")
        acc_opps = opps[opps["Account_ID"] == acc_id] if opps is not None and not opps.empty else pd.DataFrame()
        if acc_opps.empty:
            return _answer(f"No opportunities are recorded for {name}.", None, "ACCOUNT_OPPORTUNITIES")
        open_mask = ~acc_opps["Stage"].isin(CLOSED_STAGES)
        rows = [{
            "Opp_ID": display_id(o["Opp_ID"]),
            "Opp_Name": o["Opp_Name"],
            "Stage": o["Stage"],
            "Amount_USD": float(o["Amount_USD"]),
            "Probability_Pct": int(o["Probability_Pct"]) if pd.notna(o.get("Probability_Pct")) else None,
            "Close_Date": str(o["Close_Date"])[:10],
        } for _, o in acc_opps.sort_values(["Stage"], key=lambda s: s.isin(CLOSED_STAGES)).iterrows()]
        open_total = float(acc_opps[open_mask]["Amount_USD"].sum())
        closed = int((~open_mask).sum())
        narrative = f"{name} has {int(open_mask.sum())} open opportunities worth {fmt_usd(open_total)}"
        narrative += f", plus {closed} closed." if closed else "."
        return _answer(narrative,
                       {"columns": ["Opp_ID", "Opp_Name", "Stage", "Amount_USD", "Probability_Pct", "Close_Date"], "rows": rows},
                       "ACCOUNT_OPPORTUNITIES")
    return None
