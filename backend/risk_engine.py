"""
RISK RADAR ENGINE (risk_engine.py)
Deterministic risk scoring for portfolio-level executive accounts based on real CRM data:
Health Scores (30%), Stale Deals (25%), Dead Deals (20%), Single Threading (15%), Critical Cases (10%).
"""

# --- SECTION 1: Dependencies & Imports ---
# Imports pandas dataframes, typing structures, and datetime anchor calculators.
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from intelligence_engine import reference_date

# --- SECTION 2: Account Risk Radar Scoring Engine ---
# Evaluates multi-dimensional risk components and ranks accounts by risk score descending.
def score_account_risk(acc_id: str, acc_name: str, health: float, engine) -> Dict[str, Any]:
    score = 0.0
    reasons = []

    # 1. Health Score (30%)
    if health < 30:
        score += 30
        reasons.append(f"Health score critically low at {health:.1f}")
    elif health < 50:
        score += 15
        reasons.append(f"Health score below threshold at {health:.1f}")

    # DataFrames from engine
    opps_df = engine.data.get('opportunity')
    contacts_df = engine.data.get('contact')
    cases_df = engine.data.get('case')

    # Get opportunities for this account
    acc_opps = []
    total_pipeline = 0.0
    if opps_df is not None and not opps_df.empty:
        matching_opps = opps_df[opps_df['Account_ID'] == acc_id]
        total_pipeline = float(matching_opps['Amount_USD'].sum())
        
        # 2. Dead/Lost deals (20%)
        total_opps_count = len(matching_opps)
        if total_opps_count > 0:
            dead_lost = matching_opps[matching_opps['Stage'].isin(["Closed Lost", "Dead/Lost"])]
            dead_ratio = len(dead_lost) / total_opps_count
            if dead_ratio > 0.3:
                score += 20
                reasons.append(f"{len(dead_lost)} Dead/Lost deals ({dead_ratio:.0%} of pipeline)")

            # 3. Stale Deals (25%)
            today = datetime.combine(reference_date(), datetime.min.time())
            stale_count = 0
            for _, r in matching_opps.iterrows():
                close_date_str = str(r.get('Close_Date', ''))
                stage = str(r.get('Stage', ''))
                if close_date_str and "Signed" not in stage and "Closed" not in stage:
                    try:
                        close_dt = datetime.strptime(close_date_str[:10], "%Y-%m-%d")
                        if (today - close_dt).days > 90:
                            stale_count += 1
                    except Exception:
                        pass
            if stale_count > 0:
                score += min(stale_count * 5, 25)
                reasons.append(f"{stale_count} deals stalled for 90+ days")

    # 4. Zero Contacts Registered (15%)
    contacts_count = 0
    if contacts_df is not None and not contacts_df.empty:
        matching_contacts = contacts_df[contacts_df['Account_ID'] == acc_id]
        contacts_count = len(matching_contacts)
    
    if contacts_count == 0:
        score += 15
        reasons.append("No contacts registered — single-threaded risk")
    elif contacts_count <= 2:
        score += 5
        reasons.append(f"Weak contact coverage ({contacts_count} contacts registered)")

    # 5. Open Critical Cases (10%)
    critical_cases_count = 0
    if cases_df is not None and not cases_df.empty:
        matching_cases = cases_df[
            (cases_df['Account_ID'] == acc_id) & 
            (cases_df['Severity'].isin(['High', 'Critical', 'P1'])) & 
            (cases_df['Status'] != 'Closed')
        ]
        critical_cases_count = len(matching_cases)
    
    if critical_cases_count > 0:
        score += min(critical_cases_count * 5, 10)
        reasons.append(f"{critical_cases_count} open critical support case(s)")

    if score >= 60:
        classification = "CRITICAL RISK"
    elif score >= 35:
        classification = "HIGH RISK"
    elif score >= 15:
        classification = "MEDIUM RISK"
    else:
        classification = "LOW RISK"

    return {
        "account_id": acc_id,
        "account_name": acc_name,
        "risk_score": round(score, 1),
        "classification": classification,
        "open_critical_cases": critical_cases_count,
        "open_pipeline_usd": total_pipeline,
        "risk_reasons": reasons
    }


def run_risk_radar(engine) -> List[Dict[str, Any]]:
    """Returns all accounts sorted by risk score descending."""
    accounts_df = engine.data.get('account')
    if accounts_df is None or accounts_df.empty:
        return []

    scored_accounts = []
    for _, r in accounts_df.iterrows():
        acc_id = str(r.get('Account_ID', ''))
        acc_name = str(r.get('Account_Name', ''))
        health = float(r.get('Health_Score', 80.0))
        
        scored = score_account_risk(acc_id, acc_name, health, engine)
        scored_accounts.append(scored)

    return sorted(scored_accounts, key=lambda x: x["risk_score"], reverse=True)
