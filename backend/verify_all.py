import os
import sys

# Ensure current directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Base, engine as db_engine
from models.crm_models import Account, Opportunity, Contact, Case, Activity, ChatSession, ChatMessage
from sync_daemon import sync_crm_to_sqlite
from hygiene_checker import check_data_hygiene
from vector_store import vector_store

def verify():
    print("🧪 Starting verification script...")
    
    # 1. Verify table creation in SQLite
    print("1. Creating database tables in SQLite...")
    try:
        Base.metadata.create_all(bind=db_engine)
        print("  ✅ All tables successfully registered and created in SQLite.")
    except Exception as e:
        print(f"  ❌ Failed to create tables: {e}")
        return False

    # 2. Verify Sync Daemon loads Excel data into SQLite
    print("2. Running Sync Daemon execution...")
    try:
        success = sync_crm_to_sqlite()
        if success:
            print("  ✅ Sync Daemon completed successfully.")
        else:
            print("  ❌ Sync Daemon returned failure status.")
            return False
    except Exception as e:
        print(f"  ❌ Sync Daemon failed to execute: {e}")
        return False

    # 3. Verify SQLite Queries (counting records)
    print("3. Querying SQLite database records...")
    from database import SessionLocal
    db = SessionLocal()
    try:
        acc_count = db.query(Account).count()
        opp_count = db.query(Opportunity).count()
        ct_count = db.query(Contact).count()
        act_count = db.query(Activity).count()
        case_count = db.query(Case).count()
        
        print(f"  ✅ Records verified in SQLite:")
        print(f"     - Accounts: {acc_count}")
        print(f"     - Opportunities: {opp_count}")
        print(f"     - Contacts: {ct_count}")
        print(f"     - Activities: {act_count}")
        print(f"     - Cases: {case_count}")
        
        if acc_count == 0 or opp_count == 0:
            print("  ❌ SQLite is missing essential records.")
            return False
    except Exception as e:
        print(f"  ❌ Querying database failed: {e}")
        return False
    finally:
        db.close()

    # 4. Verify CRM Data Hygiene Auditing
    print("4. Testing CRM data hygiene checks...")
    db = SessionLocal()
    try:
        warnings = check_data_hygiene(db)
        print(f"  ✅ CRM Data Quality checker successfully returned {len(warnings)} alerts.")
        if len(warnings) > 0:
            print(f"     Sample Alert: [{warnings[0]['category']}] {warnings[0]['message']}")
    except Exception as e:
        print(f"  ❌ CRM Hygiene check query failed: {e}")
        return False
    finally:
        db.close()

    # 5. Verify RAG search fallback or vector client
    print("5. Testing Local RAG search indexing and retrieval...")
    try:
        # Index a sample activity
        sample_activities = [{
            "Activity_ID": "ACT_TEST_99",
            "Account_ID": "ACC_TEST_99",
            "Activity_Type": "Email",
            "Description": "Negotiating enterprise security parameters and terms with executive decision maker.",
            "Activity_Date": "2026-06-16"
        }]
        vector_store.index_activities(sample_activities)
        
        # Test retrieval
        results = vector_store.search_activities("enterprise security parameters", limit=1)
        if results:
            print(f"  ✅ Local RAG search retrieved match: {results[0]['text']}")
        else:
            print("  ❌ Local RAG search returned no matches.")
            return False
    except Exception as e:
        print(f"  ❌ RAG vector search failed: {e}")
        return False

    print("\n🎉 ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    return True

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)
