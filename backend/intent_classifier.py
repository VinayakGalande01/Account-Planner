"""
Rule-based intent classifier - no LLM needed.
Fast, reliable, deterministic.
"""

# from models import IntentClassificationOutput, IntentEnum, ExtractedEntities
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from typing import Optional
import re

class IntentEnum(str, Enum):
    RISK_ASSESSMENT = "risk_assessment"
    OPPORTUNITY_EXPANSION = "opportunity_expansion"
    COMPETITIVE_INTELLIGENCE = "competitive_intelligence"
    RELATIONSHIP_ANALYSIS = "relationship_analysis"
    ACTION_RECOMMENDATION = "action_recommendation"
    PIPELINE_SUMMARY = "pipeline_summary"


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
    scope: str = "entity"
    context_summary: str = ""

class IntentClassifier:
    """Rule-based intent classifier using keyword matching."""
    
    def classify(self, query: str, user_role: str = "Account Manager") -> IntentClassificationOutput:
        """Classify intent without LLM - pure rules."""
        
        query_lower = query.lower()
        
        # Intent detection (order matters - specific first)
        intent = self._detect_intent(query_lower)
        confidence = self._calculate_confidence(query_lower, intent)
        
        # Entity extraction
        entities = self._extract_entities(query, intent)
        
        # Urgency
        urgency = self._detect_urgency(query_lower)
        
        # Scope
        scope = self._detect_scope(query_lower)
        
        return IntentClassificationOutput(
            primary_intent=intent,
            confidence_primary=confidence,
            extracted_entities=entities,
            urgency=urgency,
            scope=scope,
            context_summary=f"Rule-based classification: {intent.value}"
        )
    
    def _has_word(self, query: str, words: list) -> bool:
        """Helper to match whole words/phrases with word boundaries."""
        for w in words:
            if re.search(r'\b' + re.escape(w) + r'\b', query, re.IGNORECASE):
                return True
        return False

    def _detect_intent(self, query: str) -> IntentEnum:
        """Detect intent from keywords."""
        
        # COMPETITIVE_INTELLIGENCE
        if self._has_word(query, ['competitor', 'losing', 'win/loss', 'threat', 'competitor x']):
            return IntentEnum.COMPETITIVE_INTELLIGENCE
        
        # RISK_ASSESSMENT
        if self._has_word(query, ['risk', 'churn', 'declining', 'health', 'at risk', 'warning', 'stalling', 'stalled', 'stuck']):
            return IntentEnum.RISK_ASSESSMENT
        
        # RELATIONSHIP_ANALYSIS
        if self._has_word(query, ['contact', 'stakeholder', 'decision maker', 'influencer', 'who are']):
            return IntentEnum.RELATIONSHIP_ANALYSIS
        
        # PIPELINE_SUMMARY
        if self._has_word(query, ['pipeline', 'velocity', 'forecast', 'closing in', 'deal velocity', 'weighted forecast']):
            return IntentEnum.PIPELINE_SUMMARY
        
        # OPPORTUNITY_EXPANSION
        if self._has_word(query, ['expand', 'grow', 'upsell', 'cross-sell', 'opportunity', 'opportunities']):
            # But check if it's about stalled/at-risk opportunities (then RISK)
            if not self._has_word(query, ['stalling', 'stalled', 'stuck']):
                return IntentEnum.OPPORTUNITY_EXPANSION
        
        # ACTION_RECOMMENDATION (default)
        if self._has_word(query, ['plan', 'strategy', 'recommend', 'action', 'playbook', 'should']):
            return IntentEnum.ACTION_RECOMMENDATION
        
        # Default
        return IntentEnum.ACTION_RECOMMENDATION
    
    def _calculate_confidence(self, query: str, intent: IntentEnum) -> float:
        """Calculate confidence based on keyword match strength."""
        
        keyword_map = {
            IntentEnum.COMPETITIVE_INTELLIGENCE: ['competitor', 'losing', 'threat', 'competitor x'],
            IntentEnum.RISK_ASSESSMENT: ['risk', 'churn', 'declining', 'health', 'at risk', 'warning', 'stalling', 'stalled', 'stuck'],
            IntentEnum.RELATIONSHIP_ANALYSIS: ['contact', 'stakeholder', 'decision maker', 'influencer', 'who are'],
            IntentEnum.PIPELINE_SUMMARY: ['pipeline', 'velocity', 'forecast', 'closing', 'deal velocity', 'weighted forecast'],
            IntentEnum.OPPORTUNITY_EXPANSION: ['expand', 'grow', 'upsell', 'cross-sell', 'opportunity', 'opportunities'],
            IntentEnum.ACTION_RECOMMENDATION: ['plan', 'strategy', 'recommend', 'action', 'playbook', 'should']
        }
        
        # Check total matches across ALL intents first to see if it's a completely unrelated query
        total_matches = sum(1 for kws in keyword_map.values() for kw in kws if re.search(r'\b' + re.escape(kw) + r'\b', query, re.IGNORECASE))
        if total_matches == 0:
            return 0.2  # Very low confidence for completely vague/unrelated queries
            
        keywords = keyword_map.get(intent, [])
        matches = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', query, re.IGNORECASE))
        
        # Confidence = 0.6 + (matches * 0.1), capped at 0.95
        confidence = min(0.6 + (matches * 0.1), 0.95)
        
        return confidence
    
    def _extract_entities(self, query: str, intent: IntentEnum) -> ExtractedEntities:
        """Extract entities using regex and keyword matching."""
        
        entities = ExtractedEntities()
        
        # STAGE extraction
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
        
        # TIMEFRAME extraction
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
        
        # ACCOUNT extraction (proper nouns, capitalized words)
        words = query.split()
        capitalized = [w.rstrip('?.,;:') for w in words if w and w[0].isupper() and len(w) > 2]
        
        # Filter noise
        noise = ['Top', 'Show', 'Give', 'Get', 'Review', 'Evaluate', 'Provide', 'Who', 'What', 'Where', 'When', 'Why', 'How', 'Which', 'Are', 'Is', 'They', 'Them', 'Our', 'Your']
        capitalized = [w for w in capitalized if w not in noise]
        
        if capitalized:
            entities.account = capitalized[0]
        
        # COMPETITOR extraction
        if 'competitor' in query:
            match = re.search(r'competitor\s+(\w+)', query, re.IGNORECASE)
            if match:
                entities.competitor = match.group(1)
        
        # METRIC extraction
        metric_keywords = ['top', 'bottom', 'highest', 'lowest', 'forecast', 'velocity', 'arr', 'health']
        if any(kw in query for kw in metric_keywords):
            match = re.search(r'top\s+(\d+)', query, re.IGNORECASE)
            if match:
                entities.metric = f"top {match.group(1)}"
            else:
                entities.metric = 'summary'
        
        return entities
    
    def _detect_urgency(self, query: str) -> str:
        """Detect urgency level."""
        
        if any(word in query for word in ['immediately', 'urgent', 'asap', 'critical', 'now', 'today']):
            return 'high'
        
        if any(word in query for word in ['soon', 'next week', 'this week', 'before']):
            return 'high'
        
        if any(word in query for word in ['next month', 'this quarter', 'eventually']):
            return 'medium'
        
        return 'medium'
    
    def _detect_scope(self, query: str) -> str:
        """Detect scope: entity, portfolio, or pipeline."""
        
        # Portfolio scope
        if any(word in query for word in ['accounts', 'all', 'portfolio', 'every', 'each']):
            return 'portfolio'
        
        # Pipeline scope
        if any(word in query for word in ['pipeline', 'forecast', 'velocity']):
            return 'pipeline'
        
        # Entity scope (default - single account/opportunity)
        return 'entity'