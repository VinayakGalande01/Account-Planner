"""
MAIN REST API SERVER (main.py)
Primary FastAPI application entrypoint providing endpoints for AI Chat, CRM data queries,
quick actions, data sync, rate limiting, and telemetry instrumentation.
"""

# --- SECTION 1: Environment Setup & Core Dependencies ---
# Configures environment variables, offline transformer modes, and imports FastAPI middleware.
import os
import sys
from dotenv import load_dotenv

backend_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(backend_dir, ".env")
load_dotenv(dotenv_path=env_path, override=False)

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import json
import asyncio
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_engine import DataEngine
from response_formatter import format_response_for_user
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

# --- SECTION 2: Logging, Rate Limiter, & App Initialization ---
# Initializes FastAPI instance, configures slowapi rate limiting, CORS headers, and tracing middleware.
IS_LOCAL_OLLAMA = os.getenv("LOCAL_OLLAMA", "true").lower() == "true"

import logging
from logging_config import setup_logging
setup_logging()
logger = logging.getLogger("backend")
frontend_logger = logging.getLogger("frontend")

session_checkpoints: Dict[str, Any] = {}

app = FastAPI(title="Account Planner Agent API")

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

def get_user_or_ip_identifier(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return request.client.host or "127.0.0.1"

limiter = Limiter(key_func=get_user_or_ip_identifier)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Automatically create database tables for the auth service
from database import Base, engine as db_engine
import models.user
import models.crm_models
import models.observability_models
try:
    Base.metadata.create_all(bind=db_engine)
    print("  [SUCCESS] Database tables initialized successfully.")
    
    # Run sync if database is empty
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    try:
        from models.crm_models import Account
        session.info["user_id"] = "1"  # Set context for RLS count check
        if session.query(Account).count() == 0:
            print("  [INFO] SQLite database is empty. Triggering initial sync...")
            from sync_daemon import sync_crm_to_sqlite
            sync_crm_to_sqlite()
    except Exception as sync_err:
        print(f"  [ERROR] Error running initial sync: {sync_err}")
    finally:
        session.close()
except Exception as db_err:
    print(f"  [ERROR] Database table initialization failed: {db_err}")
    print("     Ensure PostgreSQL is running and database 'account_planner' exists.")

from auth.router import router as auth_router
app.include_router(auth_router)

from api.golden_dataset import router as golden_dataset_router
app.include_router(golden_dataset_router)


from database import get_db
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user
from models.user import User



# Configure allowed CORS origins dynamically
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from observability import TelemetryTracingMiddleware
app.add_middleware(TelemetryTracingMiddleware)


# Global connection pool client to reuse TCP connections across API calls (improves latency & keeps connections alive)
http_client = httpx.AsyncClient(timeout=httpx.Timeout(connect=3.0, read=1800.0, write=10.0, pool=30.0))

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

@app.on_event("startup")
async def startup_event():
    """Pre-warm SentenceTransformer in a thread pool so the first user
    query does not block the event loop."""
    import asyncio
    from intent_classifier import IntentClassifier
    def _warmup():
        try:
            print("[STARTUP] Pre-warming semantic router (SentenceTransformer)...")
            router = IntentClassifier(is_local=True)
            router._init_embeddings()
            print("[STARTUP] Semantic router warmed up successfully.")
        except Exception as e:
            print(f"[STARTUP WARNING] Router warm-up failed (non-fatal): {e}")
    await asyncio.get_event_loop().run_in_executor(None, _warmup)

# Ensure the demo login exists and has demo CRM data (see demo_dataset.py)
from sqlalchemy.orm import Session
from database import SessionLocal
try:
    with SessionLocal() as startup_db:
        from sync_daemon import ensure_demo_user, sync_crm_to_sqlite_for_user
        from models.crm_models import Account
        demo_user = ensure_demo_user(startup_db)
        startup_db.info["user_id"] = str(demo_user.id)
        if startup_db.query(Account).filter(Account.user_id == demo_user.id).count() == 0:
            print("Seeding demo CRM data for demo user...")
            sync_crm_to_sqlite_for_user(startup_db, demo_user.id)
except Exception as startup_db_err:
    print(f"  [WARNING] Database startup seeding skipped: {startup_db_err}")

try:
    engine = DataEngine(SessionLocal(), 1)
except Exception as engine_init_err:
    print(f"  [WARNING] Failed to initialize root DataEngine: {engine_init_err}")
    engine = None

import threading

# Global dictionary to track per-user database sync locks
_sync_locks = {}
_sync_locks_mutex = threading.Lock()

def get_user_data_engine(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> DataEngine:
    # Set RLS user context
    db.info["user_id"] = str(current_user.id)
    
    from models.crm_models import Account
    from sync_daemon import sync_crm_to_sqlite_for_user
    
    # 1. Thread-safe lock retrieval/creation for this user
    with _sync_locks_mutex:
        if current_user.id not in _sync_locks:
            _sync_locks[current_user.id] = threading.Lock()
        user_lock = _sync_locks[current_user.id]
        
    # 2. Acquire lock to serialize sync executions
    with user_lock:
        # Re-verify count inside lock context in case a concurrent request already finished seeding
        if db.query(Account).filter(Account.user_id == current_user.id).count() == 0:
            print(f"Seeding demo data for new user: {current_user.email} (ID: {current_user.id})")
            sync_crm_to_sqlite_for_user(db, current_user.id)
        
    return DataEngine(db, current_user.id)

# Configuration for LLM (Remote or Local via .env)
import re
def normalize_url(url: str) -> str:
    if not url:
        return url
    if "://" in url:
        scheme, rest = url.split("://", 1)
    else:
        scheme, rest = "http", url
    # Clean up double slashes inside the path, preserving the protocol
    rest = re.sub(r'/+', '/', rest)
    return f"{scheme}://{rest}"

GEMINI_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("OPENROUTER_API_KEY"))
# Local Ollama endpoint is only required when no Gemini key is configured
LLM_URL = normalize_url(os.getenv("LLM_URL", "http://localhost:11434/api/generate"))
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:latest")

print("\n=============================================")
print("  [STARTUP] APEX INTELLIGENCE SYSTEM STARTING UP")
if GEMINI_KEY:
    print("  [MODE] Primary Routing: Google Gemini Cloud API (Active)")
else:
    print(f"  [URL] LLM URL    : {LLM_URL}")
    print(f"  [MODEL] LLM Model  : {MODEL_NAME}")
print("=============================================\n")

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default_session"
    active_account: Optional[str] = None
    chat_history: Optional[List[Dict[str, str]]] = []
    response_format: Optional[str] = "markdown"  # "markdown" or "json"
    response_mode: Optional[str] = "operational"  # "executive", "operational", "analyst"
    persona: Optional[str] = "account_manager"
    action_type: Optional[str] = None


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

def compute_table_for_intent(engine, intent: str, account_id: Optional[str] = None, query: str = "", p1_json: Optional[dict] = None) -> Optional[dict]:
    """Compute structured table data for a given intent.
    Returns dict with 'columns' and 'rows', or None if no table applicable.
    Backend is the single source of truth for ranking/priority/truncation."""

    # Map primary_intent / IntentEnum value to legacy table query types
    intent_str = intent.value if hasattr(intent, "value") else str(intent)
    intent_map = {
        "risk_assessment": "RISK_ANALYSIS_QUERY",
        "review_risks": "RISK_ANALYSIS_QUERY",
        "relationship_analysis": "CONTACT_QUERY",
        "pipeline_summary": "PIPELINE_SUMMARY_QUERY",
        "opportunity_expansion": "GLOBAL_LIST_QUERY",
        "action_recommendation": "GLOBAL_LIST_QUERY",
        "opportunity_ranking": "GLOBAL_LIST_QUERY",
        "pipeline_review": "PIPELINE_SUMMARY_QUERY",
        "executive_briefing": "GLOBAL_LIST_QUERY",
        "portfolio_analysis": "RISK_ANALYSIS_QUERY",
        "account_plan": "ACCOUNT_PLAN_QUERY",
        "contact_lookup": "CONTACT_QUERY"
    }
    intent = intent_map.get(intent_str, intent_str)

    from data_retrieval_layer import Phase1Output, _resolve_account_ids, normalize_stage_name
    p1 = Phase1Output.from_json(p1_json) if p1_json else None

    if p1:
        if p1.stage_filter in ("null", "none", "None", "undefined", ""):
            p1.stage_filter = None
        else:
            p1.stage_filter = normalize_stage_name(p1.stage_filter)
        if p1.time_window in ("null", "none", "None", "undefined", ""):
            p1.time_window = None
        if isinstance(p1.limit, str):
            if p1.limit in ("null", "none", "None", "undefined", ""):
                p1.limit = None
            else:
                try:
                    p1.limit = int(p1.limit)
                except ValueError:
                    p1.limit = None

    budget = RESPONSE_BUDGET.get(intent, {"max_rows": 15})
    max_rows = budget.get("max_rows", 15)
    lim = p1.limit if (p1 and p1.limit and isinstance(p1.limit, int)) else max_rows

    if intent == "GLOBAL_LIST_QUERY":
        columns = ["Rank", "Opp_ID", "Opp_Name", "Account_ID", "Stage", "Amount_USD", "Probability_Pct", "Close_Date", "Priority_Band"]
        table_rows = []
        opps = engine.data.get('opportunity')
        if opps is not None and not opps.empty:
            open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])].copy()
            if not open_opps.empty:
                # 1. Filter by target accounts if resolved
                tgt_acc_ids = []
                if account_id:
                    tgt_acc_ids = [account_id]
                elif p1 and p1.target_accounts:
                    tgt_acc_ids = _resolve_account_ids(engine, p1.target_accounts)
                
                if tgt_acc_ids:
                    open_opps = open_opps[open_opps["Account_ID"].isin(tgt_acc_ids)]

                # 2. Filter by target opportunities if resolved
                if p1 and p1.target_opportunities:
                    opp_ids = [o.strip().upper() for o in p1.target_opportunities]
                    open_opps = open_opps[open_opps["Opp_ID"].str.upper().isin(opp_ids)]

                # 3. Filter by stage if present
                stage_f = p1.stage_filter if p1 else None
                if not stage_f and "negotiation" in query.lower():
                    stage_f = "Negotiation"
                elif not stage_f and "perception" in query.lower():
                    stage_f = "Perception"
                elif not stage_f and "proposal" in query.lower():
                    stage_f = "Proposal"
                elif not stage_f and "proposition" in query.lower():
                    stage_f = "Proposition"

                if stage_f:
                    open_opps = open_opps[open_opps['Stage'].str.lower().str.contains(stage_f.lower(), na=False)]

                # 4. Filter close date by time window
                time_w = p1.time_window if p1 else None
                if not time_w and "30 days" in query.lower() and "closing" in query.lower():
                    time_w = "30 days"
                
                if time_w:
                    from data_retrieval_layer import _parse_time_window
                    cutoff = _parse_time_window(time_w)
                    if cutoff:
                        open_opps['Close_Date_Parsed'] = pd.to_datetime(open_opps['Close_Date'], errors='coerce')
                        if open_opps['Close_Date_Parsed'].dt.tz is not None:
                            open_opps['Close_Date_Parsed'] = open_opps['Close_Date_Parsed'].dt.tz_localize(None)
                        now = pd.Timestamp.now().tz_localize(None)
                        cutoff_ts = pd.Timestamp(cutoff).tz_localize(None)
                        open_opps = open_opps[(open_opps['Close_Date_Parsed'] >= now) & (open_opps['Close_Date_Parsed'] <= cutoff_ts)].copy()

                # Calculate Priorities
                priorities = []
                for _, r in open_opps.iterrows():
                    score = engine.calculate_opportunity_priority(r, "Standard")
                    priorities.append(score)
                open_opps['Priority_Score'] = priorities

                # Sorting
                sort_col = 'Priority_Score'
                ascending = False
                if p1 and p1.sort_by:
                    sb = p1.sort_by.lower()
                    if "probability" in sb:
                        sort_col = "Probability_Pct"
                    elif "close" in sb or "date" in sb:
                        sort_col = "Close_Date"
                        ascending = True
                    elif "stage" in sb:
                        sort_col = "Stage"
                        ascending = True
                    elif "amount" in sb or "value" in sb:
                        sort_col = "Amount_USD"
                
                ranked = open_opps.sort_values(by=sort_col, ascending=ascending)
                all_scores = priorities
                for rank, (_, r) in enumerate(ranked.head(lim).iterrows(), 1):
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
            
            # Use target account resolved ID
            tgt_acc_id = account_id
            if not tgt_acc_id and p1 and p1.target_accounts:
                acc_ids = _resolve_account_ids(engine, p1.target_accounts)
                if acc_ids:
                    tgt_acc_id = acc_ids[0]

            if tgt_acc_id:
                # When account/opp is resolved: show only ranked top-3 contacts, not entire directory
                df = df[df['Account_ID'] == tgt_acc_id]
                from reasoning_engine import StakeholderRanker
                # Determine opp stage for ranking
                opp_stage = "_default"
                opps = engine.data.get('opportunity')
                if opps is not None and not df.empty:
                    acc_opps = opps[(opps['Account_ID'] == tgt_acc_id) & ~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
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
                # Apply filter by target contacts if present
                if p1 and p1.target_contacts:
                    c_names_lower = [c.lower() for c in p1.target_contacts]
                    df['Full_Name'] = (df.get('First_Name', '') + ' ' + df.get('Last_Name', '')).str.lower().str.strip()
                    df = df[df['Full_Name'].apply(lambda fn: any(cn in fn for cn in c_names_lower))]

                for _, r in df.head(lim).iterrows():
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
            
            # Apply Filters
            # 1. Filter by target accounts if resolved
            tgt_acc_ids = []
            if account_id:
                tgt_acc_ids = [account_id]
            elif p1 and p1.target_accounts:
                tgt_acc_ids = _resolve_account_ids(engine, p1.target_accounts)
            
            if tgt_acc_ids:
                open_opps = open_opps[open_opps["Account_ID"].isin(tgt_acc_ids)]

            # 2. Filter by target opportunities if resolved
            if p1 and p1.target_opportunities:
                opp_ids = [o.strip().upper() for o in p1.target_opportunities]
                open_opps = open_opps[open_opps["Opp_ID"].str.upper().isin(opp_ids)]

            # 3. Filter by stage if present
            stage_f = p1.stage_filter if p1 else None
            # Extract stage_f from query if not explicitly set
            if not stage_f and "negotiation" in query.lower():
                stage_f = "Negotiation"
            elif not stage_f and "perception" in query.lower():
                stage_f = "Perception"
            elif not stage_f and "proposal" in query.lower():
                stage_f = "Proposal"
            elif not stage_f and "proposition" in query.lower():
                stage_f = "Proposition"

            if stage_f:
                open_opps = open_opps[open_opps['Stage'].str.lower().str.contains(stage_f.lower(), na=False)]

            # 4. Filter by time window if present
            time_w = p1.time_window if p1 else None
            if not time_w and "30 days" in query.lower() and "closing" in query.lower():
                time_w = "30 days"
            
            if time_w:
                from data_retrieval_layer import _parse_time_window
                cutoff = _parse_time_window(time_w)
                if cutoff:
                    open_opps['Close_Date_Parsed'] = pd.to_datetime(open_opps['Close_Date'], errors='coerce')
                    if open_opps['Close_Date_Parsed'].dt.tz is not None:
                        open_opps['Close_Date_Parsed'] = open_opps['Close_Date_Parsed'].dt.tz_localize(None)
                    now = pd.Timestamp.now().tz_localize(None)
                    cutoff_ts = pd.Timestamp(cutoff).tz_localize(None)
                    open_opps = open_opps[(open_opps['Close_Date_Parsed'] >= now) & (open_opps['Close_Date_Parsed'] <= cutoff_ts)].copy()

            # Sorting
            sort_col = 'Amount_USD'
            ascending = False
            if p1 and p1.sort_by:
                sb = p1.sort_by.lower()
                if "probability" in sb:
                    sort_col = "Probability_Pct"
                elif "close" in sb or "date" in sb:
                    sort_col = "Close_Date"
                    ascending = True
                elif "stage" in sb:
                    sort_col = "Stage"
                    ascending = True
            open_opps = open_opps.sort_values(by=sort_col, ascending=ascending)

            for _, r in open_opps.head(lim).iterrows():
                table_rows.append({
                    "Opp_ID": r['Opp_ID'],
                    "Opp_Name": r['Opp_Name'],
                    "Stage": r['Stage'],
                    "Amount_USD": float(r['Amount_USD']) if pd.notna(r['Amount_USD']) else 0,
                    "Probability_Pct": int(r['Probability_Pct']) if pd.notna(r['Probability_Pct']) else 0,
                    "Close_Date": str(r['Close_Date'])[:10] if pd.notna(r['Close_Date']) else ""
                })
        return {"columns": columns, "rows": table_rows} if table_rows else None

    elif intent == "ACCOUNT_PLAN_QUERY" and account_id:
        columns = ["Opp_ID", "Opp_Name", "Stage", "Amount_USD", "Probability_Pct", "Close_Date"]
        table_rows = []
        opps = engine.data.get('opportunity')
        if opps is not None and not opps.empty:
            acc_opps = opps[opps['Account_ID'] == account_id].copy()
            open_opps = acc_opps[~acc_opps['Stage'].isin(['Closed Won', 'Closed Lost'])]

            # Apply Filters (stage, limit, etc.)
            stage_f = p1.stage_filter if p1 else None
            if not stage_f and "negotiation" in query.lower():
                stage_f = "Negotiation"
            elif not stage_f and "perception" in query.lower():
                stage_f = "Perception"
            elif not stage_f and "proposal" in query.lower():
                stage_f = "Proposal"
            elif not stage_f and "proposition" in query.lower():
                stage_f = "Proposition"

            if stage_f:
                open_opps = open_opps[open_opps['Stage'].str.lower().str.contains(stage_f.lower(), na=False)]
            if p1 and p1.time_window:
                from data_retrieval_layer import _parse_time_window
                cutoff = _parse_time_window(p1.time_window)
                if cutoff:
                    open_opps['Close_Date_Parsed'] = pd.to_datetime(open_opps['Close_Date'], errors='coerce')
                    if open_opps['Close_Date_Parsed'].dt.tz is not None:
                        open_opps['Close_Date_Parsed'] = open_opps['Close_Date_Parsed'].dt.tz_localize(None)
                    now = pd.Timestamp.now().tz_localize(None)
                    cutoff_ts = pd.Timestamp(cutoff).tz_localize(None)
                    open_opps = open_opps[(open_opps['Close_Date_Parsed'] >= now) & (open_opps['Close_Date_Parsed'] <= cutoff_ts)].copy()

            for _, r in open_opps.head(lim).iterrows():
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
        # Check context-sensitivity (Cases vs Accounts vs Opportunities)
        q_lower = query.lower()
        if "case" in q_lower or "support" in q_lower or "ticket" in q_lower:
            # Table of Open Support Cases
            columns = ["Case_ID", "Account_Name", "Subject", "Severity", "Status", "Open_Date", "CSAT_Score"]
            table_rows = []
            cases_df = engine.data.get('case')
            accounts_df = engine.data.get('account')
            if cases_df is not None and not cases_df.empty:
                open_cases = cases_df[
                    (cases_df["Severity"].isin(["Critical", "High"])) &
                    (cases_df["Status"] != "Closed")
                ].copy()
                # Apply account filters if resolved
                tgt_acc_ids = []
                if account_id:
                    tgt_acc_ids = [account_id]
                elif p1 and p1.target_accounts:
                    tgt_acc_ids = _resolve_account_ids(engine, p1.target_accounts)
                
                if tgt_acc_ids:
                    open_cases = open_cases[open_cases["Account_ID"].isin(tgt_acc_ids)]

                if not open_cases.empty:
                    if accounts_df is not None:
                        open_cases = open_cases.merge(accounts_df[["Account_ID", "Account_Name"]], on="Account_ID", how="left")
                    open_cases = open_cases.sort_values(by="Open_Date", ascending=False)
                    for _, r in open_cases.head(lim).iterrows():
                        table_rows.append({
                            "Case_ID": r['Case_ID'],
                            "Account_Name": r.get('Account_Name', 'Unknown'),
                            "Subject": r['Subject'],
                            "Severity": r['Severity'],
                            "Status": r['Status'],
                            "Open_Date": str(r['Open_Date'])[:10] if pd.notna(r['Open_Date']) else "",
                            "CSAT_Score": float(r['CSAT_Score']) if pd.notna(r['CSAT_Score']) else 0.0
                        })
            return {"columns": columns, "rows": table_rows} if table_rows else None

        elif "account" in q_lower or "health" in q_lower:
            # Table of Account Health / Risk Priority
            columns = ["Rank", "Account_ID", "Account_Name", "Account_Tier", "Risk_Score", "Classification", "Open_Critical_Cases", "Open_Pipeline_USD"]
            table_rows = []
            accounts_df = engine.data.get('account')
            opps = engine.data.get('opportunity')
            cases = engine.data.get('case')
            if accounts_df is not None and not accounts_df.empty:
                rows = []
                # Filter strategic/key accounts if query specifies them
                for _, acc in accounts_df.iterrows():
                    aid = acc["Account_ID"]
                    risk_data = engine.calculate_risk_score(aid)
                    risk_score = risk_data.get('risk_score', 0)
                    risk_priority = engine.calculate_risk_priority(aid, risk_score)
                    
                    critical_cases = 0
                    if cases is not None and not cases.empty:
                        acc_cases = cases[cases["Account_ID"] == aid]
                        open_critical = acc_cases[
                            (acc_cases["Severity"].isin(["Critical", "High"])) &
                            (acc_cases["Status"] != "Closed")
                        ]
                        critical_cases = len(open_critical)
                    
                    open_pipeline = 0.0
                    if opps is not None and not opps.empty:
                        acc_opps = opps[(opps["Account_ID"] == aid) & (~opps["Stage"].isin(["Closed Won", "Closed Lost"]))]
                        open_pipeline = float(acc_opps["Amount_USD"].sum())
                    
                    rows.append({
                        "Account_ID": aid,
                        "Account_Name": acc.get("Account_Name", ""),
                        "Account_Tier": acc.get("Account_Tier", ""),
                        "Risk_Score": risk_score,
                        "Classification": risk_data.get("classification", "🟢 LOW RISK"),
                        "Risk_Priority": risk_priority,
                        "Open_Critical_Cases": critical_cases,
                        "Open_Pipeline_USD": open_pipeline
                    })
                
                health_df = pd.DataFrame(rows)
                # Sort by Risk Priority
                ranked = health_df.sort_values(by="Risk_Priority", ascending=False)
                for rank, (_, r) in enumerate(ranked.head(lim).iterrows(), 1):
                    table_rows.append({
                        "Rank": rank,
                        "Account_ID": r["Account_ID"],
                        "Account_Name": r["Account_Name"],
                        "Account_Tier": r["Account_Tier"],
                        "Risk_Score": int(r["Risk_Score"]),
                        "Classification": r["Classification"],
                        "Open_Critical_Cases": int(r["Open_Critical_Cases"]),
                        "Open_Pipeline_USD": float(r["Open_Pipeline_USD"])
                    })
            return {"columns": columns, "rows": table_rows} if table_rows else None

        else:
            # Default: Opportunities ranked by Risk Score
            columns = ["Rank", "Opp_ID", "Opp_Name", "Account_ID", "Stage", "Amount_USD", "Probability_Pct", "Close_Date"]
            table_rows = []
            opps = engine.data.get('opportunity')
            if opps is not None and not opps.empty:
                open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])].copy()
                
                # Apply stage, account and other filters
                tgt_acc_ids = []
                if account_id:
                    tgt_acc_ids = [account_id]
                elif p1 and p1.target_accounts:
                    tgt_acc_ids = _resolve_account_ids(engine, p1.target_accounts)
                
                if tgt_acc_ids:
                    open_opps = open_opps[open_opps["Account_ID"].isin(tgt_acc_ids)]

                if p1 and p1.target_opportunities:
                    opp_ids = [o.strip().upper() for o in p1.target_opportunities]
                    open_opps = open_opps[open_opps["Opp_ID"].str.upper().isin(opp_ids)]

                stage_f = p1.stage_filter if p1 else None
                if not stage_f and "negotiation" in query.lower():
                    stage_f = "Negotiation"
                elif not stage_f and "perception" in query.lower():
                    stage_f = "Perception"
                elif not stage_f and "proposal" in query.lower():
                    stage_f = "Proposal"
                elif not stage_f and "proposition" in query.lower():
                    stage_f = "Proposition"

                if stage_f:
                    open_opps = open_opps[open_opps['Stage'].str.lower().str.contains(stage_f.lower(), na=False)]

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
                    
                    ranked = open_opps.sort_values(by='Risk_Score', ascending=False)
                    for rank, (_, r) in enumerate(ranked.head(lim).iterrows(), 1):
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


