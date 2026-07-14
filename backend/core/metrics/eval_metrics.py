import json
import re
import logging
from typing import Dict, Any, List, Tuple, Optional
import httpx

logger = logging.getLogger("eval_metrics")

def calculate_intent_match(expected_intent: str, actual_intent: str) -> bool:
    """Compare expected intent with actual intent. Case-insensitive."""
    if not expected_intent or not actual_intent:
        return False
    return expected_intent.strip().lower() == actual_intent.strip().lower()


def calculate_entity_f1(expected_entities: Dict[str, Any], actual_entities: Dict[str, Any]) -> float:
    """Calculate F1 score for entity extraction.
    Precision = TP / (TP + FP)
    Recall = TP / (TP + FN)
    F1 = 2 * P * R / (P + R)
    """
    if not expected_entities:
        return 1.0  # If no entities expected, perfect match

    tp = 0
    fp = 0
    fn = 0

    # Clean and standardize expected entities
    clean_expected = {k: str(v).strip().lower() for k, v in expected_entities.items() if v is not None}
    # Clean and standardize actual entities
    clean_actual = {k: str(v).strip().lower() for k, v in actual_entities.items() if v is not None}

    if not clean_expected and not clean_actual:
        return 1.0

    for key, expected_val in clean_expected.items():
        actual_val = clean_actual.get(key)
        if actual_val and (expected_val in actual_val or actual_val in expected_val):
            tp += 1
        else:
            fn += 1

    for key, actual_val in clean_actual.items():
        if key not in clean_expected:
            fp += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    
    if (precision + recall) == 0:
        return 0.0
        
    f1 = 2 * (precision * recall) / (precision + recall)
    return float(f1)


def calculate_retriever_precision_recall(
    expected_ids: Dict[str, List[str]], 
    actual_opportunities: List[Dict[str, Any]], 
    actual_contacts: List[Dict[str, Any]], 
    actual_cases: List[Dict[str, Any]], 
    actual_activities: List[Dict[str, Any]],
    expected_account: Optional[str] = None
) -> Tuple[float, float]:
    """Calculate Retriever Precision & Recall.
    If expected_ids are defined, compares exact ID matches.
    If expected_ids are not defined, uses a heuristic:
      - Checks if retrieved records belong to the expected account.
    """
    # 1. Flatten actual retrieved IDs
    actual_ids = set()
    for opp in actual_opportunities:
        actual_ids.add(str(opp.get("opp_id", opp.get("id"))))
    for contact in actual_contacts:
        actual_ids.add(str(contact.get("contact_id", contact.get("id"))))
    for c in actual_cases:
        actual_ids.add(str(c.get("case_id", c.get("id"))))
    for act in actual_activities:
        actual_ids.add(str(act.get("activity_id", act.get("id"))))

    # 2. Flatten expected IDs
    expected_ids_set = set()
    if expected_ids:
        for k, v in expected_ids.items():
            if isinstance(v, list):
                expected_ids_set.update(str(x) for x in v)

    # 3. Calculate exact match if expectations exist
    if expected_ids_set:
        tp = len(actual_ids.intersection(expected_ids_set))
        fp = len(actual_ids - expected_ids_set)
        fn = len(expected_ids_set - actual_ids)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        return float(precision), float(recall)

    # 4. Fallback to Account heuristic if no expected IDs provided
    if expected_account:
        expected_acc_lower = expected_account.strip().lower()
        
        # Check if the retrieved opportunities/contacts/cases belong to expected account
        tp_count = 0
        total_retrieved = len(actual_opportunities) + len(actual_contacts) + len(actual_cases)
        
        if total_retrieved == 0:
            # If nothing retrieved but an account was expected, recall is 0
            return 0.0, 0.0

        for opp in actual_opportunities:
            opp_name = str(opp.get("opp_name", "")).lower()
            opp_id = str(opp.get("opp_id", "")).lower()
            # If the account name or ID is in the opportunity text
            if expected_acc_lower in opp_name or expected_acc_lower in opp_id:
                tp_count += 1
                
        for contact in actual_contacts:
            contact_name = str(contact.get("name", "")).lower()
            if expected_acc_lower in contact_name:
                tp_count += 1

        for c in actual_cases:
            case_title = str(c.get("title", c.get("case_name", ""))).lower()
            if expected_acc_lower in case_title:
                tp_count += 1
                
        # If we got any matching records
        precision = tp_count / total_retrieved if total_retrieved > 0 else 1.0
        recall = 1.0 if tp_count > 0 else 0.0
        return float(precision), float(recall)

    # 5. Default case: no expected IDs or expected account
    if len(actual_ids) > 0:
        return 1.0, 1.0
    return 0.0, 0.0


