"""
DATABASE CONNECTIVITY TEST (test_db.py)
Direct SQLAlchemy script testing PostgreSQL connection pooling and user query resolution on Supabase.
"""

# --- SECTION 1: Dependencies & Engine Setup ---
# Configures raw PostgreSQL pooled connection engine and sessionmaker.
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

URL = "postgresql://postgres.hqofkucrppxzgtajpjxh:APEX%242026006@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"
engine = create_engine(URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# --- SECTION 2: Direct Connection & Query Test ---
# Executes sample SQL statement to verify remote database connectivity and table state.
try:
    result = db.execute(text("SELECT id, email FROM users WHERE email = 'abhijitjagtap@gmail.com'")).fetchall()
    print("SUCCESS! Users found:", result)
except Exception as e:
    print("ERROR!", str(e))