def wrap_response_contract(
    intent: str,
    headline: str,
    summary: str,
    table_data: dict = None,
    signals: list = None,
    actions: list = None,
    crm_hygiene: list = None,
    confidence: dict = None,
    why_this_matters: str = None,
    executive_summary: str = None,
) -> str:
    """Canonical serializer for the __SECTION_*__ streaming transport format.
    Produces the tagged envelope that the frontend ContractRenderer parses.
    This is a TRANSPORT FORMAT — the frontend normalizes it into application state after stream completion."""
    parts = []

    parts.append(f"__SECTION_INTENT__\n{intent}")
    parts.append(f"__SECTION_HEADLINE__\n{headline}")
    if executive_summary:
        parts.append(f"__SECTION_EXECUTIVE_SUMMARY__\n{executive_summary}")
    parts.append(f"__SECTION_SUMMARY__\n{summary}")

    if table_data is not None:
        parts.append(f"__SECTION_TABLE_DATA__\n{json.dumps(table_data)}")

    if signals:
        signal_text = "\n".join([f"• {s}" for s in signals])
        parts.append(f"__SECTION_SIGNALS__\n{signal_text}")

    if why_this_matters:
        parts.append(f"__SECTION_WHY_THIS_MATTERS__\n{why_this_matters}")

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
    summary = {
        "executive": "Ultra-concise view of top-level revenue deals.",
        "analyst": f"Full diagnostic breakdown: {row_count} top deals ranked by priority band.",
    }.get(mode, f"Actionable view of {row_count} prioritized active deals.")

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
            confidence=confidence_data,
            why_this_matters=synthesis.why_this_matters if synthesis.why_this_matters else None
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
            confidence=confidence_data,
            why_this_matters=synthesis.why_this_matters if synthesis.why_this_matters else None
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
            confidence=confidence_data,
            why_this_matters=synthesis.why_this_matters if synthesis.why_this_matters else None
        )

