import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

class DataEngine:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.data = {}
        self.load_data()

    def load_data(self):
        """Loads all sheets from the Excel file into pandas DataFrames."""
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Excel file not found at {self.excel_path}")
        
        sheets = pd.read_excel(self.excel_path, sheet_name=None)
        # Normalize keys to lowercase for easier lookup
        self.data = {name.lower(): df for name, df in sheets.items()}
        print(f"Loaded sheets: {list(self.data.keys())}")

    def _get_days_ago(self, date_val):
        """Helper to compute days since a date."""
        if pd.isna(date_val): return 999
        if isinstance(date_val, str):
            try:
                date_val = datetime.strptime(date_val, '%Y-%m-%d')
            except:
                return 999
        now = datetime.now()
        try:
            date_val = pd.to_datetime(date_val)
            delta = now - date_val
            return delta.days
        except:
            return 999

    def calculate_health_score(self, account_id: str):
        """MODULE 1: ACCOUNT HEALTH SCORECARD"""
        accounts = self.data.get('account')
        opps = self.data.get('opportunity')
        contacts = self.data.get('contact')
        activities = self.data.get('activity')
        cases = self.data.get('case')

        if any(df is None for df in [accounts, opps, contacts, activities, cases]):
            return {"error": "Missing one or more data sheets"}

        acc_row = accounts[accounts['Account_ID'] == account_id]
        if acc_row.empty: return {"error": "Account not found"}
        acc_row = acc_row.iloc[0]

        # A. REVENUE HEALTH (25%)
        opps_acc = opps[opps['Account_ID'] == account_id]
        open_opps = opps_acc[~opps_acc['Stage'].isin(['Closed Won', 'Closed Lost'])]
        total_open_amount = open_opps['Amount_USD'].sum()
        revenue = acc_row['Annual_Revenue_USD']
        rev_score = min(100, (total_open_amount / revenue) * 100) if revenue > 0 else 0
        # Bonus for recent Closed Won
        recent_won = opps_acc[(opps_acc['Stage'] == 'Closed Won')]
        if not recent_won.empty:
            rev_score = min(100, rev_score + 15)

        # B. RELATIONSHIP DEPTH (20%)
        contacts_acc = contacts[contacts['Account_ID'] == account_id]
        has_dm = not contacts_acc[contacts_acc['Role'].str.contains('Decision Maker|C-Suite|VP', na=False, case=False)].empty
        rel_score = 30 if has_dm else 0
        rel_score += min(70, len(contacts_acc) * 10)

        # C. ENGAGEMENT MOMENTUM (25%)
        activities_acc = activities[activities['Account_ID'] == account_id]
        if not activities_acc.empty:
            last_activity = self._get_days_ago(activities_acc['Activity_Date'].max())
            eng_score = 30 if last_activity <= 14 else 20 if last_activity <= 30 else 15 if last_activity <= 60 else 0
            # Frequency bonus (timezone-safe comparison)
            act_dates = pd.to_datetime(activities_acc['Activity_Date'])
            try:
                act_dates = act_dates.dt.tz_localize(None)
            except:
                pass
            recent_count = len(activities_acc[act_dates > (datetime.now() - timedelta(days=30))])
            eng_score += min(35, recent_count * 7)
            # Mix bonus
            types = activities_acc['Activity_Type'].nunique()
            eng_score += min(15, types * 5)
        else:
            eng_score = 0

        # D. DEAL PROGRESSION (20%)
        if not open_opps.empty:
            advanced_stages = len(open_opps[open_opps['Stage'].isin(['Proposal/Price Quote', 'Negotiation/Review'])])
            deal_score = min(50, advanced_stages * 25)
            # Stale check
            deal_score += 20 
        else:
            deal_score = 100 # Neutral if no deals needed

        # E. SUPPORT & SATISFACTION (10%)
        cases_acc = cases[cases['Account_ID'] == account_id]
        if not cases_acc.empty:
            critical_cases = len(cases_acc[(cases_acc['Severity'] == 'Critical') & (cases_acc['Status'] != 'Closed')])
            sup_score = 40 if critical_cases == 0 else 0
            avg_csat = cases_acc['CSAT_Score'].mean()
            if avg_csat >= 4: sup_score += 30
            elif avg_csat >= 3: sup_score += 15
        else:
            sup_score = 100

        overall = (rev_score * 0.25) + (rel_score * 0.20) + (eng_score * 0.25) + (deal_score * 0.20) + (sup_score * 0.10)
        tier = "🟢 HEALTHY" if overall >= 80 else "🟡 NEEDS ATTENTION" if overall >= 60 else "🟠 AT RISK" if overall >= 40 else "🔴 CRITICAL"

        return {
            "account_id": account_id,
            "account_name": acc_row['Account_Name'],
            "overall_score": round(overall, 1),
            "tier": tier,
            "breakdown": {
                "revenue": round(rev_score, 1),
                "relationship": round(rel_score, 1),
                "engagement": round(eng_score, 1),
                "deals": round(deal_score, 1),
                "support": round(sup_score, 1)
            }
        }

    def calculate_risk_score(self, account_id: str):
        """MODULE 4: RISK DETECTION - Realistic implementation based on business guidelines"""
        accounts = self.data.get('account')
        opps = self.data.get('opportunity')
        contacts = self.data.get('contact')
        activities = self.data.get('activity')
        cases = self.data.get('case')

        flags = []
        risk_score = 0

        if accounts is None:
            return {"risk_score": 0, "flags": []}

        acc_row = accounts[accounts['Account_ID'] == account_id]
        if acc_row.empty:
            return {"risk_score": 0, "flags": []}
        acc_row = acc_row.iloc[0]
        tier = str(acc_row.get('Account_Tier', '')).lower()
        is_high_tier = "strategic" in tier or "key" in tier

        # 1. Check zero activity in 45+ days on Key/Strategic
        if is_high_tier:
            if activities is not None and not activities.empty:
                acc_acts = activities[activities['Account_ID'] == account_id]
                if acc_acts.empty:
                    flags.append("Strategic account with ZERO logged activities")
                    risk_score += 3
                else:
                    last_act_date = pd.to_datetime(acc_acts['Activity_Date']).max()
                    if pd.notna(last_act_date):
                        if last_act_date.tzinfo is not None:
                            last_act_date = last_act_date.tz_localize(None)
                        days_since = (datetime.now() - last_act_date).days
                    else:
                        days_since = 999
                    if days_since > 45:
                        flags.append(f"Strategic account with zero activity in {days_since} days (Limit: 45 days)")
                        risk_score += 3
            else:
                flags.append("Strategic account with ZERO logged activities")
                risk_score += 3

        # 2. Unresolved Critical-severity case
        if cases is not None and not cases.empty:
            acc_cases = cases[cases['Account_ID'] == account_id]
            unresolved_critical = acc_cases[(acc_cases['Severity'] == 'Critical') & (acc_cases['Status'] != 'Closed')]
            if not unresolved_critical.empty:
                flags.append(f"Unresolved Critical-severity case: '{unresolved_critical.iloc[0]['Subject']}'")
                risk_score += 3

        # 3. Deal > $500K passed close date and still open
        if opps is not None and not opps.empty:
            acc_opps = opps[opps['Account_ID'] == account_id]
            open_opps = acc_opps[~acc_opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
            for _, opp in open_opps.iterrows():
                amount = opp.get('Amount_USD', 0)
                try:
                    close_date = pd.to_datetime(opp.get('Close_Date'))
                    if pd.notna(close_date):
                        if close_date.tzinfo is not None:
                            close_date = close_date.tz_localize(None)
                        if amount > 500000 and close_date < datetime.now():
                            flags.append(f"Stale high-value deal (> $500K) passed close date: '{opp['Opp_Name']}' (${amount:,.2f})")
                            risk_score += 3
                except:
                    pass

        # 4. DM engagement = Low/Cold and deal in Negotiation stage
        if opps is not None and contacts is not None:
            acc_opps = opps[opps['Account_ID'] == account_id]
            in_negotiation = not acc_opps[acc_opps['Stage'] == 'Negotiation/Review'].empty
            if in_negotiation:
                acc_contacts = contacts[contacts['Account_ID'] == account_id]
                dms = acc_contacts[acc_contacts['Role'].str.contains('Decision Maker|C-Suite|VP', na=False, case=False)]
                low_engagement_dms = dms[dms['Engagement_Level'].isin(['Low', 'Cold'])]
                if not low_engagement_dms.empty:
                    flags.append(f"Decision Maker '{low_engagement_dms.iloc[0]['First_Name']} {low_engagement_dms.iloc[0]['Last_Name']}' engagement is Low/Cold while in Negotiation")
                    risk_score += 2

        # General high/medium/low risk classification
        classification = "🟢 LOW RISK" if risk_score == 0 else "🟡 MEDIUM RISK" if risk_score <= 2 else "🟠 HIGH RISK" if risk_score <= 5 else "🔴 CRITICAL RISK"

        return {
            "risk_score": risk_score,
            "flags": flags,
            "classification": classification
        }

    def calculate_engagement_score(self, account_id: str):
        """MODULE 3: ENGAGEMENT SCORE - Realistic implementation based on prompt rules"""
        accounts = self.data.get('account')
        contacts = self.data.get('contact')
        activities = self.data.get('activity')

        if any(df is None for df in [accounts, contacts, activities]):
            return {"engagement_score": 0, "classification": "🧊 COLD"}

        activities_acc = activities[activities['Account_ID'] == account_id]
        contacts_acc = contacts[contacts['Account_ID'] == account_id]

        # 1. Recency (30%)
        recency_score = 0
        if not activities_acc.empty:
            last_date = pd.to_datetime(activities_acc['Activity_Date']).max()
            if pd.notna(last_date):
                if last_date.tzinfo is not None:
                    last_date = last_date.tz_localize(None)
                days_since = (datetime.now() - last_date).days
            else:
                days_since = 999
            if days_since <= 0: recency_score = 100
            elif days_since <= 7: recency_score = 90
            elif days_since <= 14: recency_score = 75
            elif days_since <= 30: recency_score = 50
            elif days_since <= 45: recency_score = 25
            else: recency_score = 0
        else:
            recency_score = 0

        # 2. Frequency (25%)
        freq_score = 0
        if not activities_acc.empty:
            # Count in last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            act_dates = pd.to_datetime(activities_acc['Activity_Date'])
            try:
                act_dates = act_dates.dt.tz_localize(None)
            except:
                pass
            recent_activities = activities_acc[act_dates > thirty_days_ago]
            recent_count = len(recent_activities)
            if recent_count >= 8: freq_score = 100
            elif recent_count >= 5: freq_score = 80
            elif recent_count >= 3: freq_score = 60
            elif recent_count >= 1: freq_score = 30
            else: freq_score = 0

        # 3. Breadth (20%)
        breadth_score = 0
        contact_count = len(contacts_acc)
        if contact_count >= 4: breadth_score = 100
        elif contact_count == 3: breadth_score = 75
        elif contact_count == 2: breadth_score = 50
        elif contact_count == 1: breadth_score = 25

        # 4. Depth (15%)
        depth_score = 0
        if not activities_acc.empty:
            unique_types = activities_acc['Activity_Type'].nunique()
            if unique_types >= 4: depth_score = 100
            elif unique_types == 3: depth_score = 75
            elif unique_types == 2: depth_score = 50
            elif unique_types == 1: depth_score = 25

        # 5. Seniority (10%)
        seniority_score = 0
        if not contacts_acc.empty:
            has_senior = not contacts_acc[contacts_acc['Role'].str.contains('Decision Maker|C-Suite|VP', na=False, case=False)].empty
            if has_senior:
                # Check if any activity is linked to a senior contact
                senior_contact_ids = contacts_acc[contacts_acc['Role'].str.contains('Decision Maker|C-Suite|VP', na=False, case=False)]['Contact_ID'].tolist()
                if not activities_acc.empty and not activities_acc[activities_acc['Contact_ID'].isin(senior_contact_ids)].empty:
                    seniority_score = 100

        total_score = (recency_score * 0.30) + (freq_score * 0.25) + (breadth_score * 0.20) + (depth_score * 0.15) + (seniority_score * 0.10)
        
        classification = "🔥 HIGHLY ENGAGED" if total_score >= 75 else "💬 MODERATELY ENGAGED" if total_score >= 50 else "🌡️ LOW ENGAGEMENT" if total_score >= 25 else "🧊 COLD"

        return {
            "engagement_score": round(total_score, 1),
            "classification": classification
        }

    def get_pipeline_analysis(self, account_id: str = None):
        """MODULE 2: PIPELINE ANALYSIS"""
        opps = self.data.get('opportunity')
        if opps is None: return {"error": "No opportunity data"}
        
        df = opps[opps['Account_ID'] == account_id] if account_id else opps
        total_value = df['Amount_USD'].sum()
        weighted_value = (df['Amount_USD'] * df['Probability_Pct'] / 100).sum()
        
        return {
            "total_value": float(total_value),
            "weighted_value": float(weighted_value),
            "deal_count": int(len(df)),
            "stage_summary": {k: float(v) for k, v in df.groupby('Stage')['Amount_USD'].sum().to_dict().items()}
        }

    def get_enriched_accounts_list(self):
        """Returns all accounts enriched with health scores, pipeline values, and activity dates."""
        accounts = self.data.get('account')
        if accounts is None:
            return []

        opps = self.data.get('opportunity')
        activities = self.data.get('activity')
        result = []

        for _, acc_row in accounts.iterrows():
            account_id = acc_row['Account_ID']
            record = {
                'Account_ID': str(acc_row.get('Account_ID', '')),
                'Account_Name': str(acc_row.get('Account_Name', '')),
                'Account_Tier': str(acc_row.get('Account_Tier', '')),
                'Industry': str(acc_row.get('Industry', '')),
                'Territory': str(acc_row.get('Territory', '')),
                'Annual_Revenue_USD': float(acc_row.get('Annual_Revenue_USD', 0)) if pd.notna(acc_row.get('Annual_Revenue_USD')) else 0,
                'Country': str(acc_row.get('Country', '')),
            }

            # Pipeline value
            if opps is not None and not opps.empty:
                acc_opps = opps[opps['Account_ID'] == account_id]
                open_opps = acc_opps[~acc_opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
                record['total_pipeline_value'] = float(open_opps['Amount_USD'].sum()) if not open_opps.empty else 0
                record['open_deal_count'] = int(len(open_opps))
            else:
                record['total_pipeline_value'] = 0
                record['open_deal_count'] = 0

            # Last activity date
            if activities is not None and not activities.empty:
                acc_acts = activities[activities['Account_ID'] == account_id]
                if not acc_acts.empty:
                    last_date = acc_acts['Activity_Date'].max()
                    record['last_activity_date'] = str(last_date)[:10] if pd.notna(last_date) else None
                else:
                    record['last_activity_date'] = None
            else:
                record['last_activity_date'] = None

            # Health score
            try:
                health = self.calculate_health_score(account_id)
                record['health_score'] = float(health.get('overall_score', 0)) if isinstance(health, dict) and 'error' not in health else 0.0
            except:
                record['health_score'] = 0.0

            result.append(record)

        return result

    def get_account_details_json(self, account_id: str):
        """Returns structured JSON details for a specific account (Opps, Contacts, Cases)."""
        result = {
            "opportunities": [],
            "contacts": [],
            "cases": [],
            "activities": []
        }
        
        # 1. Opportunities
        opps = self.data.get('opportunity')
        if opps is not None:
            acc_opps = opps[opps['Account_ID'] == account_id]
            for _, r in acc_opps.iterrows():
                result["opportunities"].append({
                    "name": str(r.get('Opp_Name', 'Unnamed Deal')),
                    "stage": str(r.get('Stage', 'Prospecting')),
                    "value": float(r.get('Amount_USD', 0)),
                    "probability": int(r.get('Probability_Pct', 0)),
                    "close_date": str(r.get('Close_Date', ''))[:10]
                })

        # 2. Contacts
        contacts = self.data.get('contact')
        if contacts is not None:
            acc_contacts = contacts[contacts['Account_ID'] == account_id]
            for _, r in acc_contacts.iterrows():
                result["contacts"].append({
                    "first_name": str(r.get('First_Name', '')),
                    "last_name": str(r.get('Last_Name', '')),
                    "role": str(r.get('Role', 'Contact')),
                    "engagement": str(r.get('Engagement_Level', 'Medium')),
                    "email": str(r.get('Email', ''))
                })

        # 3. Cases
        cases = self.data.get('case')
        if cases is not None:
            acc_cases = cases[cases['Account_ID'] == account_id]
            for _, r in acc_cases.iterrows():
                result["cases"].append({
                    "subject": str(r.get('Subject', 'No Subject')),
                    "status": str(r.get('Status', 'Open')),
                    "severity": str(r.get('Severity', 'Low')),
                    "csat": float(r.get('CSAT_Score', 0)) if pd.notna(r.get('CSAT_Score')) else 0
                })

        return result

    def get_formatted_account_data(self, account_id: str):

        """Formats all 5 sheets into the requested APEX schema for LLM context."""
        output = []
        
        # Precalculated metrics
        try:
            health = self.calculate_health_score(account_id)
            if "error" not in health:
                output.append("[Precalculated Account Health & Scorecard]")
                output.append(f"Overall Health Score: {health.get('overall_score')} / 100 ({health.get('tier')})")
                breakdown = health.get('breakdown', {})
                output.append(f"  - Revenue Health (25% weight): {breakdown.get('revenue')}/100")
                output.append(f"  - Relationship Depth (20% weight): {breakdown.get('relationship')}/100")
                output.append(f"  - Engagement Momentum (25% weight): {breakdown.get('engagement')}/100")
                output.append(f"  - Deal Progression (20% weight): {breakdown.get('deals')}/100")
                output.append(f"  - Support & Satisfaction (10% weight): {breakdown.get('support')}/100")
                
                # Try engagement classification
                eng = self.calculate_engagement_score(account_id)
                output.append(f"Engagement Level: {eng.get('classification')} (Score: {eng.get('engagement_score')}/100)")
                
                # Risk detection
                risk = self.calculate_risk_score(account_id)
                output.append(f"Risk Score: {risk.get('risk_score')} flags | Active Risks: {', '.join(risk.get('flags', []))}")
                output.append("")
        except Exception as e:
            print(f"Error appending precalculated metrics: {e}")
        
        # 1. Account
        acc = self.data.get('account')
        if acc is not None:
            row = acc[acc['Account_ID'] == account_id]
            if not row.empty:
                output.append("[Account]")
                output.append(" | ".join(row.iloc[0].astype(str).tolist()))
                output.append("")

        # 2. Opportunities
        opps = self.data.get('opportunity')
        if opps is not None:
            rows = opps[opps['Account_ID'] == account_id]
            if not rows.empty:
                output.append("[Opportunities]")
                output.append(" | ".join(rows.columns.tolist()))
                for _, r in rows.iterrows():
                    output.append(" | ".join([str(val) for val in r.tolist()]))
                output.append("")

        # 3. Contacts
        contacts = self.data.get('contact')
        if contacts is not None:
            rows = contacts[contacts['Account_ID'] == account_id]
            if not rows.empty:
                output.append("[Contacts]")
                output.append(" | ".join(rows.columns.tolist()))
                for _, r in rows.iterrows():
                    output.append(" | ".join([str(val) for val in r.tolist()]))
                output.append("")

        # 4. Activities
        activities = self.data.get('activity')
        if activities is not None:
            rows = activities[activities['Account_ID'] == account_id]
            if not rows.empty:
                output.append("[Activities]")
                output.append(" | ".join(rows.columns.tolist()))
                for _, r in rows.iterrows():
                    output.append(" | ".join([str(val) for val in r.tolist()]))
                output.append("")

        # 5. Cases
        cases = self.data.get('case')
        if cases is not None:
            rows = cases[cases['Account_ID'] == account_id]
            if not rows.empty:
                output.append("[Cases]")
                output.append(" | ".join(rows.columns.tolist()))
                for _, r in rows.iterrows():
                    output.append(" | ".join([str(val) for val in r.tolist()]))
                output.append("")
                
        return "\n".join(output)

    def calculate_opportunity_priority(self, opp_row, acc_tier: str) -> float:
        """Calculates a dynamic priority score for an opportunity."""
        # Base: Deal Amount
        amount = float(opp_row.get('Amount_USD', 0)) if pd.notna(opp_row.get('Amount_USD')) else 0
        probability = float(opp_row.get('Probability_Pct', 0)) / 100.0 if pd.notna(opp_row.get('Probability_Pct')) else 0
        
        # Priority score starts as weighted value
        score = amount * probability
        
        # Account Tier bonus
        tier = str(acc_tier).lower()
        if "strategic" in tier:
            score += 500000
        elif "key" in tier:
            score += 250000
            
        # Stage bonus (closer to closing = higher priority)
        stage = str(opp_row.get('Stage', ''))
        if stage in ['Negotiation/Review', 'Proposal/Price Quote']:
            score += 200000
        elif stage in ['Id. Decision Makers', 'Value Proposition']:
            score += 100000
            
        # Overdue close date penalty/priority
        try:
            close_date = pd.to_datetime(opp_row.get('Close_Date'))
            if pd.notna(close_date):
                if close_date.tzinfo is not None:
                    close_date = close_date.tz_localize(None)
                if close_date < datetime.now() and stage not in ['Closed Won', 'Closed Lost']:
                    score += 150000 # High priority if deal is past close date
        except:
            pass
            
        return round(score, 2)

    def calculate_risk_priority(self, account_id: str, risk_score: int) -> float:
        """Calculates a risk priority score based on risk flags and account revenue impact."""
        accounts = self.data.get('account')
        if accounts is None: return float(risk_score)
        
        acc_row = accounts[accounts['Account_ID'] == account_id]
        if acc_row.empty: return float(risk_score)
        acc_row = acc_row.iloc[0]
        
        # Base: Risk flags count * weight
        score = float(risk_score) * 100000
        
        # Revenue impact: strategic accounts get higher priority
        revenue = float(acc_row.get('Annual_Revenue_USD', 0)) if pd.notna(acc_row.get('Annual_Revenue_USD')) else 0
        score += revenue * 0.05
        
        # Engagement classification impact
        try:
            eng = self.calculate_engagement_score(account_id)
            if eng.get('classification') in ["🧊 COLD", "🌡️ LOW ENGAGEMENT"]:
                score += 50000
        except:
            pass
            
        return round(score, 2)

    def calculate_action_priority(self, urgency: int, revenue_impact: float) -> float:
        """Calculates dynamic priority score for next actions."""
        return float(urgency) * 100000 + float(revenue_impact) * 0.1

    def audit_crm_hygiene(self, account_id: str = None) -> list:
        """MODULE 3.1: Proactively detects operational CRM blind spots."""
        accounts = self.data.get('account')
        opps = self.data.get('opportunity')
        contacts = self.data.get('contact')
        activities = self.data.get('activity')
        
        gaps = []
        
        # Filter accounts
        acc_list = accounts
        if account_id and accounts is not None:
            acc_list = accounts[accounts['Account_ID'] == account_id]
            
        if acc_list is None or acc_list.empty:
            return gaps
            
        for _, acc in acc_list.iterrows():
            curr_id = acc['Account_ID']
            name = acc['Account_Name']
            tier = str(acc.get('Account_Tier', '')).lower()
            is_high_tier = "strategic" in tier or "key" in tier
            
            # A. Contacts validation
            acc_contacts = pd.DataFrame()
            if contacts is not None and not contacts.empty:
                acc_contacts = contacts[contacts['Account_ID'] == curr_id]
                
            if acc_contacts.empty:
                gaps.append(f"⚠️ CRM Hygiene Gap: No contacts are currently mapped for {name} ({curr_id}).")
            else:
                # 1. Missing Decision Maker
                has_dm = not acc_contacts[acc_contacts['Role'].str.contains('Decision Maker|C-Suite|VP', na=False, case=False)].empty
                if not has_dm:
                    gaps.append(f"⚠️ CRM Hygiene Gap: No decision-maker contacts are currently mapped for {name} ({curr_id}).")
                
                # 2. Single-Threaded account
                if len(acc_contacts) < 2:
                    gaps.append(f"⚠️ Single-Threaded Risk: Account {name} is single-threaded with only 1 contact mapped.")
                    
            # B. Opportunities validation
            if opps is not None and not opps.empty:
                acc_opps = opps[opps['Account_ID'] == curr_id]
                open_opps = acc_opps[~acc_opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
                
                for _, opp in open_opps.iterrows():
                    opp_name = opp['Opp_Name']
                    opp_id = opp['Opp_ID']
                    # 1. Missing Close Date
                    if pd.isna(opp.get('Close_Date')):
                        gaps.append(f"⚠️ Data Completeness Risk: Opportunity '{opp_name}' ({opp_id}) is missing an expected Close Date.")
                    # 2. Missing Competitor
                    if pd.isna(opp.get('Competitor')) or str(opp.get('Competitor')).strip() == '' or str(opp.get('Competitor')).lower() == 'nan':
                        gaps.append(f"⚠️ Data Completeness Risk: Opportunity '{opp_name}' ({opp_id}) is missing Competitor information.")
                        
            # C. Activities validation
            if is_high_tier:
                acc_acts = pd.DataFrame()
                if activities is not None and not activities.empty:
                    acc_acts = activities[activities['Account_ID'] == curr_id]
                    
                if acc_acts.empty:
                    gaps.append(f"⚠️ Engagement Gap: Strategic account {name} ({curr_id}) has zero logged activities.")
                else:
                    last_date = pd.to_datetime(acc_acts['Activity_Date']).max()
                    if pd.notna(last_date):
                        if last_date.tzinfo is not None:
                            last_date = last_date.tz_localize(None)
                        days = (datetime.now() - last_date).days
                        if days > 30:
                            gaps.append(f"⚠️ Engagement Gap: Strategic account {name} ({curr_id}) has no logged activities in the last {days} days (Limit: 30).")
                            
        return gaps

    def classify_answer_confidence(self, account_id: str = None) -> str:
        """MODULE 3.2: Dynamically computes an answer confidence rating."""
        gaps = self.audit_crm_hygiene(account_id)
        
        # Logic-based classification
        critical_or_hygiene_count = len(gaps)
        
        if critical_or_hygiene_count >= 4:
            return "LOW"
        elif critical_or_hygiene_count >= 1:
            return "MEDIUM"
        else:
            return "HIGH"

    def get_top_opportunities_context(self) -> str:
        """Context Builder for GLOBAL_LIST_QUERY. Prioritized, highly scanning-friendly."""
        accounts = self.data.get('account')
        opps = self.data.get('opportunity')
        
        output = []
        output.append("[Precalculated Answer Integrity]")
        confidence = self.classify_answer_confidence()
        output.append(f"Answer Confidence: {confidence}")
        
        # General hygiene summary
        gaps = self.audit_crm_hygiene()
        if gaps:
            output.append("\n[Active CRM Hygiene & Data Gaps]")
            # Display up to 5 highest-priority gaps to keep it clean
            for g in gaps[:5]:
                output.append(g)
        output.append("")
        
        if opps is not None and not opps.empty:
            output.append("[Top Opportunities (Global - Ranked by Priority Score)]")
            headers = ["Priority_Rank", "Opp_ID", "Account_Name", "Opp_Name", "Stage", "Amount_USD", "Probability", "Close_Date", "Priority_Score"]
            output.append(" | ".join(headers))
            
            opps_enriched = opps.copy()
            if accounts is not None:
                opps_enriched = opps_enriched.merge(accounts[['Account_ID', 'Account_Name', 'Account_Tier']], on='Account_ID', how='left')
            else:
                opps_enriched['Account_Name'] = "Unknown"
                opps_enriched['Account_Tier'] = "Standard"
                
            # Open opportunities only
            open_opps = opps_enriched[~opps_enriched['Stage'].isin(['Closed Won', 'Closed Lost'])].copy()
            
            if not open_opps.empty:
                # Calculate priority scores
                priorities = []
                for _, r in open_opps.iterrows():
                    score = self.calculate_opportunity_priority(r, r.get('Account_Tier', 'Standard'))
                    priorities.append(score)
                open_opps['Priority_Score'] = priorities
                
                # Sort descending
                ranked_opps = open_opps.sort_values(by='Priority_Score', ascending=False)
                
                rank = 1
                for _, r in ranked_opps.iterrows():
                    amount = float(r.get('Amount_USD', 0)) if pd.notna(r.get('Amount_USD')) else 0
                    prob = int(r.get('Probability_Pct', 0)) if pd.notna(r.get('Probability_Pct')) else 0
                    score = float(r.get('Priority_Score', 0))
                    output.append(f"{rank} | {r.get('Opp_ID')} | {r.get('Account_Name')} | {r.get('Opp_Name')} | {r.get('Stage')} | ${amount:,.2f} | {prob}% | {str(r.get('Close_Date'))[:10]} | {score:,.2f}")
                    rank += 1
            else:
                output.append("No open opportunities found in the database.")
            output.append("")
            
        return "\n".join(output)

    def get_risk_context(self) -> str:
        """Context Builder for RISK_ANALYSIS_QUERY. Focuses on prioritized risk metadata."""
        accounts = self.data.get('account')
        
        output = []
        output.append("[Precalculated Answer Integrity]")
        confidence = self.classify_answer_confidence()
        output.append(f"Answer Confidence: {confidence}")
        output.append("")
        
        if accounts is not None and not accounts.empty:
            output.append("[Prioritized Risks Summary]")
            headers = ["Priority_Rank", "Account_ID", "Account_Name", "Risk_Score", "Classification", "Active_Flags", "Risk_Priority"]
            output.append(" | ".join(headers))
            
            risk_list = []
            for _, r in accounts.iterrows():
                acc_id = r['Account_ID']
                risk_data = self.calculate_risk_score(acc_id)
                risk_score = risk_data.get('risk_score', 0)
                risk_priority = self.calculate_risk_priority(acc_id, risk_score)
                
                # Audit specific gaps
                gaps = self.audit_crm_hygiene(acc_id)
                risk_list.append({
                    "Account_ID": acc_id,
                    "Account_Name": r['Account_Name'],
                    "Risk_Score": risk_score,
                    "Classification": risk_data.get('classification', '🟢 LOW RISK'),
                    "Active_Flags": ", ".join(risk_data.get('flags', []) + gaps[:2]),
                    "Risk_Priority": risk_priority
                })
                
            risk_df = pd.DataFrame(risk_list)
            # Sort by Priority DESC
            ranked_risks = risk_df.sort_values(by='Risk_Priority', ascending=False)
            
            rank = 1
            for _, r in ranked_risks.iterrows():
                output.append(f"{rank} | {r['Account_ID']} | {r['Account_Name']} | {r['Risk_Score']} | {r['Classification']} | {r['Active_Flags']} | {r['Risk_Priority']:,.2f}")
                rank += 1
            output.append("")
            
        return "\n".join(output)

    def get_pipeline_context(self) -> str:
        """Context Builder for PIPELINE_SUMMARY_QUERY. Focused entirely on aggregated pipeline metrics."""
        accounts = self.data.get('account')
        opps = self.data.get('opportunity')
        
        output = []
        output.append("[Precalculated Answer Integrity]")
        confidence = self.classify_answer_confidence()
        output.append(f"Answer Confidence: {confidence}")
        output.append("")
        
        if opps is not None and not opps.empty:
            open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])].copy()
            total_value = open_opps['Amount_USD'].sum() if not open_opps.empty else 0
            weighted_value = (open_opps['Amount_USD'] * open_opps['Probability_Pct'] / 100.0).sum() if not open_opps.empty else 0
            
            output.append("[Pipeline Aggregated Metrics]")
            output.append(f"Total Open Pipeline: ${total_value:,.2f}")
            output.append(f"Weighted Forecast Value: ${weighted_value:,.2f}")
            output.append(f"Total Active Open Deals: {len(open_opps)}")
            output.append("")
            
            # Stage Breakdown
            output.append("[Active Stage Breakdown]")
            output.append("Stage | Deal_Count | Total_Amount_USD")
            if not open_opps.empty:
                breakdown = open_opps.groupby('Stage').agg(
                    Deal_Count=('Opp_ID', 'count'),
                    Total_Amount=('Amount_USD', 'sum')
                ).reset_index()
                for _, r in breakdown.iterrows():
                    amount = float(r['Total_Amount'])
                    output.append(f"{r['Stage']} | {r['Deal_Count']} | ${amount:,.2f}")
            output.append("")
            
            # Top open deals
            output.append("[Top Open Opportunities (Ranked by Opportunity Priority)]")
            headers = ["Opp_ID", "Opp_Name", "Stage", "Amount_USD", "Probability", "Close_Date", "Priority_Score"]
            output.append(" | ".join(headers))
            
            if not open_opps.empty:
                opps_enriched = open_opps.copy()
                if accounts is not None:
                    opps_enriched = opps_enriched.merge(accounts[['Account_ID', 'Account_Tier']], on='Account_ID', how='left')
                else:
                    opps_enriched['Account_Tier'] = 'Standard'
                    
                priorities = []
                for _, r in opps_enriched.iterrows():
                    score = self.calculate_opportunity_priority(r, r.get('Account_Tier', 'Standard'))
                    priorities.append(score)
                opps_enriched['Priority_Score'] = priorities
                
                ranked_opps = opps_enriched.sort_values(by='Priority_Score', ascending=False).head(10)
                for _, r in ranked_opps.iterrows():
                    amount = float(r['Amount_USD'])
                    prob = int(r['Probability_Pct'])
                    output.append(f"{r['Opp_ID']} | {r['Opp_Name']} | {r['Stage']} | ${amount:,.2f} | {prob}% | {str(r['Close_Date'])[:10]} | {r['Priority_Score']:,.2f}")
            output.append("")
            
        return "\n".join(output)

    def get_contact_context(self, account_id: str = None) -> str:
        """Context Builder for CONTACT_QUERY. Returns key stakeholders and engagement levels."""
        accounts = self.data.get('account')
        contacts = self.data.get('contact')
        
        output = []
        output.append("[Precalculated Answer Integrity]")
        confidence = self.classify_answer_confidence(account_id)
        output.append(f"Answer Confidence: {confidence}")
        output.append("")
        
        # Gaps check
        gaps = self.audit_crm_hygiene(account_id)
        if gaps:
            output.append("[Active Stakeholder Mapping Gaps]")
            contact_gaps = [g for g in gaps if "contact" in g.lower() or "decision-maker" in g.lower() or "single-threaded" in g.lower()]
            for g in contact_gaps:
                output.append(g)
            output.append("")
            
        if contacts is not None and not contacts.empty:
            output.append("[Key Contacts & Relationship Profiles]")
            headers = ["Contact_ID", "Account_Name", "Name", "Role", "Engagement_Level", "Last_Contact_Date", "Department"]
            output.append(" | ".join(headers))
            
            contacts_enriched = contacts.copy()
            if accounts is not None:
                contacts_enriched = contacts_enriched.merge(accounts[['Account_ID', 'Account_Name']], on='Account_ID', how='left')
            else:
                contacts_enriched['Account_Name'] = "Unknown"
                
            # Filter by account if supplied
            if account_id:
                contacts_enriched = contacts_enriched[contacts_enriched['Account_ID'] == account_id]
                
            for _, r in contacts_enriched.iterrows():
                name = f"{r.get('First_Name', '')} {r.get('Last_Name', '')}".strip()
                last_contact = str(r.get('Last_Contact_Date', ''))[:10] if pd.notna(r.get('Last_Contact_Date')) else "Never"
                output.append(f"{r.get('Contact_ID')} | {r.get('Account_Name')} | {name} | {r.get('Role')} | {r.get('Engagement_Level')} | {last_contact} | {r.get('Department')}")
            output.append("")
            
        return "\n".join(output)

    def get_account_context(self, account_id: str) -> str:
        """Context Builder for ACCOUNT_PLAN_QUERY. Aggregates deep, contextual account details."""
        output = []
        
        # Precalculated scorecards and answer integrity
        output.append("[Precalculated Answer Integrity]")
        confidence = self.classify_answer_confidence(account_id)
        output.append(f"Answer Confidence: {confidence}")
        output.append("")
        
        # Hygiene audits
        gaps = self.audit_crm_hygiene(account_id)
        if gaps:
            output.append("[CRM Hygiene Gaps & Risks]")
            for g in gaps:
                output.append(g)
            output.append("")
            
        # Call the existing formatted builder to get full tables
        formatted_tables = self.get_formatted_account_data(account_id)
        output.append(formatted_tables)
        
        return "\n".join(output)

    def get_global_context(self):
        """Formats a global context summary containing top opportunities, health breakdown, and general system status."""
        output = []
        
        # 1. Accounts overview (ID, Name, Tier, Health Score)
        accounts = self.data.get('account')
        if accounts is not None:
            output.append("[Global Accounts Overview]")
            headers = ["Account_ID", "Account_Name", "Account_Tier", "Health_Score", "Status"]
            output.append(" | ".join(headers))
            
            for _, r in accounts.iterrows():
                acc_id = r['Account_ID']
                try:
                    health = self.calculate_health_score(acc_id)
                    score = health.get('overall_score', 0)
                    tier = health.get('tier', 'Unknown')
                except:
                    score = 0.0
                    tier = 'Unknown'
                output.append(f"{acc_id} | {r['Account_Name']} | {r['Account_Tier']} | {score} | {tier}")
            output.append("")

        # 2. Top Opportunities across all accounts
        opps = self.data.get('opportunity')
        if opps is not None and not opps.empty:
            output.append("[Top Opportunities (Global)]")
            headers = ["Opp_ID", "Account_Name", "Opp_Name", "Stage", "Amount_USD", "Probability_Pct", "Close_Date", "Owner"]
            output.append(" | ".join(headers))
            
            opps_enriched = opps.copy()
            if accounts is not None:
                opps_enriched = opps_enriched.merge(accounts[['Account_ID', 'Account_Name']], on='Account_ID', how='left')
            
            top_opps = opps_enriched.sort_values(by='Amount_USD', ascending=False).head(15)
            for _, r in top_opps.iterrows():
                output.append(f"{r.get('Opp_ID')} | {r.get('Account_Name')} | {r.get('Opp_Name')} | {r.get('Stage')} | ${r.get('Amount_USD'):,.2f} | {r.get('Probability_Pct')}% | {str(r.get('Close_Date'))[:10]} | {r.get('Owner')}")
            output.append("")

        # 3. Jeopardy / At-Risk Accounts (Overall score < 60)
        output.append("[Jeopardy Accounts Summary (Health < 60)]")
        has_jeopardy = False
        if accounts is not None:
            for _, r in accounts.iterrows():
                acc_id = r['Account_ID']
                try:
                    health = self.calculate_health_score(acc_id)
                    score = health.get('overall_score', 0)
                    if score < 60:
                        has_jeopardy = True
                        output.append(f"Account: {r['Account_Name']} ({acc_id}) | Score: {score} | Reason: {health.get('tier')}")
                except:
                    pass
        if not has_jeopardy:
            output.append("No accounts currently flagged as Jeopardy (all scores >= 60).")
        output.append("")

        # 4. Critical Support Cases
        cases = self.data.get('case')
        if cases is not None and not cases.empty:
            output.append("[Open Critical & High Severity Support Cases]")
            headers = ["Case_ID", "Account_Name", "Subject", "Severity", "Status", "Open_Date"]
            output.append(" | ".join(headers))
            
            cases_enriched = cases.copy()
            if accounts is not None:
                cases_enriched = cases_enriched.merge(accounts[['Account_ID', 'Account_Name']], on='Account_ID', how='left')
                
            critical_cases = cases_enriched[cases_enriched['Severity'].isin(['Critical', 'High']) & (cases_enriched['Status'] != 'Closed')]
            if not critical_cases.empty:
                for _, r in critical_cases.iterrows():
                    output.append(f"{r.get('Case_ID')} | {r.get('Account_Name')} | {r.get('Subject')} | {r.get('Severity')} | {r.get('Status')} | {str(r.get('Open_Date'))[:10]}")
            else:
                output.append("No open Critical or High severity cases found.")
            output.append("")

        return "\n".join(output)

    # ─── Phase 4: Additive Analytics Methods ────────────────────

    def get_stage_distribution(self) -> dict:
        """Returns stage distribution for concentration analysis.
        Returns: dict of stage -> {count, total_amount, pct_of_pipeline}"""
        opps = self.data.get('opportunity')
        if opps is None or opps.empty:
            return {}

        open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
        if open_opps.empty:
            return {}

        total_pipeline = open_opps['Amount_USD'].sum()
        if total_pipeline == 0:
            return {}

        result = {}
        stage_agg = open_opps.groupby('Stage').agg(
            count=('Opp_ID', 'count'),
            total_amount=('Amount_USD', 'sum')
        )

        for stage, row in stage_agg.iterrows():
            result[stage] = {
                "count": int(row['count']),
                "total_amount": float(row['total_amount']),
                "pct_of_pipeline": round((row['total_amount'] / total_pipeline) * 100, 1)
            }

        return result

    def get_close_window_deals(self, days: int = 30) -> list:
        """Returns deals closing within the next N days with urgency metadata.
        Returns: list of dicts with opp details + days_until_close."""
        opps = self.data.get('opportunity')
        if opps is None or opps.empty:
            return []

        now = datetime.now()
        window_end = now + timedelta(days=days)
        open_opps = opps[~opps['Stage'].isin(['Closed Won', 'Closed Lost'])]
        if open_opps.empty:
            return []

        results = []
        for _, opp in open_opps.iterrows():
            try:
                close_date = pd.to_datetime(opp.get('Close_Date'))
                if pd.notna(close_date):
                    if close_date.tzinfo is not None:
                        close_date = close_date.tz_localize(None)
                    if now <= close_date <= window_end:
                        days_until = (close_date - now).days
                        results.append({
                            "Opp_ID": opp['Opp_ID'],
                            "Opp_Name": opp['Opp_Name'],
                            "Account_ID": opp['Account_ID'],
                            "Stage": opp['Stage'],
                            "Amount_USD": float(opp['Amount_USD']) if pd.notna(opp['Amount_USD']) else 0,
                            "Close_Date": str(close_date)[:10],
                            "Days_Until_Close": days_until
                        })
            except Exception:
                pass

        # Sort by urgency (soonest first)
        results.sort(key=lambda x: x['Days_Until_Close'])
        return results

    def get_engagement_decay_accounts(self) -> list:
        """Returns strategic/key accounts with declining engagement (30+ days inactive).
        Returns: list of dicts with account details + days_since_last_activity."""
        accounts = self.data.get('account')
        activities = self.data.get('activity')
        if accounts is None or accounts.empty:
            return []

        now = datetime.now()
        results = []

        for _, acc in accounts.iterrows():
            tier = str(acc.get('Account_Tier', '')).lower()
            if 'strategic' not in tier and 'key' not in tier:
                continue

            days_since = 999
            if activities is not None and not activities.empty:
                acc_acts = activities[activities['Account_ID'] == acc['Account_ID']]
                if not acc_acts.empty:
                    last_date = pd.to_datetime(acc_acts['Activity_Date']).max()
                    if pd.notna(last_date):
                        try:
                            if last_date.tzinfo is not None:
                                last_date = last_date.tz_localize(None)
                        except Exception:
                            pass
                        days_since = (now - last_date).days

            if days_since > 30:
                results.append({
                    "Account_ID": acc['Account_ID'],
                    "Account_Name": acc['Account_Name'],
                    "Account_Tier": acc.get('Account_Tier', 'Standard'),
                    "Days_Since_Last_Activity": days_since if days_since < 900 else None
                })

        return results
