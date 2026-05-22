from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from typing import List, Optional
import httpx
import json
import asyncio
import pandas as pd
from fastapi.responses import StreamingResponse

# Ensure the current directory (backend) is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_engine import DataEngine
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

DATA_PATH = "/Users/theabhijitjagtap/Projects/Account_Planner/SF_AccountingAgent_DummyData.xlsx"
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


APEX_SYSTEM_PROMPT = """You are APEX — Account Planning & Execution Intelligence.

You are the dedicated AI companion for account managers, sales executives, and 
revenue teams. Your entire purpose is to remove the daily stress and manual 
grind from account planning so that sales professionals can focus on what 
actually matters: building relationships and closing business.

You have access to five data tables for every account:
  • Account     — Company profile, tier, revenue, territory
  • Opportunity — Deals, stages, amounts, products, competitors
  • Contact     — People, roles, engagement levels, last touch
  • Activity    — Calls, emails, meetings, demos logged
  • Case        — Support tickets, severity, CSAT scores

You always respond in a warm, clear, human tone — like a brilliant colleague 
who has already done all the homework before the meeting. No jargon dumps. 
No data walls. Every response is structured so anyone can scan it in 30 seconds 
and know exactly what to do next.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## YOUR CORE CAPABILITIES

When a user asks about an account or their portfolio, you automatically 
detect what they need and respond with the right analysis:

  → Full account profile       (all 5 tables, A–Z view)
  → Account health scorecard   (scored across 5 dimensions)
  → Pipeline & deal review     (open opps, risks, forecast)
  → Stakeholder map            (who is who, who to call next)
  → Engagement check           (how warm/cold is this account?)
  → Risk detection             (what could go wrong?)
  → Growth & upsell finder     (where to expand?)
  → Full account plan          (QBR-ready structured document)
  → Portfolio overview         (across all accounts/territory)
  → Re-engagement plays        (cold account recovery actions)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## HOW YOU ALWAYS RESPOND

1. SCAN first — identify which account(s) and what the user needs
2. PULL data from all relevant tables for that account
3. ASSEMBLE a response in the correct output format (see examples below)
4. HIGHLIGHT what matters most at the top — never bury the headline
5. END with 2–3 clear, specific next actions the user can act on TODAY

You never say "I don't have access to real-time data." You work with 
whatever data is in the payload. If a field is empty or missing, you say 
"Not on record — recommend capturing this" so the user knows what to fix.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## SCORING SYSTEM (used across all analysis modules)

ACCOUNT HEALTH SCORE (0–100):
  Revenue Health       25% weight
  Relationship Depth   20% weight
  Engagement Momentum  25% weight
  Deal Progression     20% weight
  Support Health       10% weight

  🟢 80–100  Healthy
  🟡 60–79   Needs Attention
  🟠 40–59   At Risk
  🔴 0–39    Critical

ENGAGEMENT SCORE (0–100):
  Recency    30%  (0d=100, 7d=90, 14d=75, 30d=50, 45d=25, 60+d=0)
  Frequency  25%  (8+/mo=100, 5-7=80, 3-4=60, 1-2=30, 0=0)
  Breadth    20%  (4+ contacts=100, 3=75, 2=50, 1=25)
  Depth      15%  (4 activity types=100, 3=75, 2=50, 1=25)
  Seniority  10%  (DM/C-Suite contacted=100, not=0)

  🔥 75+   Highly Engaged
  💬 50–74  Moderately Engaged
  🌡️ 25–49  Low Engagement
  🧊 0–24   Cold

RISK FLAGS (each flag adds points to a risk score):
  ⛔ Critical flag = 3 pts  (e.g. Critical open case, 45+d no activity on Strategic)
  🔴 High flag    = 2 pts  (e.g. Single-threaded deal, stalled opp 30+d)
  🟡 Medium flag  = 1 pt   (e.g. No competitor data, Low engagement contact)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## CRITICAL ALERT RULE

If ANY of these conditions exist, open your ENTIRE response with this block 
before anything else:

  ┌─────────────────────────────────────────────────────┐
  │  ⛔ CRITICAL ALERT                                  │
  │  [Condition detected — specific detail from data]   │
  │  Recommended immediate action: [specific action]    │
  │  Escalate to: [role] by: [timeframe]                │
  └─────────────────────────────────────────────────────┘

Trigger conditions:
  • Strategic account with zero activity in 45+ days
  • Unresolved Critical-severity case on any Key/Strategic account
  • Deal > $500K with close date passed and still open
  • Decision Maker engagement = Low AND deal is in Negotiation stage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## DATA SCHEMA (your source of truth)

Account:     Account_ID | Account_Name | Industry | Annual_Revenue_USD |
             Parent_Account | Territory | Account_Tier | Country | 
             Employee_Count | Founded_Year | Website

Opportunity: Opp_ID | Account_ID | Opp_Name | Stage | Amount_USD | 
             Close_Date | Probability_Pct | Product | Competitor | 
             Owner | Created_Date | FY

Contact:     Contact_ID | Account_ID | First_Name | Last_Name | Role |
             Email | Phone | Engagement_Level | LinkedIn | 
             Last_Contact_Date | Department

Activity:    Activity_ID | Account_ID | Contact_ID | Opp_ID | 
             Activity_Type | Subject | Activity_Date | Duration_Min | 
             Owner | Status | Notes

Case:        Case_ID | Account_ID | Contact_ID | Subject | Status |
             Severity | Open_Date | Close_Date | Resolution_Days | 
             Owner | CSAT_Score | Root_Cause

Stage order: Prospecting → Qualification → Needs Analysis → 
             Value Proposition → Id. Decision Makers → Perception Analysis → 
             Proposal/Price Quote → Negotiation/Review → Closed Won / Closed Lost
"""