@app.get("/api/chat/sessions")
async def get_chat_sessions(current_user: User = Depends(get_current_user)):
    from database import SessionLocal
    from models.crm_models import ChatSession, ChatMessage
    from fastapi import HTTPException
    
    db_sess = SessionLocal()
    db_sess.info["user_id"] = str(current_user.id)
    try:
        sessions = db_sess.query(ChatSession).filter(
            ChatSession.user_id == current_user.id
        ).order_by(ChatSession.created_at.desc()).all()
        
        from sqlalchemy import func
        
        # Subquery to get the minimum (first) message ID for each session
        subq = db_sess.query(
            ChatMessage.session_id,
            func.min(ChatMessage.id).label("min_id")
        ).filter(
            ChatMessage.user_id == current_user.id
        ).group_by(
            ChatMessage.session_id
        ).subquery()
        
        # Fetch first messages for all sessions in one query
        first_messages = db_sess.query(
            ChatMessage.session_id,
            ChatMessage.text
        ).join(
            subq,
            ChatMessage.id == subq.c.min_id
        ).all()
        
        # Map first messages by session ID
        first_msg_map = {m.session_id: m.text for m in first_messages}
        
        result = []
        for s in sessions:
            msg_text = first_msg_map.get(s.id)
            title = "New Chat"
            if msg_text:
                # Remove sys_meta_log progress prefixes from visual session titles
                clean_title = msg_text
                if "sys_meta_log|" in clean_title:
                    clean_title = "\n".join([line for line in clean_title.split("\n") if not line.startswith("sys_meta_log|")])
                clean_title = clean_title.strip()
                title = clean_title[:25] + "..." if len(clean_title) > 25 else clean_title
            
            result.append({
                "id": s.id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "title": title
            })
        return result
    except Exception as e:
        print(f"Error listing chat sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_sess.close()

@app.get("/api/chat/sessions/{session_id}/messages")
async def get_chat_messages(session_id: str, current_user: User = Depends(get_current_user)):
    from database import SessionLocal
    from models.crm_models import ChatMessage
    from fastapi import HTTPException
    
    db_sess = SessionLocal()
    db_sess.info["user_id"] = str(current_user.id)
    try:
        messages = db_sess.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == current_user.id
        ).order_by(ChatMessage.timestamp.asc()).all()
        
        return [
            {
                "id": m.id,
                "role": m.sender,
                "content": m.text,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            }
            for m in messages
        ]
    except Exception as e:
        print(f"Error fetching chat messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_sess.close()

@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str, current_user: User = Depends(get_current_user)):
    from database import SessionLocal
    from models.crm_models import ChatSession
    from fastapi import HTTPException
    
    db_sess = SessionLocal()
    db_sess.info["user_id"] = str(current_user.id)
    try:
        chat_session = db_sess.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")
            
        db_sess.delete(chat_session)
        db_sess.commit()
        return {"status": "SUCCESS", "message": "Session deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error deleting session: {e}")
        db_sess.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_sess.close()

