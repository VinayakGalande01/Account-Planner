"""
GROUNDING VERIFIER (grounding_verifier.py)
Computes anti-hallucination grounding scores (0.0 to 1.0) by matching narrative claims
(deal amounts, opportunity IDs, contact names) against actual CRM database dictionaries.
"""

# --- SECTION 1: Dependencies & Import Setup ---
# Imports dictionary typing for comparing generated text against raw CRM facts.
from typing import Dict, Any

# --- SECTION 2: Grounding Score Calculation & Labeling ---
# Extracts verifiable values, computes match ratios, and converts numeric scores to HIGH/MEDIUM/LOW labels.
def compute_grounding_score(narrative: str, account_data: Dict[str, Any]) -> float:
    """
    Checks how many verifiable data points in the narrative
    (opportunity IDs, amounts, stage names, account names) 
    match actual values in the CRM account_data dict.
    """
    if not narrative or not account_data:
        return 1.0 # Default to high if no data is involved to prevent penalty

    verifiable_values = set()

    # Collect known real values from CRM data
    account_name = account_data.get("account_name", "")
    if account_name:
        verifiable_values.add(account_name.lower())

    for opp in account_data.get("opportunities", []):
        opp_id = opp.get("opp_id") or opp.get("id")
        if opp_id:
            verifiable_values.add(str(opp_id).lower())
        if opp.get("stage"):
            verifiable_values.add(str(opp["stage"]).lower())
        if opp.get("amount_usd") or opp.get("amount"):
            amount = opp.get("amount_usd") or opp.get("amount") or 0
            # Match dollar amount patterns e.g. "$4,964,000" or "$4.9M"
            verifiable_values.add(f"${amount:,.0f}".lower())
            if amount >= 1000000:
                verifiable_values.add(f"${amount/1000000:.1f}m".lower())
                verifiable_values.add(f"${amount/1000000:.0f}m".lower())

    for contact in account_data.get("contacts", []):
        if contact.get("name"):
            verifiable_values.add(str(contact["name"]).lower())

    if not verifiable_values:
        return 1.0  # No CRM facts to match, default to grounded

    # Count how many verifiable values appear in the narrative
    narrative_lower = narrative.lower()
    matches = sum(1 for v in verifiable_values if v in narrative_lower)
    
    # We normalize by total verifiable values, capped at a reasonable limit (e.g. 5) 
    # to avoid penalizing long lists of irrelevant records in the DB
    denominator = min(len(verifiable_values), 5)
    score = min(matches / denominator if denominator > 0 else 1.0, 1.0)
    return round(score, 2)


def score_to_label(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    elif score >= 0.45:
        return "MEDIUM"
    else:
        return "LOW"
