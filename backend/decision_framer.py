"""
DECISION FRAMER ENGINE (decision_framer.py)
Classifies natural language intent into strategic decision frames:
Churn Risk, Revenue Expansion, Deal Winback, Renewal Readiness, and Competitive Threats.
"""

# --- SECTION 1: Dependencies & Decision Frame Definitions ---
# Imports Pydantic models and configures keyword triggers, priority signals, and ignore signals.
import os
import json
import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

# --- SECTION 2: DecisionFramer Implementation ---
# Analyzes queries to match decision templates and priority signal hierarchies.
class DecisionFramer:
    """
    Classifies user intent into specific decision frames.
    
    Frames:
    - churn_risk: Is this account at risk of leaving?
    - expansion: Can we grow revenue in this account?
    - winback: Can we win back a lost deal?
    - sales_closure: How do we close a stalled deal?
    - health_assessment: What's the overall account health?
    - competitive_threat: Are we losing to competition?
    - renewal_readiness: Are we ready for renewal?
    """
    
    DECISION_FRAMES = {
        "churn_risk": {
            "keywords": ["risk", "churn", "losing", "retain", "engagement", "at risk"],
            "intent": "Assess probability of account loss",
            "priority_signals": ["engagement_trend", "support_tickets", "competitive_activity"],
            "ignore_signals": ["historical_contracts"]
        },
        "expansion": {
            "keywords": ["expand", "grow", "upsell", "cross-sell", "opportunity", "expansion"],
            "intent": "Identify revenue expansion opportunities",
            "priority_signals": ["usage_penetration", "unmet_needs", "budget_remaining"],
            "ignore_signals": ["historical_contracts"]
        },
        "winback": {
            "keywords": ["win back", "lost", "recover", "re-engage", "reactivate"],
            "intent": "Understand why lost and how to recover",
            "priority_signals": ["churn_reason", "competitive_winner", "historical_satisfaction"],
            "ignore_signals": ["current_usage"]
        },
        "sales_closure": {
            "keywords": ["close", "deal", "stuck", "stalled", "blocker", "won't move", "negociation"],
            "intent": "Identify deal blockers and closure path",
            "priority_signals": ["deal_velocity", "budget_availability", "competitive_threats"],
            "ignore_signals": ["historical_engagement"]
        },
        "health_assessment": {
            "keywords": ["health", "overall", "status", "assessment", "how doing", "summary"],
            "intent": "Get comprehensive account health snapshot",
            "priority_signals": ["engagement_trend", "support_tickets", "usage_trend"],
            "ignore_signals": []
        },
        "competitive_threat": {
            "keywords": ["competitive", "competitor", "threat", "losing to", "benchmark"],
            "intent": "Assess competitive positioning and risk",
            "priority_signals": ["competitive_activity", "feature_parity", "customer_satisfaction_vs_competitor"],
            "ignore_signals": []
        },
        "renewal_readiness": {
            "keywords": ["renewal", "renew", "ready", "prep", "renewal window"],
            "intent": "Assess readiness for upcoming renewal",
            "priority_signals": ["renewal_date", "health_score", "negotiation_risks"],
            "ignore_signals": []
        }
    }
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name

    def frame_decision(self, query: str, account_context: dict) -> dict:
        """
        Main entry: Determine the decision frame for this query.
        """
        # Try heuristic matching first (fast, 0 tokens)
        frame = self._heuristic_match(query)
        
        if frame and frame != "unknown":
            return {
                "frame": frame,
                "method": "heuristic",
                "signals": self.DECISION_FRAMES[frame]["priority_signals"],
                "ignore": self.DECISION_FRAMES[frame]["ignore_signals"],
                "reasoning": f"Matched keywords for {frame}"
            }
        
        # Fall back to LLM if heuristic fails
        return self._llm_frame(query, account_context)
    
    def _heuristic_match(self, query: str) -> str:
        """Quick keyword-based matching (0 tokens)."""
        query_lower = query.lower()
        
        for frame, config in self.DECISION_FRAMES.items():
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    return frame
        
        return "unknown"
    
    def _llm_frame(self, query: str, account_context: dict) -> dict:
        """LLM-based framing."""
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            # Fallback to health assessment if no API key
            return {
                "frame": "health_assessment",
                "method": "fallback",
                "signals": self.DECISION_FRAMES["health_assessment"]["priority_signals"],
                "ignore": [],
                "reasoning": "Gemini API key missing, default to health assessment"
            }

        frames_json = json.dumps({
            name: {
                "intent": config["intent"],
                "keywords": config["keywords"]
            }
            for name, config in self.DECISION_FRAMES.items()
        })
        
        system_prompt = "You are a sales decision classifier. Classify the user query into the best matching decision frame."
        user_prompt = f"""
User query: "{query}"
Account: {account_context.get('account_name', 'Unknown')}

What is the user trying to DECIDE?

Available decision frames:
{frames_json}

Pick the BEST MATCH or "health_assessment" if ambiguous.

Respond in raw JSON:
{{
  "frame": "churn_risk|expansion|winback|sales_closure|health_assessment|competitive_threat|renewal_readiness",
  "confidence": 0.0-1.0,
  "reasoning": "Why this frame matches the query"
}}
"""
        
        try:
            from reasoning_engine import call_gemini_api
            response_text = call_gemini_api(system_prompt, user_prompt, gemini_key, max_tokens=256, timeout=10)
            
            # Clean markdown code fences if present
            response_text = re.sub(r"^```(?:json)?\s*", "", response_text.strip())
            response_text = re.sub(r"\s*```$", "", response_text)
            
            try:
                result = json.loads(response_text)
            except Exception:
                from reasoning_engine import repair_json_string
                repaired = repair_json_string(response_text)
                result = json.loads(repaired)
                
            frame = result.get("frame", "health_assessment")
            if frame not in self.DECISION_FRAMES:
                frame = "health_assessment"
                
            return {
                "frame": frame,
                "method": "llm",
                "confidence": result.get("confidence", 0.7),
                "signals": self.DECISION_FRAMES[frame]["priority_signals"],
                "ignore": self.DECISION_FRAMES[frame]["ignore_signals"],
                "reasoning": result.get("reasoning", "")
            }
        except Exception as e:
            print(f"[DecisionFramer Warning] LLM framing failed: {e}. Falling back to default.")
            return {
                "frame": "health_assessment",
                "method": "fallback_error",
                "signals": self.DECISION_FRAMES["health_assessment"]["priority_signals"],
                "ignore": [],
                "reasoning": f"Error running LLM framer: {str(e)}"
            }
