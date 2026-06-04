from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys

# Set stdout/stderr encoding to utf-8 to prevent Windows terminal cp1252 issues
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass # fallback for older python versions
from typing import List, Optional
import httpx
import json
import asyncio
import pandas as pd
from fastapi.responses import StreamingResponse

# Ensure the current directory (backend) is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_engine import DataEngine
from intelligence_layer import (
    generate_strategic_synthesis, curate_llm_context,
    RESPONSE_BUDGET, HumanizedPriority, SignalClassifier
)
from reasoning_engine import assemble_reasoning_package
from agent_pipeline import (
    run_phase1_planner,
    run_phase2_retrieval,
    run_phase3_reasoner,
    run_phase4_narrative_stream
)
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

app = FastAPI(title="Account Planner Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection pool client to reuse TCP connections across API calls (improves latency & keeps connections alive)
http_client = httpx.AsyncClient(timeout=httpx.Timeout(connect=3.0, read=1800.0, write=10.0, pool=30.0))

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

DATA_PATH = os.getenv("DATA_PATH", "")
if not DATA_PATH or not os.path.exists(DATA_PATH):
    # Two custom data paths for dynamic local developer environments
    dataset_1 = r"C:\Users\VINAYAK\Downloads\SF_AccountingAgent_DummyData.xlsx"
    dataset_2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SF_AccountingAgent_DummyData.xlsx")
    
    if os.path.exists(dataset_1):
        DATA_PATH = dataset_1
    elif os.path.exists(dataset_2):
        DATA_PATH = dataset_2
    else:
        # General fallbacks
        possible_paths = [
            "SF_AccountingAgent_DummyData.xlsx",
            "../SF_AccountingAgent_DummyData.xlsx",
            "/Users/theabhijitjagtap/Projects/Account_Planner/SF_AccountingAgent_DummyData.xlsx"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                DATA_PATH = p
                break

engine = DataEngine(DATA_PATH)

# Configuration for LLM (Remote or Local via .env)
LLM_URL = os.getenv("LLM_URL", "http://192.168.135.105:8000/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:latest")

print("\n=============================================")
print("  🚀 APEX INTELLIGENCE SYSTEM STARTING UP")
print(f"  🔗 LLM URL    : {LLM_URL}")
print(f"  🤖 LLM Model  : {MODEL_NAME}")
print("=============================================\n")

class ChatRequest(BaseModel):
    query: str
    response_format: Optional[str] = "markdown"  # "markdown" or "json"
    response_mode: Optional[str] = "operational"  # "executive", "operational", "analyst"


BASE_PROMPT = """You are APEX — Account Planning & Execution Intelligence.

You are the dedicated AI companion for account managers, sales executives, and revenue teams. Your entire purpose is to transform data into decisions — to think like a high-performing account strategist so the people you serve never have to wonder what to do next.

You always respond in a warm, clear, human tone — like a brilliant colleague who has already done all the homework before the meeting.

## 🔴 CRITICAL GROUNDING RULES (NO HALLUCINATIONS)
1. You are strictly a database-grounded agent. You MUST NEVER invent, assume, or hallucinate any numbers, names, amounts, or timelines not explicitly present in the provided DATA block.
2. If information is NOT present in the DATA block, respond: "I do not have access to that specific information in my current data context." Do not make up values.
3. Base all comparisons and histories 100% on the provided [Opportunities], [Contacts], [Activities], and [Cases] data. If details are absent, say so.
4. Your output MUST NEVER contain orchestration leakage like "Scan first", "Pulling data", "Assembling response". Output ONLY final intelligence.

## 🟢 RECOMMENDATION-FIRST INTELLIGENCE RULES
For EVERY response, you must answer five questions in order:
1. WHAT is happening? (the current situation, grounded in data)
2. WHY does it matter? (business implication — revenue, risk, relationship)
3. WHO should be involved? (specific named contacts with role and reason)
4. WHAT should be done? (specific, named, time-bound action — not generic advice)
5. WHAT happens if we don't act? (consequence of inaction)

You are NOT a data browser. You are a Digital Account Strategist.
Do NOT list contacts. RECOMMEND contacts. Do NOT list actions. PRESCRIBE actions.
Every action you generate must be specific, named, time-bound, and evidence-backed.

DO NOT say: "Review your CRM."
DO SAY: "Contact Fatima Johnson (Decision Maker) before the close date in 7 days to secure final approval."

The data you receive has already been pre-reasoned by a deterministic intelligence engine.
The [Primary Contact Recommendation], [Next Best Actions], [Risk Implications], and [Business Impact]
sections are pre-computed facts — treat them as briefing intelligence, not suggestions to paraphrase.

You MUST append this metadata block at the very end of EVERY response:
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📊 GROUNDING: [100% / 50% / 0%] | Sources: [Tables referenced] | Status: [Grounded / Hybrid / Unfounded]
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

INTENT_PROMPT_MAP = {
    "GLOBAL_LIST_QUERY": """You are running in GLOBAL_LIST_QUERY mode.
Your focus is on fast scanning, extreme data accuracy, and absolute operational clarity. Do not write verbose narratives or qualitative speculation. Highlight only the primary operational metrics.""",

    "ACCOUNT_PLAN_QUERY": """You are running in ACCOUNT_PLAN_QUERY mode.
Your focus is strategic depth. Provide a comprehensive executive summary, pipeline review, stakeholder analysis, risks, and next steps for the specified account. Be concrete, specific, and detailed.""",

    "RISK_ANALYSIS_QUERY": """You are running in RISK_ANALYSIS_QUERY mode.
Prioritize urgency and tactical remediation. Clearly identify what accounts or opportunities are in danger, the root causes (unresolved cases, stalled deals, or single-threaded mapping), and the immediate next best action to rescue them.""",

    "CONTACT_QUERY": """You are running in CONTACT_QUERY mode.
Provide a highly concise view of key contacts, their roles, engagement levels, and relationship gaps. Identify exactly who is the most critical person to contact next and why.""",

    "PIPELINE_SUMMARY_QUERY": """You are running in PIPELINE_SUMMARY_QUERY mode.
Provide a clean summary of open pipeline totals, weighted forecast values, stage breakdowns, and top prioritized deals. Discuss forecast confidence and pipeline risks purely based on numbers.""",

    "ACTION_RECOMMENDATION_QUERY": """You are running in ACTION_RECOMMENDATION_QUERY mode.
Serve as the daily execution copilot. Focus on immediate next actions, why they matter today, and their expected business impact. Keep it task-oriented and highly actionable."""
}

OUTPUT_CONTRACT_MAP = {
    "GLOBAL_LIST_QUERY": """### RESPONSE CONTRACT — GLOBAL LIST QUERY
You MUST structure your ENTIRE response using these exact section headers.
Table data is already pre-rendered by the system. Do NOT generate any tables yourself.

__SECTION_HEADLINE__
A single, punchy sentence highlighting the top portfolio signal from the data.

__SECTION_SUMMARY__
2-3 sentences summarizing the portfolio opportunity landscape AND why it matters to revenue.

__SECTION_SIGNALS__
• [Key signal 1 based strictly on data — include WHY it matters]
• [Key signal 2]
• [Key signal 3]

__SECTION_ACTIONS__
• [Specific named action 1 — who, what, by when]
• [Specific named action 2]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables.""",

    "ACCOUNT_PLAN_QUERY": """### RESPONSE CONTRACT — ACCOUNT PLAN QUERY
You MUST structure your ENTIRE response using these exact section headers.
Table data is already pre-rendered by the system. Do NOT generate any tables yourself.
The DATA block contains pre-computed recommendations. Use them. Do NOT ignore or paraphrase them away.

__SECTION_HEADLINE__
A single high-impact sentence about this account's most urgent situation.

__SECTION_SUMMARY__
Current situation (2 sentences): What is happening and why it matters to revenue.
Relationship status (1 sentence): Who is the recommended primary contact and their engagement state.
Risk (1 sentence): The single highest-risk item if left unaddressed.

__SECTION_SIGNALS__
• [REVENUE/RISK/ENGAGEMENT signal 1 — grounded in data from the DATA block]
• [Signal 2]
• [Signal 3]

__SECTION_ACTIONS__
• [Specific action 1 — name the contact, the action, and the timeline]
• [Action 2 — specific and evidence-backed]
• [Action 3]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables.""",

    "RISK_ANALYSIS_QUERY": """### RESPONSE CONTRACT — RISK ANALYSIS QUERY
You MUST structure your ENTIRE response using these exact section headers.
Table data is already pre-rendered by the system. Do NOT generate any tables yourself.

__SECTION_HEADLINE__
High-level impact statement: what revenue is at risk and the primary reason.

__SECTION_SUMMARY__
2 sentences on the primary risk landscape grounded in data.
1 sentence on the consequence of inaction (from [Risk Implications] in the DATA block).

__SECTION_SIGNALS__
• [Root cause signal 1 — why flagged, what evidence]
• [Signal 2]
• [Signal 3]

__SECTION_ACTIONS__
• [Specific named remediation step 1 — contact, action, urgency]
• [Remediation step 2]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables.""",

    "CONTACT_QUERY": """### RESPONSE CONTRACT — CONTACT / STAKEHOLDER RECOMMENDATION
You MUST structure your ENTIRE response using these exact section headers.
The DATA block contains a pre-computed [Primary Contact Recommendation] — use it directly.
Do NOT list all contacts. RECOMMEND the right contacts with full reasoning.

__SECTION_HEADLINE__
One sentence identifying who should be contacted and why — right now.

__SECTION_SUMMARY__
Situation (1 sentence): What is happening with this opportunity/account.
Recommendation (2 sentences): Name the primary contact, their role, why they are the priority, and their engagement risk.
Secondary contact (1 sentence): Who else should be looped in and why.

__SECTION_SIGNALS__
• [Engagement risk or relationship gap — specific, named, from data]
• [Signal 2 — e.g. single-threaded risk, cooling DM engagement]

__SECTION_ACTIONS__
• [Action 1 — exact contact name, specific action, timeframe, expected outcome]
• [Action 2 — secondary contact action]
• [Action 3 — what happens if NOT actioned]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables. Do NOT list all 110 contacts.""",

    "PIPELINE_SUMMARY_QUERY": """### RESPONSE CONTRACT — PIPELINE SUMMARY QUERY
You MUST structure your ENTIRE response using these exact section headers.
Table data is already pre-rendered by the system. Do NOT generate any tables yourself.

__SECTION_HEADLINE__
Single sentence on pipeline health and the most urgent forecast risk.

__SECTION_SUMMARY__
2-3 sentences summarizing pipeline metrics, stage concentrations, and forecast confidence.

__SECTION_SIGNALS__
• [Pipeline risk or concentration signal 1 — with data evidence]
• [Signal 2]

__SECTION_ACTIONS__
• [Pipeline action 1 — specific, named]
• [Action 2]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables.""",

    "ACTION_RECOMMENDATION_QUERY": """### RESPONSE CONTRACT — ACTION RECOMMENDATION QUERY
You MUST structure your ENTIRE response using these exact section headers.
The DATA block contains pre-computed [Next Best Actions] — use them directly, do NOT ignore them.

__SECTION_HEADLINE__
Single sentence naming the single highest-priority action to take today.

__SECTION_SUMMARY__
Why now (1 sentence): What data conditions make today the moment of action.
Consequence of inaction (1 sentence): What happens if these actions are not taken.

__SECTION_SIGNALS__
• [Most urgent signal — revenue or risk, with data evidence]
• [Signal 2]

__SECTION_ACTIONS__
• [Top priority action — named contact, specific step, urgency, expected outcome]
• [Action 2 — equally specific]
• [Action 3]

STRICT: Use the exact __SECTION_*__ headers above."""
}

MODE_PROMPT_MAP = {
    "executive": "Format your response as an **Executive Summary**. Keep it ultra-concise, headline-driven, and focused purely on top-level strategic and revenue impact. Avoid long details or detailed listings.",
    "operational": "Format your response as an **Operational Overview**. Maintain a balanced level of detail with task-oriented, actionable lists and clear steps. This is the default mode.",
    "analyst": "Format your response as a **Deep Diagnostic Analyst Report**. Provide full breakdowns, metrics-heavy aggregations, specific CRM hygiene gaps, and thorough risk analysis. Include all metadata."
}

JSON_PROMPT = """
You MUST output your response strictly as a valid JSON object matching the following structure:
{
  "query_type": "INTENT_TYPE",
  "headline": "A short, descriptive headline",
  "summary": "High-impact summary text",
  "data_summary": "Any structured statistics or lists formatted beautifully",
  "signals": ["key signal 1", "key signal 2"],
  "actions": ["recommended action 1", "recommended action 2"],
  "answer_confidence": "HIGH/MEDIUM/LOW",
  "integrity_score": "100%"
}
Do NOT wrap the JSON in markdown code blocks like ```json ... ```. Output raw JSON text only.
"""


import re as _re

def find_matching_account(query: str, engine):
    """Returns (account_id, opp_id) tuple. Either may be None."""
    accounts_df = engine.data.get('account')
    opps_df = engine.data.get('opportunity')

    query_clean = query.lower().strip()
    resolved_opp_id = None

    # Check if query contains an opportunity ID (e.g. OPP0023)
    opp_match = _re.search(r'opp\d+', query_clean)
    if opp_match and opps_df is not None:
        resolved_opp_id = opp_match.group(0).upper()
        matching_opp = opps_df[opps_df['Opp_ID'].str.upper() == resolved_opp_id]
        if not matching_opp.empty:
            return matching_opp.iloc[0]['Account_ID'], resolved_opp_id

    # First, try exact matching or substring matching of full name in query
    for _, row in accounts_df.iterrows():
        name = str(row['Account_Name']).lower()
        if name in query_clean:
            return row['Account_ID'], None

    # Second, try cleaning common suffixes
    suffixes = ["india", "bank", "ltd", "inc", "co", "pharmaceutical", "labs", "group", "corp", "corporation", "healthcare", "university", "hospital", "pharmaceuticals"]
    for _, row in accounts_df.iterrows():
        name = str(row['Account_Name']).lower()
        words = name.split()
        core_words = [w for w in words if w not in suffixes and len(w) > 2]
        if core_words:
            core_name = " ".join(core_words)
            if core_name in query_clean:
                return row['Account_ID'], None
            for cw in core_words:
                if cw in query_clean:
                    return row['Account_ID'], None
    return None, None

def classify_intent(query: str, account_id: Optional[str]) -> str:
    q = query.lower()
    
    # 1. GLOBAL_LIST_QUERY (Intersection check for deal terms + ranking/listing terms)
    has_deal_term = any(w in q for w in ["opportunity", "opportunities", "deal", "deals"])
    has_list_term = any(w in q for w in ["top", "largest", "big", "list", "show", "ranking", "rank", "best", "greatest", "which", "what", "closing"])
    if has_deal_term and has_list_term:
        return "GLOBAL_LIST_QUERY"
        
    # 2. RISK_ANALYSIS_QUERY
    risk_keywords = ["at risk", "risky", "jeopardy", "risk", "stalled", "blockers", "active risks", "critical risk", "danger"]
    if any(kw in q for kw in risk_keywords):
        return "RISK_ANALYSIS_QUERY"
        
    # 3. CONTACT_QUERY
    contact_keywords = ["contact", "stakeholder", "who to call", "people", "engagement levels", "decision maker", "dm", "contacts", "stakeholders"]
    if any(kw in q for kw in contact_keywords):
        return "CONTACT_QUERY"
        
    # 4. PIPELINE_SUMMARY_QUERY
    pipeline_keywords = ["pipeline", "forecast", "stage breakdown", "pipeline summary", "pipeline total", "pipeline forecast", "pipeline totals"]
    if any(kw in q for kw in pipeline_keywords):
        return "PIPELINE_SUMMARY_QUERY"
        
    # 5. ACTION_RECOMMENDATION_QUERY
    action_keywords = ["what should i do", "priority accounts", "action plan", "today", "recommendation", "next steps", "action recommendation", "what is today", "best action", "focus on today", "priorities today"]
    if any(kw in q for kw in action_keywords):
        return "ACTION_RECOMMENDATION_QUERY"
        
    # Default fallback
    if account_id:
        return "ACCOUNT_PLAN_QUERY"
    return "ACTION_RECOMMENDATION_QUERY"

# ─── Contract Protocol Helpers ─────────────────────────────────

def compute_table_for_intent(engine, intent: str, account_id: Optional[str] = None, query: str = "") -> Optional[dict]:
    """Compute structured table data for a given intent.
    Returns dict with 'columns' and 'rows', or None if no table applicable.
    Backend is the single source of truth for ranking/priority/truncation."""

    budget = RESPONSE_BUDGET.get(intent, {"max_rows": 15})
    max_rows = budget.get("max_rows", 15)

    if intent == "GLOBAL_LIST_QUERY":
        columns = ["Rank", "Opp_ID", "Opp_Name", "Account_ID", "Stage", "Amount_USD", "Probability_Pct", "Close_Date", "Priority_Band"]
        table_rows = []
        opps = engine.data.get('opportunity')
        if opps is not None and not opps.empty:
            open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])].copy()
            if not open_opps.empty:
                # Optional filter for deals closing in 30 days
                if "30 days" in query.lower() and "closing" in query.lower():
                    now = pd.Timestamp.now()
                    window_end = now + pd.Timedelta(days=30)
                    open_opps['Close_Date_Parsed'] = pd.to_datetime(open_opps['Close_Date'], errors='coerce')
                    if open_opps['Close_Date_Parsed'].dt.tz is not None:
                        open_opps['Close_Date_Parsed'] = open_opps['Close_Date_Parsed'].dt.tz_localize(None)
                    open_opps = open_opps[(open_opps['Close_Date_Parsed'] >= now) & (open_opps['Close_Date_Parsed'] <= window_end)].copy()
                
                priorities = []
                for _, r in open_opps.iterrows():
                    score = engine.calculate_opportunity_priority(r, "Standard")
                    priorities.append(score)
                open_opps['Priority_Score'] = priorities
                ranked = open_opps.sort_values(by='Priority_Score', ascending=False)
                all_scores = priorities
                for rank, (_, r) in enumerate(ranked.head(max_rows).iterrows(), 1):
                    raw_score = float(r['Priority_Score'])
                    table_rows.append({
                        "Rank": rank,
                        "Opp_ID": r['Opp_ID'],
                        "Opp_Name": r['Opp_Name'],
                        "Account_ID": r['Account_ID'],
                        "Stage": r['Stage'],
                        "Amount_USD": float(r['Amount_USD']) if pd.notna(r['Amount_USD']) else 0,
                        "Probability_Pct": int(r['Probability_Pct']) if pd.notna(r['Probability_Pct']) else 0,
                        "Close_Date": str(r['Close_Date'])[:10] if pd.notna(r['Close_Date']) else "",
                        "Priority_Band": HumanizedPriority.score_to_band(raw_score, all_scores)
                    })
        return {"columns": columns, "rows": table_rows} if table_rows else None

    elif intent == "CONTACT_QUERY":
        columns = ["Contact_ID", "Name", "Role", "Department", "Engagement_Level", "Last_Contact_Date"]
        table_rows = []
        contacts = engine.data.get('contact')
        if contacts is not None and not contacts.empty:
            df = contacts.copy()
            if account_id:
                # When account/opp is resolved: show only ranked top-3 contacts, not entire directory
                df = df[df['Account_ID'] == account_id]
                from reasoning_engine import StakeholderRanker
                # Determine opp stage for ranking
                opp_stage = "_default"
                opps = engine.data.get('opportunity')
                if opps is not None and not df.empty:
                    acc_opps = opps[(opps['Account_ID'] == account_id) & ~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
                    if not acc_opps.empty:
                        stage_order = ["Negotiation/Review", "Proposal/Price Quote", "Perception Analysis",
                                       "Value Proposition", "Id. Decision Makers", "Needs Analysis",
                                       "Qualification", "Prospecting"]
                        for s in stage_order:
                            if s in acc_opps['Stage'].values:
                                opp_stage = s
                                break
                ranked = StakeholderRanker.rank(df, opp_stage, max_contacts=3)
                for r in ranked:
                    table_rows.append({
                        "Contact_ID": r.contact_id,
                        "Name": r.name,
                        "Role": r.role,
                        "Department": r.department,
                        "Engagement_Level": r.engagement_level,
                        "Last_Contact_Date": r.last_contact_date,
                    })
            else:
                # Global contact query — show full list (existing behaviour)
                for _, r in df.iterrows():
                    name = f"{r.get('First_Name', '')} {r.get('Last_Name', '')}".strip()
                    table_rows.append({
                        "Contact_ID": r['Contact_ID'],
                        "Name": name,
                        "Role": r['Role'],
                        "Department": r.get('Department', 'N/A'),
                        "Engagement_Level": r.get('Engagement_Level', 'Unknown'),
                        "Last_Contact_Date": str(r.get('Last_Contact_Date', ''))[:10] if pd.notna(r.get('Last_Contact_Date')) else "Never"
                    })
        return {"columns": columns, "rows": table_rows} if table_rows else None

    elif intent == "PIPELINE_SUMMARY_QUERY":
        columns = ["Opp_ID", "Opp_Name", "Stage", "Amount_USD", "Probability_Pct", "Close_Date"]
        table_rows = []
        opps = engine.data.get('opportunity')
        if opps is not None and not opps.empty:
            open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])].copy()
            for _, r in open_opps.iterrows():
                table_rows.append({
                    "Opp_ID": r['Opp_ID'],
                    "Opp_Name": r['Opp_Name'],
                    "Stage": r['Stage'],
                    "Amount_USD": float(r['Amount_USD']) if pd.notna(r['Amount_USD']) else 0,
                    "Probability_Pct": int(r['Probability_Pct']) if pd.notna(r['Probability_Pct']) else 0,
                    "Close_Date": str(r['Close_Date'])[:10] if pd.notna(r['Close_Date']) else ""
                })
        return {"columns": columns, "rows": table_rows[:max_rows]} if table_rows else None

    elif intent == "ACCOUNT_PLAN_QUERY" and account_id:
        columns = ["Opp_ID", "Opp_Name", "Stage", "Amount_USD", "Probability_Pct", "Close_Date"]
        table_rows = []
        opps = engine.data.get('opportunity')
        if opps is not None and not opps.empty:
            acc_opps = opps[opps['Account_ID'] == account_id].copy()
            open_opps = acc_opps[~acc_opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
            for _, r in open_opps.iterrows():
                table_rows.append({
                    "Opp_ID": r['Opp_ID'],
                    "Opp_Name": r['Opp_Name'],
                    "Stage": r['Stage'],
                    "Amount_USD": float(r['Amount_USD']) if pd.notna(r['Amount_USD']) else 0,
                    "Probability_Pct": int(r['Probability_Pct']) if pd.notna(r['Probability_Pct']) else 0,
                    "Close_Date": str(r['Close_Date'])[:10] if pd.notna(r['Close_Date']) else ""
                })
        return {"columns": columns, "rows": table_rows[:max_rows]} if table_rows else None

    elif intent == "RISK_ANALYSIS_QUERY":
        columns = ["Rank", "Opp_ID", "Opp_Name", "Account_ID", "Stage", "Amount_USD", "Probability_Pct", "Close_Date"]
        table_rows = []
        opps = engine.data.get('opportunity')
        if opps is not None and not opps.empty:
            open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])].copy()
            if not open_opps.empty:
                # Risk-rank by low probability + high value (higher risk = lower prob * higher value)
                risk_scores = []
                for _, r in open_opps.iterrows():
                    try:
                        score = engine.calculate_risk_priority(r)
                    except (AttributeError, TypeError):
                        prob = float(r.get('Probability_Pct', 50)) if pd.notna(r.get('Probability_Pct')) else 50
                        amt = float(r.get('Amount_USD', 0)) if pd.notna(r.get('Amount_USD')) else 0
                        score = (100 - prob) * (amt / 100000)
                    risk_scores.append(score)
                open_opps['Risk_Score'] = risk_scores
                ranked = open_opps.sort_values(by='Risk_Score', ascending=False).head(max_rows)
                for rank, (_, r) in enumerate(ranked.iterrows(), 1):
                    table_rows.append({
                        "Rank": rank,
                        "Opp_ID": r['Opp_ID'],
                        "Opp_Name": r['Opp_Name'],
                        "Account_ID": r['Account_ID'],
                        "Stage": r['Stage'],
                        "Amount_USD": float(r['Amount_USD']) if pd.notna(r['Amount_USD']) else 0,
                        "Probability_Pct": int(r['Probability_Pct']) if pd.notna(r['Probability_Pct']) else 0,
                        "Close_Date": str(r['Close_Date'])[:10] if pd.notna(r['Close_Date']) else ""
                    })
        return {"columns": columns, "rows": table_rows} if table_rows else None

    # ACTION_RECOMMENDATION_QUERY and others — no table
    return None


def wrap_response_contract(
    intent: str,
    headline: str,
    summary: str,
    table_data: dict = None,
    signals: list = None,
    actions: list = None,
    crm_hygiene: list = None,
    confidence: dict = None,
) -> str:
    """Canonical serializer for the __SECTION_*__ streaming transport format.
    Produces the tagged envelope that the frontend ContractRenderer parses.
    This is a TRANSPORT FORMAT — the frontend normalizes it into application state after stream completion."""
    parts = []

    parts.append(f"__SECTION_INTENT__\n{intent}")
    parts.append(f"__SECTION_HEADLINE__\n{headline}")
    parts.append(f"__SECTION_SUMMARY__\n{summary}")

    if table_data is not None:
        parts.append(f"__SECTION_TABLE_DATA__\n{json.dumps(table_data)}")

    if signals:
        signal_text = "\n".join([f"• {s}" for s in signals])
        parts.append(f"__SECTION_SIGNALS__\n{signal_text}")

    if actions:
        action_text = "\n".join([f"• {a}" for a in actions])
        parts.append(f"__SECTION_ACTIONS__\n{action_text}")

    if crm_hygiene:
        hygiene_text = "\n".join([f"⚠️ {h}" for h in crm_hygiene])
        parts.append(f"__SECTION_CRM_HYGIENE__\n{hygiene_text}")

    if confidence:
        parts.append(f"__SECTION_CONFIDENCE__\n{json.dumps(confidence)}")

    parts.append("__SECTION_END__")

    return "\n".join(parts)


# ─── Deterministic Renderers (Contract-Aligned) ───────────────

def generate_deterministic_global_list(engine, mode: str, format: str, query: str = "") -> str:
    confidence = engine.classify_answer_confidence()
    gaps = engine.audit_crm_hygiene()
    table_data = compute_table_for_intent(engine, "GLOBAL_LIST_QUERY", query=query)

    # Phase 4: Strategic synthesis layer
    synthesis = generate_strategic_synthesis(engine, "GLOBAL_LIST_QUERY", crm_gaps=gaps)
    row_count = len(table_data["rows"]) if table_data else 0

    headline = f"Top {row_count} Prioritized Opportunities — Portfolio Intelligence"

    # "Why This Matters" enriched summary
    base_summary = {
        "executive": "Ultra-concise view of top-level revenue deals.",
        "analyst": f"Full diagnostic breakdown: {row_count} top deals ranked by priority band.",
    }.get(mode, f"Actionable view of {row_count} prioritized active deals.")
    if synthesis.why_this_matters:
        summary = f"{base_summary} {synthesis.why_this_matters}"
    else:
        summary = base_summary

    # Classified signals (revenue-first, CRM-last)
    signals = synthesis.get_all_signals_for_display(RESPONSE_BUDGET["GLOBAL_LIST_QUERY"]["max_signals"])
    actions = synthesis.actions
    confidence_data = {
        "score": "100%",
        "status": "100% Grounded (Direct facts from Excel)",
        "sources": ["Opportunity Table", "Account Table"]
    }

    if format == "json":
        return json.dumps({
            "query_type": "GLOBAL_LIST_QUERY",
            "headline": headline,
            "summary": summary,
            "table_data": table_data["rows"] if table_data else [],
            "signals": signals,
            "actions": actions,
            "answer_confidence": confidence,
            "integrity_score": "100%"
        })
    else:
        # CRM hygiene signals are secondary — only non-classified gaps go to crm_hygiene section
        crm_only = [g for g in (gaps or []) if SignalClassifier.classify(g).value == "CRM"][:2]
        return wrap_response_contract(
            intent="GLOBAL_LIST_QUERY",
            headline=headline,
            summary=summary,
            table_data=table_data,
            signals=signals,
            actions=actions,
            crm_hygiene=crm_only if crm_only else None,
            confidence=confidence_data
        )

def generate_deterministic_contacts(engine, account_id: Optional[str], mode: str, format: str, query: str = "") -> str:
    confidence = engine.classify_answer_confidence(account_id)
    gaps = engine.audit_crm_hygiene(account_id)
    table_data = compute_table_for_intent(engine, "CONTACT_QUERY", account_id, query=query)

    # Phase 4: Strategic synthesis
    synthesis = generate_strategic_synthesis(engine, "CONTACT_QUERY", account_id, crm_gaps=gaps)
    contact_count = len(table_data["rows"]) if table_data else 0

    headline = f"Stakeholder Directory: {contact_count} contacts mapped"

    base_summary = {
        "executive": "Ultra-concise overview of mapped key stakeholders and active relationship gaps.",
        "analyst": f"Full diagnostic contact report: {contact_count} contacts with engagement analysis.",
    }.get(mode, "Actionable overview of stakeholders and next recommended contact.")
    if synthesis.why_this_matters:
        summary = f"{base_summary} {synthesis.why_this_matters}"
    else:
        summary = base_summary

    signals = synthesis.get_all_signals_for_display(RESPONSE_BUDGET["CONTACT_QUERY"]["max_signals"])
    actions = synthesis.actions
    confidence_data = {
        "score": "100%",
        "status": "100% Grounded (Direct facts from Excel)",
        "sources": ["Contact Table"]
    }

    if format == "json":
        return json.dumps({
            "query_type": "CONTACT_QUERY",
            "headline": headline,
            "summary": summary,
            "table_data": table_data["rows"] if table_data else [],
            "signals": [s for s in signals],
            "actions": actions,
            "answer_confidence": confidence,
            "integrity_score": "100%"
        })
    else:
        crm_only = [g for g in (gaps or []) if SignalClassifier.classify(g).value == "CRM"][:2]
        return wrap_response_contract(
            intent="CONTACT_QUERY",
            headline=headline,
            summary=summary,
            table_data=table_data,
            signals=signals if signals else None,
            actions=actions,
            crm_hygiene=crm_only if crm_only else None,
            confidence=confidence_data
        )

def generate_deterministic_pipeline(engine, mode: str, format: str, query: str = "") -> str:
    confidence = engine.classify_answer_confidence()
    gaps = engine.audit_crm_hygiene()
    table_data = compute_table_for_intent(engine, "PIPELINE_SUMMARY_QUERY", query=query)

    # Phase 4: Strategic synthesis
    synthesis = generate_strategic_synthesis(engine, "PIPELINE_SUMMARY_QUERY", crm_gaps=gaps)

    # Compute aggregate stats
    total_value = 0
    weighted_value = 0
    opps = engine.data.get('opportunity')
    if opps is not None and not opps.empty:
        open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
        total_value = float(open_opps['Amount_USD'].sum()) if not open_opps.empty else 0
        weighted_value = float((open_opps['Amount_USD'] * open_opps['Probability_Pct'] / 100.0).sum()) if not open_opps.empty else 0

    deal_count = len(table_data["rows"]) if table_data else 0
    fmt_total = HumanizedPriority.format_currency(total_value)
    fmt_weighted = HumanizedPriority.format_currency(weighted_value)

    headline = f"Pipeline Intelligence: {fmt_total} total | {fmt_weighted} weighted forecast"

    base_summary = {
        "executive": f"Ultra-concise view: {fmt_total} total pipeline, {fmt_weighted} weighted forecast.",
        "analyst": f"Full diagnostic pipeline: {fmt_total} total | {fmt_weighted} weighted | {deal_count} active deals.",
    }.get(mode, f"Actionable pipeline overview: {fmt_total} total open pipeline | {fmt_weighted} weighted forecast | {deal_count} active deals.")
    if synthesis.why_this_matters:
        summary = f"{base_summary} {synthesis.why_this_matters}"
    else:
        summary = base_summary

    signals = synthesis.get_all_signals_for_display(RESPONSE_BUDGET["PIPELINE_SUMMARY_QUERY"]["max_signals"])
    actions = synthesis.actions
    confidence_data = {
        "score": "100%",
        "status": "100% Grounded (Direct facts from Excel)",
        "sources": ["Opportunity Table"]
    }

    if format == "json":
        return json.dumps({
            "query_type": "PIPELINE_SUMMARY_QUERY",
            "headline": headline,
            "summary": summary,
            "total_pipeline": total_value,
            "weighted_forecast": weighted_value,
            "table_data": table_data["rows"] if table_data else [],
            "signals": signals,
            "actions": actions,
            "answer_confidence": confidence,
            "integrity_score": "100%"
        })
    else:
        crm_only = [g for g in (gaps or []) if SignalClassifier.classify(g).value == "CRM"][:2]
        return wrap_response_contract(
            intent="PIPELINE_SUMMARY_QUERY",
            headline=headline,
            summary=summary,
            table_data=table_data,
            signals=signals,
            actions=actions,
            crm_hygiene=crm_only if crm_only else None,
            confidence=confidence_data
        )

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def generate_stream():
        start_time = asyncio.get_event_loop().time()

        # Yield Phase 1 status
        yield "sys_meta_log|[SYS_LOG] Initializing Orchestration Planner (Phase 1)...\n\n"
        await asyncio.sleep(0.05)
        
        # Execute Phase 1: Planner
        try:
            p1_json = await run_phase1_planner(request.query, http_client)
            from data_retrieval_layer import Phase1Output
            p1_parsed = Phase1Output.from_json(p1_json)
            intent = p1_parsed.extracted_intent
            yield f"sys_meta_log|[SYS_LOG] Intent identified: {intent}\n\n"
        except Exception as e:
            print(f"[API ERROR] Phase 1 failed: {e}")
            p1_json = {
                "extracted_intent": "ACTION_RECOMMENDATION",
                "query_parameters": {"target_accounts": []}
            }
            intent = "ACTION_RECOMMENDATION"
            yield "sys_meta_log|[SYS_LOG] Planner failed. Initializing baseline intent routing...\n\n"
        await asyncio.sleep(0.05)

        # Execute Phase 2: Data Retrieval
        yield "sys_meta_log|[SYS_LOG] Querying CRM Database Engine (Phase 2)...\n\n"
        await asyncio.sleep(0.05)
        try:
            retrieved_text = run_phase2_retrieval(engine, p1_json)
            # Resolve accounts for telemetry / table context
            from data_retrieval_layer import _resolve_account_ids, Phase1Output
            p1_parsed = Phase1Output.from_json(p1_json)
            target_accounts = p1_parsed.target_accounts or []
            account_ids = _resolve_account_ids(engine, target_accounts)
            account_id = account_ids[0] if account_ids else None
            
            if account_id:
                yield f"sys_meta_log|[SYS_LOG] Extracted CRM records for Account: {account_id}\n\n"
            else:
                yield "sys_meta_log|[SYS_LOG] Extracted global portfolio telemetry.\n\n"
        except Exception as e:
            print(f"[API ERROR] Phase 2 failed: {e}")
            retrieved_text = "[DATA_ERROR] Ingestion pipeline failure."
            account_id = None
        await asyncio.sleep(0.05)

        # Pre-compute table data for UI
        table_data = compute_table_for_intent(engine, intent, account_id, request.query)

        # Yield deterministic contract tags to UI before the narrative stream
        yield f"__SECTION_INTENT__\n{intent}\n"
        if table_data:
            yield f"__SECTION_TABLE_DATA__\n{json.dumps(table_data)}\n"

        # Execute Phase 3: Core Reasoning Engine
        yield "sys_meta_log|[SYS_LOG] Launching Core Strategic Reasoner (Phase 3)...\n\n"
        await asyncio.sleep(0.05)
        try:
            sip_json = await run_phase3_reasoner(retrieved_text, http_client)
            overall_pct = sip_json.get("confidence", {}).get("overall_pct") or sip_json.get("confidence", {}).get("pct") or 80
            yield f"sys_meta_log|[SYS_LOG] Strategic trace generated. Confidence: {overall_pct}%\n\n"
        except Exception as e:
            print(f"[API ERROR] Phase 3 failed: {e}")
            sip_json = {
                "headline": "Strategic trace unavailable",
                "situation_summary": "Core reasoning trace defaulted due to processing error.",
                "confidence": {"overall_pct": 50}
            }
            yield "sys_meta_log|[SYS_LOG] Reasoner trace defaulted.\n\n"
        await asyncio.sleep(0.05)

        # Execute Phase 4: Narrative Stream
        yield "sys_meta_log|[SYS_LOG] Commencing Strategic Narrative delivery...\n\n"
        await asyncio.sleep(0.05)
        
        async for token in run_phase4_narrative_stream(sip_json, request.query, http_client):
            yield token

        end_time = asyncio.get_event_loop().time()
        latency_ms = (end_time - start_time) * 1000
        print(f"[TELEMETRY] Four-Phase Agentic Route | Intent: {intent} | Latency: {latency_ms:.2f}ms")

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


# ─── New Tactical Endpoints ───────────────────────────────────

@app.get("/api/insights")
async def get_insights():
    """Analyzes the account portfolio and pipeline to generate proactive insights, alerts, and suggestions using rules + LLM."""
    from datetime import datetime
    try:
        accounts = engine.data.get('account')
        opps = engine.data.get('opportunity')
        contacts = engine.data.get('contact')
        activities = engine.data.get('activity')
        cases = engine.data.get('case')

        insights_list = []
        
        # 1. Critical Support Cases on key/strategic accounts
        if cases is not None and not cases.empty:
            open_cases = cases[cases['Status'] != 'Closed']
            critical_cases = open_cases[open_cases['Severity'].isin(['Critical', 'High'])]
            for _, c_row in critical_cases.iterrows():
                acc_name = "Unknown"
                acc_id = c_row['Account_ID']
                if accounts is not None:
                    acc_df = accounts[accounts['Account_ID'] == acc_id]
                    if not acc_df.empty:
                        acc_name = acc_df.iloc[0]['Account_Name']
                
                insights_list.append({
                    "id": f"ins-case-{c_row['Case_ID']}",
                    "type": "critical",
                    "title": f"Critical Case: {c_row['Subject']}",
                    "description": f"Unresolved critical case found on {acc_name} ({acc_id}). Case Owner: {c_row.get('Owner', 'N/A')}.",
                    "targetAccount": acc_name,
                    "targetAccountId": acc_id,
                    "suggestedAction": f"Escalate case {c_row['Case_ID']} to engineering team immediately."
                })

        # 2. Single-threaded Deals
        # High value deals (> $100K) in advanced stages (Negotiation/Review, Proposal/Price Quote, Perception Analysis) with <= 1 contact
        if opps is not None and not opps.empty:
            advanced_opps = opps[opps['Stage'].isin(['Negotiation/Review', 'Proposal/Price Quote', 'Perception Analysis']) & (opps['Amount_USD'] >= 100000)]
            for _, o_row in advanced_opps.iterrows():
                acc_id = o_row['Account_ID']
                acc_contacts = contacts[contacts['Account_ID'] == acc_id] if contacts is not None else pd.DataFrame()
                if len(acc_contacts) <= 1:
                    acc_name = "Unknown"
                    if accounts is not None:
                        acc_df = accounts[accounts['Account_ID'] == acc_id]
                        if not acc_df.empty:
                            acc_name = acc_df.iloc[0]['Account_Name']
                    
                    insights_list.append({
                        "id": f"ins-opp-{o_row['Opp_ID']}",
                        "type": "warning",
                        "title": f"Single-Threaded Deal: {o_row['Opp_Name']}",
                        "description": f"Deal '{o_row['Opp_Name']}' (${o_row['Amount_USD']:,.0f}) is in {o_row['Stage']} with only {len(acc_contacts)} contact mapped. High risk of stall.",
                        "targetAccount": acc_name,
                        "targetAccountId": acc_id,
                        "suggestedAction": f"Identify and engage additional stakeholders (e.g. Finance or procurement) for {acc_name}."
                    })

        # 3. Stalled Strategic Account (no activity in 30 days)
        if accounts is not None and not accounts.empty:
            strat_accounts = accounts[accounts['Account_Tier'] == 'Strategic']
            for _, acc_row in strat_accounts.iterrows():
                acc_id = acc_row['Account_ID']
                acc_name = acc_row['Account_Name']
                acc_activities = activities[activities['Account_ID'] == acc_id] if activities is not None else pd.DataFrame()
                
                days_ago = 999
                if not acc_activities.empty:
                    max_date = pd.to_datetime(acc_activities['Activity_Date']).max()
                    delta = datetime.now() - max_date.to_pydatetime()
                    days_ago = delta.days
                
                if days_ago > 30:
                    insights_list.append({
                        "id": f"ins-stale-{acc_id}",
                        "type": "warning",
                        "title": "Stalled Strategic Account",
                        "description": f"Strategic account {acc_name} has had no activities logged for {days_ago if days_ago < 900 else 'over 60'} days.",
                        "targetAccount": acc_name,
                        "targetAccountId": acc_id,
                        "suggestedAction": f"Schedule a check-in call with the primary contact at {acc_name}."
                    })

        # 4. Upsell Opportunities: High Revenue, Low Pipeline
        if accounts is not None and not accounts.empty:
            for _, acc_row in accounts.iterrows():
                acc_id = acc_row['Account_ID']
                acc_name = acc_row['Account_Name']
                revenue = acc_row.get('Annual_Revenue_USD', 0)
                if pd.notna(revenue) and revenue > 10000000: # > 10M
                    acc_opps = opps[opps['Account_ID'] == acc_id] if opps is not None else pd.DataFrame()
                    open_opps = acc_opps[~acc_opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
                    total_pipe = open_opps['Amount_USD'].sum() if not open_opps.empty else 0
                    
                    if total_pipe < 50000: # low pipeline (< 50K) for a $10M+ revenue account
                        insights_list.append({
                            "id": f"ins-upsell-{acc_id}",
                            "type": "opportunity",
                            "title": "Upsell Opportunity",
                            "description": f"Account {acc_name} has high annual revenue (${revenue:,.0f}) but only ${total_pipe:,.0f} in active pipeline.",
                            "targetAccount": acc_name,
                            "targetAccountId": acc_id,
                            "suggestedAction": "Initiate discovery session to discuss additional product lines or services."
                        })

        # 5. CSAT Drop
        if cases is not None and not cases.empty:
            avg_csats = cases.groupby('Account_ID')['CSAT_Score'].mean().reset_index()
            low_csats = avg_csats[avg_csats['CSAT_Score'] < 3.0]
            for _, csat_row in low_csats.iterrows():
                acc_id = csat_row['Account_ID']
                acc_name = "Unknown"
                if accounts is not None:
                    acc_df = accounts[accounts['Account_ID'] == acc_id]
                    if not acc_df.empty:
                        acc_name = acc_df.iloc[0]['Account_Name']
                
                insights_list.append({
                    "id": f"ins-csat-{acc_id}",
                    "type": "critical",
                    "title": f"Low Account Satisfaction",
                    "description": f"Average customer support CSAT for {acc_name} is critical: {csat_row['CSAT_Score']:.1f}/5.",
                    "targetAccount": acc_name,
                    "targetAccountId": acc_id,
                    "suggestedAction": "Arrange an executive outreach or service recovery review meeting."
                })

        # Calculate a pipeline quality score based on number of critical or warning insights
        # E.g. base is 100, deduct 10 for each warning, 20 for each critical, min 20
        warn_count = sum(1 for x in insights_list if x['type'] == 'warning')
        crit_count = sum(1 for x in insights_list if x['type'] == 'critical')
        pipe_score = max(20, 100 - (warn_count * 10) - (crit_count * 20))

        # Generate a Briefing using the LLM
        # Formulate a condensed summary of the pipeline to send to the LLM
        pipeline_summary_text = ""
        if opps is not None and not opps.empty:
            open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
            total_open = open_opps['Amount_USD'].sum()
            avg_prob = open_opps['Probability_Pct'].mean()
            pipeline_summary_text += f"Total Open Pipeline: ${total_open:,.2f}. Average Close Probability: {avg_prob:.1f}%. "
            stage_groups = open_opps.groupby('Stage')['Amount_USD'].sum().to_dict()
            pipeline_summary_text += "Stages: " + ", ".join([f"{k}: ${v:,.0f}" for k, v in stage_groups.items()])
        else:
            pipeline_summary_text += "No open opportunities in pipeline."

        # Alert context
        alert_summary = f"Anomalies detected: {crit_count} Critical issue(s), {warn_count} Warning issue(s)."

        llm_prompt = f"""
You are the APEX Strategic Core engine.
Analyze the following sales pipeline health data and anomalies, and write a high-level executive strategic briefing.
Keep it strictly under 3 sentences. Be punchy, actionable, and tactical.

Pipeline Context:
{pipeline_summary_text}

Anomalies Detected:
{alert_summary}

Write a 2-3 sentence strategic briefing summarizing the key pipeline risks and focus areas for today.
"""
        briefing = "Pipeline health nominal. Operational indicators show stable progression across main account tiers."
        try:
            res = await http_client.post(
                LLM_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": llm_prompt,
                    "stream": False
                },
                timeout=5.0
            )
            if res.status_code == 200:
                data = res.json()
                if "response" in data:
                    briefing = data["response"].strip()
        except Exception as e:
            print(f"LLM briefing error: {e}")
            if crit_count > 0:
                briefing = f"Urgent action required: {crit_count} critical issues are currently impacting key accounts, including unresolved tickets and customer satisfaction drops. Direct immediate focus to account stabilization and risk mitigation."
            elif warn_count > 0:
                briefing = "Pipeline remains active but shows signs of deal friction. Several high-value deals are single-threaded or stalling in middle stages. Prioritize multi-threading and relationship expansion."
            else:
                briefing = "All pipeline parameters are nominal. Focus on standard deal progression and Q4 pipeline generation."

        return {
            "insights": insights_list,
            "pipeline_quality_score": pipe_score,
            "briefing": briefing
        }
    except Exception as e:
        print(f"Insights Endpoint Error: {e}")
        return {
            "insights": [],
            "pipeline_quality_score": 100,
            "briefing": "Unable to compute intelligence briefing. Verification in progress."
        }

@app.get("/api/health")
async def health_check():
    """System health check — pinged by the frontend sidebar every 15s."""
    return {
        "status": "operational",
        "engine": "loaded",
        "sheets": list(engine.data.keys()),
    }

@app.get("/api/accounts/enriched")
async def get_enriched_accounts():
    """Returns all accounts with computed health scores, pipeline values, and last activity dates."""
    try:
        enriched = engine.get_enriched_accounts_list()
        return enriched
    except Exception as e:
        return []

@app.get("/api/pipeline/summary")
async def get_pipeline_summary():
    """Returns aggregated pipeline data grouped by stage."""
    try:
        analysis = engine.get_pipeline_analysis()
        return analysis
    except Exception as e:
        return {"total_value": 0, "weighted_value": 0, "deal_count": 0, "stage_summary": {}}

@app.get("/api/accounts/{account_id}/details")
async def get_account_details(account_id: str):
    """Returns real JSON details for a specific account."""
    try:
        details = engine.get_account_details_json(account_id)
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Existing Endpoints ───────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Account Planner Agent API is running"}

@app.get("/api/accounts")
async def get_accounts():
    if 'account' not in engine.data:
        return []
    return engine.data['account'][['Account_ID', 'Account_Name', 'Account_Tier']].to_dict('records')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