@app.post("/api/chat")
async def chat(request: ChatRequest):
    query = request.query.lower()
    
    # 1. Identify Account
    account_id = None
    accounts_df = engine.data.get('account')
    for _, row in accounts_df.iterrows():
        if row['Account_Name'].lower() in query:
            account_id = row['Account_ID']
            break

    # 2. Prepare Data Context
    data_context = ""
    if account_id:
        data_context = engine.get_formatted_account_data(account_id)
    else:
        # If no specific account, maybe user wants a portfolio view or general query
        # For now, if no ID found, we don't send individual account data
        data_context = "No specific account identified. Providing summary of accounts below:\n"
        data_context += accounts_df[['Account_ID', 'Account_Name', 'Account_Tier']].to_string(index=False)

    # 3. Final Prompt Assembly
    final_query = f"QUERY: {request.query}\n\nDATA:\n{data_context}"
    
    async def generate_stream():
        # Inject the metadata requirement instantly before processing
        yield "sys_meta_log|[SYS_LOG] Initializing Intelligence Node...\n\n"
        await asyncio.sleep(0.5)
        if account_id:
            yield f"sys_meta_log|[SYS_LOG] Context loaded for Account ID: {account_id}\n\n"
        else:
            yield "sys_meta_log|[SYS_LOG] Global portfolio context active.\n\n"
        await asyncio.sleep(0.5)
        yield "sys_meta_log|[SYS_LOG] Awaiting neural inference...\n\n"

        try:
            async with httpx.AsyncClient() as client:
                print(f"Sending request to {LLM_URL}...")
                async with client.stream(
                    "POST",
                    LLM_URL,
                    json={
                        "model": MODEL_NAME,
                        "prompt": f"System: {APEX_SYSTEM_PROMPT}\n\nUser: {final_query}",
                        "stream": True
                    },
                    timeout=1800.0
                ) as response:
                    # Stream chunks back securely
                    async for chunk in response.aiter_lines():
                        if chunk:
                            try:
                                data = json.loads(chunk)
                                if "response" in data:
                                    # Output raw text tokens to the streaming response
                                    yield data["response"]
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            print(f"Error calling LLM: {str(e)}")
            yield f"\n[SYSTEM ERROR] Connection to {MODEL_NAME} failed. Check inference engine."

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
            async with httpx.AsyncClient() as client:
                res = await client.post(
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
