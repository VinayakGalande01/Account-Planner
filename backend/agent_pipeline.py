"""
AGENT PIPELINE ENGINE (agent_pipeline.py)
Orchestrates the 4-Phase Plan-and-Execute agentic workflow:
Phase 1 (Planner LLM), Phase 2 (Python Retrieval), Phase 3 (Reasoner LLM), Phase 4 (Narrative LLM Stream).
"""

# --- SECTION 1: Dependencies & Network Setup ---
# Imports HTTP clients, asyncio tasks, data retrieval layers, and environmental model URLs.
import os
import sys
import json
import time
import httpx
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, asdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_engine import DataEngine
from data_retrieval_layer import execute_data_retrieval

logger = logging.getLogger("llm")
LLM_URL = os.getenv("LLM_URL", "http://10.181.43.105:8000/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:latest")

# --- SECTION 2: Anti-Hallucination & JSON Healing Utilities ---
# Sanitizes LLM outputs, strips markdown fences, and heals missing JSON delimiters dynamically.
def clean_and_parse_json(text: str) -> dict:
    """Robust parser that strips markdown wrappers, sanitizes control characters,
    performs syntax healing on missing delimiters, and parses JSON."""
    clean_text = text.strip()
    
    # Remove markdown code fences if present (e.g. ```json ... ```)
    clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
    clean_text = re.sub(r"\s*```$", "", clean_text)
    clean_text = clean_text.strip()

    # Try parsing directly with strict=False
    try:
        return json.loads(clean_text, strict=False)
    except json.JSONDecodeError:
        pass

    # Heuristic emergency extraction: find outer boundaries
    start = clean_text.find("{")
    end = clean_text.rfind("}")
    if start != -1 and end != -1:
        clean_text = clean_text[start:end+1]
        try:
            return json.loads(clean_text, strict=False)
        except json.JSONDecodeError:
            pass

    # Regex Syntax Healing: inject missing commas (Step D Refinement)
    # 1. Properties or elements separated by newline: "val"\n"key" -> "val",\n"key"
    healed = re.sub(r'("|\d+|true|false|null|\}|\])\s*\n\s*"', r'\1,\n"', clean_text)
    # 2. Array objects missing commas: }\n{ -> },\n{
    healed = re.sub(r'\}\s*\n\s*\{', r'},\n{', healed)

    try:
        return json.loads(healed, strict=False)
    except json.JSONDecodeError:
        pass

    # Clean non-printable control characters except \t, \n, \r
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", clean_text)
    
    # Try one more time with the sanitized string
    try:
        return json.loads(sanitized, strict=False)
    except json.JSONDecodeError:
        pass

    # Try extraction on sanitized string
    start = sanitized.find("{")
    end = sanitized.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(sanitized[start:end+1], strict=False)
        except json.JSONDecodeError:
            pass

    # Final attempt: standard json.loads to raise the original/correct exception
    return json.loads(clean_text)


# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════

PHASE1_PLANNER_PROMPT = """You are the Orchestration Planner for APEX.
Analyze the user query, classify intent, extract parameters, and output ONLY a valid JSON matching this schema:
{
  "intent": "CONTACT_QUERY" | "PIPELINE_QUERY" | "HEALTH_QUERY" | "ACTION_RECOMMENDATION" | "RISK_ANALYSIS" | "ACCOUNT_PLAN",
  "decision": "Decision type label",
  "outcome": "Desired outcome label",
  "params": {
    "accounts": ["names of accounts mentioned"],
    "opportunities": ["IDs of opportunities mentioned"],
    "contacts": ["names of contacts mentioned"],
    "window": "time window string or null",
    "stage": "stage name or null",
    "limit": integer or null
  },
  "confidence": "HIGH" | "MEDIUM" | "LOW"
}
Do not include any pre/post text. Output raw JSON only.
"""

