"""
Hybrid Semantic-Symbolic Intent Classifier.
Uses local embeddings for deterministic fast-path, falling back to a local LLM Matrix Router.
"""

import os
import re
import json
import numpy as np
from enum import Enum
from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, ValidationError

# Defensively import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

_GLOBAL_EMBEDDING_MODEL = None
_GLOBAL_SEED_EMBEDDINGS = None

class IntentEnum(str, Enum):
    RISK_ASSESSMENT = "risk_assessment"
    OPPORTUNITY_EXPANSION = "opportunity_expansion"
    COMPETITIVE_INTELLIGENCE = "competitive_intelligence"
    RELATIONSHIP_ANALYSIS = "relationship_analysis"
    ACTION_RECOMMENDATION = "action_recommendation"
    PIPELINE_SUMMARY = "pipeline_summary"
    DRAFT_EMAIL = "draft_email"
    MEETING_AGENDA = "meeting_agenda"
    SHOW_STAKEHOLDERS = "show_stakeholders"
    REVIEW_RISKS = "review_risks"
    CALCULATION_EXPLANATION = "calculation_explanation"

class ExtractedEntities(BaseModel):
    account: Optional[str] = None
    stage: Optional[str] = None
    metric: Optional[str] = None
    timeframe: Optional[str] = None
    competitor: Optional[str] = None

class IntentClassificationOutput(BaseModel):
    primary_intent: IntentEnum
    confidence_primary: float
    extracted_entities: ExtractedEntities
    urgency: str = "medium"
    scope: str = "ENTITY"  # "ENTITY", "PORTFOLIO", "MIXED"
    context_summary: str = ""
    
    # New Skills Architecture fields
    intent: str
    complexity: str       # "FACTUAL", "OPERATIONAL", "STRATEGIC", "EXECUTIVE"
    target_entities: List[str] = []

class RouterOutput(BaseModel):
    intent: Literal["ACT_REVIEW", "RISK_TRIAGE", "DEAL_VELOCITY", "DRAFT_EMAIL", "MEETING_AGENDA", "SHOW_STAKEHOLDERS", "REVIEW_RISKS"]
    complexity: Literal["TACTICAL", "STRATEGIC", "EXECUTIVE"]
    target_entity: Optional[str] = None
    focus_area: Optional[str] = None

