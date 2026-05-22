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
            # For development, if file doesn't exist, we might fail or use mock data
            # But the user provided a specific path, so we fail if missing
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
        delta = now - date_val
        return delta.days

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
            # Frequency bonus
            recent_count = len(activities_acc[activities_acc['Activity_Date'] > (datetime.now() - timedelta(days=30))])
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
            # For simplicity, 80 if no stale deals, else 60
            deal_score += 20 
        else:
            deal_score = 100 # No deals needed = healthy? Or 0? Let's say 50 neutral.

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
        """MODULE 4: RISK DETECTION"""
        # Count risk flags and weight them
        flags = []
        # Placeholder for real logic
        return {"risk_score": 2, "flags": ["No activity in 60 days", "Single-threaded"]}

    def calculate_engagement_score(self, account_id: str):
        """MODULE 3: ENGAGEMENT SCORE"""
        # Recency, Frequency, Breadth, Depth, Senior Reach
        return {"engagement_score": 75, "classification": "🔥 HIGHLY ENGAGED"}

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
        
        # 1. Account
        acc = self.data.get('account')
        if acc is not None:
            row = acc[acc['Account_ID'] == account_id]
            if not row.empty:
                output.append("[Account]")
                output.append(" | ".join([str(val) for val in row.iloc[0].tolist()]))
                output.append("")

        # 2. Opportunities
        opps = self.data.get('opportunity')
        if opps is not None:
            rows = opps[opps['Account_ID'] == account_id]
            if not rows.empty:
                output.append("[Opportunities]")
                for _, r in rows.iterrows():
                    output.append(" | ".join([str(val) for val in r.tolist()]))
                output.append("")

        # 3. Contacts
        contacts = self.data.get('contact')
        if contacts is not None:
            rows = contacts[contacts['Account_ID'] == account_id]
            if not rows.empty:
                output.append("[Contacts]")
                for _, r in rows.iterrows():
                    output.append(" | ".join([str(val) for val in r.tolist()]))
                output.append("")

        # 4. Activities
        activities = self.data.get('activity')
        if activities is not None:
            rows = activities[activities['Account_ID'] == account_id]
            if not rows.empty:
                output.append("[Activities]")
                for _, r in rows.iterrows():
                    output.append(" | ".join([str(val) for val in r.tolist()]))
                output.append("")

        # 5. Cases
        cases = self.data.get('case')
        if cases is not None:
            rows = cases[cases['Account_ID'] == account_id]
            if not rows.empty:
                output.append("[Cases]")
                for _, r in rows.iterrows():
                    output.append(" | ".join([str(val) for val in r.tolist()]))
                output.append("")
                
        return "\n".join(output)
