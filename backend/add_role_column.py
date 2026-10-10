"""
DATABASE MIGRATION COLUMN ADDER (add_role_column.py)
SQL migration script that safely appends the 'role' column (VARCHAR) to the users table
across both local SQLite files and remote PostgreSQL/Supabase databases.
"""

# --- SECTION 1: Dependencies & Engine Setup ---
# Imports migration libraries and database engine builder modules.
import os
from sqlalchemy import create_engine, text

# --- SECTION 2: Database Migration Implementation ---
# Migrates local SQLite and remote PostgreSQL schemas.
def migrate():
    print("Running migration: Adding 'role' column to users table...")
    
    # 1. Try local SQLite
    sqlite_engine = create_engine("sqlite:///./local_planner.db", connect_args={"check_same_thread": False})
    with sqlite_engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'account_manager';"))
            conn.commit()
            print("  [SQLite] Added 'role' column to local_planner.db.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("  [SQLite] Column 'role' already exists.")
            else:
                print(f"  [SQLite Notice] {e}")

    # 2. Try PostgreSQL / Supabase
    pg_url = os.getenv("ADMIN_DATABASE_URL")
    if not pg_url:
        print("  [PostgreSQL] ADMIN_DATABASE_URL not set; skipping.")
        return
    try:
        pg_engine = create_engine(pg_url, connect_args={"connect_timeout": 5})
        with pg_engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'account_manager';"))
            conn.commit()
            print("  [Supabase DB] Successfully added 'role' column to PostgreSQL!")
    except Exception as e:
        print(f"  [Supabase DB Notice] {e}")

if __name__ == "__main__":
    migrate()
