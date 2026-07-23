import sys, os
sys.path.append(os.path.abspath('backend'))
from data_engine import DataEngine
engine = DataEngine()
engine.load_data()
accounts = engine.get_enriched_accounts_list()
if accounts:
    print(accounts[0])
else:
    print("No accounts")
