"""
RESPONSE FORMATTER (response_formatter.py)
Formats raw LLM outputs into structured JSON schemas, managing persona tone,
urgency levels, conversation history context, and clean markdown presentation.
"""

# --- SECTION 1: Dependencies & LLM Endpoint Resolver ---
# Imports HTTP clients, regex utilities, and loads active LLM configuration endpoints.
import os
import json
import logging
import re
from typing import Optional, List, Dict
from dotenv import load_dotenv

backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(backend_dir, ".env"), override=True)

logger = logging.getLogger("response_formatter")

def get_active_llm_config() -> tuple:
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

# --- SECTION 2: Persona Response Formatting Engine ---
# Formats raw text according to specified user personas (Account Manager, Executive, AE).

async def format_response_for_user(
    raw_output: str, 
    persona: str = "account_manager", 
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Accepts raw LLM response, detects tone/urgency, handles conversation history memory,
    and calls Gemini 2.5 Flash API to format output into a senior sales advisor JSON object.
    If it fails or Gemini is unavailable, silently returns the original raw_output.
    """
    if not raw_output or not raw_output.strip():
        return raw_output

    # Detect if raw_output is already a quick-action JSON payload and bypass formatting
    trimmed = raw_output.strip()
    quick_action_keys = ["EXEC_EMAIL", "MEETING_AGENDA", "STAKEHOLDERS", "RISK_REVIEW"]
    if any(qkey in trimmed for qkey in quick_action_keys):
        # Checks if quick action JSON type is present in raw_output
        for qkey in quick_action_keys:
            if f'"type": "{qkey}"' in trimmed or f'"type":"{qkey}"' in trimmed or f'"type": \'{qkey}\'' in trimmed:
                logger.info(f"[ResponseFormatter] Quick action payload {qkey} detected. Bypassing persona formatting.")
                return raw_output

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logger.warning("[ResponseFormatter] GEMINI_API_KEY not found in env, bypassing formatting.")
        return raw_output

    # STEP 2 — PERSONA LAYER
    persona_norm = (persona or "account_manager").lower().replace(" ", "_")
    if persona_norm in ["executive", "exec", "c_suite"]:
        persona_instruction = (
            "EXECUTIVE PERSONA (BLUF Format): Lead immediately with 'BOTTOM LINE: ...'. "
            "Compress everything to 3-4 sentences max. Provide 1 key dollar metric, 1 core risk, "
            "and 1 executive decision to make. No tactical fluff or long lists."
        )
    elif persona_norm in ["vp_sales", "vp", "sales_director", "head_of_sales"]:
        persona_instruction = (
            "VP OF SALES PERSONA: Focus on overall pipeline health, revenue at risk, forecast accuracy, "
            "and team performance patterns. Highlight quarterly coverage impact and cross-account risks."
        )
    else:
        persona_instruction = (
            "ACCOUNT MANAGER PERSONA: Focus on deal-by-deal tactical actions, specific stakeholder names, "
            "case resolution steps, and what needs to happen in the next 48 hours. Be direct and operational."
        )

    # STEP 3 — TONE DETECTION
    health_score = None
    health_match = re.search(r'health\D*(\d+(?:\.\d+)?)', raw_output, re.IGNORECASE)
    if health_match:
        try:
            health_score = float(health_match.group(1))
        except ValueError:
            pass

    has_zero_prob = "0%" in raw_output or "probability: 0" in raw_output or "probability of 0" in raw_output

    if (health_score is not None and health_score < 30) or has_zero_prob:
        tone = "Be direct and urgent. Do not soften the message. Name the specific risk immediately."
    elif health_score is not None and health_score > 70:
        probs = re.findall(r'(\d+)%', raw_output)
        has_high_prob = any(int(p) > 75 for p in probs if p.isdigit())
        if has_high_prob:
            tone = "Be confident and forward-looking. Focus on accelerating momentum."
        else:
            tone = "Be balanced. Acknowledge momentum but state specific gap items clearly."
    else:
        tone = "Be balanced. Name the specific gaps clearly without being alarmist."

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

    # STEP 5 — SYSTEM PROMPT & FORMATTING INSTRUCTIONS
    system_prompt = f"""You are APEX, a senior revenue intelligence advisor. You speak directly, confidently, and always connect data to business consequences. You never just report numbers — you tell the user what those numbers mean and what they should do right now. Use 'you' and 'your team' — never 'the user' or 'the system'.

TONE:
{tone}

PERSONA ROLE INSTRUCTION:
{persona_instruction}

CONVERSATION CONTEXT MEMORY:
Earlier in this conversation: {history_summary}

JSON SCHEMA TO EXCLUSIVELY OUTPUT:
{{
  "headline": "one punchy line that captures the most important thing",
  "urgency": "P1 | P2 | P3",
  "summary": "Persona-tailored summary paragraph matching instructions above.",
  "opportunities": [
    {{
      "id": "string",
      "name": "string", 
      "stage": "string",
      "amount": "string",
      "probability": "string",
      "insight": "one sentence of human commentary"
    }}
  ],
  "risks": [
    {{
      "type": "string",
      "account": "string",
      "action": "Do X because Y"
    }}
  ],
  "flag": "one unasked thing the user needs to know, starting with 'I want to flag something.'",
  "recommended_actions": [
    {{
      "priority": 1,
      "role": "Account Manager | VP Sales | Executive",
      "action": "Do X because Y format"
    }}
  ],
  "closing_question": "one natural question inviting next step",
  "next_steps_suggestions": [
    "string", "string", "string"
  ]
}}

Output ONLY valid raw JSON without preamble or markdown fences.
"""

    try:
        from reasoning_engine import call_gemini_api
        user_prompt = f"Raw Data Output to Format:\n{raw_output}"
        
        result_text = call_gemini_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            api_key=gemini_key,
            max_tokens=2048,
            timeout=20
        )
        
        if not result_text:
            return raw_output

        # Clean code fences if returned
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        # Tier-1: Strict native parse (fastest)
        try:
            parsed = json.loads(result_text)
        except json.JSONDecodeError:
            # Tier-2: Structural repair — handles unescaped quotes, trailing commas,
            # truncated strings — common artifacts from Gemini 2.5 Flash streaming.
            try:
                from json_repair import repair_json
                repaired = repair_json(result_text, return_objects=True)
                if isinstance(repaired, dict):
                    parsed = repaired
                    logger.warning("[ResponseFormatter] json_repair rescued malformed Gemini output.")
                else:
                    raise ValueError("json_repair returned non-dict")
            except Exception as repair_err:
                # Tier-3: Irrecoverable — return raw_output (graceful degradation)
                logger.error(f"[ResponseFormatter Error] json_repair also failed: {repair_err}. Returning raw output.")
                return raw_output

        # Validate required schema keys
        required = ["headline", "urgency", "summary", "opportunities", "risks", "flag", "recommended_actions", "closing_question", "next_steps_suggestions"]
        for req in required:
            if req not in parsed:
                raise ValueError(f"Missing schema key: {req}")

        # STEP 6 — EMOJI SIGNAL INJECTION
        # Add priority icons to recommended actions
        for act in parsed.get("recommended_actions", []):
            prio = act.get("priority", 2)
            act_text = act.get("action", "")
            if prio == 1 and not act_text.startswith("⚡"):
                act["action"] = f"⚡ {act_text}"
            elif prio == 2 and not act_text.startswith("📋"):
                act["action"] = f"📋 {act_text}"
            elif prio >= 3 and not act_text.startswith("📊"):
                act["action"] = f"📊 {act_text}"

        logger.info(f"[ResponseFormatter] Formatting succeeded for persona: {persona_norm}")
        return json.dumps(parsed)

    except Exception as e:
        logger.error(f"[ResponseFormatter Error] Failed response formatting: {e}")
        return raw_output