def save_telemetry_bg(trace_id, request_id, session_id, user_id, workspace_id, correlation_id, start_time, full_contract, trace_payload, spans, user_query, active_account, model_name):
    try:
        import time
        from decimal import Decimal
        from observability import (
            get_telemetry_recorder,
            calculate_token_cost,
            classify_grounding,
            get_git_revision_hash
        )
        
        total_runtime_ms = int((time.time() - start_time) * 1000)
        
        # Heuristic token estimation
        prompt_tokens = len(user_query.split()) * 4
        completion_tokens = len(full_contract.split()) * 4
        calculated_cost = calculate_token_cost(model_name, prompt_tokens, completion_tokens)
        
        intent = trace_payload.get("intent")
        consensus = trace_payload.get("consensus")
        acc_data = trace_payload.get("account_data") or {}
        
        selected_intent = "UNKNOWN"
        planner_confidence = "LOW"
        entities = {}
        filters = {}
        reasoning_conf = 0
        
        if intent:
            if hasattr(intent, "primary_intent"):
                selected_intent = intent.primary_intent.value if hasattr(intent.primary_intent, "value") else str(intent.primary_intent)
                planner_confidence = "HIGH" if intent.confidence_primary >= 0.8 else ("MEDIUM" if intent.confidence_primary >= 0.5 else "LOW")
                entities = intent.extracted_entities.model_dump() if hasattr(intent.extracted_entities, "model_dump") else (intent.extracted_entities.dict() if hasattr(intent.extracted_entities, "dict") else (intent.extracted_entities if isinstance(intent.extracted_entities, dict) else {}))
            else:
                selected_intent = str(intent)
            filters = {"active_account": active_account}
            
        if consensus:
            reasoning_conf = int(consensus.final_confidence * 100) if hasattr(consensus, "final_confidence") else 0
            
        # Grounding check
        grounding_cat = "HIGH"
        if acc_data and full_contract:
            try:
                from grounding_verifier import compute_grounding_score, score_to_label
                g_score = compute_grounding_score(full_contract, acc_data)
                grounding_cat = score_to_label(g_score)
            except Exception as ge:
                print(f"[Telemetry Warning] Grounding score computation failed: {ge}")
                grounding_cat = "HIGH"
                
        git_commit = get_git_revision_hash()
        
        trace_record = {
            "trace_id": trace_id,
            "request_id": request_id,
            "session_id": session_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "user_query": user_query,
            "final_response": full_contract,
            "total_runtime_ms": total_runtime_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "model_name": model_name,
            "calculated_cost_usd": calculated_cost,
            "selected_intent": selected_intent,
            "planner_confidence": planner_confidence,
            "extracted_entities": entities,
            "applied_filters": filters,
            "reasoning_confidence_pct": reasoning_conf,
            "validation_passed": True,
            "validation_error": None,
            "grounding_score": grounding_cat,
            "reflection_triggered": False,
            "backend_git_commit": git_commit,
            "reasoning_engine_version": "1.0.0"
        }
        
        recorder = get_telemetry_recorder()
        recorder.record_trace(trace_record)
        
        # Save Spans
        if spans:
            for s in spans:
                s["trace_id"] = trace_id
            recorder.record_spans(spans)
            
        # Save Payload
        payload_record = {
            "trace_id": trace_id,
            "planner_prompt_hash": None,
            "reasoner_prompt_hash": None,
            "narrator_prompt_hash": None,
            "planner_output": trace_payload.get("raw_reasoning_bucket", {}).get("reasoning_plan") or trace_payload.get("raw_reasoning_bucket", {}).get("planner"),
            "retrieved_context_summary": f"Opps: {len(acc_data.get('opportunities', []))}, Contacts: {len(acc_data.get('contacts', []))}",
            "retrieved_record_ids": {
                "opportunities": [o.get("opp_id") or o.get("id") for o in acc_data.get("opportunities", [])],
                "evidence_scope": trace_payload.get("raw_reasoning_bucket", {}).get("evidence_bundle", {}).get("query_scope")
            },
            "reasoning_package": trace_payload.get("raw_reasoning_bucket") or {}
        }
        recorder.record_payload(payload_record)
        print(f"[TELEMETRY SAVE] Successfully logged trace {trace_id} in background.")
    except Exception as telemetry_err:
        print(f"[TELEMETRY ERROR] Failed to save telemetry in background: {telemetry_err}")

