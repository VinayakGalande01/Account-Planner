import os
import json
import httpx
import logging

logger = logging.getLogger("query_classifier")

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

def classify_query(user_message: str) -> str:
    """
    Calls the LLM to classify the user query into DATA, GENERAL, or UNCLEAR.
    Returns "DATA" on failure or timeout as a safe fallback.
    """
    url, model = get_active_llm_config()
    
    system_prompt = (
        "You are a query classifier. Read the user message "
        "and return ONLY one word. No explanation. No extra "
        "text. Just one word from these three options:\n\n"
        "DATA — if user is asking about accounts, deals, "
        "opportunities, pipeline, revenue, health scores, "
        "risks, trends, performance, specific companies, "
        "or anything related to sales data\n\n"
        "GENERAL — if user is asking what APEX is, how it "
        "works, greeting the system, asking about features, "
        "asking for help, or anything NOT about sales data\n\n"
        "UNCLEAR — if the message is too vague, too short, "
        "or could mean multiple things\n\n"
        f"User message: {user_message}\n\n"
        "Return only one word:"
    )

    try:
        # Use sync client as this is called before async streaming in main.py, but FastAPI endpoints can handle blocking or we can make it sync. Wait, the main.py endpoint `generate_stream()` might be async.
        # Actually, let's make it sync for simplicity if we are calling it sequentially, or we can use httpx.Client().
        # Wait, the instruction says "classify_query(user_message)", not async def.
        with httpx.Client(timeout=5.0) as client:
            payload = {
                "model": model,
                "prompt": system_prompt,
                "stream": False
            }
            response = client.post(url, json=payload)
            response.raise_for_status()
            result = response.json().get("response", "").strip().upper()
            
            # Clean up potential punctuation or extra words
            if "DATA" in result:
                return "DATA"
            elif "GENERAL" in result:
                return "GENERAL"
            elif "UNCLEAR" in result:
                return "UNCLEAR"
            else:
                return "DATA" # Default safe fallback
                
    except Exception as e:
        logger.warning(f"[CLASSIFIER ERROR] Failed to classify query: {e}")
        return "DATA" # Default safe fallback
