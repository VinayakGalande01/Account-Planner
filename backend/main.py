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

You are the dedicated AI companion for account managers, sales executives, and revenue teams. Your entire purpose is to remove the daily stress and manual grind from account planning so that sales professionals can focus on what actually matters: building relationships and closing business.

You always respond in a warm, clear, human tone — like a brilliant colleague who has already done all the homework before the meeting. No jargon dumps. No data walls. Every response is structured so anyone can scan it in 30 seconds and know exactly what to do next.

## 🔴 CRITICAL GROUNDING RULES (NO HALLUCINATIONS)
1. You are strictly a database-grounded agent. You MUST NEVER under any circumstances invent, assume, or hallucinate any numbers, names, amounts, or timelines that are not explicitly present in the provided DATA block.
2. If the user asks a question about an account, a deal, a contact, or a support case, and the data is NOT present in the provided DATA block, you MUST respond exactly: "I do not have access to that specific information in my current data context." Do not make up dummy values.
3. If the user asks for a comparison, review, or chronological history, base it 100% on the logged dates and notes in the provided [Opportunities], [Contacts], [Activities], and [Cases] tables. If no dates or details are present, say so explicitly.
4. When a global query is made (such as "give me top 10 opportunities" or "list jeopardy accounts"), look strictly at the [Global Accounts Overview], [Top Opportunities (Global)], [Jeopardy Accounts Summary], and [Open Critical & High Severity Support Cases] sections. Do NOT guess or hallucinate any opportunities or accounts outside of what is explicitly detailed in those global summaries.
5. Your output MUST NEVER contain internal orchestration leakage or scaffolding keywords like "Scan first", "Pulling data", "Assembling response", or reasoning scaffolding. Output ONLY final operational intelligence.
6. You MUST append the following exact metadata block at the very end of EVERY response you generate:
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📊 APEX GROUNDING & INTEGRITY SCORE: [100% / 50% / 0%]
     • Sources: [E.g., Account Table (ACC001), Opportunity Table (OPP084)]
     • Status: [E.g., 100% Grounded (Direct facts from Excel) OR 50% Hybrid (Excel facts + strategic reasoning) OR 0% Unfounded (Data missing from database)]
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
2-3 sentences summarizing the portfolio opportunity landscape.

__SECTION_SIGNALS__
• [Key signal 1 based strictly on data]
• [Key signal 2]
• [Key signal 3]

__SECTION_ACTIONS__
• [Recommended action 1]
• [Recommended action 2]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables, critical alerts, or any other sections.""",

    "ACCOUNT_PLAN_QUERY": """### RESPONSE CONTRACT — ACCOUNT PLAN QUERY
You MUST structure your ENTIRE response using these exact section headers.
Table data is already pre-rendered by the system. Do NOT generate any tables yourself.

__SECTION_HEADLINE__
A warm, high-impact sentence about the account's overall state.

__SECTION_SUMMARY__
Comprehensive executive summary: health, engagement, risks, and growth signals in 3-5 sentences.

__SECTION_SIGNALS__
• [Key risk or opportunity signal 1]
• [Key signal 2]
• [Key signal 3]

__SECTION_ACTIONS__
• [Next best action 1 with ownership and timeframe]
• [Action 2]
• [Action 3]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables.""",

    "RISK_ANALYSIS_QUERY": """### RESPONSE CONTRACT — RISK ANALYSIS QUERY
You MUST structure your ENTIRE response using these exact section headers.
Table data is already pre-rendered by the system. Do NOT generate any tables yourself.

__SECTION_HEADLINE__
High-level impact statement about portfolio risk exposure.

__SECTION_SUMMARY__
2-3 sentences summarizing the primary risk landscape and root causes.

__SECTION_SIGNALS__
• [Root cause signal 1 — why flagged]
• [Signal 2]
• [Signal 3]

__SECTION_ACTIONS__
• [Concrete remediation step 1]
• [Remediation step 2]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables.""",

    "CONTACT_QUERY": """### RESPONSE CONTRACT — CONTACT / STAKEHOLDER QUERY
