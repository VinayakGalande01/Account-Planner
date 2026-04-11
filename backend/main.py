from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from typing import List, Optional

# Ensure the current directory (backend) is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_engine import DataEngine
import openai

app = FastAPI(title="Account Planner Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = r"C:\Users\VINAYAK\Downloads\SF_AccountingAgent_DummyData.xlsx"
engine = DataEngine(DATA_PATH)

import httpx
import json

# Configuration for Native Local LLM (Ollama style)
LLM_URL = "http://127.0.0.1:8000/api/generate" # Adjust if your manual test used a different path
MODEL_NAME = "phi3:mini" 

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
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"Sending request to {LLM_URL}...")
            resp = await client.post(
                LLM_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": f"System: {APEX_SYSTEM_PROMPT}\n\nUser: {final_query}",
                    "stream": False
                },
                timeout=1800.0
            )
            
            if resp.status_code != 200:
                return {"type": "text", "response": f"Intelligence server error ({resp.status_code})."}
                
            data = resp.json()
            raw_response = data.get("response", "").strip()
            
            return {"type": "text", "response": raw_response}
            
    except Exception as e:
        return {"type": "text", "response": f"Connection Failure. (Error: {str(e)})"}

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
    uvicorn.run(app, host="0.0.0.0", port=8001)