PHASE3_REASONER_PROMPT = """You are the Core Reasoning Engine of APEX, operating as an Elite Enterprise Account Strategist with 25+ years of experience in B2B revenue operations.

Your input consists of:
1. The Decision Context and Execution Plan calculated in Phase 1.
2. Raw data subsets retrieved from the CRM tables (Account, Opportunity, Contact, Activity, Case).
3. The deterministic [DATA_SUFFICIENCY_REPORT] and [CONTRADICTIONS_AND_WARNINGS] if any are triggered.

Your task is to synthesize this input and construct a comprehensive, highly strategic 'Structured Intelligence Package' in strict JSON format.

CRITICAL DESIGN AND REASONING CONSTRAINTS:
1. NO GENERIC RECOMMENDATIONS: Do not say 'conduct stakeholder mapping' or 'follow up soon'. You must name specific people, actions, deadlines (e.g., 'within 5 business days'), and revenue justifications derived from the metrics.
2. STAKEHOLDER SELECTION & GROUNDING: Never fabricate, invent, or guess any contact names. If the referenced entity exists in CRM, use its name. Otherwise, explicitly state: "No mapped contact available." NEVER generate actions like "Contact [Name]" if no contact is mapped.
3. CONFIDENCE-DRIVEN AGGRESSIVENESS: Your tone and recommendations must match the data confidence. HIGH CONFIDENCE: Recommend immediate, aggressive execution. LOW CONFIDENCE: Recommend validation, investigation, and data hygiene actions before escalation.
4. EVIDENCE REQUIREMENT: Every single strategic recommendation MUST explicitly cite at least one supporting evidence point directly derived from the CRM data.
5. EXPLAINABILITY & EVIDENCE TRACE: For every major recommendation, you must populate the 5-step reasoning trace tracking: Priority Badge (Priority: CRITICAL/HIGH/MEDIUM/LOW) -> Observation -> Evidence -> Business Impact -> Implication -> Action.
6. NO FAKE PRECISION: Do not invent expected revenue impact dollar amounts or risk reduction percentages. Use qualitative bands ("HIGH", "MEDIUM", "LOW") or reference the exact deterministic numbers calculated by the engine in the context.
7. DUAL MODES (FACTUAL vs STRATEGIC): If `intent` is `CONTACT_QUERY`, run in Factual Mode: leave the `reasoning_trace` empty and only output the raw facts. For all other intents, run in Strategic Mode and fully execute the 5-step reasoning trace.
8. CONTRADICTION & SUFFICIENCY INTEGRATION: Respect the deterministic sufficiency score and contradiction warning signals. Lower overall confidence if data is insufficient.
9. EVIDENCE CITATION: Every recommendation in the `recommendations` array MUST include supporting evidence derived from the CRM data context. If no evidence exists for a recommendation, DO NOT include the recommendation. Unearned recommendations are forbidden.
10. ROLE DEFINITION — You are an INTERPRETER, not a decision-maker. The deterministic intelligence layer has ALREADY decided what matters, what is risky, what actions are valid, and what actions are forbidden (via [HARD_CONSTRAINTS]). Your job is to EXPLAIN why it matters, why it is risky, and why the action is recommended. Do NOT override deterministic findings. Do NOT invent new actions beyond what the data supports.

You must output a single, valid JSON object matching this exact architectural structure without any markdown wrappers or conversational text:
{
  "intent": "...",
  "decision_context": "...",
  "desired_outcome": "...",
  "account_state": {
    "health_score": 1-100,
    "risk_factors": []
  },
  "opportunity_state": {
    "deal_velocity": "STALLING|ACCELERATING|NORMAL",
    "value_at_risk_usd": 0.00
  },
  "stakeholder_state": {
    "primary_decision_maker": "NAME or UNMAPPED",
    "key_influencers": [],
    "blockers": []
  },
  "reasoning_trace": {
    "observations": [],
    "evidence": [],
    "business_impact": [],
    "implications": [],
    "decisions": []
  },
  "recommendations": [
    {
      "action": "EXPLICIT_ACTION_STEP",
      "reason": "STRATEGIC_WHY",
      "expected_impact": "BUSINESS_OUTCOME",
      "urgency": "IMMEDIATE|HIGH|MEDIUM",
      "timeline_days": 5
    }
  ],
  "alternative_recommendations": [],
  "expected_outcomes": {
    "expected_revenue_impact": "HIGH|MEDIUM|LOW",
    "expected_risk_reduction": "HIGH|MEDIUM|LOW",
    "revenue_exposure_usd": 0.00
  },
  "confidence": {
    "intent_confidence": 1-100,
    "decision_confidence": 1-100,
    "data_confidence": 1-100,
    "reasoning_confidence": 1-100,
    "recommendation_confidence": 1-100,
    "overall_confidence": 1-100
  }
}
"""

