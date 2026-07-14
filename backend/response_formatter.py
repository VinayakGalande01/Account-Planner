import os
import json
import httpx
import logging
import re
from typing import Optional, List, Dict

logger = logging.getLogger("response_formatter")

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

async def format_response_for_user(
    raw_output: str, 
    persona: str = "account_manager", 
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Accepts raw LLM response, detects tone/urgency, handles conversation history memory,
    calls local Ollama model to format output into a senior sales advisor JSON object.
    If it fails, silently returns the original raw_output.
    """
    if not raw_output or not raw_output.strip():
        return raw_output

    # Detect if raw_output is already a quick-action JSON payload and bypass formatting
    trimmed = raw_output.strip()
    if trimmed.startswith("{"):
        try:
            parsed = json.loads(trimmed)
            if "type" in parsed and parsed["type"] in ["EXEC_EMAIL", "MEETING_AGENDA", "STAKEHOLDERS", "RISK_REVIEW"]:
                return trimmed
        except Exception:
            pass

    url, model = get_active_llm_config()

    # STEP 2 — PERSONA LAYER
    persona_instruction = ""
    if persona == "account_manager":
        persona_instruction = "Focus on deal-by-deal actions, specific stakeholder names, and what needs to happen in the next 48 hours. Be tactical and direct."
    elif persona == "vp_sales":
        persona_instruction = "Focus on pipeline health, revenue at risk, forecast accuracy, and team performance patterns. Be strategic and data-driven but still human."
    elif persona == "executive":
        persona_instruction = "Compress everything to 3 sentences max. One key number. One risk. One decision to make. No fluff whatsoever."
    else:
        persona_instruction = "Focus on deal-by-deal actions and specific steps."

    # STEP 3 — TONE DETECTION
    health_score = None
    # Match strings like "health score of 21.3%" or "health score: 21"
    health_match = re.search(r'health\D*(\d+(?:\.\d+)?)', raw_output, re.IGNORECASE)
    if health_match:
        try:
            health_score = float(health_match.group(1))
        except ValueError:
            pass

    has_zero_prob = "0%" in raw_output or "probability: 0" in raw_output or "probability of 0" in raw_output

    if (health_score is not None and health_score < 30) or has_zero_prob:
        tone = "Be direct and urgent. Do not soften the message. This account needs immediate attention."
    elif health_score is not None and health_score > 70:
        # Check if there are deal probabilities > 75% in raw text
        probs = re.findall(r'(\d+)%', raw_output)
        has_high_prob = any(int(p) > 75 for p in probs if p.isdigit())
        if has_high_prob:
            tone = "Be confident and forward-looking. Focus on maximizing momentum. Energy should feel like a team that is winning."
        else:
            tone = "Be balanced. Acknowledge what is working but name the specific gaps clearly. Be honest about risk without being alarmist."
    else:
        tone = "Be balanced. Acknowledge what is working but name the specific gaps clearly. Be honest about risk without being alarmist."

    # STEP 4 — CONVERSATION MEMORY
    history_summary = "None"
    if conversation_history:
        last_messages = conversation_history[-3:]
        summary_parts = []
        for msg in last_messages:
            role = msg.get("role", "user") if "role" in msg else msg.get("sender", "user")
            content = msg.get("content", "") if "content" in msg else msg.get("text", "")
            truncated = content[:150] + "..." if len(content) > 150 else content
            summary_parts.append(f"{role}: {truncated}")
        history_summary = " | ".join(summary_parts)

    # STEP 1 & 5 — SYSTEM PROMPT & FORMATTING INSTRUCTIONS
    system_prompt = f"""You are APEX, a senior revenue intelligence advisor with 15 years of enterprise sales experience. You speak directly, confidently, and always connect data to business consequences. You never just report numbers — you tell the user what those numbers mean and what they should do right now. You use 'you' and 'your team' — never 'the user' or 'the system'. You have opinions. You notice things the user didn't ask about. You sound like the smartest person in the room who is also on their side.

TONE:
{tone}

PERSONA ROLE INSTRUCTION:
{persona_instruction}

CONVERSATION CONTEXT MEMORY:
Earlier in this conversation: {history_summary}
Reference this context naturally if relevant to the current response. If the user asked about something before, connect it to what you are saying now.

JSON SCHEMA TO EXCLUSIVELY OUTPUT:
{{
  "headline": "one punchy line that captures the most important thing",
  "urgency": "P1 | P2 | P3",
  "summary": "2-3 sentences written like a senior advisor speaking directly to the user. Lead with meaning not data. Connect numbers to business consequences.",
  "opportunities": [
    {{
      "id": "string",
      "name": "string", 
      "stage": "string",
      "amount": "string",
      "probability": "string",
      "insight": "one sentence of human commentary about what this deal actually means"
    }}
  ],
  "risks": [
    {{
      "type": "string — name the risk plainly",
      "account": "string",
      "action": "string — written as Do X because Y"
    }}
  ],
  "flag": "one thing the user did not ask about but needs to know. Start with 'I want to flag something.'",
  "recommended_actions": [
    {{
      "priority": 1,
      "role": "Account Manager | VP Sales | Executive",
      "action": "string — Do X because Y format. Specific, not generic."
    }}
  ],
  "closing_question": "one natural question that invites the user to go deeper. Should feel like a conversation not a menu.",
  "next_steps_suggestions": [
    "string", "string", "string"
  ]
}}

IMPORTANT: Do not output any preamble, markdown code fences, or explanation. Output ONLY the raw JSON string matching the schema.
"""

    payload = {
        "model": model,
        "prompt": f"System: {system_prompt}\n\nUser Prompt (Raw Data output to format):\n{raw_output}\n\nOutput ONLY the valid raw JSON object.",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 2048
        }
    }

    try:
        limits = httpx.Timeout(timeout=25.0, connect=5.0)
        async with httpx.AsyncClient(timeout=limits) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                result_text = response.json().get("response", "").strip()
                
                # Strip code block decorators if present
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                elif result_text.startswith("```"):
                    result_text = result_text[3:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                result_text = result_text.strip()
                
                # Test parse
                parsed = json.loads(result_text)
                
                # Check for required fields
                required = ["headline", "urgency", "summary", "opportunities", "risks", "flag", "recommended_actions", "closing_question", "next_steps_suggestions"]
                for req in required:
                    if req not in parsed:
                        raise ValueError(f"Missing schema key: {req}")
                
                return json.dumps(parsed)
            else:
                raise Exception(f"HTTP status {response.status_code}")
    except Exception as e:
        logger.error(f"Failed response formatting: {e}")
        # STEP 6 — SAFETY FALLBACK
        return raw_output