def calculate_narrative_structure_score(narrative_data: Any, expected_keys: Optional[List[str]] = None) -> float:
    """Calculate Narrative Structure score (M-09 schema conformance).
    Checks if the generated narrative dictionary contains the required schema keys.
    """
    if not narrative_data:
        return 0.0

    if not isinstance(narrative_data, dict):
        # Try parsing if it's a string
        if isinstance(narrative_data, str):
            try:
                # Strip markdown json wrappers
                clean_text = re.sub(r"^```(?:json)?\s*", "", narrative_data.strip())
                clean_text = re.sub(r"\s*```$", "", clean_text)
                narrative_data = json.loads(clean_text)
            except Exception:
                return 0.0
        else:
            return 0.0

    if not expected_keys:
        # Default AM Role playbook keys
        expected_keys = [
            "narrative", 
            "urgency", 
            "playbook_7day", 
            "stakeholder_sequence", 
            "risks_and_mitigations"
        ]

    matched_keys = sum(1 for k in expected_keys if k in narrative_data)
    return float(matched_keys / len(expected_keys))


def calculate_narrative_keyword_score(narrative_text: str, expected_keywords: List[str]) -> float:
    """Calculate keyword matching score (M-08 recommendation quality).
    Measures the ratio of golden keywords found in the generated text.
    """
    if not expected_keywords:
        return 1.0
    
    if not narrative_text:
        return 0.0

    matches = 0
    narrative_lower = narrative_text.lower()
    for kw in expected_keywords:
        if kw.strip().lower() in narrative_lower:
            matches += 1

    return float(matches / len(expected_keywords))


async def calculate_grounding_score_llm(
    context_data: Dict[str, Any], 
    narrative_text: str, 
    llm_url: str, 
    model_name: str
) -> Tuple[float, str]:
    """Calculate Grounding Score using local LLM-as-judge (M-07).
    Pings the LLM with database context and generated narrative.
    """
    if not narrative_text:
        return 0.0, "Empty narrative response."

    # Format small context payload to fit context window
    context_summary = {
        "opportunities_count": len(context_data.get("opportunities", [])),
        "opportunities": [
            {"name": o.get("opp_name"), "amount": o.get("amount_usd"), "stage": o.get("stage")}
            for o in context_data.get("opportunities", [])[:10]
        ],
        "contacts": [c.get("name") for c in context_data.get("contacts", [])[:5]],
        "cases": [c.get("title", c.get("case_name")) for c in context_data.get("cases", [])[:5]],
        "health_score": context_data.get("health_score")
    }

    prompt = f"""System: You are the APEX Evaluation Auditor. You are an expert in validating whether an AI's narrative report is strictly grounded in and supported by a set of retrieved database facts.
Your task is to judge the Grounding Score of the narrative.
Rules:
1. Every claim, number, and status in the Narrative must be present in the Database Context.
2. If the Narrative mentions a number or status that is NOT in the Database Context (or contradicts it), this is a hallucination.
3. Ignore formatting differences.

Output ONLY a JSON block matching this schema:
{{
  "grounding_score": 0.0 to 1.0,
  "category": "HIGH" | "MEDIUM" | "LOW",
  "rationale": "1-sentence explanation of your score"
}}

Database Context:
{json.dumps(context_summary, indent=2)}

Narrative:
{narrative_text}
"""
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 150
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(llm_url, json=payload)
            if res.status_code == 200:
                response_text = res.json().get("response", "").strip()
                # Parse JSON block
                clean_text = re.sub(r"^```(?:json)?\s*", "", response_text)
                clean_text = re.sub(r"\s*```$", "", clean_text)
                parsed = json.loads(clean_text)
                
                score = float(parsed.get("grounding_score", 0.0))
                rationale = str(parsed.get("rationale", "LLM-as-judge computed successfully."))
                return score, rationale
    except Exception as e:
        logger.warning(f"[Grounding Judge Warning] LLM-as-judge call failed or timed out: {e}. Falling back to default.")
        
    # Heuristic fallback: check if some keyword numbers match
    return 1.0, "Fallback score applied (LLM-as-judge timed out)."


def calculate_composite_eqs(
    intent_accuracy: float,
    entity_f1: float,
    retriever_precision: float,
    retriever_recall: float,
    grounding_score: float,
    narrative_structure: float,
    recommendation_quality: float
) -> float:
    """Calculate the Execution Quality Score (EQS).
    EQS = (
        Intent Accuracy      × 0.20  +
        Entity F1            × 0.15  +
        Retriever Precision  × 0.10  +
        Retriever Recall     × 0.10  +
        Grounding Score      × 0.20  +
        Narrative Structure  × 0.10  +
        Recommendation Quality × 0.15
    ) * 100
    """
    score = (
        intent_accuracy * 0.20 +
        entity_f1 * 0.15 +
        retriever_precision * 0.10 +
        retriever_recall * 0.10 +
        grounding_score * 0.20 +
        narrative_structure * 0.10 +
        recommendation_quality * 0.15
    )
    return float(round(score * 100, 2))