@app.post("/api/chat")
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    is_quick_action = body.action_type is not None and body.action_type.strip() != ""
    
    if not is_quick_action:
        from query_classifier import classify_query
        from conversational_handler import handle_conversational_query
        
        query_type = classify_query(body.query)
        
        if query_type == "GENERAL":
            result = handle_conversational_query(body.query)
            # Yield the JSON string directly as a "stream" so frontend text decoder matches it
            async def conv_stream():
                yield json.dumps(result)
            return StreamingResponse(conv_stream(), media_type="text/event-stream")
            
        if query_type == "UNCLEAR":
            result = {
                "type": "clarification",
                "message": "I want to make sure I help you correctly. Are you looking for data about your accounts, or do you have a general question about how APEX works?",
                "suggestions": [
                    "Show me my accounts",
                    "Explain how APEX works",
                    "Analyze my pipeline"
                ]
            }
            async def clear_stream():
                yield json.dumps(result)
            return StreamingResponse(clear_stream(), media_type="text/event-stream")
        
    if request.headers.get("x-test-mock") == "true":
        async def mock_stream():
            yield "__SECTION_HEADLINE__\nMock Response\n"
            yield "__SECTION_SUMMARY__\nThis is a mock response for testing.\n"
            yield "__SECTION_END__"
        return StreamingResponse(mock_stream(), media_type="text/event-stream")
        
    from database import SessionLocal
    from models.crm_models import ChatSession, ChatMessage
    
    session_id = body.session_id or "default_session"
    db_sess = SessionLocal()
    db_sess.info["user_id"] = str(current_user.id)
    chat_history = []
    pre_built_intent_data = None
    try:
        chat_session = db_sess.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        if not chat_session:
            chat_session = ChatSession(id=session_id, user_id=current_user.id)
            db_sess.add(chat_session)
            db_sess.commit()
            db_sess.refresh(chat_session)
        
        # Check for checkpoint message
        checkpoint_msg = db_sess.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.sender == "checkpoint",
            ChatMessage.user_id == current_user.id
        ).first()
        if checkpoint_msg:
            try:
                pre_built_intent_data = json.loads(checkpoint_msg.text)
                db_sess.delete(checkpoint_msg)
                db_sess.commit()
                print(f"[Checkpoint] Found and consumed checkpoint in DB for session: {session_id}")
            except Exception as parse_err:
                print(f"[Checkpoint Warning] Failed to parse checkpoint: {parse_err}")
        
        db_history = db_sess.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == current_user.id,
            ChatMessage.sender != "checkpoint"
        ).order_by(ChatMessage.timestamp.desc()).limit(10).all()
        for msg in reversed(db_history):
            text = msg.text or ""
            if msg.sender == "assistant" and "__SECTION_" in text:
                import re
                match = re.search(r'__SECTION_(?:SUMMARY|HEADLINE)__\n(.*?)(?=__SECTION_|\Z)', text, re.DOTALL)
                text = match.group(1).strip() if match else text[:300]
            chat_history.append({
                "sender": msg.sender,
                "text": text
            })
    except Exception as e:
        print(f"  [WARNING] Database error retrieving chat history: {e}")
    finally:
        db_sess.close()

    trace_payload = {}

    async def _generate_stream_impl():
        start_time = asyncio.get_event_loop().time()

        try:
            from pipeline_logger import PipelineLogger
            from observability.context import trace_id_var
            PipelineLogger.start(
                query=body.query,
                session_id=session_id,
                user_role=getattr(current_user, 'email', 'sales'),
                trace_id=trace_id_var.get() or "trace_local"
            )
        except Exception:
            pass

        yield "sys_meta_log|[SYS_LOG] Initializing Account Planning Agent...\n\n"
        await asyncio.sleep(0.05)
        
        if request.headers.get("x-test-mock") == "true":
            yield "__SECTION_HEADLINE__\nMock Response\n"
            yield "__SECTION_SUMMARY__\nThis is a mock response for testing.\n"
            yield "__SECTION_END__"
            return
            
        generator_db = SessionLocal()
        try:
            user_engine = await asyncio.to_thread(get_user_data_engine, generator_db, current_user)
            
            # Dynamically determine LLM provider from frontend request headers
            provider_header = request.headers.get("x-llm-provider", "local").lower()
            is_local = (provider_header == "local")
            
            # Instantiate agent at request time
            from agent_orchestrator import AccountPlanningAgent
            agent = AccountPlanningAgent(data_engine=user_engine, is_local=is_local)
            
            # Map response_mode to recipient_role
            role_map = {
                "analyst": "vp",
                "operational": "am",
                "executive": "svp"
            }
            
            target_role = role_map.get(body.response_mode, "am")
            
            # Contact-to-Account & History active account auto-resolution
            resolved_active_account = body.active_account
            if not resolved_active_account and user_engine:
                query_lower = (body.query or "").lower()
                contacts_df = user_engine.data.get('contact')
                accounts_df = user_engine.data.get('account')
                if contacts_df is not None and not contacts_df.empty:
                    for idx, row in contacts_df.iterrows():
                        fname = str(row.get('First_Name', '')).strip().lower()
                        lname = str(row.get('Last_Name', '')).strip().lower()
                        full_name = f"{fname} {lname}".strip()
                        if (fname and fname in query_lower) or (full_name and full_name in query_lower):
                            acc_id = row.get('Account_ID')
                            if accounts_df is not None and not accounts_df.empty:
                                acc_match = accounts_df[accounts_df['Account_ID'] == acc_id]
                                if not acc_match.empty:
                                    resolved_active_account = acc_match.iloc[0]['Account_Name']
                                    print(f"[Contact Resolution] Auto-resolved {full_name} -> Account: {resolved_active_account}")
                                    break
                
                if not resolved_active_account and chat_history:
                    for h_msg in reversed(chat_history):
                        h_text = h_msg.get("text", "")
                        if accounts_df is not None and not accounts_df.empty:
                            for acc_name in accounts_df['Account_Name'].tolist():
                                if acc_name and acc_name.lower() in h_text.lower():
                                    resolved_active_account = acc_name
                                    print(f"[History Resolution] Inherited active account from history: {resolved_active_account}")
                                    break
                        if resolved_active_account:
                            break
                            
            pre_built_intent = None
            if pre_built_intent_data:
                cached_intent = pre_built_intent_data.get("intent")
                if cached_intent:
                    if hasattr(cached_intent, "extracted_entities") and cached_intent.extracted_entities:
                        cached_intent.extracted_entities.account = body.query
                    elif isinstance(cached_intent, dict) and "extracted_entities" in cached_intent:
                        cached_intent["extracted_entities"]["account"] = body.query
                    
                    if hasattr(cached_intent, "target_entities"):
                        cached_intent.target_entities = [body.query]
                    elif isinstance(cached_intent, dict):
                        cached_intent["target_entities"] = [body.query]
                    
                    pre_built_intent = cached_intent
                    yield f"sys_meta_log|[SYS_LOG] Resuming session checkpoint. Account resolved: {body.query}✓\n\n"
                    await asyncio.sleep(0.05)
            
            # Setup thread-safe progress callback queue
            progress_queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            def on_progress(label: str):
                loop.call_soon_threadsafe(progress_queue.put_nowait, label)
            
            yield f"sys_meta_log|[SYS_LOG] Processing query for role: {target_role.upper()}...\n\n"
            await asyncio.sleep(0.05)
            # Run the 3-Layer pipeline in a task so we can stream keep-alive heartbeats in the meantime
            query_task = asyncio.create_task(
                asyncio.to_thread(
                    agent.process_query,
                    query=body.query,
                    user_role="sales", # Default
                    recipient_roles=[target_role],
                    history=body.chat_history if body.chat_history else chat_history,
                    active_account=resolved_active_account,
                    action_type=body.action_type,
                    pre_built_intent=pre_built_intent,
                    progress_callback=on_progress
                )
            )
            
            while not query_task.done():
                # Non-blocking draining of progress callback messages
                while not progress_queue.empty():
                    progress_label = progress_queue.get_nowait()
                    yield f"sys_meta_log|⚙️ {progress_label}\n\n"
                    await asyncio.sleep(0.02)
                try:
                    await asyncio.wait_for(asyncio.shield(query_task), timeout=0.2)
                except asyncio.TimeoutError:
                    pass
            
            # Final drain check
            while not progress_queue.empty():
                progress_label = progress_queue.get_nowait()
                yield f"sys_meta_log|⚙️ {progress_label}\n\n"
                await asyncio.sleep(0.02)
                
            res = query_task.result()
            
            if res.get("status") == "CLARIFICATION_REQUIRED":
                # Save checkpoint in database
                checkpoint_db = SessionLocal()
                checkpoint_db.info["user_id"] = str(current_user.id)
                try:
                    # Clear any old checkpoints for this session
                    checkpoint_db.query(ChatMessage).filter(
                        ChatMessage.session_id == session_id,
                        ChatMessage.sender == "checkpoint",
                        ChatMessage.user_id == current_user.id
                    ).delete()
                    
                    # Create a new checkpoint entry
                    serialized_res = json.dumps(res, default=str)
                    checkpoint_msg = ChatMessage(
                        session_id=session_id,
                        sender="checkpoint",
                        text=serialized_res,
                        user_id=current_user.id
                    )
                    checkpoint_db.add(checkpoint_msg)
                    checkpoint_db.commit()
                    print(f"[Checkpoint] Successfully saved checkpoint to DB for session {session_id}")
                except Exception as save_err:
                    print(f"[Checkpoint Error] Failed to save checkpoint to DB: {save_err}")
                finally:
                    checkpoint_db.close()

                clarification_payload = {
                    "type": "clarification",
                    "message": res.get("question"),
                    "suggestions": res.get("suggested_options", [])
                }
                yield json.dumps(clarification_payload)
                return
            
            trace_payload["intent"] = res.get("intent")
            trace_payload["consensus"] = res.get("consensus")
            trace_payload["account_data"] = res.get("account_data")
            trace_payload["raw_reasoning_bucket"] = res.get("raw_reasoning_bucket")
            trace_payload["raw_response_bucket"] = res.get("raw_response_bucket")
            
            try:
                from pipeline_logger import PipelineLogger
                from observability.context import trace_id_var
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                acc_name = str(res.get("account_data", {}).get("account_name", "Global"))
                data_qual = float(res.get("data_quality_score", 100.0))
                conf_raw = res.get("confidence", 1.0)
                conf_val = float(conf_raw) * 100.0 if float(conf_raw) <= 1.0 else float(conf_raw)
                intent_obj = res.get("intent")
                primary_val = getattr(intent_obj, 'primary_intent', intent_obj)
                intent_str = str(primary_val.value if hasattr(primary_val, 'value') else primary_val)

                PipelineLogger.finish(
                    trace_id=trace_id_var.get() or "trace_local",
                    session_id=session_id,
                    query=body.query,
                    intent_name=intent_str,
                    account_name=acc_name,
                    data_quality_pct=data_qual,
                    confidence_pct=conf_val,
                    duration_ms=duration_ms,
                    status=res.get("status", "SUCCESS")
                )
            except Exception as finish_err:
                print(f"  [Warning] PipelineLogger finish error: {finish_err}")
            
            # Yield active account for frontend tracking
            resolved_account = res.get("account_data", {}).get("account_name")
            if resolved_account and resolved_account != "Global Portfolio View":
                yield f"sys_meta_log|Active Account: {resolved_account}\n\n"
                await asyncio.sleep(0.05)
            
            # Database save logic moved to the outer wrapper function to capture full streamed payload

            
            # # OLD LOW_CONFIDENCE PATH (Commented down)
            # if res["status"] == "LOW_CONFIDENCE":
            #     yield "__SECTION_HEADLINE__\nQuery Clarification Needed"
            #     yield f"__SECTION_SUMMARY__\n{res['message']}"
            #     yield "__SECTION_END__"
            #     return

            if res["status"] == "DATA_ONLY_LOCAL":
                data = res["data"]
                data_quality = res["data_quality"]
                intent = res["intent"]
                
                print(f"DEBUG: Opportunities retrieved: {len(data.get('opportunities', []))}")
                print(f"DEBUG: Intent extracted stage: {intent.extracted_entities.stage}")
                print(f"DEBUG: Full data keys: {data.keys()}")
                print(f"DEBUG: Opportunities: {data.get('opportunities', [])}")
                
                yield "[SYS_LOG] Running in local mode. Data summary below.\n"
                
                # 1. HEADLINE
                account = data.get('account_name') or data.get('account', {}).get('name', 'Account')
                stage = intent.extracted_entities.stage or "Negotiation"
                yield f"__SECTION_HEADLINE__ Top 5 Opportunities in {stage}\n"
                
                # 2. DIRECT ANSWER
                opps = data.get('opportunities', [])
                # Map opportunities defensively to prevent KeyErrors
                mapped_opps = []
                for o in opps:
                    raw_amt = o.get("amount_usd") or o.get("amount") or 0.0
                    # Scale raw USD to Millions if it's large
                    amt_in_m = raw_amt / 1e6 if raw_amt >= 1e5 else raw_amt
                    mapped_opps.append({
                        "id": o.get("opp_id") or o.get("id") or "N/A",
                        "name": o.get("opp_name") or o.get("name") or "",
                        "amount": round(amt_in_m, 1),
                        "stage": o.get("stage") or "",
                        "probability": o.get("probability") or 100
                    })
                    
                if mapped_opps:
                    opp_list = "\n".join([
                        f"{i+1}. {o.get('name') or ('OPP-' + str(o.get('id')))} - ${o.get('amount', 0)}M ({o.get('probability', 0)}%)"
                        for i, o in enumerate(mapped_opps[:5])
                    ])
                    yield f"__SECTION_DIRECT_ANSWER__ {len(opps)} opportunities found:\n{opp_list}\n"
                else:
                    yield "__SECTION_DIRECT_ANSWER__ No opportunities found.\n"
                
                # 3. TABLE DATA
                if mapped_opps:
                    table = "Opp ID | Name | Amount | Stage | Probability\n"
                    table += "--------|-------|--------|-------|-------\n"
                    for opp in mapped_opps[:5]:
                        table += f"{opp.get('id', 'N/A')} | {opp.get('name', '')[:20]} | ${opp.get('amount', 0)}M | {opp.get('stage', '')} | {opp.get('probability', 0)}%\n"
                    yield f"__SECTION_TABLE_DATA__ {table}\n"
                
                # 4. SIGNALS (Key metrics)
                primary_intent_val = intent.primary_intent.value if hasattr(intent.primary_intent, "value") else str(intent.primary_intent)
                urgency_val = intent.urgency.value if hasattr(intent.urgency, "value") else str(intent.urgency)
                
                signals = f"Total Opportunities: {len(opps)}\n"
                signals += f"Data Quality: {int(data_quality.overall_sufficiency * 100)}%\n"
                signals += f"Intent Detected: {primary_intent_val}\n"
                signals += f"Urgency: {urgency_val}\n"
                yield f"__SECTION_SIGNALS__ {signals}\n"
                
                # 5. ACTIONS (Recommendations)
                actions = "RECOMMENDED ACTIONS:\n"
                actions += "1. Review data quality gaps (see CRM Hygiene)\n"
                actions += "2. Validate opportunity stages in CRM\n"
                actions += "3. For full strategic analysis, use cloud deployment\n"
                yield f"__SECTION_ACTIONS__ {actions}\n"
                          # 8. RECOMMENDED ACTIONS (Copilot chips)
                try:
                    from recommended_actions import generate_recommended_actions, serialize_recommended_actions
                    rec_actions = generate_recommended_actions(
                        intent=res.get("intent"),
                        query=body.query,
                        account_data=data,
                    )
                    if rec_actions:
                        yield f"__SECTION_RECOMMENDED_ACTIONS__\n{serialize_recommended_actions(rec_actions)}\n"
                except Exception as ra_err:
                    print(f"[API Warning] Could not generate recommended actions: {ra_err}")
                
                yield "__SECTION_END__\n"
                return
 
            if res["status"] == "INTENT_LOW_CONFIDENCE":
                yield "sys_meta_log|[SYS_LOG] Intent confidence too low. Returning data summary only.\n\n"
                await asyncio.sleep(0.05)
                data = res["data"]
                data_quality = res["data_quality"]
                account_name = data.get("account_name") or data.get("account") or "Account"
                yield f"__SECTION_HEADLINE__\n{account_name} Data Summary\n"
                yield f"__SECTION_DIRECT_ANSWER__\n{len(data.get('opportunities', []))} opportunities found\n"
                confidence_json = json.dumps({
                    "score": f"{data_quality.overall_sufficiency * 100:.0f}%",
                    "status": "Data-Only View",
                    "sources": ["CRM Sufficiency Score"]
                })
                yield f"__SECTION_CONFIDENCE__\n{confidence_json}\n"
                
                # RECOMMENDED ACTIONS (Copilot chips)
                try:
                    from recommended_actions import generate_recommended_actions, serialize_recommended_actions
                    rec_actions = generate_recommended_actions(
                        intent=res.get("intent"),
                        query=body.query,
                        account_data=data,
                    )
                    if rec_actions:
                        yield f"__SECTION_RECOMMENDED_ACTIONS__\n{serialize_recommended_actions(rec_actions)}\n"
                except Exception as ra_err:
                    print(f"[API Warning] Could not generate recommended actions: {ra_err}")
                
                yield "__SECTION_END__\n"
                return
                
            yield "sys_meta_log|[SYS_LOG] Layer 1: Intent classified ✓\n\n"
            await asyncio.sleep(0.05)
            yield "sys_meta_log|[SYS_LOG] Layer 2: Data retrieved + Reasoning running...\n\n"
            await asyncio.sleep(0.05)
            yield "sys_meta_log|[SYS_LOG] Layer 3: Generating response...\n\n"
            await asyncio.sleep(0.05)

            intent = res["intent"].primary_intent
            yield f"sys_meta_log|[SYS_LOG] Intent Identified: {intent}\n\n"
            await asyncio.sleep(0.05)
            
            # Format the output using SectionContractMapper
            from section_mapper import SectionContractMapper
            response_obj = res["responses"][target_role]
            consensus = res["consensus"]
            data_sufficiency_score = res["data_quality_score"]
            # Yield pre-computed table data if available (skip for simple conversational greetings)
            account_id = res.get("account_data", {}).get("account_id")
            complexity_val = res.get("intent").complexity if hasattr(res.get("intent"), "complexity") else None
            
            if complexity_val != "CONVERSATIONAL":
                try:
                    # Need to synthesize p1_json structure for compute_table_for_intent
                    limit_val = None
                    intent_obj = res.get("intent")
                    if intent_obj and hasattr(intent_obj, "extracted_entities") and intent_obj.extracted_entities.metric:
                        import re
                        metric_str = str(intent_obj.extracted_entities.metric)
                        digit_match = re.search(r'\d+', metric_str)
                        if digit_match:
                            limit_val = int(digit_match.group())
                    if not limit_val:
                        import re
                        digit_match = re.search(r'\b(top|limit|show|first)\s+(\d+)\b', body.query.lower())
                        if digit_match:
                            limit_val = int(digit_match.group(2))
                        else:
                            any_digit = re.search(r'\b\d+\b', body.query)
                            if any_digit:
                                limit_val = int(any_digit.group())

                    p1_json = {
                        "extracted_intent": intent,
                        "query_parameters": {
                            "target_accounts": [res.get("account_data", {}).get("account_name", "")],
                            "limit": limit_val
                        }
                    }
                    table_data = compute_table_for_intent(user_engine, intent, account_id, body.query, p1_json)
                    if table_data:
                        yield f"__SECTION_TABLE_DATA__\n{json.dumps(table_data)}\n"
                except Exception as e:
                    print(f"[API Warning] Could not generate table data: {e}")
                
            yield f"sys_meta_log|[SYS_LOG] Reasoning completed. Confidence: {consensus.final_confidence * 100:.0f}%\n\n"
            await asyncio.sleep(0.05)

            mapped_content = SectionContractMapper.map_to_stream(
                response_obj=response_obj,
                consensus=consensus,
                data_sufficiency_score=data_sufficiency_score,
                intent=res["intent"].intent,
                complexity=res["intent"].complexity,
                pipeline_breakdown=res.get("account_data", {}).get("pipeline_breakdown")
            )
            
            # Stream the complete mapped contract
            yield mapped_content
            
            # Stream recommended actions (Copilot chips)
            try:
                from recommended_actions import generate_recommended_actions, serialize_recommended_actions
                rec_actions = generate_recommended_actions(
                    intent=res.get("intent"),
                    query=body.query,
                    account_data=res.get("account_data"),
                    consensus=consensus,
                    response_obj=response_obj,
                )
                if rec_actions:
                    yield f"\n__SECTION_RECOMMENDED_ACTIONS__\n{serialize_recommended_actions(rec_actions)}"
            except Exception as ra_err:
                print(f"[API Warning] Could not generate recommended actions: {ra_err}")
            
            end_time = asyncio.get_event_loop().time()
            latency_ms = (end_time - start_time) * 1000
            print(f"[TELEMETRY] Account Planning Agent | Intent: {intent} | Role: {target_role} | Latency: {latency_ms:.2f}ms")
            
        except Exception as e:
            print(f"[API ERROR] Agent processing failed: {e}")
            import traceback
            traceback.print_exc()
            yield "__SECTION_HEADLINE__\nProcessing Error"
            yield f"__SECTION_SUMMARY__\nAn error occurred while generating the response: {str(e)}"
            yield "__SECTION_END__"
        finally:
            try:
                generator_db.close()
            except Exception as close_err:
                print(f"[API Warning] Failed to close database session cleanly: {close_err}")


    async def generate_stream():
        import time
        from observability import (
            trace_id_var,
            request_id_var,
            session_id_var,
            user_id_var,
            workspace_id_var,
            correlation_id_var,
            active_spans_var
        )
        
        # Start timer for whole stream runtime
        start_time_val = time.time()
        
        _contract_chunks = []
        async for chunk in _generate_stream_impl():
            yield chunk
            if isinstance(chunk, str) and not chunk.startswith("sys_meta_log|"):
                _contract_chunks.append(chunk)
        
        full_contract = "".join(_contract_chunks)
        
        # Call response formatter
        formatted_json = full_contract
        try:
            persona = body.persona if (body.persona and body.persona.strip()) else getattr(current_user, "role", "account_manager")
            chat_history = body.chat_history if body.chat_history else []
            
            # Call the formatter
            formatted_json = await format_response_for_user(
                raw_output=full_contract, 
                persona=persona,
                conversation_history=chat_history
            )
            
            # If the formatter returned something different than full_contract (meaning it succeeded),
            # yield it with the separator.
            if formatted_json != full_contract:
                yield f"\n__SECTION_FORMATTED_JSON__\n{formatted_json}\n"
        except Exception as formatter_err:
            print(f"[FORMATTER ERROR] Failed to format response: {formatter_err}")
            formatted_json = full_contract

        db_save = SessionLocal()
        db_save.info["user_id"] = str(current_user.id)
        try:
            user_msg = ChatMessage(session_id=session_id, sender="user", text=body.query, user_id=current_user.id)
            db_save.add(user_msg)
            
            to_save = full_contract
            if formatted_json != full_contract:
                to_save = f"{full_contract}\n__SECTION_FORMATTED_JSON__\n{formatted_json}\n"
                
            if to_save.strip():
                assistant_msg = ChatMessage(session_id=session_id, sender="assistant", text=to_save, user_id=current_user.id)
                db_save.add(assistant_msg)
            db_save.commit()
            print(f"[DB SAVE] Saved contract ({len(to_save)} chars) to session {session_id}")
        except Exception as save_err:
            print(f"  [WARNING] Failed to save chat history: {save_err}")
            db_save.rollback()
        finally:
            db_save.close()
            
        # Queue the background telemetry task using extracted request-context variables
        try:
            trace_id = trace_id_var.get()
            request_id = request_id_var.get()
            session_id_val = session_id_var.get()
            user_id_val = user_id_var.get()
            workspace_id_val = workspace_id_var.get()
            correlation_id_val = correlation_id_var.get()
            spans = active_spans_var.get().copy() if active_spans_var.get() else []
            
            import asyncio
            asyncio.create_task(
                asyncio.to_thread(
                    save_telemetry_bg,
                    trace_id=trace_id,
                    request_id=request_id,
                    session_id=session_id_val,
                    user_id=user_id_val,
                    workspace_id=workspace_id_val,
                    correlation_id=correlation_id_val,
                    start_time=start_time_val,
                    full_contract=full_contract,
                    trace_payload=trace_payload,
                    spans=spans,
                    user_query=body.query,
                    active_account=body.active_account,
                    model_name=MODEL_NAME
                )
            )
        except Exception as queue_err:
            print(f"[TELEMETRY] Warning: Failed to queue telemetry background task: {queue_err}")

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )



