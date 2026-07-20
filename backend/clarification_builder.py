"""
APEX Clarification Builder - targeted human-in-the-loop questioning
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("backend")

def build_clarification_prompt(last_user_message: str, prior_history: List[Dict[str, str]] = None, known_accounts: List[str] = None) -> str:
    """
    Builds a targeted clarification question based on user message and known accounts.
    """
    known_accounts = known_accounts or []
    
    # Try to find partial string matches in query
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
    """
    Extracts candidate accounts to present as option chips.
    """
    query_lower = query.lower()
    candidates = []
    for acc in known_accounts:
        if acc.lower() in query_lower or any(part in query_lower for part in acc.lower().split() if len(part) > 3):
            candidates.append(acc)
    if not candidates:
        candidates = known_accounts[:3]
    return candidates
