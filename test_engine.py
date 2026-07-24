"""
DATA ENGINE TEST RUNNER (test_engine.py)
Diagnostic diagnostic script to load datasets, initialize the in-memory DataEngine,
and verify enriched account query retrievals.
"""

# --- SECTION 1: Dependencies & System Paths ---
# Configures local module imports and adds the backend path to environment variables.
import sys, os
sys.path.append(os.path.abspath('backend'))
from data_engine import DataEngine

# --- SECTION 2: Diagnostic Loading & Verification ---
# Boots the data engine cache and outputs enriched customer records.
engine = DataEngine()
engine.load_data()
accounts = engine.get_enriched_accounts_list()
if accounts:
    print(accounts[0])
else:
    print("No accounts")