PHASE3_FACTUAL_PROMPT = """You are the APEX Factual Router.
Your ONLY task is to read the exact facts from the retrieved CRM data and output them cleanly.
DO NOT invent any actions, do NOT generate a reasoning trace, do NOT attempt to strategize.
If the requested entity (e.g. contact) is not explicitly listed in the data, you MUST state "No mapped contact available".

You must output a single, valid JSON object matching this exact structure:
{
  "intent": "CONTACT_QUERY",
  "decision_context": "...",
  "desired_outcome": "...",
  "account_state": {
    "health_score": 100,
    "risk_factors": []
  },
  "opportunity_state": {
    "deal_velocity": "NORMAL",
    "value_at_risk_usd": 0.00
  },
  "stakeholder_state": {
    "primary_decision_maker": "NAME or 'No mapped contact available'",
    "key_influencers": ["NAME 1", "NAME 2"],
    "blockers": []
  },
  "reasoning_trace": {
    "observations": [],
    "evidence": [],
    "business_impact": [],
    "implications": [],
    "decisions": []
  },
  "recommendations": [
    {
      "action": "Ensure mapped stakeholders are correct and reach out for validation if missing.",
      "reason": "Standard contact hygiene",
      "expected_impact": "Improved stakeholder map",
      "urgency": "MEDIUM",
      "timeline_days": 5
    }
  ],
  "alternative_recommendations": [],
  "expected_outcomes": {
    "expected_revenue_impact": "LOW",
    "expected_risk_reduction": "LOW",
    "revenue_exposure_usd": 0.00
  },
  "confidence": {
    "intent_confidence": 100,
    "decision_confidence": 100,
    "data_confidence": 100,
    "reasoning_confidence": 100,
    "recommendation_confidence": 100,
    "overall_confidence": 100
  }
}
"""

# PHASE4_NARRATIVE_PROMPT is now dynamically built per-request by
# response_blueprint.build_phase4_prompt(blueprint).
# The static monolithic prompt has been replaced with mode-variant
# identity prompts + section templates in response_blueprint.py.
#
# Legacy fallback (used when no blueprint is provided):
PHASE4_NARRATIVE_PROMPT_FALLBACK = """You are the APEX Strategic Narrative Layer.
Generate a warm, professional strategic sales narrative based on the Structured Intelligence Package (SIP) JSON.

## RESPONSE CONTRACT
You MUST structure your response using these exact section headers:

__SECTION_INTENT__
[Intent from SIP]

__SECTION_HEADLINE__
[headline from SIP]

__SECTION_EXECUTIVE_SUMMARY__
[Maximum 3 bullet points. High-level executive summary.]

__SECTION_SUMMARY__
[3 clear sentences: situation, contact context, risk.]

__SECTION_SIGNALS__
• [Signal 1 with data evidence]
• [Signal 2]

__SECTION_ACTIONS__
• [Evidence-backed action 1]
• [Action 2]

__SECTION_CONFIDENCE__
{"score": "<confidence_pct>%", "status": "<confidence_pct>% Grounded (Direct facts from Excel)", "sources": ["Excel Database"]}

__SECTION_END__

STRICT RULES:
1. Do not output any conversational preambles or postambles.
2. Use the exact section headers.
3. Replace "<confidence_pct>" with the actual confidence percentage from the SIP JSON.
4. Every recommendation MUST cite supporting evidence.
"""


# ═══════════════════════════════════════════════════════════════
# DYNAMIC LLM CONFIGURATION RESOLUTION (Auto-Healing Fallbacks)
# ═══════════════════════════════════════════════════════════════

_cached_url: Optional[str] = None
_cached_model: Optional[str] = None

