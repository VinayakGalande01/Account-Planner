"""
APEX Pure-Agentic Plan-and-Execute Pipeline

Orchestrates:
    Phase 1 (Planner LLM): Extract strategic business intent and parameters -> JSON
    Phase 2 (Retrieval Py): Deterministic Pandas filtering -> Pipe-delimited Text Context
    Phase 3 (Reasoner LLM): Core business reasoning -> Structured Intelligence Package (SIP) JSON
    Phase 4 (Narrative LLM): Strategic response contract generation -> RC Stream
"""

import os
import sys
import json
import time
import httpx
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, asdict

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_engine import DataEngine
from data_retrieval_layer import execute_data_retrieval

# Load configuration from environment
LLM_URL = os.getenv("LLM_URL", "http://10.181.43.105:8000/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:latest")


# ═══════════════════════════════════════════════════════════════
# JSON PARSING UTILITIES (Anti-Hallucination Guardrails)
# ═══════════════════════════════════════════════════════════════

import re

def clean_and_parse_json(text: str) -> dict:
    """Robust parser that strips markdown wrappers, sanitizes control characters,
    and parses JSON."""
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
        extracted = clean_text[start:end+1]
        try:
            return json.loads(extracted, strict=False)
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

PHASE3_REASONER_PROMPT = """You are the Core Reasoner for APEX.
Analyze the retrieved CRM data context, run strategic business thinking, and output ONLY a valid JSON representing the Structured Intelligence Package (SIP) exactly matching this schema:
{
  "headline": "One short strategic headline",
  "situation": "1-2 sentences summarizing the current state and its business relevance",
  "contact": {
    "name": "Full name or empty string",
    "role": "Role (e.g. Decision Maker) or empty string",
    "action": "Specific next step with them or empty string"
  },
  "actions": [
    {
      "text": "Specific evidence-based action (who, what, when)",
      "impact": "Expected positive business impact",
      "urgency": "CRITICAL" | "HIGH" | "MEDIUM"
    }
  ],
  "risks": [
    "Core data-derived risk statement"
  ],
  "confidence": {
    "overall": "HIGH" | "MEDIUM" | "LOW",
    "pct": 0 to 100
  }
}
Do not invent facts. Only use numbers and names from the data. Do not include any pre/post text. Output raw JSON only.
"""