You MUST structure your ENTIRE response using these exact section headers.
Table data is already pre-rendered by the system. Do NOT generate any tables yourself.

__SECTION_HEADLINE__
Concise statement about stakeholder relationship status.

__SECTION_SUMMARY__
2-3 sentences on engagement depth, decision-maker access, and relationship gaps.

__SECTION_SIGNALS__
• [Engagement gap or risk signal 1]
• [Signal 2]

__SECTION_ACTIONS__
• [Recommended next touch — exact contact, talking point]
• [Action 2]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables.""",

    "PIPELINE_SUMMARY_QUERY": """### RESPONSE CONTRACT — PIPELINE SUMMARY QUERY
You MUST structure your ENTIRE response using these exact section headers.
Table data is already pre-rendered by the system. Do NOT generate any tables yourself.

__SECTION_HEADLINE__
Single sentence on pipeline health and forecast positioning.

__SECTION_SUMMARY__
2-3 sentences summarizing pipeline metrics, stage concentrations, and forecast confidence.

__SECTION_SIGNALS__
• [Pipeline risk or concentration signal 1]
• [Signal 2]

__SECTION_ACTIONS__
• [Pipeline action 1]
• [Action 2]

STRICT: Use the exact __SECTION_*__ headers above. Do NOT generate tables.""",

    "ACTION_RECOMMENDATION_QUERY": """### RESPONSE CONTRACT — ACTION RECOMMENDATION QUERY
You MUST structure your ENTIRE response using these exact section headers.

__SECTION_HEADLINE__
Single sentence on today's operational priorities.

__SECTION_SUMMARY__
2-3 sentences on strategic context — why these priorities matter today.

__SECTION_SIGNALS__
• [Why this matters — pending close dates, revenue exposure, etc.]
• [Signal 2]

__SECTION_ACTIONS__
• [Top priority action 1]
• [Action 2]
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


def find_matching_account(query: str, accounts_df):
    query_clean = query.lower().strip()
    
    # First, try exact matching or substring matching of full name in query
    for _, row in accounts_df.iterrows():
        name = str(row['Account_Name']).lower()
        if name in query_clean:
            return row['Account_ID']
            
    # Second, try cleaning common suffixes and checking if the core name is in the query
    suffixes = ["india", "bank", "ltd", "inc", "co", "pharmaceutical", "labs", "group", "corp", "corporation", "healthcare", "university", "hospital", "pharmaceuticals"]
    for _, row in accounts_df.iterrows():
        name = str(row['Account_Name']).lower()
        words = name.split()
        core_words = [w for w in words if w not in suffixes and len(w) > 2]
        if core_words:
            core_name = " ".join(core_words)
            if core_name in query_clean:
                return row['Account_ID']
            # Check individual core words (if unique enough)
            for cw in core_words:
                if cw in query_clean:
                    return row['Account_ID']
    return None

def classify_intent(query: str, account_id: Optional[str]) -> str:
    q = query.lower()
    
    # 1. GLOBAL_LIST_QUERY (Intersection check for deal terms + ranking/listing terms)
    has_deal_term = any(w in q for w in ["opportunity", "opportunities", "deal", "deals"])
    has_list_term = any(w in q for w in ["top", "largest", "big", "list", "show", "ranking", "rank", "best", "greatest"])
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

def compute_table_for_intent(engine, intent: str, account_id: Optional[str] = None) -> Optional[dict]:
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
                df = df[df['Account_ID'] == account_id]
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

def generate_deterministic_global_list(engine, mode: str, format: str) -> str:
    confidence = engine.classify_answer_confidence()
    gaps = engine.audit_crm_hygiene()
    table_data = compute_table_for_intent(engine, "GLOBAL_LIST_QUERY")

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

def generate_deterministic_contacts(engine, account_id: Optional[str], mode: str, format: str) -> str:
    confidence = engine.classify_answer_confidence(account_id)
    gaps = engine.audit_crm_hygiene(account_id)
    table_data = compute_table_for_intent(engine, "CONTACT_QUERY", account_id)

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