# Seed queries for deterministic embedding lookup
SEED_QUERIES = [
    # DRAFT_EMAIL
    {"query": "draft an email to", "intent": "DRAFT_EMAIL", "complexity": "TACTICAL", "primary_intent": IntentEnum.DRAFT_EMAIL},
    {"query": "write an email", "intent": "DRAFT_EMAIL", "complexity": "TACTICAL", "primary_intent": IntentEnum.DRAFT_EMAIL},
    
    # MEETING_AGENDA
    {"query": "create a meeting agenda", "intent": "MEETING_AGENDA", "complexity": "TACTICAL", "primary_intent": IntentEnum.MEETING_AGENDA},
    {"query": "prepare an agenda", "intent": "MEETING_AGENDA", "complexity": "TACTICAL", "primary_intent": IntentEnum.MEETING_AGENDA},
    
    # ACT_REVIEW
    {"query": "strategic account plan for Wipro", "intent": "ACT_REVIEW", "complexity": "STRATEGIC", "primary_intent": IntentEnum.ACTION_RECOMMENDATION},
    {"query": "playbook for Wipro", "intent": "ACT_REVIEW", "complexity": "STRATEGIC", "primary_intent": IntentEnum.ACTION_RECOMMENDATION},
    {"query": "TCS strategy mitigation plan", "intent": "ACT_REVIEW", "complexity": "STRATEGIC", "primary_intent": IntentEnum.ACTION_RECOMMENDATION},
    {"query": "objections for Wipro alignment", "intent": "ACT_REVIEW", "complexity": "STRATEGIC", "primary_intent": IntentEnum.ACTION_RECOMMENDATION},
    {"query": "Show Wipro account", "intent": "ACT_REVIEW", "complexity": "STRATEGIC", "primary_intent": IntentEnum.ACTION_RECOMMENDATION},
    {"query": "Give me a high-level summary of the Wipro pipeline for my VP", "intent": "ACT_REVIEW", "complexity": "EXECUTIVE", "primary_intent": IntentEnum.ACTION_RECOMMENDATION},
    {"query": "Wipro executive briefing", "intent": "ACT_REVIEW", "complexity": "EXECUTIVE", "primary_intent": IntentEnum.ACTION_RECOMMENDATION},
    {"query": "board review summary for TCS", "intent": "ACT_REVIEW", "complexity": "EXECUTIVE", "primary_intent": IntentEnum.ACTION_RECOMMENDATION},
    
    # RISK_TRIAGE
    {"query": "stale activity notes for Wipro", "intent": "RISK_TRIAGE", "complexity": "TACTICAL", "primary_intent": IntentEnum.RISK_ASSESSMENT},
    {"query": "Write an email to the Wipro CIO about their open security ticket", "intent": "RISK_TRIAGE", "complexity": "TACTICAL", "primary_intent": IntentEnum.RISK_ASSESSMENT},
    {"query": "critical open support cases for TCS", "intent": "RISK_TRIAGE", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.RISK_ASSESSMENT},
    {"query": "high risk accounts in my portfolio", "intent": "RISK_TRIAGE", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.RISK_ASSESSMENT},
    {"query": "TCS open support tickets and blockers", "intent": "RISK_TRIAGE", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.RISK_ASSESSMENT},
    {"query": "value at risk for Wipro account", "intent": "RISK_TRIAGE", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.RISK_ASSESSMENT},
    
    # DEAL_VELOCITY
    {"query": "Top opportunities stalling in TCS", "intent": "DEAL_VELOCITY", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.PIPELINE_SUMMARY},
    {"query": "opportunities list for Wipro", "intent": "DEAL_VELOCITY", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.PIPELINE_SUMMARY},
    {"query": "active pipeline for this month", "intent": "DEAL_VELOCITY", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.PIPELINE_SUMMARY},
    {"query": "weighted forecast review", "intent": "DEAL_VELOCITY", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.PIPELINE_SUMMARY},
    {"query": "TCS largest deals in negotiation", "intent": "DEAL_VELOCITY", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.PIPELINE_SUMMARY},
    {"query": "Wipro close rate and deal velocity", "intent": "DEAL_VELOCITY", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.PIPELINE_SUMMARY},
    {"query": "forecast summary for the quarter", "intent": "DEAL_VELOCITY", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.PIPELINE_SUMMARY},
    
    # SHOW_STAKEHOLDERS
    {"query": "show stakeholders", "intent": "SHOW_STAKEHOLDERS", "complexity": "TACTICAL", "primary_intent": IntentEnum.SHOW_STAKEHOLDERS},
    {"query": "who are the key contacts", "intent": "SHOW_STAKEHOLDERS", "complexity": "TACTICAL", "primary_intent": IntentEnum.SHOW_STAKEHOLDERS},
    {"query": "show me the decision makers", "intent": "SHOW_STAKEHOLDERS", "complexity": "TACTICAL", "primary_intent": IntentEnum.SHOW_STAKEHOLDERS},
    
    # REVIEW_RISKS
    {"query": "review risks", "intent": "REVIEW_RISKS", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.REVIEW_RISKS},
    {"query": "what are the account risks", "intent": "REVIEW_RISKS", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.REVIEW_RISKS},
    {"query": "show me deal risks", "intent": "REVIEW_RISKS", "complexity": "OPERATIONAL", "primary_intent": IntentEnum.REVIEW_RISKS},
]

