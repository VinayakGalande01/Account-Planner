"""
SYSTEM INTEGRITY VERIFICATION SUITE (verify_all.py)
End-to-end verification script testing database creation, sync daemon execution,
record counts, CRM data hygiene checks, and vector RAG retrieval with zero errors.
"""

# --- SECTION 1: Dependencies & Environment Setup ---
# Loads environment overrides and imports database engines, models, sync daemons, and vector stores.
import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Base, engine as db_engine
from models.crm_models import Account, Opportunity, Contact, Case, Activity, ChatSession, ChatMessage
from sync_daemon import sync_crm_to_sqlite
from hygiene_checker import check_data_hygiene
from vector_store import vector_store

# --- SECTION 2: System-Wide Verification Execution Routine ---
# Cleans SQLite files, rebuilds ORM metadata, executes sync daemons, and tests RAG vector search.
def verify():
    print("Starting verification script...")
    
    # 1. Clean up local SQLite db if database is SQLite to prevent stale schema errors
    from database import DATABASE_URL
    is_sqlite = DATABASE_URL.startswith("sqlite")
    if is_sqlite:
        db_file = "./local_planner.db"
        if os.path.exists(db_file):
            print(f"Removing old SQLite file: {db_file} to refresh schema.")
            try:
                # Close any active engine connections first
                db_engine.dispose()
                os.remove(db_file)
                print("  Successfully removed old SQLite file.")
            except Exception as e:
                print(f"  Warning: Could not remove SQLite file: {e}")

    # 2. Verify table creation
    print("2. Rebuilding database tables...")
    try:
        Base.metadata.create_all(bind=db_engine)
        print("  All tables successfully registered and created.")
    except Exception as e:
        print(f"  Failed to create tables: {e}")
        return False

    # 3. Verify Sync Daemon loads Excel data
    print("3. Running Sync Daemon execution...")
    try:
        success = sync_crm_to_sqlite()
        if success:
            print("  Sync Daemon completed successfully.")
        else:
            print("  Sync Daemon returned failure status.")
            return False
    except Exception as e:
        print(f"  Sync Daemon failed to execute: {e}")
        return False

    # 4. Verify Database Queries (counting records)
    print("4. Querying database records...")
    from database import SessionLocal
    db = SessionLocal()
    try:
        acc_count = db.query(Account).count()
        opp_count = db.query(Opportunity).count()
        ct_count = db.query(Contact).count()
        act_count = db.query(Activity).count()
        case_count = db.query(Case).count()
        
        print(f"  Records verified in database:")
        print(f"     - Accounts: {acc_count}")
        print(f"     - Opportunities: {opp_count}")
        print(f"     - Contacts: {ct_count}")
        print(f"     - Activities: {act_count}")
        print(f"     - Cases: {case_count}")
        
        if acc_count == 0 or opp_count == 0:
            print("  Database is missing essential records.")
            return False
    except Exception as e:
        print(f"  Querying database failed: {e}")
        return False
    finally:
        db.close()

    # 5. Verify CRM Data Hygiene Auditing
    print("5. Testing CRM data hygiene checks...")
    db = SessionLocal()
    try:
        warnings = check_data_hygiene(db, 1) # Scoped to admin user (ID = 1)
        print(f"  CRM Data Quality checker successfully returned {len(warnings)} alerts.")
        if len(warnings) > 0:
            print(f"     Sample Alert: [{warnings[0]['category']}] {warnings[0]['message']}")
    except Exception as e:
        print(f"  CRM Hygiene check query failed: {e}")
        return False
    finally:
        db.close()

    # 6. Verify RAG search fallback or vector client
    print("6. Testing Local RAG search indexing and retrieval...")
    try:
        # Index a sample activity
        sample_activities = [{
            "Activity_ID": "ACT_TEST_99",
            "Account_ID": "ACC_TEST_99",
            "Activity_Type": "Email",
            "Description": "Negotiating enterprise security parameters and terms with executive decision maker.",
            "Activity_Date": "2026-06-16"
        }]
        vector_store.index_activities(sample_activities, user_id=1)
        
        # Test retrieval
        results = vector_store.search_activities("enterprise security parameters", user_id=1, limit=1)
        if results:
            print(f"  Local RAG search retrieved match: {results[0]['text']}")
        else:
            print("  Local RAG search returned no matches.")
            return False
    except Exception as e:
        print(f"  RAG vector search failed: {e}")
        return False

    print("\nALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    return True

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)
