"""
NARRATIVE BUILDER ENGINE (narrative_builder.py)
Transforms CRM intelligence signals into causality narratives, alternative hypothesis scenarios,
and disambiguation tests for strategic decision-making.
"""

# --- SECTION 1: Dependencies & Class Initialization ---
# Imports JSON, regex utilities, and typing structures for narrative generation.
import os
import json
import re
from typing import Optional, List, Dict, Any

# --- SECTION 2: Strategic Causality Narrative Builder ---
# Builds primary narrative chains, alternative hypotheses, and disambiguation test prompts.
class NarrativeBuilder:
    """
    Transforms CRM and intelligence signals into strategic causality narratives.
    
    Primary Narrative + Alternative Hypothesis + Disambiguation Test.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name

    def build_narrative(self, signals: dict, frame: str, account_data: dict) -> dict:
        """
        Build causality chains, primary narrative, alternative hypothesis, 
        and a test to tell them apart.
        """
        gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("OPENROUTER_API_KEY"))
        if not gemini_key:
            # Fallback if no API key is set
            return {
                "decision_frame": frame,
                "signals_analyzed": list(signals.keys()),
                "primary_narrative": {
                    "narrative": "Factual metrics displayed directly.",
                    "timeline": "N/A",
                    "expected_next": "Continue monitoring metrics.",
                    "confidence": 0.9
                },
                "alternative_narrative": {
                    "narrative": "N/A",
                    "likelihood": 0.0
                },
                "test_to_disambiguate": {
                    "description": "N/A"
                },
                "suggested_action": {
                    "immediate_action": "Review account dashboard and CRM logs.",
                    "goal": "Verify data consistency",
                    "who_should_execute": "Account Manager",
                    "timeline": "As needed",
                    "escalation_trigger": "None"
                },
                "confidence": 0.9
            }

        # Step 1: Generate causality chains
        causality = self._generate_causality_chains(signals, frame, account_data, gemini_key)
        
        # Step 2: Generate narratives and action plan
        narrative_data = self._generate_narratives(causality, signals, frame, account_data, gemini_key)
        
        return {
            "decision_frame": frame,
            "signals_analyzed": list(signals.keys()),
            "causality_chains": causality,
            **narrative_data
        }

    def _generate_causality_chains(self, signals: dict, frame: str, account_data: dict, gemini_key: str) -> dict:
        """Trace root causes for key metrics."""
        system_prompt = "You are a sales operations analyst. Connect observed metrics/signals to their underlying business causes."
        user_prompt = f"""
Decision frame: {frame}
Account: {account_context_name(account_data)}

Signals observed:
{json.dumps(signals, indent=2)}

Identify the potential root causes for these signals. Be specific, logical, and trace dependencies.

Respond in raw JSON:
{{
  "signal_causality": [
    {{
      "signal": "Name of the signal (e.g. engagement_trend)",
      "cause": "Underlying root cause (e.g. buyer role transition)",
      "evidence": "Observed evidence supporting this cause",
      "likelihood": 0.0-1.0
    }}
  ]
}}
"""
        try:
            from reasoning_engine import call_gemini_api
            response_text = call_gemini_api(system_prompt, user_prompt, gemini_key, max_tokens=1024, timeout=12)
            try:
                return json.loads(response_text)
            except Exception:
                from reasoning_engine import repair_json_string
                repaired = repair_json_string(response_text)
                return json.loads(repaired)
        except Exception as e:
            print(f"[NarrativeBuilder Warning] Causality generation failed: {e}")
            return {"signal_causality": []}

    def _generate_narratives(self, causality: dict, signals: dict, frame: str, account_data: dict, gemini_key: str) -> dict:
        """Create primary and alternative narratives and a disambiguation test."""
        system_prompt = "You are a strategic sales consultant. Formulate a primary theory and a testable alternative theory explaining customer behavior."
        user_prompt = f"""
Decision frame: {frame}
Account: {account_context_name(account_data)}
Causality data: {json.dumps(causality)}

Based on this context:
1. Formulate a PRIMARY narrative (most likely explanation).
2. Formulate an ALTERNATIVE narrative (alternative risk or opportunity hypothesis).
3. Design a test (e.g., specific question to ask, contact to reach out to) to tell which theory is correct.
4. Recommend the immediate next action.

Respond in raw JSON:
{{
  "primary_narrative": {{
    "narrative": "Detailed primary theory",
    "timeline": "When this risk/opportunity started and how it develops",
    "expected_next": "What will happen next if untreated"
  }},
  "alternative_narrative": {{
    "narrative": "Detailed alternative hypothesis",
    "likelihood": 0.0-1.0,
    "key_differentiator": "What indicator distinguishes this from the primary narrative"
  }},
  "test_to_disambiguate": {{
    "test_name": "Name of the validation step",
    "description": "Clear step to run",
    "who_to_contact": "Role/name of target contact",
    "what_to_ask": "Specific validation question",
    "how_to_interpret": "How to interpret the outcome"
  }},
  "suggested_action": {{
    "immediate_action": "Specific task to execute",
    "goal": "Outcome of this action",
    "who_should_execute": "Role of the owner",
    "timeline": "Target timeline",
    "escalation_trigger": "Conditions to escalate to senior leaders"
  }},
  "confidence": 0.0-1.0
}}
"""
        try:
            from reasoning_engine import call_gemini_api
            response_text = call_gemini_api(system_prompt, user_prompt, gemini_key, max_tokens=1536, timeout=15)
            try:
                return json.loads(response_text)
            except Exception:
                from reasoning_engine import repair_json_string
                repaired = repair_json_string(response_text)
                return json.loads(repaired)
        except Exception as e:
            print(f"[NarrativeBuilder Warning] Narrative synthesis failed: {e}")
            return {
                "primary_narrative": {"narrative": "Factual database review requested."},
                "alternative_narrative": {"narrative": "None."},
                "test_to_disambiguate": {"description": "None."},
                "suggested_action": {
                    "immediate_action": "Review account contacts.",
                    "goal": "Data verification",
                    "who_should_execute": "Account Manager",
                    "timeline": "Routine",
                    "escalation_trigger": "None"
                },
                "confidence": 0.5
            }

def account_context_name(account_data: dict) -> str:
    return account_data.get("account_name") or account_data.get("name") or "Account"
