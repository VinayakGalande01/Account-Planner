import os
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from database import SessionLocal
from models.crm_models import Account, Opportunity, Contact, Case, Activity

def get_data_path():
    """Resolves Excel file path exactly like main.py."""
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
    """Clean NaN or NaT values from pandas to None for database safety."""
    if pd.isna(val):
        return None
    if isinstance(val, (np.integer, np.floating)):
        return val.item()
    return str(val)

def sync_crm_to_sqlite():
    excel_path = get_data_path()
    if not excel_path or not os.path.exists(excel_path):
        print(f"❌ Excel data file not found at path: {excel_path}")
        return False

    print(f"🔄 Starting database sync from Excel: {excel_path}")
    sheets = pd.read_excel(excel_path, sheet_name=None)
    data = {name.lower(): df for name, df in sheets.items()}

    db: Session = SessionLocal()
    try:
        # Clear existing tables first
        db.query(Activity).delete()
        db.query(Case).delete()
        db.query(Contact).delete()
        db.query(Opportunity).delete()
        db.query(Account).delete()
        db.commit()

        # 1. Sync Accounts
        accounts_df = data.get("account")
        if accounts_df is not None:
            for _, r in accounts_df.iterrows():
                annual_rev = r.get("Annual_Revenue_USD", 0)
                if pd.isna(annual_rev):
                    annual_rev = 0
                acc = Account(
                    Account_ID=clean_value(r.get("Account_ID")),
                    Account_Name=clean_value(r.get("Account_Name")),
                    Account_Tier=clean_value(r.get("Account_Tier")),
                    Industry=clean_value(r.get("Industry")),
                    Territory=clean_value(r.get("Territory")),
                    Annual_Revenue_USD=float(annual_rev),
                    Country=clean_value(r.get("Country")),
                    Health_Score=float(clean_value(r.get("Health_Score"))) if r.get("Health_Score") is not None and not pd.isna(r.get("Health_Score")) else 80.0
                )
                db.add(acc)
            db.commit()
            print(f"  ✅ Synced {len(accounts_df)} Accounts.")

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
                    Opp_ID=clean_value(r.get("Opp_ID")),
                    Account_ID=clean_value(r.get("Account_ID")),
                    Opp_Name=clean_value(r.get("Opp_Name")),
                    Amount_USD=float(amt),
                    Stage=clean_value(r.get("Stage")),
                    Close_Date=clean_value(r.get("Close_Date")),
                    Probability_Pct=int(prob),
                    Competitor=clean_value(r.get("Competitor"))
                )
                db.add(opp)
            db.commit()
            print(f"  ✅ Synced {len(opps_df)} Opportunities.")

        # 3. Sync Contacts
        contacts_df = data.get("contact")
        if contacts_df is not None:
            for _, r in contacts_df.iterrows():
                ct = Contact(
                    Contact_ID=clean_value(r.get("Contact_ID")),
                    Account_ID=clean_value(r.get("Account_ID")),
                    First_Name=clean_value(r.get("First_Name")),
                    Last_Name=clean_value(r.get("Last_Name")),
                    Role=clean_value(r.get("Role")),
                    Department=clean_value(r.get("Department")),
                    Engagement_Level=clean_value(r.get("Engagement_Level")),
                    Email=clean_value(r.get("Email")),
                    Phone=clean_value(r.get("Phone")),
                    Last_Contact_Date=clean_value(r.get("Last_Contact_Date"))
                )
                db.add(ct)
            db.commit()
            print(f"  ✅ Synced {len(contacts_df)} Contacts.")

        # 4. Sync Cases
        cases_df = data.get("case")
        if cases_df is not None:
            for _, r in cases_df.iterrows():
                csat = r.get("CSAT_Score", 0)
                if pd.isna(csat):
                    csat = 0.0
                c = Case(
                    Case_ID=clean_value(r.get("Case_ID")),
                    Account_ID=clean_value(r.get("Account_ID")),
                    Subject=clean_value(r.get("Subject")),
                    Status=clean_value(r.get("Status")),
                    Severity=clean_value(r.get("Severity")),
                    CSAT_Score=float(csat),
                    Open_Date=clean_value(r.get("Open_Date"))
                )
                db.add(c)
            db.commit()
            print(f"  ✅ Synced {len(cases_df)} Cases.")

        # 5. Sync Activities
        activities_df = data.get("activity")
        if activities_df is not None:
            activities_list = []
            for _, r in activities_df.iterrows():
                act = Activity(
                    Activity_ID=clean_value(r.get("Activity_ID")),
                    Account_ID=clean_value(r.get("Account_ID")),
                    Contact_ID=clean_value(r.get("Contact_ID")),
                    Activity_Type=clean_value(r.get("Activity_Type")),
                    Type=clean_value(r.get("Activity_Type")), # For compatibility with 'Type' field
                    Description=clean_value(r.get("Notes") or r.get("Description")),
                    Activity_Date=clean_value(r.get("Activity_Date"))
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
            print(f"  ✅ Synced {len(activities_df)} Activities.")

            # Trigger local RAG vector indexing
            try:
                from vector_store import vector_store
                vector_store.index_activities(activities_list)
            except Exception as index_err:
                print(f"⚠️ Warning: Failed to index activities to vector store: {index_err}")

        print("🎉 Database sync completed successfully!")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Error during database sync: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    sync_crm_to_sqlite()