class IntentClassifier:
    """Hybrid intent classifier combining embeddings and LLM routing."""
    
    def __init__(self, known_accounts: Optional[List[str]] = None, known_opportunities: Optional[Dict[str, str]] = None, is_local: bool = True, **kwargs):
        self.known_accounts = known_accounts or []
        self.known_opportunities = known_opportunities or {}
        self.is_local = is_local
        self.embedding_model = None
        self.seed_embeddings = None
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _init_embeddings(self):
        """Lazy load sentence transformers and calculate seed embeddings."""
        global _GLOBAL_EMBEDDING_MODEL, _GLOBAL_SEED_EMBEDDINGS
        if _GLOBAL_EMBEDDING_MODEL is None and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                print("[Router] Initializing SentenceTransformer model...")
                _GLOBAL_EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
                queries = [q["query"] for q in SEED_QUERIES]
                _GLOBAL_SEED_EMBEDDINGS = _GLOBAL_EMBEDDING_MODEL.encode(queries)
                print(f"[Router] Successfully cached {len(queries)} seed embeddings.")
            except Exception as e:
                print(f"Warning: Failed to load SentenceTransformer for fast router: {e}")
        self.embedding_model = _GLOBAL_EMBEDDING_MODEL
        self.seed_embeddings = _GLOBAL_SEED_EMBEDDINGS

    def classify(self, query: str, history: Optional[List[Dict[str, str]]] = None, user_role: str = "Account Manager", active_account: Optional[str] = None) -> IntentClassificationOutput:
        """Classify query using Hybrid Semantic-Symbolic routing."""
        
        query_lower = query.lower()
        self._init_embeddings()
        
        # Default fallback values (derived from legacy rules)
        scope_val = self._detect_scope(query_lower)
        primary_intent_val = self._detect_intent(query_lower)
        confidence_val = self._calculate_confidence(query_lower, primary_intent_val)
        
        # Legacy to Skills Mapper for fallback defaults
        complexity_val = "STRATEGIC"
        intent_val = "ACT_REVIEW"
        if primary_intent_val == IntentEnum.RELATIONSHIP_ANALYSIS:
            intent_val = "CONTACT_LOOKUP"
            complexity_val = "FACTUAL"
        elif primary_intent_val == IntentEnum.PIPELINE_SUMMARY:
            intent_val = "OPPORTUNITY_RANKING"
            complexity_val = "OPERATIONAL"
        elif primary_intent_val == IntentEnum.RISK_ASSESSMENT:
            intent_val = "RISK_ANALYSIS"
            complexity_val = "OPERATIONAL"
        elif primary_intent_val == IntentEnum.ACTION_RECOMMENDATION:
            if "brief" in query_lower or "executive" in query_lower:
                intent_val = "EXECUTIVE_BRIEFING"
                complexity_val = "EXECUTIVE"
            else:
                intent_val = "ACCOUNT_PLAN"
                complexity_val = "STRATEGIC"
        
        # Check for Conversational Greetings and Chitchat first
        GREETING_PATTERN = r"\b(hello|hi|hey|what's up|howdy|anyone there|how are you|can you help|good morning|good afternoon|good evening|thanks|thank you|bye|goodbye)\b"
        OFF_TOPIC_SIGNALS = ["joke", "capital of", "who won", "weather", "news", "sport", "movie", "tell me about yourself", "what can you do"]
        CRM_DOMAIN_TERMS = ["opp", "opportunity", "opportunities", "forecast", "pipeline", "stalled", "contact", "decision maker", "action plan", "playbook", "blocker", "cases", "risk", "deal", "account", "revenue", "stakeholder", "ticket", "case", "close"]

        is_greeting = bool(re.search(GREETING_PATTERN, query_lower))
        is_off_topic = any(sig in query_lower for sig in OFF_TOPIC_SIGNALS)
        has_crm_context = any(t in query_lower for t in CRM_DOMAIN_TERMS)

        if (is_greeting or is_off_topic) and not has_crm_context:
            chitchat_intent = "GREETING" if is_greeting else "CHITCHAT"
            return IntentClassificationOutput(
                primary_intent=IntentEnum.ACTION_RECOMMENDATION,
                confidence_primary=1.0,
                extracted_entities=ExtractedEntities(),
                urgency="low",
                scope="MIXED",
                intent=chitchat_intent,
                complexity="CONVERSATIONAL",
                target_entities=[],
                context_summary=f"Conversational: {chitchat_intent}"
            )

        # Fast-path for Calculation Breakdown Queries
        CALC_PATTERNS = [
            r"\bhow (did you|was this|was it|were they|is it) calculate(d)?\b",
            r"\bbreakdown of (how|the|how you|deals|total|revenue|stalled|\$\d+)\b",
            r"\bexplain (the|how|this|my|that|\$\d+) (calculation|figure|sum|number|total|math)\b",
            r"\bmath breakdown\b",
            r"\bwhere did (the|\$\d+) come from\b"
        ]
        if any(re.search(p, query_lower) for p in CALC_PATTERNS):
            return IntentClassificationOutput(
                primary_intent=IntentEnum.CALCULATION_EXPLANATION,
                confidence_primary=0.95,
                extracted_entities=ExtractedEntities(account=active_account),
                urgency="medium",
                scope="ENTITY" if active_account else "PORTFOLIO",
                intent="CALCULATION_EXPLANATION",
                complexity="FACTUAL",
                target_entities=[active_account] if active_account else [],
                context_summary="Fast-path Calculation Breakdown Inspector"
            )

        # Entity extraction (using robust legacy rules)
        entities = self._extract_entities(query, primary_intent_val)
        urgency = self._detect_urgency(query_lower)
        
        # Extract target entities from database
        target_entities_val = []
        
        # Look for opportunity ID in query to resolve target account
        opp_id_match = re.search(r'\b(\d+_OPP\d+|OPP\d+)\b', query, re.IGNORECASE)
        if opp_id_match and getattr(self, 'known_opportunities', None):
            matched_opp_id = opp_id_match.group(1).lower()
            resolved_acc = self.known_opportunities.get(matched_opp_id)
            if resolved_acc:
                target_entities_val.append(resolved_acc)
                
        if not target_entities_val and self.known_accounts:
            for acc in self.known_accounts:
                pattern = r'\b' + re.escape(acc.lower()) + r'\b'
                if re.search(pattern, query_lower):
                    target_entities_val.append(acc)
        
        # Contiguous capitalized word fallback
        if not target_entities_val:
            noise = {'Top', 'Show', 'Give', 'Get', 'Review', 'Evaluate', 'Provide', 'Who', 'What', 'Where', 'When', 'Why', 'How', 'Which', 'Are', 'Is', 'They', 'Them', 'Our', 'Your', 'Please', 'Traced'}
            matches = re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b', query)
            for m in matches:
                m_words = m.split()
                filtered_words = [w for w in m_words if w not in noise]
                if filtered_words:
                    target_entities_val.append(" ".join(filtered_words))
        
        # Carrying over active account from history if no account is specified and query is not global
        if not target_entities_val:
            global_indicators = ["portfolio", "all accounts", "across accounts", "every account", "entire portfolio", "global", "high risk accounts", "top opportunities"]
            is_global = any(indicator in query_lower for indicator in global_indicators)
            
            if not is_global and active_account:
                target_entities_val.append(active_account)
            elif not is_global and history:
                for msg in reversed(history):
                    msg_text = msg.get("content", msg.get("text", "")).lower()
                    found_acc = None
                    if self.known_accounts:
                        for acc in self.known_accounts:
                            pattern = r'\b' + re.escape(acc.lower()) + r'\b'
                            if re.search(pattern, msg_text):
                                found_acc = acc
                                break
                    if found_acc:
                        target_entities_val.append(found_acc)
                        break
        
        if target_entities_val:
            entities.account = target_entities_val[0]

        # Conversational query detection bypass
        conversational_keywords = ["hello", "hi", "hii", "hey", "greetings", "what can you do for me", "help me", "who are you"]
        is_conversational = any(kw == query_lower or query_lower.startswith(kw + " ") for kw in conversational_keywords)
        if is_conversational:
            return IntentClassificationOutput(
                primary_intent=IntentEnum.ACTION_RECOMMENDATION,
                confidence_primary=1.0,
                extracted_entities=entities,
                urgency="low",
                scope="MIXED",
                intent="GREETING",
                complexity="CONVERSATIONAL",
                target_entities=[],
                context_summary="APEX Router: Conversational Bypass (GREETING)"
            )

        # Factual query detection bypass
        factual_keywords = ["who is", "who are", "what is", "where is", "how many", "list of", "show me contacts", "get contacts", "decision maker", "contact details"]
        is_factual = any(kw in query_lower for kw in factual_keywords)
        if is_factual:
            return IntentClassificationOutput(
                primary_intent=primary_intent_val,
                confidence_primary=1.0,
                extracted_entities=entities,
                urgency=urgency,
                scope=scope_val,
                intent=intent_val,
                complexity="FACTUAL",
                target_entities=target_entities_val,
                context_summary=f"APEX Router: Factual Bypass ({primary_intent_val})"
            )

        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Deterministic Fast-Lane (Embeddings Cosine Similarity)
        # ═══════════════════════════════════════════════════════════════
        fast_path_matched = False
        if self.embedding_model is not None and self.seed_embeddings is not None:
            try:
                query_emb = self.embedding_model.encode([query])
                # Calculate cosine similarities
                norm_seeds = np.linalg.norm(self.seed_embeddings, axis=1)
                norm_query = np.linalg.norm(query_emb)
                
                if norm_query > 0:
                    sims = np.dot(self.seed_embeddings, query_emb[0]) / (norm_seeds * norm_query)
                    best_idx = np.argmax(sims)
                    best_score = sims[best_idx]
                    
                    if best_score >= 0.85:
                        matched = SEED_QUERIES[best_idx]
                        intent_val = matched["intent"]
                        complexity_val = matched["complexity"]
                        primary_intent_val = matched["primary_intent"]
                        confidence_val = float(best_score)
                        fast_path_matched = True
                        print(f"[Router Fast-Path] Similarity: {best_score:.4f} -> Routed to {intent_val} / {complexity_val}")
            except Exception as e:
                print(f"[Router Fast-Path] Fast-path embedding routing failed: {e}")

        # ═══════════════════════════════════════════════════════════════
        # STEP 2 & 3: LLM Matrix Router & Pydantic Guardrail
        # ═══════════════════════════════════════════════════════════════
        if not fast_path_matched:
            print("[Router] Fast-lane missed (similarity < 0.85). Invoking Turn 1 LLM Router...")
            
            system_rules = """You are the APEX Matrix Router. Your sole function is to translate raw sales queries into symbolic system variables.
You do not answer the user. You only output a flat JSON object matching the exact schema provided.

[INTENT_MAP]
ACT_REVIEW = Account planning and strategy
RISK_TRIAGE = Dealing with support cases and blockers
DEAL_VELOCITY = Closing active opportunities

[COMPLEXITY_MAP]
TACTICAL = Daily tasks, emails, immediate next steps
STRATEGIC = Multi-day playbooks, risk analysis
EXECUTIVE = Macro revenue summaries, VP-level outputs"""

            few_shots = """Input: "Write an email to the Wipro CIO about their open security ticket."
Output: {"intent": "RISK_TRIAGE", "complexity": "TACTICAL", "target_entity": "Wipro", "focus_area": "security ticket"}

Input: "Give me a high-level summary of the Wipro pipeline for my VP."
Output: {"intent": "ACT_REVIEW", "complexity": "EXECUTIVE", "target_entity": "Wipro", "focus_area": "pipeline"}"""

            user_prompt = f"Analyze and classify this input:\nInput: \"{query}\""
            
            try:
                raw_llm_output = self._call_llm(
                    system_prompt=f"{system_rules}\n\n{few_shots}",
                    user_prompt=user_prompt
                )
                
                parsed_json = self._clean_and_parse_json(raw_llm_output)
                
                # Pydantic Guardrail
                validated = RouterOutput(**parsed_json)
                
                intent_val = validated.intent
                complexity_val = validated.complexity
                confidence_val = 0.90
                
                # Map to legacy / skills enums
                if intent_val == "DEAL_VELOCITY":
                    primary_intent_val = IntentEnum.PIPELINE_SUMMARY
                    intent_val = "OPPORTUNITY_RANKING"
                    complexity_val = "OPERATIONAL"
                elif intent_val == "RISK_TRIAGE":
                    primary_intent_val = IntentEnum.RISK_ASSESSMENT
                    intent_val = "RISK_ANALYSIS"
                    complexity_val = "OPERATIONAL"
                elif intent_val == "SHOW_STAKEHOLDERS":
                    primary_intent_val = IntentEnum.SHOW_STAKEHOLDERS
                    intent_val = "CONTACT_LOOKUP"
                    complexity_val = "FACTUAL"
                elif intent_val == "REVIEW_RISKS":
                    primary_intent_val = IntentEnum.REVIEW_RISKS
                    intent_val = "RISK_ANALYSIS"
                    complexity_val = "OPERATIONAL"
                elif intent_val == "DRAFT_EMAIL":
                    primary_intent_val = IntentEnum.DRAFT_EMAIL
                elif intent_val == "MEETING_AGENDA":
                    primary_intent_val = IntentEnum.MEETING_AGENDA
                else:
                    primary_intent_val = IntentEnum.ACTION_RECOMMENDATION
                    if complexity_val == "EXECUTIVE":
                        intent_val = "EXECUTIVE_BRIEFING"
                    else:
                        intent_val = "ACCOUNT_PLAN"
                        complexity_val = "STRATEGIC"
                    
                print(f"[Router LLM] Output verified: {intent_val} / {complexity_val}")
                
            except (ValidationError, Exception) as err:
                # Intercept error and fallback gracefully to default values without raising exceptions
                print(f"[Router Guardrail] Validation or LLM error: {err}. Safe fallback applied.")
                primary_intent_val = self._detect_intent(query_lower)
                confidence_val = 0.50
                if primary_intent_val == IntentEnum.RELATIONSHIP_ANALYSIS:
                    intent_val = "CONTACT_LOOKUP"
                    complexity_val = "FACTUAL"
                elif primary_intent_val == IntentEnum.PIPELINE_SUMMARY:
                    intent_val = "OPPORTUNITY_RANKING"
                    complexity_val = "OPERATIONAL"
                elif primary_intent_val == IntentEnum.RISK_ASSESSMENT:
                    intent_val = "RISK_ANALYSIS"
                    complexity_val = "OPERATIONAL"
                else:
                    if "brief" in query_lower or "executive" in query_lower:
                        intent_val = "EXECUTIVE_BRIEFING"
                        complexity_val = "EXECUTIVE"
                    else:
                        intent_val = "ACCOUNT_PLAN"
                        complexity_val = "STRATEGIC"
            
        return IntentClassificationOutput(
            primary_intent=primary_intent_val,
            confidence_primary=confidence_val,
            extracted_entities=entities,
            urgency=urgency,
            scope=scope_val,
            intent=intent_val,
            complexity=complexity_val,
            target_entities=target_entities_val,
            context_summary=f"APEX Router: {intent_val} ({complexity_val})"
        )

    def _call_llm(self, system_prompt: str, user_prompt: str, timeout: int = 60) -> str:
        # Check for Gemini API integration (Primary Cloud Route)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                print("[Cloud Route] Routing Layer 1 Intent Classification call to Google Gemini API...")
                # Groq/Gemini call helper is in reasoning_engine
                from reasoning_engine import call_gemini_api
                # Limit output response size using max_tokens=1024 and enforce a 10s connection limit
                return call_gemini_api(system_prompt, user_prompt, gemini_key, max_tokens=1024, timeout=10)
            except Exception as e:
                print(f"[Cloud Route Error] Gemini API intent routing failed: {e}. Falling back...")

        # --- LOCAL LLM EXECUTION CODE (COMMENTED OUT FOR PERFORMANCE) ---
        # model = os.getenv("MODEL_NAME", "llama3.2:latest")
        # url = os.getenv("LLM_URL", "")
        # import httpx
        # payload = {
        #     "model": model,
        #     "prompt": f"System: {system_prompt}\n\nUser Prompt: {user_prompt}\nOutput ONLY valid raw JSON.",
        #     "stream": False,
        #     "options": {
        #         "temperature": 0.0,
        #         "num_predict": 128
        #     }
        # }
        # httpx_timeout = httpx.Timeout(timeout=float(timeout), connect=5.0)
        # print(f"  [LLM CONNECT] Attempting connection to: {url} (model: {model})")
        # with httpx.Client(timeout=httpx_timeout) as client:
        #     print(f"  [LLM REQUEST] Sending query payload to: {url}...")
        #     response = client.post(url, json=payload)
        #     print(f"  [LLM RESPONSE] Received status {response.status_code} from: {url}")
        #     if response.status_code == 200:
        #         return response.json().get("response", "").strip()
        #     else:
        #         raise Exception(f"HTTP error {response.status_code}")
        
        # Raise timeout error if no cloud api credentials found to activate local fallback logic
        raise TimeoutError("Local model execution bypassed. Please configure Gemini credentials in your environment.")


    def _clean_and_parse_json(self, text: str) -> dict:
        text = text.strip()
        # Remove markdown wrapper blocks
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        
        # Robustly find the outermost JSON structure
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # If standard parse fails, try basic regex cleanup for common LLM syntax anomalies
                # (e.g. unescaped newlines, trailing commas)
                cleaned = re.sub(r',\s*([\]}])', r'\1', json_str)
                return json.loads(cleaned)
        raise ValueError(f"No valid JSON structure found in LLM output: {text[:200]}")


    def _has_word(self, query: str, words: list) -> bool:
        for w in words:
            if re.search(r'\b' + re.escape(w) + r'\b', query, re.IGNORECASE):
                return True
        return False

    def _detect_intent(self, query: str) -> IntentEnum:
        if self._has_word(query, ['competitor', 'losing', 'win/loss', 'threat', 'competitor x']):
            return IntentEnum.COMPETITIVE_INTELLIGENCE
        if self._has_word(query, ['risk', 'churn', 'declining', 'health', 'at risk', 'warning', 'stalling', 'stalled', 'stuck']):
            return IntentEnum.RISK_ASSESSMENT
        if self._has_word(query, ['contact', 'stakeholder', 'decision maker', 'influencer', 'who are']):
            return IntentEnum.RELATIONSHIP_ANALYSIS
        if self._has_word(query, ['pipeline', 'velocity', 'forecast', 'closing in', 'deal velocity', 'weighted forecast']):
            return IntentEnum.PIPELINE_SUMMARY
        if self._has_word(query, ['expand', 'grow', 'upsell', 'cross-sell', 'opportunity', 'opportunities']):
            if not self._has_word(query, ['stalling', 'stalled', 'stuck']):
                return IntentEnum.OPPORTUNITY_EXPANSION
        return IntentEnum.ACTION_RECOMMENDATION

    def _calculate_confidence(self, query: str, intent: IntentEnum) -> float:
        keyword_map = {
            IntentEnum.COMPETITIVE_INTELLIGENCE: ['competitor', 'losing', 'threat', 'competitor x'],
            IntentEnum.RISK_ASSESSMENT: ['risk', 'churn', 'declining', 'health', 'at risk', 'warning', 'stalling', 'stalled', 'stuck'],
            IntentEnum.RELATIONSHIP_ANALYSIS: ['contact', 'stakeholder', 'decision maker', 'influencer', 'who are'],
            IntentEnum.PIPELINE_SUMMARY: ['pipeline', 'velocity', 'forecast', 'closing', 'deal velocity', 'weighted forecast'],
            IntentEnum.OPPORTUNITY_EXPANSION: ['expand', 'grow', 'upsell', 'cross-sell', 'opportunity', 'opportunities'],
            IntentEnum.ACTION_RECOMMENDATION: ['plan', 'strategy', 'recommend', 'action', 'playbook', 'should']
        }
        
        total_matches = sum(1 for kws in keyword_map.values() for kw in kws if re.search(r'\b' + re.escape(kw) + r'\b', query, re.IGNORECASE))
        if total_matches == 0:
            return 0.2
            
        keywords = keyword_map.get(intent, [])
        matches = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', query, re.IGNORECASE))
        confidence = min(0.6 + (matches * 0.1), 0.95)
        return confidence

    def _extract_entities(self, query: str, intent: IntentEnum) -> ExtractedEntities:
        entities = ExtractedEntities()
        
        stage_patterns = {
            r'\b(negotiation|negotiate|review)\b': 'negotiation/review',
            r'\b(proposal|quote|proposal/price)\b': 'proposal/price quote',
            r'\b(needs|needs analysis)\b': 'needs analysis',
            r'\b(qualification|qualify)\b': 'qualification',
            r'\b(closed won|won)\b': 'closed won',
            r'\b(closed lost|lost)\b': 'closed lost',
            r'\b(value proposition)\b': 'value proposition'
        }
        for pattern, stage_value in stage_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                entities.stage = stage_value
                break
        
        timeframe_patterns = {
            r'(\d+)\s*days?': lambda m: f"{m.group(1)} days",
            r'next\s*(week|month|quarter)': lambda m: f"next {m.group(1)}",
            r'closing in\s*(\d+)\s*days?': lambda m: f"closing in {m.group(1)} days",
            r'end of\s*(month|quarter|year)': lambda m: f"end of {m.group(1)}"
        }
        for pattern, formatter in timeframe_patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                entities.timeframe = formatter(match)
                break
        
        words = query.split()
        capitalized = [w.rstrip('?.,;:') for w in words if w and w[0].isupper() and len(w) > 2]
        noise = ['Top', 'Show', 'Give', 'Get', 'Review', 'Evaluate', 'Provide', 'Who', 'What', 'Where', 'When', 'Why', 'How', 'Which', 'Are', 'Is', 'They', 'Them', 'Our', 'Your']
        capitalized = [w for w in capitalized if w not in noise]
        if capitalized:
            entities.account = capitalized[0]
        
        if 'competitor' in query:
            match = re.search(r'competitor\s+(\w+)', query, re.IGNORECASE)
            if match:
                entities.competitor = match.group(1)
        
        metric_keywords = ['top', 'bottom', 'highest', 'lowest', 'forecast', 'velocity', 'arr', 'health']
        if any(kw in query for kw in metric_keywords):
            match = re.search(r'top\s+(\d+)', query, re.IGNORECASE)
            if match:
                entities.metric = f"top {match.group(1)}"
            else:
                entities.metric = 'summary'
        
        return entities

    def _detect_urgency(self, query: str) -> str:
        if any(word in query for word in ['immediately', 'urgent', 'asap', 'critical', 'now', 'today']):
            return 'high'
        if any(word in query for word in ['soon', 'next week', 'this week', 'before']):
            return 'high'
        if any(word in query for word in ['next month', 'this quarter', 'eventually']):
            return 'medium'
        return 'medium'

    def _detect_scope(self, query: str) -> str:
        if any(word in query for word in ['accounts', 'all', 'portfolio', 'every', 'each']):
            return 'portfolio'
        if any(word in query for word in ['pipeline', 'forecast', 'velocity']):
            return 'pipeline'
        return 'entity'