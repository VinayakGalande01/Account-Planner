"""
SQLITE DATABASE DIAGNOSTIC (test_db.py)
Direct diagnostic query verification script checking local SQLite data.db
tables and columns availability.
"""

# --- SECTION 1: Dependencies & Engine Setup ---
# Imports database engines, pandas loaders, and configures sqlite paths.
from sqlalchemy import create_engine
import pandas as pd
engine = create_engine('sqlite:///backend/data.db')

# --- SECTION 2: Table Column Verification ---
# Runs sample SQL queries and lists columns.
try:
    df = pd.read_sql("SELECT * FROM account LIMIT 1", engine)
    print(df.columns.tolist())
except Exception as e:
    print(e)