async def _get_active_llm_config(client: httpx.AsyncClient) -> tuple[str, str]:
    """Dynamically resolves the active LLM URL and Model name.
    Checks memory cache, then a local file-based cache ('llm_cache.json') to persist across processes.
    If uncached, probes the configured primary URL first, falling back to local localhost:11434."""
    global _cached_url, _cached_model
    
    # 1. Memory Cache
    if _cached_url is not None and _cached_model is not None:
        return _cached_url, _cached_model
        
    # 2. Local File Cache (persists across processes/test-runs)
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cached_url = data.get("url")
                cached_model = data.get("model")
                if cached_url and cached_model:
                    # Verify cached URL is reachable
                    base_url = cached_url.rsplit("/api/generate", 1)[0] or cached_url
                    try:
                        res = await client.get(base_url, timeout=1.5)
                        if res.status_code < 500:
                            _cached_url = cached_url
                            _cached_model = cached_model
                            logger.info(f"[LLM CONFIG] Loaded active LLM from cache file: {cached_url} (model: {cached_model})")
                            return _cached_url, _cached_model
                    except Exception:
                        logger.info(f"[LLM CONFIG WARNING] Cached LLM at {cached_url} was unreachable. Re-probing...")
        except Exception:
            pass
            
    primary_url = os.getenv("LLM_URL", "http://10.181.43.105:8000/api/generate")
    primary_model = os.getenv("MODEL_NAME", "llama3.2:latest")
    
    # 3. Try to ping primary endpoint using its configured URL directly (probe base server or model list)
    try:
        # Check base URL or probe URL directly to support custom remote proxies
        base_url = primary_url.rsplit("/api/generate", 1)[0] or primary_url
        res = await client.get(base_url, timeout=2.0)
        if res.status_code < 500:
            logger.info(f"[LLM CONFIG] Successfully connected to remote GPU primary LLM at {primary_url} (model: {primary_model})")
            _cached_url = primary_url
            _cached_model = primary_model
            # Save to file cache
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump({"url": _cached_url, "model": _cached_model}, f)
            except Exception:
                pass
            return _cached_url, _cached_model
    except Exception:
        pass
        
    # Default fallback to configured values if primary is completely unreachable
    logger.info(f"[LLM CONFIG] Primary LLM unreachable. Defaulting to configured environment values: {primary_url} (model: {primary_model})")
    return primary_url, primary_model


# ═══════════════════════════════════════════════════════════════
# PIPELINE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def run_phase1_planner(query: str, client: httpx.AsyncClient) -> dict:
    """Phase 1: Parse user query into structured context JSON using local LLM via Layer 1 IntentClassifier."""
    logger.info(f"[PHASE 1] Analyzing query intent & parameters: '{query}'...")
    
    from intent_classifier import IntentClassifier, IntentEnum, UrgencyEnum, ScopeEnum, ExtractedEntities
    
    try:
        active_url, active_model = await _get_active_llm_config(client)
        classifier = IntentClassifier(model=active_model)
        classifier.url = active_url
        
        # Call synchronously in a thread pool to avoid blocking the async event loop
        output = await asyncio.to_thread(classifier.classify, query, "Account Manager")
    except Exception as e:
        logger.info(f"[PHASE 1 WARNING] IntentClassifier instantiation or call failed: {e}. Falling back to default.")
        from intent_classifier import IntentClassificationOutput
        output = IntentClassificationOutput(
            primary_intent=IntentEnum.ACTION_RECOMMENDATION,
            confidence_primary=0.5,
            extracted_entities=ExtractedEntities(),
            urgency=UrgencyEnum.MEDIUM,
            scope=ScopeEnum.ENTITY,
            context_summary=f"Classification failed: {str(e)}"
        )

    # Map primary intent enum to canonical pipeline intent name
    primary_intent = output.primary_intent.value
    has_account = bool(output.extracted_entities.account or (output.extracted_entities.account_list and len(output.extracted_entities.account_list) > 0))
    
    canonical_intent = "ACTION_RECOMMENDATION_QUERY"
    if primary_intent == "risk_assessment":
        canonical_intent = "RISK_ANALYSIS_QUERY"
    elif primary_intent == "opportunity_expansion":
        canonical_intent = "ACCOUNT_PLAN_QUERY" if has_account else "ACTION_RECOMMENDATION_QUERY"
    elif primary_intent == "competitive_intelligence":
        canonical_intent = "RISK_ANALYSIS_QUERY"
    elif primary_intent == "relationship_analysis":
        canonical_intent = "CONTACT_QUERY"
    elif primary_intent == "action_recommendation":
        canonical_intent = "ACCOUNT_PLAN_QUERY" if has_account else "ACTION_RECOMMENDATION_QUERY"
    elif primary_intent == "pipeline_summary":
        canonical_intent = "PIPELINE_SUMMARY_QUERY"
        
    # Map confidence to "HIGH", "MEDIUM", "LOW"
    confidence_val = "HIGH"
    if output.confidence_primary < 0.5:
        confidence_val = "LOW"
    elif output.confidence_primary < 0.8:
        confidence_val = "MEDIUM"
        
    # Format target lists
    accounts = []
    if output.extracted_entities.account:
        accounts.append(output.extracted_entities.account)
    if output.extracted_entities.account_list:
        for acc in output.extracted_entities.account_list:
            if acc not in accounts:
                accounts.append(acc)
                
    opportunities = []
    if output.extracted_entities.opportunity:
        opportunities.append(output.extracted_entities.opportunity)
        
    contacts = []
    if output.extracted_entities.contact:
        contacts.append(output.extracted_entities.contact)
        
    # Return backward-compatible dict
    return {
        "extracted_intent": canonical_intent,
        "decision_context": {
            "label": output.context_summary,
            "desired_outcome": f"Process query with intent '{primary_intent}' and urgency '{output.urgency.value}'"
        },
        "query_parameters": {
            "target_accounts": accounts,
            "target_opportunities": opportunities,
            "target_contacts": contacts,
            "time_window": output.extracted_entities.timeframe,
            "stage_filter": output.extracted_entities.stage,
            "limit": 10,
            "sort_by": None
        },
        "secondary_intents": [si.intent.value for si in (output.secondary_intents or [])],
        "confidence": confidence_val
    }


