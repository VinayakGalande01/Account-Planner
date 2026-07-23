"""
OBSERVABILITY TABLE INITIALIZER (create_observability_tables.py)
Database initialization script that builds and registers Observability Telemetry tables
(Prompt Hashes, Traces, Token Costs) on the configured target database.
"""

# --- SECTION 1: Dependencies & Imports ---
# Imports database engines, environment configuration, and telemetry model bindings.
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from database import Base, get_engine
import models.observability_models

# --- SECTION 2: Observability Schema Build Routine ---
# Binds engine to database and creates all tables defined in observability_models.
def main():
    print("=== APEX OBSERVABILITY TABLE INITIALIZER ===")
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
        # Create all tables defined in models.observability_models
        Base.metadata.create_all(bind=engine)
        print("[SUCCESS] Observability tables created/verified successfully on the target database!")
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}")

if __name__ == "__main__":
    main()
