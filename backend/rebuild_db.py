"""
DATABASE REBUILD UTILITY (rebuild_db.py)
Re-creates database schema tables and enforces PostgreSQL Row Level Security (RLS) policies
and tenant isolation rules directly on Supabase/PostgreSQL destinations.
"""

# --- SECTION 1: Environment & Admin Connection ---
# Configures environment variables and establishes administrative connection to PostgreSQL or SQLite.
import os
from dotenv import load_dotenv

load_dotenv(override=True)

from sqlalchemy import create_engine, text
from database import Base, DATABASE_URL, engine as db_engine
import models.user
import models.crm_models

# --- SECTION 2: Database Rebuild & RLS Enforcement ---
# Drops legacy tables, creates fresh schema instances, and applies tenant isolation policies.
def rebuild_database():
    is_sqlite = db_engine.dialect.name == "sqlite"
    if not is_sqlite:
        admin_url = os.getenv("ADMIN_DATABASE_URL", DATABASE_URL)
        engine = create_engine(admin_url)
        db_name = admin_url.split('@')[-1]
    else:
        engine = db_engine
        db_name = "SQLite (local_planner.db)"
    print(f"Connecting to database: {db_name}")
    
    # Tables to drop in order of dependencies
    tables = [
        "chat_messages",
        "chat_sessions",
        "activities",
        "cases",
        "contacts",
        "opportunities",
        "accounts",
        "users"
    ]
    
    with engine.connect() as conn:
        if not is_sqlite:
            # Enable RLS on CRM and Chat tables
            rls_tables = [
                "accounts",
                "opportunities",
                "contacts",
                "cases",
                "activities",
                "chat_sessions",
                "chat_messages"
            ]
            
            print("Applying RLS policies directly to existing tables...")
            for table in rls_tables:
                # 1. Enable RLS
                try:
                    conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
                    conn.commit()
                    print(f"  Enabled RLS on: {table}")
                except Exception as e:
                    print(f"  Warning: Could not enable RLS on {table} (might already be enabled): {e}")
                    conn.rollback()
                    
                # 2. Force RLS
                try:
                    conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))
                    conn.commit()
                    print(f"  Forced RLS on: {table}")
                except Exception as e:
                    print(f"  Warning: Could not force RLS on {table}: {e}")
                    conn.rollback()

                # 3. Create Tenant Policy
                try:
                    conn.execute(text(f"DROP POLICY IF EXISTS {table}_tenant_policy ON {table};"))
                    conn.execute(text(f"""
                        CREATE POLICY {table}_tenant_policy ON {table}
                        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer)
                        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer);
                    """))
                    conn.commit()
                    print(f"  Tenant policy created on: {table}")
                except Exception as e:
                    print(f"  Error creating policy on {table}: {e}")
                    conn.rollback()
        else:
            print("Skipped RLS setup since database is SQLite.")

    print("Database rebuild complete!")

if __name__ == "__main__":
    rebuild_database()