def run_phase2_retrieval(engine: DataEngine, phase1_json: dict) -> str:
    """Phase 2: Query the local Pandas engine and retrieve formatted text payload."""
    logger.info("[PHASE 2] Executing deterministic data retrieval...")
    return execute_data_retrieval(engine, phase1_json)


async def run_phase3_reasoner(retrieved_text: str, phase1_json: dict, client: httpx.AsyncClient, governance_directives: Optional[List[str]] = None) -> dict:
    """Phase 3: Execute deep strategic business reasoning on the retrieved data -> SIP JSON."""
    logger.info("[PHASE 3] Executing core business reasoning on retrieved facts...")
    
    max_attempts = 5
    cooldown_seconds = 3.5
    timeout_seconds = 1200.0 # 20 minutes
    custom_timeout = httpx.Timeout(timeout_seconds)
    
    for attempt in range(1, max_attempts + 1):
        try:
            active_url, active_model = await _get_active_llm_config(client)
            
            intent = phase1_json.get("intent") or phase1_json.get("extracted_intent") or ""
            is_factual = intent == "CONTACT_QUERY"
            system_content = PHASE3_FACTUAL_PROMPT if is_factual else PHASE3_REASONER_PROMPT

            if governance_directives:
                system_content += "\n\n[HARD_CONSTRAINTS]\n"
                for directive in governance_directives:
                    system_content += f"- {directive}\n"
            user_content = (
                f"CONTEXT DETAILS:\n{json.dumps(phase1_json, indent=2)}\n\n"
                f"RAW CRM DATA SUBSET EXECUTED:\n{retrieved_text}\n"
                f"Output ONLY valid JSON code block."
            )

            # Attempt to use Chat API (Step B Refinement - Token Hygiene)
            chat_url = active_url.replace("/api/generate", "/api/chat")
            chat_payload = {
                "model": active_model,
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content}
                ],
                "stream": False
            }
            
            try:
                logger.info(f"[PHASE 3] Attempt {attempt}/{max_attempts} - Chat API call: {chat_url}")
                response = await client.post(chat_url, json=chat_payload, timeout=custom_timeout)
                if response.status_code == 200:
                    raw_text = response.json().get("message", {}).get("content", "")
                    return clean_and_parse_json(raw_text)
                else:
                    logger.info(f"[PHASE 3 WARNING] Chat API returned {response.status_code}. Trying Generate API fallback...")
            except Exception as chat_err:
                logger.info(f"[PHASE 3 WARNING] Chat API failed: {chat_err}. Trying Generate API fallback...")

            # Fallback to Generate API (Raw Prompt concatenation)
            prompt_content = f"System: {system_content}\n\nCONTEXT DETAILS:\n{json.dumps(phase1_json, indent=2)}\n\nRAW CRM DATA SUBSET EXECUTED:\n{retrieved_text}\nOutput ONLY valid JSON code block."
            generate_payload = {
                "model": active_model,
                "prompt": prompt_content,
                "stream": False
            }
            logger.info(f"[PHASE 3] Attempt {attempt}/{max_attempts} - Generate API call: {active_url}")
            response = await client.post(active_url, json=generate_payload, timeout=custom_timeout)
            if response.status_code == 200:
                raw_text = response.json().get("response", "")
                return clean_and_parse_json(raw_text)
            else:
                raise httpx.HTTPStatusError(f"HTTP {response.status_code}", request=response.request, response=response)
                
        except Exception as e:
            logger.info(f"[PHASE 3 WARNING] Attempt {attempt}/{max_attempts} failed: {e.__class__.__name__} - {e}.")
            if attempt < max_attempts:
                logger.info(f"[PHASE 3] Halting for {cooldown_seconds}s before next retry...")
                await asyncio.sleep(cooldown_seconds)
            else:
                import traceback
                traceback.print_exc()
                logger.info(f"[PHASE 3 ERROR] All {max_attempts} attempts failed. Generating safe fallback reasoning package.")
                
    # Safe default fallback matrix aligned to the upgraded schema (Step C Refinement)
    fallback_plan = {
        "intent": phase1_json.get("intent") or phase1_json.get("extracted_intent") or "ACTION_RECOMMENDATION",
        "decision_context": "Core Strategic Reasoner Trace Offline",
        "desired_outcome": "Verify connection and restore dynamic reasoning engine functionality",
        "account_state": {
            "health_score": 100,
            "risk_factors": []
        },
        "opportunity_state": {
            "deal_velocity": "NORMAL",
            "value_at_risk_usd": 0.00
        },
        "stakeholder_state": {
            "primary_decision_maker": "UNMAPPED",
            "key_influencers": [],
            "blockers": []
        },
        "reasoning_trace": {
            "observations": [
                "APEX lost connection to your remote reasoning GPU."
            ],
            "inferences": [
                "Dynamic cognitive trace is currently unavailable."
            ],
            "decisions": [
                "Defaulting to safe local rule-based diagnostics."
            ]
        },
        "recommendations": [
            {
                "action": "Check connection to your local Ollama node or remote GPU.",
                "reason": "Restores full cognitive strategic capabilities.",
                "expected_impact": "Cognitive actions return to active status.",
                "urgency": "HIGH",
                "timeline_days": 1
            }
        ],
        "alternative_recommendations": [],
        "expected_outcomes": {
            "expected_revenue_impact_usd": 0.00,
            "expected_risk_reduction_pct": 0
        },
        "confidence": {
            "intent_confidence": 100,
            "decision_confidence": 100,
            "data_confidence": 100,
            "reasoning_confidence": 0,
            "recommendation_confidence": 0,
            "overall_confidence": 0
        }
    }
    return fallback_plan