# ─── New Tactical Endpoints ───────────────────────────────────

# ─── Observability Control Panel Endpoints ────────────────────

@app.get("/api/observability/traces")
def list_traces(
    intent: Optional[str] = None,
    user_id: Optional[int] = None,
    model_name: Optional[str] = None,
    validation_passed: Optional[bool] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    from database import SessionLocal
    from models.observability_models import ObservabilityTrace
    
    db = SessionLocal()
    try:
        query = db.query(ObservabilityTrace)
        if intent:
            query = query.filter(ObservabilityTrace.selected_intent == intent)
        if user_id:
            query = query.filter(ObservabilityTrace.user_id == user_id)
        if model_name:
            query = query.filter(ObservabilityTrace.model_name == model_name)
        if validation_passed is not None:
            query = query.filter(ObservabilityTrace.validation_passed == validation_passed)
            
        traces = query.order_by(ObservabilityTrace.timestamp.desc()).limit(limit).all()
        return [
            {
                "trace_id": t.trace_id,
                "request_id": t.request_id,
                "session_id": t.session_id,
                "user_id": t.user_id,
                "user_query": t.user_query,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                "total_runtime_ms": t.total_runtime_ms,
                "selected_intent": t.selected_intent,
                "planner_confidence": t.planner_confidence,
                "calculated_cost_usd": float(t.calculated_cost_usd or 0.0),
                "validation_passed": t.validation_passed,
                "grounding_score": t.grounding_score
            }
            for t in traces
        ]
    finally:
        db.close()

@app.get("/api/observability/traces/{trace_id}")
def get_trace_detail(trace_id: str, current_user: User = Depends(get_current_user)):
    from database import SessionLocal
    from models.observability_models import ObservabilityTrace, ObservabilitySpan, ObservabilityPayload
    from fastapi import HTTPException
    
    db = SessionLocal()
    try:
        trace = db.query(ObservabilityTrace).filter(ObservabilityTrace.trace_id == trace_id).first()
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
            
        spans = db.query(ObservabilitySpan).filter(ObservabilitySpan.trace_id == trace_id).order_by(ObservabilitySpan.start_time.asc()).all()
        payload = db.query(ObservabilityPayload).filter(ObservabilityPayload.trace_id == trace_id).first()
        
        return {
            "trace": {
                "trace_id": trace.trace_id,
                "request_id": trace.request_id,
                "session_id": trace.session_id,
                "user_id": trace.user_id,
                "workspace_id": trace.workspace_id,
                "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
                "user_query": trace.user_query,
                "final_response": trace.final_response,
                "total_runtime_ms": trace.total_runtime_ms,
                "prompt_tokens": trace.prompt_tokens,
                "completion_tokens": trace.completion_tokens,
                "model_name": trace.model_name,
                "calculated_cost_usd": float(trace.calculated_cost_usd or 0.0),
                "selected_intent": trace.selected_intent,
                "planner_confidence": trace.planner_confidence,
                "extracted_entities": trace.extracted_entities,
                "applied_filters": trace.applied_filters,
                "reasoning_confidence_pct": trace.reasoning_confidence_pct,
                "validation_passed": trace.validation_passed,
                "validation_error": trace.validation_error,
                "grounding_score": trace.grounding_score,
                "reflection_triggered": trace.reflection_triggered,
                "backend_git_commit": trace.backend_git_commit,
                "reasoning_engine_version": trace.reasoning_engine_version
            },
            "spans": [
                {
                    "stage_name": s.stage_name,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "duration_ms": s.duration_ms
                }
                for s in spans
            ],
            "payload": {
                "planner_output": payload.planner_output if payload else None,
                "retrieved_context_summary": payload.retrieved_context_summary if payload else None,
                "retrieved_record_ids": payload.retrieved_record_ids if payload else {},
                "reasoning_package": payload.reasoning_package if payload else {}
            }
        }
    finally:
        db.close()

@app.post("/api/observability/business-metrics")
def record_metric(action_type: str, trace_id: Optional[str] = None, metadata: dict = {}, current_user: User = Depends(get_current_user)):
    from observability import get_telemetry_recorder
    
    recorder = get_telemetry_recorder()
    metric_record = {
        "trace_id": trace_id,
        "user_id": current_user.id,
        "action_type": action_type,
        "time_saved_est_sec": 420 if action_type == "REPORT_GENERATED" else 60,
        "metadata": metadata
    }
    recorder.record_business_metric(metric_record)
    return {"status": "SUCCESS"}

@app.post("/api/observability/replay/{trace_id}")
async def replay_trace(trace_id: str, current_user: User = Depends(get_current_user)):
    from database import SessionLocal
    from models.observability_models import ObservabilityTrace, ObservabilityPayload
    from fastapi import HTTPException
    
    db = SessionLocal()
    try:
        trace = db.query(ObservabilityTrace).filter(ObservabilityTrace.trace_id == trace_id).first()
        payload = db.query(ObservabilityPayload).filter(ObservabilityPayload.trace_id == trace_id).first()
        if not trace or not payload:
            raise HTTPException(status_code=404, detail="Trace data missing")
            
        # Sandbox execution: Instantiate agent using the snapshot context from payload
        user_engine = get_user_data_engine(db, current_user)
        from agent_orchestrator import AccountPlanningAgent
        agent = AccountPlanningAgent(data_engine=user_engine, is_local=True)
        
        # Execute query sandbox replay
        result = agent.process_query(
            query=trace.user_query,
            user_role="sales",
            recipient_roles=["am"],
            history=[]
        )
        
        return {
            "original_response": trace.final_response,
            "replayed_response": result.get("responses", {}).get("am", {}).get("narrative", "")
        }
    finally:
        db.close()

@app.get("/api/prompts")
def get_prompts(current_user: User = Depends(get_current_user)):
    return [
        {
            "id": "negotiation_stalled",
            "text": "Give me the top 5 opportunities stalling in the negotiation stage.",
            "category": "Pipeline & Opportunities",
            "icon": "📊"
        },
        {
            "id": "accenture_decision_makers",
            "text": "Who are the key decision makers at Accenture and when was the last time we contacted them?",
            "category": "Stakeholders & Engagement",
            "icon": "👥"
        },
        {
            "id": "high_risk_cases",
            "text": "Show me the highest risk accounts with critical open support cases",
            "category": "Risk & Support",
            "icon": "⚠️"
        },
        {
            "id": "weighted_forecast_30d",
            "text": "What opportunities are closing in the next 30 days and what is our weighted forecast?",
            "category": "Pipeline & Opportunities",
            "icon": "📈"
        },
        {
            "id": "accenture_strategic_plan",
            "text": "Give me a strategic account plan for Accenture.",
            "category": "Strategic Accounts",
            "icon": "🎯"
        },
        {
            "id": "priority_actions_today",
            "text": "What are my top priority actions for today?",
            "category": "Daily Action Plan",
            "icon": "⚡"
        },
        {
            "id": "servicenow_decision_makers",
            "text": "Who is the primary decision maker at ServiceNow and are there any unmapped key influencers we need to engage?",
            "category": "Stakeholders & Engagement",
            "icon": "🔎"
        },
        {
            "id": "accenture_blockers_plan",
            "text": "Which stakeholders at Accenture are acting as blockers, and what is our action plan to align them?",
            "category": "Stakeholders & Engagement",
            "icon": "🛡️"
        },
        {
            "id": "perception_stalled_var",
            "text": "What is our total value-at-risk for opportunities stalling in the perception stage, and what is the expected revenue impact of resolving them?",
            "category": "Risk & Support",
            "icon": "💸"
        },
        {
            "id": "pipeline_deal_velocity",
            "text": "Show me the deal velocity and estimated risk reduction percentage for our active pipeline.",
            "category": "Pipeline & Opportunities",
            "icon": "⚙️"
        },
        {
            "id": "grab_holdings_review",
            "text": "Provide a complete strategic review of our opportunity with Grab Holdings, tracing our key observations to next recommended steps.",
            "category": "Strategic Accounts",
            "icon": "📋"
        },
        {
            "id": "deloitte_india_focus",
            "text": "What is the strategic focus for Deloitte India, and what observations from the raw cases database support this?",
            "category": "Strategic Accounts",
            "icon": "💡"
        },
        {
            "id": "pipeline_confidence_stale_notes",
            "text": "Evaluate our pipeline confidence. Are there accounts with stale activity notes (>30 days) where we need to downgrade our reasoning confidence?",
            "category": "Risk & Support",
            "icon": "🔍"
        }
    ]


@app.get("/test/intent")
def test_intent_classification(query: str):
    """Test Layer 1 validation."""
    from intent_classifier import IntentClassifier
    classifier = IntentClassifier()
    result = classifier.classify(query)
    
    primary_intent_val = result.primary_intent.value if hasattr(result.primary_intent, "value") else str(result.primary_intent)
    urgency_val = result.urgency.value if hasattr(result.urgency, "value") else str(result.urgency)
    scope_val = result.scope.value if hasattr(result.scope, "value") else str(result.scope)
    
    return {
        "query": query,
        "primary_intent": primary_intent_val,
        "confidence": result.confidence_primary,
        "entities": {
            "account": result.extracted_entities.account,
            "stage": result.extracted_entities.stage,
            "metric": result.extracted_entities.metric,
            "timeframe": result.extracted_entities.timeframe,
            "competitor": getattr(result.extracted_entities, "competitor", None)
        },
        "urgency": urgency_val,
        "scope": scope_val
    }

@app.get("/api/insights")
async def get_insights(
    user_engine: DataEngine = Depends(get_user_data_engine),
    current_user: User = Depends(get_current_user)
):
    """Analyzes the account portfolio and pipeline to generate proactive insights, alerts, and suggestions using rules + LLM."""
    from datetime import datetime
    try:
        accounts = user_engine.data.get('account')
        opps = user_engine.data.get('opportunity')
        contacts = user_engine.data.get('contact')
        activities = user_engine.data.get('activity')
        cases = user_engine.data.get('case')

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
                    "description": f"{c_row.get('Severity', 'High')} severity case on {acc_name} is still {str(c_row.get('Status', 'open')).lower()} (opened {c_row.get('Open_Date', 'recently')}).",
                    "targetAccount": acc_name,
                    "targetAccountId": acc_id,
                    "suggestedAction": f"Escalate case {str(c_row['Case_ID']).split('_', 1)[-1]} to engineering and brief the account owner before the next customer call."
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
async def get_enriched_accounts(
    user_engine: DataEngine = Depends(get_user_data_engine),
    current_user: User = Depends(get_current_user)
):
    """Returns all accounts with computed health scores, pipeline values, and last activity dates."""
    try:
        enriched = user_engine.get_enriched_accounts_list()
        return enriched
    except Exception as e:
        return []

@app.get("/api/pipeline/summary")
async def get_pipeline_summary(
    user_engine: DataEngine = Depends(get_user_data_engine),
    current_user: User = Depends(get_current_user)
):
    """Returns aggregated pipeline data grouped by stage."""
    try:
        analysis = user_engine.get_pipeline_analysis()
        return analysis
    except Exception as e:
        return {"total_value": 0, "weighted_value": 0, "deal_count": 0, "stage_summary": {}}

@app.get("/api/accounts/{account_id}/details")
async def get_account_details(
    account_id: str, 
    user_engine: DataEngine = Depends(get_user_data_engine),
    current_user: User = Depends(get_current_user)
):
    """Returns real JSON details for a specific account."""
    try:
        # Enforce Access Checks (403 Forbidden)
        from models.crm_models import Account
        db_account = user_engine.db.query(Account).filter(
            Account.Account_ID == account_id,
            Account.user_id == current_user.id
        ).first()
        if not db_account:
            raise HTTPException(status_code=403, detail="Access denied to this account")
            
        details = user_engine.get_account_details_json(account_id)
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Existing Endpoints ───────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Account Planner Agent API is running"}

@app.get("/api/accounts")
async def get_accounts(
    user_engine: DataEngine = Depends(get_user_data_engine),
    current_user: User = Depends(get_current_user)
):
    if 'account' not in user_engine.data or user_engine.data['account'].empty:
        return []
    return user_engine.data['account'][['Account_ID', 'Account_Name', 'Account_Tier']].to_dict('records')

@app.post("/api/sync")
async def sync_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API endpoint to manually trigger the sync daemon scoped to this user."""
    from sync_daemon import sync_crm_to_sqlite_for_user
    success = sync_crm_to_sqlite_for_user(db, current_user.id)
    if not success:
        raise HTTPException(status_code=500, detail="Database sync failed")
        
    return {"status": "SUCCESS", "message": "Database successfully synced from CRM dataset"}

@app.get("/api/dashboard/hygiene")
async def get_hygiene_warnings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API endpoint to retrieve CRM data hygiene alerts."""
    from hygiene_checker import check_data_hygiene
    try:
        warnings = check_data_hygiene(db, current_user.id)
        return {"warnings": warnings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Write-Back & CRM Sync Endpoints ───────────────────────────────────

class CRMActivityCreate(BaseModel):
    account_id: str
    contact_id: Optional[str] = None
    activity_type: str
    description: str
    activity_date: str

class CRMOpportunityUpdate(BaseModel):
    opp_name: Optional[str] = None
    amount_usd: Optional[float] = None
    stage: Optional[str] = None
    close_date: Optional[str] = None
    probability_pct: Optional[int] = None

class CRMCaseUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None

class CRMSyncRequest(BaseModel):
    provider: str  # "salesforce" or "hubspot"
    instance_url: Optional[str] = None
    access_token: str

@app.post("/api/crm/activity")
async def create_crm_activity(
    payload: CRMActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from models.crm_models import Activity, Account
    import uuid
    
    # Verify account belongs to user
    account = db.query(Account).filter(Account.Account_ID == payload.account_id, Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=403, detail="Access denied to this account")
        
    activity = Activity(
        Activity_ID=f"act_{uuid.uuid4().hex[:8]}",
        Account_ID=payload.account_id,
        Contact_ID=payload.contact_id,
        Activity_Type=payload.activity_type,
        Type=payload.activity_type,
        Description=payload.description,
        Activity_Date=payload.activity_date,
        user_id=current_user.id
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    
    # Re-index in vector store fallback
    try:
        from vector_store import vector_store
        vector_store.index_activities([{
            "activity_id": activity.Activity_ID,
            "account_id": activity.Account_ID,
            "type": activity.Activity_Type,
            "description": activity.Description,
            "date": activity.Activity_Date
        }], user_id=current_user.id)
    except Exception as e:
        print(f"Warning: Failed to index created activity: {e}")
        
    return {"status": "SUCCESS", "activity_id": activity.Activity_ID}

@app.patch("/api/crm/opportunity/{opp_id}")
async def update_crm_opportunity(
    opp_id: str,
    payload: CRMOpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from models.crm_models import Opportunity
    opp = db.query(Opportunity).filter(Opportunity.Opp_ID == opp_id, Opportunity.user_id == current_user.id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
        
    if payload.opp_name is not None:
        opp.Opp_Name = payload.opp_name
    if payload.amount_usd is not None:
        opp.Amount_USD = payload.amount_usd
    if payload.stage is not None:
        opp.Stage = payload.stage
    if payload.close_date is not None:
        opp.Close_Date = payload.close_date
    if payload.probability_pct is not None:
        opp.Probability_Pct = payload.probability_pct
        
    db.commit()
    return {"status": "SUCCESS", "message": "Opportunity updated successfully"}

@app.patch("/api/crm/case/{case_id}")
async def update_crm_case(
    case_id: str,
    payload: CRMCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from models.crm_models import Case
    crm_case = db.query(Case).filter(Case.Case_ID == case_id, Case.user_id == current_user.id).first()
    if not crm_case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if payload.status is not None:
        crm_case.Status = payload.status
    if payload.severity is not None:
        crm_case.Severity = payload.severity
        
    db.commit()
    return {"status": "SUCCESS", "message": "Case updated successfully"}

@app.post("/api/sync/crm")
async def sync_crm_data(
    payload: CRMSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sync_daemon import sync_salesforce_to_db, sync_hubspot_to_db
    
    if payload.provider.lower() == "salesforce":
        if not payload.instance_url and payload.access_token != "mock_token":
            raise HTTPException(status_code=400, detail="instance_url is required for Salesforce sync")
        success = sync_salesforce_to_db(db, current_user.id, payload.instance_url or "", payload.access_token)
    elif payload.provider.lower() == "hubspot":
        success = sync_hubspot_to_db(db, current_user.id, payload.access_token)
    else:
        raise HTTPException(status_code=400, detail="Unsupported CRM provider")
        
    if not success:
        raise HTTPException(status_code=500, detail="CRM synchronization failed")
        
    return {"status": "SUCCESS", "message": f"Successfully synchronized data from {payload.provider.upper()}"}


class FrontendLogPayload(BaseModel):
    level: str
    message: str
    context: Optional[dict] = None

@app.post("/api/logs/frontend")
async def log_frontend_event(payload: FrontendLogPayload):
    log_msg = f"{payload.message} | Context: {payload.context}"
    if payload.level.lower() == "error":
        frontend_logger.error(log_msg)
    elif payload.level.lower() == "warn":
        frontend_logger.warning(log_msg)
    else:
        frontend_logger.info(log_msg)
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
