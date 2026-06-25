from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models.crm_models import Account, Opportunity, Contact, Case, Activity

def check_data_hygiene(db: Session, user_id: int) -> list:
    """Runs a series of database queries to check for CRM data quality warnings scoped by user_id."""
    warnings = []
    today_str = datetime.today().strftime('%Y-%m-%d')
    thirty_days_ago = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

    # 1. Stale Opportunities (Close date is in the past, but the deal stage is not closed)
    try:
        overdue_opps = db.query(Opportunity).filter(
            Opportunity.user_id == user_id,
            Opportunity.Close_Date < today_str,
            ~Opportunity.Stage.in_(["Closed Won", "Closed Lost"])
        ).all()
        for opp in overdue_opps:
            warnings.append({
                "category": "Opportunity Completeness",
                "severity": "High",
                "entity_id": opp.Opp_ID,
                "entity_name": opp.Opp_Name,
                "message": f"Opportunity '{opp.Opp_Name}' close date ({opp.Close_Date}) is in the past, but stage is still '{opp.Stage}'."
            })
    except Exception as e:
        print(f"⚠️ Error querying overdue opportunities: {e}")

    # 2. Missing contact info (Email or phone is missing/blank)
    try:
        missing_info = db.query(Contact).filter(
            Contact.user_id == user_id,
            ((Contact.Email == None) | (Contact.Email == "") |
             (Contact.Phone == None) | (Contact.Phone == ""))
        ).all()
        for contact in missing_info:
            warnings.append({
                "category": "Contact Details",
                "severity": "Medium",
                "entity_id": contact.Contact_ID,
                "entity_name": f"{contact.First_Name} {contact.Last_Name}".strip(),
                "message": f"Contact '{contact.First_Name} {contact.Last_Name}' is missing contact details (Email: '{contact.Email or 'Missing'}', Phone: '{contact.Phone or 'Missing'}')."
            })
    except Exception as e:
        print(f"⚠️ Error querying missing contact details: {e}")

    # 3. Strategic Accounts with no activity logged in the last 30 days
    try:
        strategic_accounts = db.query(Account).filter(
            Account.user_id == user_id,
            ((Account.Account_Tier.ilike("%Strategic%")) | 
             (Account.Account_Tier.ilike("%Key%")))
        ).all()
        for acc in strategic_accounts:
            latest_activity = db.query(Activity).filter(
                Activity.user_id == user_id,
                Activity.Account_ID == acc.Account_ID
            ).order_by(Activity.Activity_Date.desc()).first()
            
            if not latest_activity:
                warnings.append({
                    "category": "Account Engagement",
                    "severity": "High",
                    "entity_id": acc.Account_ID,
                    "entity_name": acc.Account_Name,
                    "message": f"Strategic account '{acc.Account_Name}' has zero logged activities in the database."
                })
            elif latest_activity.Activity_Date < thirty_days_ago:
                warnings.append({
                    "category": "Account Engagement",
                    "severity": "Medium",
                    "entity_id": acc.Account_ID,
                    "entity_name": acc.Account_Name,
                    "message": f"Strategic account '{acc.Account_Name}' has no activities logged since {latest_activity.Activity_Date} (limit: 30 days)."
                })
    except Exception as e:
        print(f"⚠️ Error querying strategic accounts engagement: {e}")

    return warnings