async def run_phase4_narrative_stream(
    sip_json: dict,
    original_query: str,
    client: httpx.AsyncClient,
    blueprint=None,
) -> AsyncGenerator[str, None]:
    """Phase 4: Stream the strategic Response Contract formatted narrative to the client.
    
    Information Choreography:
        When a ResponseBlueprint is provided, the Phase 4 prompt is dynamically
        assembled to include ONLY the sections relevant to the current query's
        intent + scope + confidence. This ensures narrative variability across
        different query types.
    """
    logger.info("[PHASE 4] Streaming narrative response contract...")
    
    # Build prompt dynamically from blueprint, or fall back to legacy
    if blueprint is not None:
        from response_blueprint import build_phase4_prompt
        narrative_prompt = build_phase4_prompt(blueprint)
        logger.info(f"[PHASE 4] Blueprint mode: {blueprint.mode.value} | Sections: {blueprint.get_ordered_sections()}")
    else:
        narrative_prompt = PHASE4_NARRATIVE_PROMPT_FALLBACK
    
    try:
        active_url, active_model = await _get_active_llm_config(client)
        prompt = f"System: {narrative_prompt}\n\nOriginal Query: {original_query}\nStructured Intelligence Package (SIP):\n{json.dumps(sip_json)}"
        payload = {
            "model": active_model,
            "prompt": prompt,
            "stream": True
        }
        custom_timeout = httpx.Timeout(connect=3.0, read=1800.0, write=10.0, pool=30.0)
        async with client.stream("POST", active_url, json=payload, timeout=custom_timeout) as response:
            async for chunk in response.aiter_lines():
                if chunk:
                    try:
                        data = json.loads(chunk)
                        if "response" in data:
                            yield data["response"]
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.info(f"[PHASE 4 ERROR] Streaming failed: {e}")
        # Standard fallback output so the UI never breaks
        yield f"__SECTION_INTENT__\nACTION_RECOMMENDATION\n"
        yield f"__SECTION_HEADLINE__\nStrategic Assessment nominal — Narrative fallback active\n"
        fallback_summary = sip_json.get("situation") or sip_json.get("situation_summary") or "Strategic overview trace loaded."
        yield f"__SECTION_SUMMARY__\nI have successfully retrieved the core data package, but experienced an issue compiling the natural language stream. Here is the direct situation overview: {fallback_summary}\n"
        yield f"__SECTION_SIGNALS__\n• [RISK] Reasoning trace fallback initialized.\n"
        yield f"__SECTION_ACTIONS__\n• [Action] Check the status of your remote GPU node.\n"
        yield f"__SECTION_CONFIDENCE__\n{{\"score\": \"30%\", \"status\": \"Degraded\", \"sources\": [\"Excel Database\"]}}\n"
        yield "__SECTION_END__"


