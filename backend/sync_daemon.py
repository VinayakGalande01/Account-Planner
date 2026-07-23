"""
CRM DATA SYNC DAEMON (sync_daemon.py)
Reads Salesforce dummy Excel datasets and synchronizes Account, Opportunity,
Contact, Case, and Activity data directly into the user-isolated database.
"""

# --- SECTION 1: Dependencies & Environment Setup ---
# Imports data processing and ORM libraries for parsing Excel sheets and DB operations.
import os
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import numpy as np
import httpx
from sqlalchemy.orm import Session
from database import SessionLocal
import models.user
from models.crm_models import Account, Opportunity, Contact, Case, Activity

# --- SECTION 2: Dataset Path Resolution & Value Sanitization ---
# Resolves the local Excel file location and cleans pandas NaN/NaT values for database safety.
def get_data_path():
    data_path = os.getenv("DATA_PATH", "")
    if not data_path or not os.path.exists(data_path):
        dataset_1 = r"C:\Users\VINAYAK\Downloads\SF_AccountingAgent_DummyData.xlsx"
        dataset_2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SF_AccountingAgent_DummyData.xlsx")
        
        if os.path.exists(dataset_1):
            data_path = dataset_1
        elif os.path.exists(dataset_2):
            data_path = dataset_2
        else:
            possible_paths = [
                "SF_AccountingAgent_DummyData.xlsx",
                "../SF_AccountingAgent_DummyData.xlsx",
                "/Users/theabhijitjagtap/Projects/Account_Planner/SF_AccountingAgent_DummyData.xlsx"
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    data_path = p
                    break
    return data_path

def clean_value(val):
    if pd.isna(val):
        return None
    if isinstance(val, (np.integer, np.floating)):
        return val.item()
    return str(val)

# --- SECTION 3: Per-User Database Synchronization ---
# Wipes existing records for the specified user and re-populates tables from Excel.
def sync_crm_to_sqlite_for_user(db: Session, user_id: int, excel_path: str = None) -> bool:
    db.info["user_id"] = str(user_id)
    
    if not excel_path:
        excel_path = get_data_path()
    if not excel_path or not os.path.exists(excel_path):
        print(f"Error: Excel data file not found at path: {excel_path}")
        return False

    print(f"Starting database sync for user {user_id} from Excel: {excel_path}")
    sheets = pd.read_excel(excel_path, sheet_name=None)
    data = {name.lower(): df for name, df in sheets.items()}

    try:
        db.query(Activity).filter(Activity.user_id == user_id).delete()
        db.query(Case).filter(Case.user_id == user_id).delete()
        db.query(Contact).filter(Contact.user_id == user_id).delete()
        db.query(Opportunity).filter(Opportunity.user_id == user_id).delete()
        db.query(Account).filter(Account.user_id == user_id).delete()
        db.commit()

        # 1. Sync Accounts
        accounts_df = data.get("account")
        if accounts_df is not None:
            for _, r in accounts_df.iterrows():
                annual_rev = r.get("Annual_Revenue_USD", 0)
                if pd.isna(annual_rev):
                    annual_rev = 0
                acc = Account(
                    Account_ID=f"{user_id}_{clean_value(r.get('Account_ID'))}",
                    Account_Name=clean_value(r.get("Account_Name")),
                    Account_Tier=clean_value(r.get("Account_Tier")),
                    Industry=clean_value(r.get("Industry")),
                    Territory=clean_value(r.get("Territory")),
                    Annual_Revenue_USD=float(annual_rev),
                    Country=clean_value(r.get("Country")),
                    Health_Score=float(clean_value(r.get("Health_Score"))) if r.get("Health_Score") is not None and not pd.isna(r.get("Health_Score")) else 80.0,
                    user_id=user_id
                )
                db.add(acc)
            db.commit()
            print(f"  Synced {len(accounts_df)} Accounts for user {user_id}.")

        # 2. Sync Opportunities
        opps_df = data.get("opportunity")
        if opps_df is not None:
            for _, r in opps_df.iterrows():
                amt = r.get("Amount_USD", 0)
                if pd.isna(amt):
                    amt = 0
                prob = r.get("Probability_Pct", 0)
                if pd.isna(prob):
                    prob = 0
                opp = Opportunity(
                    Opp_ID=f"{user_id}_{clean_value(r.get('Opp_ID'))}",
                    Account_ID=f"{user_id}_{clean_value(r.get('Account_ID'))}",
                    Opp_Name=clean_value(r.get("Opp_Name")),
                    Amount_USD=float(amt),
                    Stage=clean_value(r.get("Stage")),
                    Close_Date=clean_value(r.get("Close_Date")),
                    Probability_Pct=int(prob),
                    Competitor=clean_value(r.get("Competitor")),
                    user_id=user_id
                )
                db.add(opp)
            db.commit()
            print(f"  Synced {len(opps_df)} Opportunities for user {user_id}.")

        # 3. Sync Contacts
        contacts_df = data.get("contact")
        if contacts_df is not None:
            for _, r in contacts_df.iterrows():
                ct = Contact(
                    Contact_ID=f"{user_id}_{clean_value(r.get('Contact_ID'))}",
                    Account_ID=f"{user_id}_{clean_value(r.get('Account_ID'))}",
                    First_Name=clean_value(r.get("First_Name")),
                    Last_Name=clean_value(r.get("Last_Name")),
                    Role=clean_value(r.get("Role")),
                    Department=clean_value(r.get("Department")),
                    Engagement_Level=clean_value(r.get("Engagement_Level")),
                    Email=clean_value(r.get("Email")),
                    Phone=clean_value(r.get("Phone")),
                    Last_Contact_Date=clean_value(r.get("Last_Contact_Date")),
                    user_id=user_id
                )
                db.add(ct)
            db.commit()
            print(f"  Synced {len(contacts_df)} Contacts for user {user_id}.")

        # 4. Sync Cases
        cases_df = data.get("case")
        if cases_df is not None:
            for _, r in cases_df.iterrows():
                csat = r.get("CSAT_Score", 0)
                if pd.isna(csat):
                    csat = 0.0
                c = Case(
                    Case_ID=f"{user_id}_{clean_value(r.get('Case_ID'))}",
                    Account_ID=f"{user_id}_{clean_value(r.get('Account_ID'))}",
                    Subject=clean_value(r.get("Subject")),
                    Status=clean_value(r.get("Status")),
                    Severity=clean_value(r.get("Severity")),
                    CSAT_Score=float(csat),
                    Open_Date=clean_value(r.get("Open_Date")),
                    user_id=user_id
                )
                db.add(c)
            db.commit()
            print(f"  Synced {len(cases_df)} Cases for user {user_id}.")

        # 5. Sync Activities
        activities_df = data.get("activity")
        if activities_df is not None:
            activities_list = []
            for _, r in activities_df.iterrows():
                act = Activity(
                    Activity_ID=f"{user_id}_{clean_value(r.get('Activity_ID'))}",
                    Account_ID=f"{user_id}_{clean_value(r.get('Account_ID'))}",
                    Contact_ID=f"{user_id}_{clean_value(r.get('Contact_ID'))}" if r.get("Contact_ID") and not pd.isna(r.get("Contact_ID")) else None,
                    Activity_Type=clean_value(r.get("Activity_Type")),
                    Type=clean_value(r.get("Activity_Type")), # For compatibility with 'Type' field
                    Description=clean_value(r.get("Notes") or r.get("Description")),
                    Activity_Date=clean_value(r.get("Activity_Date")),
                    user_id=user_id
                )
                db.add(act)
                
                # Append dict representation for vector store RAG indexing
                activities_list.append({
                    "activity_id": act.Activity_ID,
                    "account_id": act.Account_ID,
                    "type": act.Activity_Type,
                    "description": act.Description,
                    "date": act.Activity_Date
                })
            db.commit()
            print(f"  Synced {len(activities_df)} Activities for user {user_id}.")

            # Trigger local RAG vector indexing
            try:
                from vector_store import vector_store
                vector_store.index_activities(activities_list, user_id=user_id)
            except Exception as index_err:
                print(f"Warning: Failed to index activities to vector store: {index_err}")

        print(f"Database sync for user {user_id} completed successfully!")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error during database sync for user {user_id}: {e}")
        return False

def sync_crm_to_sqlite() -> bool:
    # Backwards compatibility fallback (e.g. for verify_all.py or admin sync)
    db = SessionLocal()
    try:
        from models.user import User
        from auth.password import hash_password
        
        # Get or create default admin user for Company-A
        default_user = db.query(User).filter(User.email == "admin@apex.com").first()
        if not default_user:
            default_user = User(name="Default Admin", email="admin@apex.com", hashed_password=hash_password("admin"))
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            
        # Get or create AbhiTech admin user for Company-B
        abhitech_user = db.query(User).filter(User.email == "abhitech_admin@apex.com").first()
        if not abhitech_user:
            abhitech_user = User(name="AbhiTech Admin", email="abhitech_admin@apex.com", hashed_password=hash_password("admin123"))
            db.add(abhitech_user)
            db.commit()
            db.refresh(abhitech_user)

        # Sync original dataset for default admin
        success_1 = sync_crm_to_sqlite_for_user(db, default_user.id)
        
        # Sync AbhiTech dataset for AbhiTech admin
        abhitech_dataset_path = "/Users/theabhijitjagtap/Downloads/AbhiTech_DummyData_100Companies.xlsx"
        print(f"Syncing secondary dataset from: {abhitech_dataset_path}")
        success_2 = sync_crm_to_sqlite_for_user(db, abhitech_user.id, excel_path=abhitech_dataset_path)
        
        return success_1 and success_2
    finally:
        db.close()

def sync_salesforce_to_db(db: Session, user_id: int, instance_url: str, access_token: str) -> bool:
    if access_token == "mock_token":
        print(f"Detected mock token for Salesforce. Falling back to local Excel seed for user {user_id}")
        return sync_crm_to_sqlite_for_user(db, user_id)

    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Clear existing tables for this user first
        db.query(Activity).filter(Activity.user_id == user_id).delete()
        db.query(Case).filter(Case.user_id == user_id).delete()
        db.query(Contact).filter(Contact.user_id == user_id).delete()
        db.query(Opportunity).filter(Opportunity.user_id == user_id).delete()
        db.query(Account).filter(Account.user_id == user_id).delete()
        db.commit()

        # 1. Sync Accounts
        acc_url = f"{instance_url}/services/data/v57.0/query?q=SELECT+Id,Name,Industry,BillingCountry,AnnualRevenue+FROM+Account"
        r = httpx.get(acc_url, headers=headers)
        r.raise_for_status()
        sf_accounts = r.json().get("records", [])
        
        for sa in sf_accounts:
            acc = Account(
                Account_ID=sa.get("Id"),
                Account_Name=sa.get("Name"),
                Account_Tier="Tier 1" if (sa.get("AnnualRevenue") or 0) > 1000000 else "Tier 2",
                Industry=sa.get("Industry"),
                Territory="Global",
                Annual_Revenue_USD=float(sa.get("AnnualRevenue") or 0),
                Country=sa.get("BillingCountry"),
                Health_Score=80.0,
                user_id=user_id
            )
            db.add(acc)
        db.commit()

        # 2. Sync Opportunities
        opp_url = f"{instance_url}/services/data/v57.0/query?q=SELECT+Id,AccountId,Name,Amount,StageName,CloseDate,Probability+FROM+Opportunity"
        r = httpx.get(opp_url, headers=headers)
        r.raise_for_status()
        sf_opps = r.json().get("records", [])
        for so in sf_opps:
            opp = Opportunity(
                Opp_ID=so.get("Id"),
                Account_ID=so.get("AccountId"),
                Opp_Name=so.get("Name"),
                Amount_USD=float(so.get("Amount") or 0),
                Stage=so.get("StageName"),
                Close_Date=so.get("CloseDate"),
                Probability_Pct=int(so.get("Probability") or 0),
                Competitor="Unknown",
                user_id=user_id
            )
            db.add(opp)
        db.commit()

        # 3. Sync Contacts
        con_url = f"{instance_url}/services/data/v57.0/query?q=SELECT+Id,AccountId,FirstName,LastName,Email,Phone,Title+FROM+Contact"
        r = httpx.get(con_url, headers=headers)
        r.raise_for_status()
        sf_contacts = r.json().get("records", [])
        for sc in sf_contacts:
            ct = Contact(
                Contact_ID=sc.get("Id"),
                Account_ID=sc.get("AccountId"),
                First_Name=sc.get("FirstName"),
                Last_Name=sc.get("LastName"),
                Role=sc.get("Title"),
                Department="Sales",
                Engagement_Level="Medium",
                Email=sc.get("Email"),
                Phone=sc.get("Phone"),
                Last_Contact_Date=None,
                user_id=user_id
            )
            db.add(ct)
        db.commit()

        # 4. Sync Cases
        case_url = f"{instance_url}/services/data/v57.0/query?q=SELECT+Id,AccountId,Subject,Status+FROM+Case"
        r = httpx.get(case_url, headers=headers)
        r.raise_for_status()
        sf_cases = r.json().get("records", [])
        for scase in sf_cases:
            c = Case(
                Case_ID=scase.get("Id"),
                Account_ID=scase.get("AccountId"),
                Subject=scase.get("Subject"),
                Status=scase.get("Status"),
                Severity="Medium",
                CSAT_Score=4.0,
                Open_Date=None,
                user_id=user_id
            )
            db.add(c)
        db.commit()

        # 5. Sync Activities
        act_url = f"{instance_url}/services/data/v57.0/query?q=SELECT+Id,AccountId,Subject,Description,ActivityDate+FROM+Task"
        r = httpx.get(act_url, headers=headers)
        r.raise_for_status()
        sf_tasks = r.json().get("records", [])
        activities_list = []
        for st in sf_tasks:
            act = Activity(
                Activity_ID=st.get("Id"),
                Account_ID=st.get("AccountId"),
                Contact_ID=None,
                Activity_Type=st.get("Subject") or "Task",
                Type=st.get("Subject") or "Task",
                Description=st.get("Description"),
                Activity_Date=st.get("ActivityDate"),
                user_id=user_id
            )
            db.add(act)
            activities_list.append({
                "activity_id": act.Activity_ID,
                "account_id": act.Account_ID,
                "type": act.Activity_Type,
                "description": act.Description,
                "date": act.Activity_Date
            })
        db.commit()

        # Index to vector store
        try:
            from vector_store import vector_store
            vector_store.index_activities(activities_list, user_id=user_id)
        except Exception as e:
            print(f"Warning: Failed to index SF activities: {e}")

        return True
    except Exception as e:
        db.rollback()
        print(f"Salesforce Sync Error: {e}")
        return False

def sync_hubspot_to_db(db: Session, user_id: int, access_token: str) -> bool:
    if access_token == "mock_token":
        print(f"Detected mock token for HubSpot. Falling back to local Excel seed for user {user_id}")
        return sync_crm_to_sqlite_for_user(db, user_id)

    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Clear existing tables for this user first
        db.query(Activity).filter(Activity.user_id == user_id).delete()
        db.query(Case).filter(Case.user_id == user_id).delete()
        db.query(Contact).filter(Contact.user_id == user_id).delete()
        db.query(Opportunity).filter(Opportunity.user_id == user_id).delete()
        db.query(Account).filter(Account.user_id == user_id).delete()
        db.commit()

        # 1. Sync Companies -> Accounts
        r = httpx.get("https://api.hubapi.com/crm/v3/objects/companies?properties=name,industry,country,annualrevenue", headers=headers)
        r.raise_for_status()
        hs_companies = r.json().get("results", [])
        for hc in hs_companies:
            props = hc.get("properties", {})
            acc = Account(
                Account_ID=hc.get("id"),
                Account_Name=props.get("name"),
                Account_Tier="Tier 1" if float(props.get("annualrevenue") or 0) > 1000000 else "Tier 2",
                Industry=props.get("industry"),
                Territory="Global",
                Annual_Revenue_USD=float(props.get("annualrevenue") or 0),
                Country=props.get("country"),
                Health_Score=80.0,
                user_id=user_id
            )
            db.add(acc)
        db.commit()

        # 2. Sync Deals -> Opportunities
        r = httpx.get("https://api.hubapi.com/crm/v3/objects/deals?properties=dealname,amount,dealstage,closedate", headers=headers)
        r.raise_for_status()
        hs_deals = r.json().get("results", [])
        for hd in hs_deals:
            props = hd.get("properties", {})
            opp = Opportunity(
                Opp_ID=hd.get("id"),
                Account_ID=None,
                Opp_Name=props.get("dealname"),
                Amount_USD=float(props.get("amount") or 0),
                Stage=props.get("dealstage"),
                Close_Date=props.get("closedate"),
                Probability_Pct=50,
                Competitor="Unknown",
                user_id=user_id
            )
            db.add(opp)
        db.commit()

        # 3. Sync Contacts -> Contacts
        r = httpx.get("https://api.hubapi.com/crm/v3/objects/contacts?properties=firstname,lastname,email,phone,jobtitle", headers=headers)
        r.raise_for_status()
        hs_contacts = r.json().get("results", [])
        for hcon in hs_contacts:
            props = hcon.get("properties", {})
            ct = Contact(
                Contact_ID=hcon.get("id"),
                Account_ID=None,
                First_Name=props.get("firstname"),
                Last_Name=props.get("lastname"),
                Role=props.get("jobtitle"),
                Department="Sales",
                Engagement_Level="Medium",
                Email=props.get("email"),
                Phone=props.get("phone"),
                Last_Contact_Date=None,
                user_id=user_id
            )
            db.add(ct)
        db.commit()

        # 4. Sync Tickets -> Cases
        r = httpx.get("https://api.hubapi.com/crm/v3/objects/tickets?properties=subject,hs_ticket_status,hs_ticket_priority", headers=headers)
        r.raise_for_status()
        hs_tickets = r.json().get("results", [])
        for ht in hs_tickets:
            props = ht.get("properties", {})
            c = Case(
                Case_ID=ht.get("id"),
                Account_ID=None,
                Subject=props.get("subject"),
                Status=props.get("hs_ticket_status"),
                Severity=props.get("hs_ticket_priority") or "Medium",
                CSAT_Score=4.0,
                Open_Date=None,
                user_id=user_id
            )
            db.add(c)
        db.commit()

        # 5. Sync Meetings -> Activities
        r = httpx.get("https://api.hubapi.com/crm/v3/objects/meetings?properties=hs_meeting_title,hs_meeting_body,hs_meeting_start_time", headers=headers)
        r.raise_for_status()
        hs_meetings = r.json().get("results", [])
        activities_list = []
        for hm in hs_meetings:
            props = hm.get("properties", {})
            act = Activity(
                Activity_ID=hm.get("id"),
                Account_ID=None,
                Contact_ID=None,
                Activity_Type="Meeting",
                Type="Meeting",
                Description=props.get("hs_meeting_body") or props.get("hs_meeting_title"),
                Activity_Date=props.get("hs_meeting_start_time"),
                user_id=user_id
            )
            db.add(act)
            activities_list.append({
                "activity_id": act.Activity_ID,
                "account_id": act.Account_ID,
                "type": act.Activity_Type,
                "description": act.Description,
                "date": act.Activity_Date
            })
        db.commit()

        # Index to vector store
        try:
            from vector_store import vector_store
            vector_store.index_activities(activities_list, user_id=user_id)
        except Exception as e:
            print(f"Warning: Failed to index HS activities: {e}")

        return True
    except Exception as e:
        db.rollback()
        print(f"HubSpot Sync Error: {e}")
        return False

if __name__ == "__main__":
    sync_crm_to_sqlite()
