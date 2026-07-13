import os
import json
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger("conversational_handler")

def get_active_llm_config() -> tuple:
    """Helper to load cached or environment-configured LLM URL and model name."""
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                url = data.get("url")
                model = data.get("model")
                if url and model:
                    return url, model
        except Exception:
            pass
    
    primary_url = os.getenv("LLM_URL", "http://10.181.43.105:8000/api/generate")
    primary_model = os.getenv("MODEL_NAME", "llama3.2:latest")
    return primary_url, primary_model

def handle_conversational_query(user_message: str) -> Dict[str, Any]:
    """
    Calls the LLM to generate a conversational, plain English response.
    Returns a dictionary matching the required JSON format.
    """
    url, model = get_active_llm_config()
    
    system_prompt = (
        "You are APEX, a friendly and intelligent sales assistant. "
        "Answer the user's question in simple plain English. Follow these rules strictly:\n\n"
        "- Use short sentences only\n"
        "- Use simple everyday words\n"
        "- Maximum 5 sentences in your answer\n"
        "- Be warm, helpful, and clear\n"
        "- Never show data tables or numbers\n"
        "- Never mention health scores, opportunity IDs, or database terms\n"
        "- Sound like a smart helpful colleague\n"
        "- If they asked what APEX is, explain it simply: APEX is a smart sales assistant "
        "that reads your CRM data and helps you understand which deals need attention, "
        "which accounts are healthy, and what your team should focus on next. "
        "You can ask it anything in plain English.\n"
        "- If they said hello or greeted you, greet them back warmly and ask how you can help them today\n"
        "- If they asked how to use APEX, tell them they can simply type questions like "
        "'show me my top deals' or 'which accounts are at risk' and APEX will answer instantly\n\n"
        f"User message: {user_message}\n\n"
        "Generate your plain English response now:"
    )

    fallback_response = {
        "type": "conversational",
        "message": "Hi! I am APEX, your sales assistant. You can ask me about your accounts, deals, and pipeline. Try asking something like 'show me my top accounts' to get started.",
        "suggestions": [
            "Show me top accounts",
            "Which deals are at risk",
            "Analyze my pipeline"
        ]
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            payload = {
                "model": model,
                "prompt": system_prompt,
                "stream": False
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
            message_text = response.json().get("response", "").strip()
            
            if not message_text:
                return fallback_response
                
            return {
                "type": "conversational",
                "message": message_text,
                "suggestions": [
                    "Show me top accounts",
                    "Which deals are at risk",
                    "Analyze my pipeline"
                ]
            }
                
    except Exception as e:
        logger.warning(f"[CONVERSATIONAL ERROR] Failed to generate conversational response: {e}")
        return fallback_response