PHASE4_NARRATIVE_PROMPT = """You are the APEX Strategic Narrative Layer.
Generate a warm, professional strategic sales narrative based on the Structured Intelligence Package (SIP) JSON, matching the exact Response Contract format.

## RESPONSE CONTRACT
You MUST structure your response using these exact section headers:

__SECTION_INTENT__
[Intent from SIP, e.g. PIPELINE_QUERY]

__SECTION_HEADLINE__
[headline from SIP]

__SECTION_SUMMARY__
[Based on situation, contact, and risks from SIP, write a human, professional overview in 3 clear sentences]

__SECTION_SIGNALS__
• [Formulate strategic signal 1 based on SIP risks and situation - with details and numbers]
• [Signal 2]
• [Signal 3]

__SECTION_ACTIONS__
• [Action 1 from SIP actions - specific contact, action, timeline, expected impact]
• [Action 2]
• [Action 3]

[Include CRM Hygiene gaps if any in the data context, e.g.]
__SECTION_CRM_HYGIENE__
⚠️ [Hygiene Gap]

__SECTION_CONFIDENCE__
{"score": "<confidence_pct>%", "status": "<confidence_pct>% Grounded (Direct facts from Excel)", "sources": ["Excel Database"]}

__SECTION_END__

STRICT RULES:
1. Do not output any conversational preambles or postambles. Only output the section headers and content.
2. Use the exact section headers.
3. Be friendly and highly strategic, like a top sales co-pilot.
4. Replace the "<confidence_pct>" placeholders in the __SECTION_CONFIDENCE__ section with the actual confidence percentage number from the SIP JSON (e.g., if pct is 80, output "80%").
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
                            print(f"[LLM CONFIG] Loaded active LLM from cache file: {cached_url} (model: {cached_model})")
                            return _cached_url, _cached_model
                    except Exception:
                        print(f"[LLM CONFIG WARNING] Cached LLM at {cached_url} was unreachable. Re-probing...")
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
            print(f"[LLM CONFIG] Successfully connected to remote GPU primary LLM at {primary_url} (model: {primary_model})")
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
        
    # 4. Try to auto-detect local fallback Ollama (http://localhost:11434)
    fallback_url = "http://localhost:11434/api/generate"
    try:
        res = await client.get("http://localhost:11434/api/tags", timeout=2.0)
        if res.status_code == 200:
            data = res.json()
            models = data.get("models", [])
            if models:
                available_names = [m["name"] for m in models]
                matched_model = primary_model
                if primary_model not in available_names:
                    # Match by base name
                    base_model = primary_model.split(":")[0]
                    found = False
                    for name in available_names:
                        if base_model in name:
                            matched_model = name
                            found = True
                            break
                    if not found:
                        matched_model = models[0]["name"]
                
                print(f"[LLM CONFIG] Primary LLM unreachable. Auto-healed to local fallback at {fallback_url} (model: {matched_model})")
                _cached_url = fallback_url
                _cached_model = matched_model
                # Save to file cache
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump({"url": _cached_url, "model": _cached_model}, f)
                except Exception:
                    pass
                return _cached_url, _cached_model
    except Exception:
        pass
        
    # Default fallback to configured values if both are completely unreachable
    print(f"[LLM CONFIG] Both primary and local fallback unreachable. Defaulting to configured {primary_url}")
    return primary_url, primary_model


# ═══════════════════════════════════════════════════════════════
# PIPELINE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def run_phase1_planner(query: str, client: httpx.AsyncClient) -> dict:
    """Phase 1: Parse user query into structured context JSON using local LLM."""
    print(f"[PHASE 1] Analyzing query intent & parameters: '{query}'...")
    
    try:
        active_url, active_model = await _get_active_llm_config(client)
        payload = {
            "model": active_model,
            "prompt": f"System: {PHASE1_PLANNER_PROMPT}\n\nUser Query: {query}\nOutput ONLY valid JSON code block.",
            "stream": False
        }
        response = await client.post(active_url, json=payload, timeout=120.0)
        if response.status_code == 200:
            raw_text = response.json().get("response", "")
            return clean_and_parse_json(raw_text)
        else:
            raise httpx.HTTPStatusError(f"HTTP {response.status_code}", request=response.request, response=response)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[PHASE 1 WARNING] LLM planner failed: {e.__class__.__name__} - {e}. Activating deterministic fallback.")
        # Minimal robust fallback
        return {
            "extracted_intent": "ACTION_RECOMMENDATION",
            "decision_context": {
                "label": "Operational Overview",
                "desired_outcome": "Address general portfolio inquiry"
            },
            "query_parameters": {
                "target_accounts": [],
                "target_opportunities": [],
                "target_contacts": [],
                "time_window": None,
                "stage_filter": None,
                "limit": 10,
                "sort_by": None
            },
            "secondary_intents": [],
            "confidence": "MEDIUM"
        }


def run_phase2_retrieval(engine: DataEngine, phase1_json: dict) -> str:
    """Phase 2: Query the local Pandas engine and retrieve formatted text payload."""
    print("[PHASE 2] Executing deterministic data retrieval...")
    return execute_data_retrieval(engine, phase1_json)


async def run_phase3_reasoner(retrieved_text: str, client: httpx.AsyncClient) -> dict:
    """Phase 3: Execute deep strategic business reasoning on the retrieved data -> SIP JSON."""
    print("[PHASE 3] Executing core business reasoning on retrieved facts...")
    
    try:
        active_url, active_model = await _get_active_llm_config(client)
        payload = {
            "model": active_model,
            "prompt": f"System: {PHASE3_REASONER_PROMPT}\n\nRetrieved CRM Data Context:\n{retrieved_text}\nOutput ONLY valid JSON code block.",
            "stream": False
        }
        response = await client.post(active_url, json=payload, timeout=180.0)
        if response.status_code == 200:
            raw_text = response.json().get("response", "")
            return clean_and_parse_json(raw_text)
        else:
            raise httpx.HTTPStatusError(f"HTTP {response.status_code}", request=response.request, response=response)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[PHASE 3 ERROR] Core Reasoner failed: {e.__class__.__name__} - {e}. Generating safe fallback reasoning package.")
        return {
            "headline": "Core Reasoning Unreachable — Displaying Raw Portfolio Baseline",
            "situation_summary": "System was unable to establish a deep neural reasoning trace due to local LLM timeout.",
            "primary_contact_recommendation": None,
            "next_best_actions": [
                {
                    "text": "Check connection to your local Ollama node",
                    "reason": "Neural engine request timed out",
                    "expected_impact": "Restores full cognitive capabilities",
                    "ignore_risk": "Cognitive actions remain degraded",
                    "urgency": "HIGH",
                    "owner": "Account Manager"
                }
            ],
            "risk_implications": ["System is running on degraded deterministic rules."],
            "business_outcome": "Nominal tracking",
            "confidence": {
                "intent": "MEDIUM",
                "decision": "MEDIUM",
                "data": "HIGH",
                "reasoning": "LOW",
                "recommendation": "LOW",
                "overall": "LOW",
                "overall_pct": 30
            }
        }


async def run_phase4_narrative_stream(
    sip_json: dict,
    original_query: str,
    client: httpx.AsyncClient
) -> AsyncGenerator[str, None]:
    """Phase 4: Stream the strategic Response Contract formatted narrative to the client."""
    print("[PHASE 4] Streaming narrative response contract...")
    
    try:
        active_url, active_model = await _get_active_llm_config(client)
        prompt = f"System: {PHASE4_NARRATIVE_PROMPT}\n\nOriginal Query: {original_query}\nStructured Intelligence Package (SIP):\n{json.dumps(sip_json)}"
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
        print(f"[PHASE 4 ERROR] Streaming failed: {e}")
        # Standard fallback output so the UI never breaks
        yield f"__SECTION_INTENT__\nACTION_RECOMMENDATION\n"
        yield f"__SECTION_HEADLINE__\nStrategic Assessment nominal — Narrative fallback active\n"
        fallback_summary = sip_json.get("situation") or sip_json.get("situation_summary") or "Strategic overview trace loaded."
        yield f"__SECTION_SUMMARY__\nI have successfully retrieved the core data package, but experienced an issue compiling the natural language stream. Here is the direct situation overview: {fallback_summary}\n"
        yield f"__SECTION_SIGNALS__\n• [RISK] Reasoning trace fallback initialized.\n"
        yield f"__SECTION_ACTIONS__\n• [Action] Check the status of your remote GPU node.\n"
        yield f"__SECTION_CRM_HYGIENE__\n⚠️ Database access functional. LLM Narrative node offline.\n"
        yield f"__SECTION_CONFIDENCE__\n{{\"score\": \"30%\", \"status\": \"Degraded\", \"sources\": [\"Excel Database\"]}}\n"
        yield "__SECTION_END__"


# ═══════════════════════════════════════════════════════════════
# LOCAL INTEGRATION TESTING RUNNER
# ═══════════════════════════════════════════════════════════════

async def test_agent_pipeline():
    """Verify Phase 1, 2, and 3 synchronously to validate the pipeline flow."""
    print("=== STARTING AGENT PIPELINE INTEGRATION TEST ===")
    
    test_query = "Who should I call at Infosys?"
    
    # Initialize DataEngine
    dataset_1 = r"C:\Users\VINAYAK\Downloads\SF_AccountingAgent_DummyData.xlsx"
    dataset_2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SF_AccountingAgent_DummyData.xlsx")
    p = dataset_1 if os.path.exists(dataset_1) else dataset_2
    print(f"Loading test database: {p}")
    engine = DataEngine(p)
    
    async with httpx.AsyncClient() as client:
        # Phase 1
        p1_res = await run_phase1_planner(test_query, client)
        print(f"\n[PHASE 1 RESULT] JSON:\n{json.dumps(p1_res, indent=2)}")
        
        # Phase 2
        p2_res = run_phase2_retrieval(engine, p1_res)
        print(f"\n[PHASE 2 RESULT] Length: {len(p2_res)} chars. Sample:\n{p2_res[:800]}")
        
        # Phase 3
        p3_res = await run_phase3_reasoner(p2_res, client)
        print(f"\n[PHASE 3 RESULT] Structured Intelligence Package (SIP):\n{json.dumps(p3_res, indent=2)}")
        
        # Phase 4 Narrative sample
        print("\n[PHASE 4 PREVIEW] Streaming first 200 chars:")
        count = 0
        async for token in run_phase4_narrative_stream(p3_res, test_query, client):
            print(token, end="", flush=True)
            count += len(token)
            if count > 200:
                print("\n[Truncated Preview]")
                break
                
    print("\n=== AGENT PIPELINE TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_agent_pipeline())