def generate_deterministic_pipeline(engine, mode: str, format: str) -> str:
    confidence = engine.classify_answer_confidence()
    gaps = engine.audit_crm_hygiene()
    table_data = compute_table_for_intent(engine, "PIPELINE_SUMMARY_QUERY")

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
    query = request.query.lower()
    
    # 1. Identify Account using robust matcher
    accounts_df = engine.data.get('account')
    account_id = find_matching_account(request.query, accounts_df)

    # 2. Intent Routing & Context Optimization
    intent = classify_intent(request.query, account_id)
    response_mode = request.response_mode or "operational"
    response_format = request.response_format or "markdown"
    
    # 2b. Pre-compute strategic synthesis (deterministic, fast)
    crm_gaps = engine.audit_crm_hygiene(account_id)
    synthesis = generate_strategic_synthesis(engine, intent, account_id, response_mode, crm_gaps)

    # 2c. Pre-compute table data for LLM context curation
    table_data_for_context = compute_table_for_intent(engine, intent, account_id)

    # 3. Deterministic Routing Decision
    requires_llm = True
    if intent in ["GLOBAL_LIST_QUERY", "CONTACT_QUERY", "PIPELINE_SUMMARY_QUERY"]:
        # Only use LLM if user explicitly asks for qualitative evaluation
        reasoning_keywords = ["why", "suggest", "explain", "how", "reason", "strategic", "insight", "recommend", "recommends", "recommending", "suggests", "suggesting", "explains", "explaining"]
        query_clean_words = set(query.replace("?", " ").replace("!", " ").replace(".", " ").replace(",", " ").split())
        if not any(kw in query_clean_words for kw in reasoning_keywords):
            requires_llm = False

    # Assemble Split Prompt if using LLM
    assembled_system = ""
    final_query = ""
    if requires_llm:
        assembled_system = f"{BASE_PROMPT}\n\n{INTENT_PROMPT_MAP[intent]}\n\n{OUTPUT_CONTRACT_MAP[intent]}\n\n{MODE_PROMPT_MAP[response_mode]}"
        if response_format == "json":
            assembled_system += f"\n\n{JSON_PROMPT}"
        # Phase 4: LLM receives CURATED synthesis, NOT raw CRM dumps
        curated_context = curate_llm_context(engine, intent, account_id, synthesis, table_data_for_context)
        final_query = f"QUERY: {request.query}\n\nDATA:\n{curated_context}"
    
    async def generate_stream():
        start_time = asyncio.get_event_loop().time()

        # ── Phase 1: Meta Logs (before any __SECTION_* tags) ──
        yield "sys_meta_log|[SYS_LOG] Initializing Intelligence Node...\n\n"
        await asyncio.sleep(0.1)
        if account_id:
            yield f"sys_meta_log|[SYS_LOG] Context loaded for Account ID: {account_id}\n\n"
        else:
            yield "sys_meta_log|[SYS_LOG] Global portfolio context active.\n\n"
        await asyncio.sleep(0.1)

        # ── Phase 2: Deterministic Path (full contract, atomic) ──
        if not requires_llm:
            yield "sys_meta_log|[SYS_LOG] Instantly rendering deterministic context...\n\n"
            await asyncio.sleep(0.1)

            if intent == "GLOBAL_LIST_QUERY":
                resp_text = generate_deterministic_global_list(engine, response_mode, response_format)
            elif intent == "CONTACT_QUERY":
                resp_text = generate_deterministic_contacts(engine, account_id, response_mode, response_format)
            else:  # PIPELINE_SUMMARY_QUERY
                resp_text = generate_deterministic_pipeline(engine, response_mode, response_format)

            yield resp_text

            end_time = asyncio.get_event_loop().time()
            latency_ms = (end_time - start_time) * 1000
            print(f"[TELEMETRY] Intent: {intent} | Mode: {response_mode} | Route: DETERMINISTIC | Latency: {latency_ms:.2f}ms | Fallback: False")
            return

        # ── Phase 3: LLM Path (Hybrid Streaming) ──
        yield "sys_meta_log|[SYS_LOG] Awaiting neural inference...\n\n"
        await asyncio.sleep(0.1)

        # Step 3a: Yield deterministic contract sections atomically
        # Intent metadata
        yield f"__SECTION_INTENT__\n{intent}\n"

        # Pre-compute table data (backend truth — tables NEVER stream row-by-row)
        table_data = compute_table_for_intent(engine, intent, account_id)
        if table_data:
            yield f"__SECTION_TABLE_DATA__\n{json.dumps(table_data)}\n"

        # Step 3b: Stream LLM narrative (headline, summary, signals, actions)
        fallback_active = False
        try:
            print(f"Sending request to {LLM_URL}...")
            custom_timeout = httpx.Timeout(connect=3.0, read=1800.0, write=10.0, pool=30.0)
            async with http_client.stream(
                "POST",
                LLM_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": f"System: {assembled_system}\n\nUser: {final_query}",
                    "stream": True
                },
                timeout=custom_timeout
            ) as response:
                async for chunk in response.aiter_lines():
                    if chunk:
                        try:
                            data = json.loads(chunk)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            fallback_active = True
            print(f"Error calling primary LLM ({MODEL_NAME}): {str(e)}")
            print("Attempting to connect to local fallback Ollama (http://localhost:11434/api/generate)...")
            yield "\nsys_meta_log|[SYS_LOG] Primary inference failed. Activating local fallback node...\n\n"
            await asyncio.sleep(0.1)

            local_model = MODEL_NAME
            try:
                resp = await http_client.get("http://localhost:11434/api/tags", timeout=2.0)
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    if models:
                        available_names = [m["name"] for m in models]
                        matched_model = None
                        for name in available_names:
                            if MODEL_NAME == name or MODEL_NAME.split(":")[0] == name.split(":")[0]:
                                matched_model = name
                                break
                        if matched_model:
                            local_model = matched_model
                        else:
                            local_model = models[0]["name"]

                yield f"\nsys_meta_log|[SYS_LOG] Local node active. Model: {local_model}\n\n"
                await asyncio.sleep(0.1)
                yield "sys_meta_log|[SYS_LOG] Running local neural inference...\n\n"
                await asyncio.sleep(0.1)

                async with http_client.stream(
                    "POST",
                    "http://localhost:11434/api/generate",
                    json={
                        "model": local_model,
                        "prompt": f"System: {assembled_system}\n\nUser: {final_query}",
                        "stream": True
                    },
                    timeout=1800.0
                ) as response:
                    async for chunk in response.aiter_lines():
                        if chunk:
                            try:
                                data = json.loads(chunk)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                pass
            except Exception as fallback_err:
                print(f"Local fallback also failed: {fallback_err}")
                yield f"\n[SYSTEM ERROR] Connection to primary ({MODEL_NAME}) and local fallback ({local_model}) both failed. Verify Ollama status."

        # Step 3c: Yield deterministic governance sections (backend truth)
        crm_gaps = engine.audit_crm_hygiene(account_id)
        if crm_gaps:
            hygiene_text = "\n".join([f"⚠️ {g}" for g in crm_gaps[:3]])
            yield f"\n__SECTION_CRM_HYGIENE__\n{hygiene_text}"

        conf_level = engine.classify_answer_confidence(account_id)
        conf_score = "100%" if conf_level == "HIGH" else "50%" if conf_level == "MEDIUM" else "LOW"
        conf_status = f"{'100% Grounded' if conf_level == 'HIGH' else '50% Hybrid' if conf_level == 'MEDIUM' else 'Low Confidence'}"
        conf_data = {"score": conf_score, "status": conf_status, "sources": ["Excel Database"]}
        yield f"\n__SECTION_CONFIDENCE__\n{json.dumps(conf_data)}"
        yield "\n__SECTION_END__"

        end_time = asyncio.get_event_loop().time()
        latency_ms = (end_time - start_time) * 1000
        signal_types = [cs.signal_type.value for cs in synthesis.classified_signals] if synthesis.classified_signals else []
        print(f"[TELEMETRY] Intent: {intent} | Mode: {response_mode} | Route: LLM | Latency: {latency_ms:.2f}ms | Fallback: {fallback_active} | Synthesis: {synthesis.synthesis_latency_ms:.1f}ms | Signals: {signal_types}")

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