# ═══════════════════════════════════════════════════════════════
# LOCAL INTEGRATION TESTING RUNNER
# ═══════════════════════════════════════════════════════════════

async def test_agent_pipeline():
    """Verify Phase 1, 2, and 3 synchronously to validate the pipeline flow."""
    logger.info("=== STARTING AGENT PIPELINE INTEGRATION TEST ===")
    
    test_query = "Who should I call at Infosys?"
    
    # Initialize DataEngine
    dataset_1 = r"C:\Users\VINAYAK\Downloads\SF_AccountingAgent_DummyData.xlsx"
    dataset_2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SF_AccountingAgent_DummyData.xlsx")
    p = dataset_1 if os.path.exists(dataset_1) else dataset_2
    logger.info(f"Loading test database: {p}")
    engine = DataEngine(p)
    
    async with httpx.AsyncClient() as client:
        # Phase 1
        p1_res = await run_phase1_planner(test_query, client)
        logger.info(f"\n[PHASE 1 RESULT] JSON:\n{json.dumps(p1_res, indent=2)}")
        
        # Phase 2
        p2_res = run_phase2_retrieval(engine, p1_res)
        logger.info(f"\n[PHASE 2 RESULT] Length: {len(p2_res)} chars. Sample:\n{p2_res[:800]}")
        
        # Phase 3
        from intelligence_layer import generate_strategic_synthesis
        from data_retrieval_layer import Phase1Output
        p1_parsed = Phase1Output.from_json(p1_res)
        synthesis = generate_strategic_synthesis(
            engine,
            intent=p1_res.get("extracted_intent", ""),
            account_id=None,
            query_scope=p1_parsed.query_scope
        )
        p3_res = await run_phase3_reasoner(p2_res, p1_res, client, synthesis.governance_directives)
        logger.info(f"\n[PHASE 3 RESULT] Structured Intelligence Package (SIP):\n{json.dumps(p3_res, indent=2)}")
        
        # Phase 4 Narrative sample
        logger.info("\n[PHASE 4 PREVIEW] Streaming first 200 chars:")
        count = 0
        async for token in run_phase4_narrative_stream(p3_res, test_query, client):
            logger.info(token, end="", flush=True)
            count += len(token)
            if count > 200:
                logger.info("\n[Truncated Preview]")
                break
                
    logger.info("\n=== AGENT PIPELINE TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_agent_pipeline())
