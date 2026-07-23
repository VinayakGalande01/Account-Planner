"""
CLARIFICATION BUILDER (clarification_builder.py)
Constructs targeted human-in-the-loop clarification prompts when user queries
have ambiguous or unspecified account references, extracting candidate entity chips.
"""

# --- SECTION 1: Dependencies & Logging Setup ---
# Imports backend logger and typing constructs for clarification generation.
import logging
from typing import List, Dict, Any

logger = logging.getLogger("backend")

# --- SECTION 2: Clarification Prompt & Candidate Extraction ---
# Builds targeted clarification text and extracts account candidate options for frontend chips.
def build_clarification_prompt(last_user_message: str, prior_history: List[Dict[str, str]] = None, known_accounts: List[str] = None) -> str:
    known_accounts = known_accounts or []
    
    query_lower = last_user_message.lower()
    candidates = []
    for acc in known_accounts:
        if acc.lower() in query_lower or any(part in query_lower for part in acc.lower().split() if len(part) > 3):
            candidates.append(acc)
            
    if candidates:
        accounts_str = " or ".join(candidates[:3])
        return f"I see you're asking about your accounts, but I want to make sure I focus on the right one. Did you mean {accounts_str}?"
        
    return "I wasn't able to identify which account or deal you're referring to. Could you please specify the name of the account?"

def extract_candidate_options(known_accounts: List[str], query: str) -> List[str]:
    query_lower = query.lower()
    candidates = []
    for acc in known_accounts:
        if acc.lower() in query_lower or any(part in query_lower for part in acc.lower().split() if len(part) > 3):
            candidates.append(acc)
    if not candidates:
        candidates = known_accounts[:3]
    return candidates

