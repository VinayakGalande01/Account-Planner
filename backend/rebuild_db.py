import os
from dotenv import load_dotenv

# Run load_dotenv BEFORE importing database modules so it picks up the correct DATABASE_URL
load_dotenv(override=True)

from sqlalchemy import create_engine, text
from database import Base, DATABASE_URL
import models.user
import models.crm_models

def rebuild_database():
    print(f"Connecting to database: {DATABASE_URL.split('@')[-1]}")
    engine = create_engine(DATABASE_URL)
    is_sqlite = DATABASE_URL.startswith("sqlite")
    
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
        print("Dropping existing tables...")
        for table in tables:
            try:
                if is_sqlite:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table};"))
                else:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
                print(f"  Dropped table: {table}")
            except Exception as e:
                print(f"  Error dropping {table}: {e}")
        conn.commit()

        print("Recreating all tables using SQLAlchemy models...")
        Base.metadata.create_all(bind=engine)
        print("  All tables created successfully.")

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
            
            print("Enabling Row-Level Security (RLS) on tables...")
            for table in rls_tables:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
                    conn.execute(text(f"DROP POLICY IF EXISTS {table}_tenant_policy ON {table};"))
                    conn.execute(text(f"""
                        CREATE POLICY {table}_tenant_policy ON {table}
                        USING (true)
                        WITH CHECK (true);
                    """))
                    print(f"  Enabled RLS and created policy on: {table}")
                except Exception as e:
                    print(f"  Error enabling RLS on {table}: {e}")
            conn.commit()
        else:
            print("Skipped RLS setup since database is SQLite.")

    print("Database rebuild complete!")

if __name__ == "__main__":
    rebuild_database()
