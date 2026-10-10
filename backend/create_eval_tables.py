"""
EVALUATION TABLE INITIALIZER (create_eval_tables.py)
Database setup script that creates and registers Layer 2 Evaluation tables
(Golden Dataset, Benchmark Results, Eval Runs) on PostgreSQL or SQLite destinations.
"""

# --- SECTION 1: Environment & Engine Setup ---
# Loads environment parameters and sets target database connections.
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from database import Base, get_engine, DATABASE_URL
import models.eval_models

# --- SECTION 2: Table Creation Routine ---
# Connects to target database schema and executes metadata creation for eval tables.
def main():
    print("=== APEX EVALUATION / LAYER 2 TABLE INITIALIZER ===")
    
    # Check if target is postgres and use admin_url if so, similar to rebuild_db.py
    if DATABASE_URL.startswith("postgresql") or "aws-1-ap-southeast-2.pooler.supabase.com" in DATABASE_URL:
        admin_url = os.getenv("ADMIN_DATABASE_URL", DATABASE_URL)
        print("[INFO] PostgreSQL detected. Using admin credentials for table creation...")
        engine = create_engine(admin_url)
    else:
        engine = get_engine()
    
    # Print the database destination (redacting password for security)
    url_repr = str(engine.url)
    if "@" in url_repr:
        db_part = url_repr.split("@")[-1]
        scheme_part = url_repr.split("://")[0]
        print(f"[INFO] Connecting to: {scheme_part}://****@{db_part}")
    else:
        print(f"[INFO] Connecting to: {url_repr}")
        
    try:
        # Create all tables defined in models.eval_models
        Base.metadata.create_all(bind=engine)
        print("[SUCCESS] Layer 2 evaluation tables created/verified successfully on the target database!")
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}")

if __name__ == "__main__":
    main()
