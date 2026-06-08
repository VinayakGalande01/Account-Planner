"""
APEX Response Blueprint System — Information Choreography Engine

Architecture Position:
    Phase 1 (Intent Classification) → query_scope computed
    ↓
    THIS MODULE → resolve_blueprint(intent, scope, confidence) → ResponseBlueprint
    ↓
    Phase 2 (Data Retrieval) — unchanged
    ↓
    Intelligence Layer → curate_llm_context(... blueprint) → gated context
    ↓
    Phase 4 (Narrative) → build_phase4_prompt(blueprint) → dynamic prompt

Design Principles:
    1. Blueprints are keyed by (ReasoningMode, QueryScope) — NEVER by query strings.
    2. Fully deterministic. Zero LLM dependency.
    3. The system remains generic and enterprise-grade.
    4. Blueprints control: which sections appear, narrative depth, governance visibility.
    5. New intents or modes can be added without touching other modules.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ═══════════════════════════════════════════════════════════════
# REASONING MODES
# ═══════════════════════════════════════════════════════════════

class ReasoningMode(str, Enum):
    """Four generic reasoning modes — not tied to specific queries."""
    FACTUAL     = "FACTUAL"       # Pure data retrieval — contacts, lookups, entity facts
    OPERATIONAL = "OPERATIONAL"   # Rankings, lists, pipeline summaries, table-heavy
    STRATEGIC   = "STRATEGIC"     # Account plans, risk analysis, deep recommendations
    EXECUTIVE   = "EXECUTIVE"     # High-level portfolio reviews, board-ready briefings


# ═══════════════════════════════════════════════════════════════
# RESPONSE BLUEPRINT
# ═══════════════════════════════════════════════════════════════

@dataclass
class ResponseBlueprint:
    """Declarative configuration controlling response shape.

    Controls which sections appear, in what order, how deep the narrative goes,
    and how governance findings are surfaced (or suppressed).
    """
    mode: ReasoningMode
    required_sections: List[str] = field(default_factory=list)    # MUST appear
    optional_sections: List[str] = field(default_factory=list)    # Included only if data exists
    suppressed_sections: List[str] = field(default_factory=list)  # NEVER included
    max_signals: int = 4
    max_actions: int = 3
    narrative_depth: str = "standard"       # "minimal" | "standard" | "deep"
    governance_visibility: str = "footer"   # "hidden" | "footer" | "inline"
    direct_answer_required: bool = False    # Must the first section directly answer the question?

    def is_section_allowed(self, section_name: str) -> bool:
        """Check if a section is permitted by this blueprint."""
        if section_name in self.suppressed_sections:
            return False
        if section_name in self.required_sections:
            return True
        if section_name in self.optional_sections:
            return True
        return False

    def get_ordered_sections(self) -> List[str]:
        """Return all allowed sections in render order."""
        ordered = []
        for s in self.required_sections:
            if s not in ordered:
                ordered.append(s)
        for s in self.optional_sections:
            if s not in ordered:
                ordered.append(s)
        return ordered


# ═══════════════════════════════════════════════════════════════
# INTENT → REASONING MODE MAPPING
# ═══════════════════════════════════════════════════════════════

# Maps (intent, scope) → ReasoningMode. Falls back gracefully.
_INTENT_MODE_MAP: Dict[str, ReasoningMode] = {
    "CONTACT_QUERY":                ReasoningMode.FACTUAL,
    "GLOBAL_LIST_QUERY":            ReasoningMode.OPERATIONAL,
    "PIPELINE_SUMMARY_QUERY":       ReasoningMode.OPERATIONAL,
    "PIPELINE_QUERY":               ReasoningMode.OPERATIONAL,
    "RISK_ANALYSIS_QUERY":          ReasoningMode.STRATEGIC,
    "RISK_ANALYSIS":                ReasoningMode.STRATEGIC,
    "HEALTH_QUERY":                 ReasoningMode.STRATEGIC,
    "ACCOUNT_PLAN_QUERY":           ReasoningMode.STRATEGIC,
    "ACCOUNT_PLAN":                 ReasoningMode.STRATEGIC,
    "ACTION_RECOMMENDATION_QUERY":  ReasoningMode.STRATEGIC,
    "ACTION_RECOMMENDATION":        ReasoningMode.STRATEGIC,
}

# Scope can override mode in specific cases
_SCOPE_MODE_OVERRIDES: Dict[tuple, ReasoningMode] = {
    # Portfolio-level contact queries become operational (list all contacts)
    ("CONTACT_QUERY", "Portfolio"): ReasoningMode.OPERATIONAL,
}


def _resolve_mode(intent: str, query_scope: str) -> ReasoningMode:
    """Resolve the reasoning mode from intent + scope."""
    # Check scope override first
    override = _SCOPE_MODE_OVERRIDES.get((intent, query_scope))
    if override:
        return override
    return _INTENT_MODE_MAP.get(intent, ReasoningMode.OPERATIONAL)


# ═══════════════════════════════════════════════════════════════
# BLUEPRINT TEMPLATES (Keyed by ReasoningMode)
# ═══════════════════════════════════════════════════════════════

_BLUEPRINT_TEMPLATES: Dict[ReasoningMode, dict] = {

    ReasoningMode.FACTUAL: {
        "required_sections":    ["DIRECT_ANSWER", "HEADLINE"],
        "optional_sections":    ["ACTIONS", "CONFIDENCE"],
        "suppressed_sections":  ["EXECUTIVE_SUMMARY", "SIGNALS", "WHY_THIS_MATTERS", "CRM_HYGIENE", "SUMMARY"],
        "max_signals":          0,
        "max_actions":          2,
        "narrative_depth":      "minimal",
        "governance_visibility": "hidden",
        "direct_answer_required": True,
    },

    ReasoningMode.OPERATIONAL: {
        "required_sections":    ["HEADLINE", "DIRECT_ANSWER", "TABLE_DATA"],
        "optional_sections":    ["SIGNALS", "ACTIONS", "CONFIDENCE"],
        "suppressed_sections":  ["EXECUTIVE_SUMMARY", "WHY_THIS_MATTERS", "CRM_HYGIENE", "SUMMARY"],
        "max_signals":          3,
        "max_actions":          3,
        "narrative_depth":      "standard",
        "governance_visibility": "footer",
        "direct_answer_required": True,
    },

    ReasoningMode.STRATEGIC: {
        "required_sections":    ["HEADLINE", "EXECUTIVE_SUMMARY", "SIGNALS", "ACTIONS"],
        "optional_sections":    ["SUMMARY", "WHY_THIS_MATTERS", "CRM_HYGIENE", "CONFIDENCE", "DIRECT_ANSWER", "TABLE_DATA"],
        "suppressed_sections":  [],
        "max_signals":          5,
        "max_actions":          5,
        "narrative_depth":      "deep",
        "governance_visibility": "inline",
        "direct_answer_required": False,
    },

    ReasoningMode.EXECUTIVE: {
        "required_sections":    ["HEADLINE", "EXECUTIVE_SUMMARY", "SIGNALS", "WHY_THIS_MATTERS", "ACTIONS"],
        "optional_sections":    ["CRM_HYGIENE", "CONFIDENCE"],
        "suppressed_sections":  ["DIRECT_ANSWER", "TABLE_DATA", "SUMMARY"],
        "max_signals":          4,
        "max_actions":          4,
        "narrative_depth":      "deep",
        "governance_visibility": "inline",
        "direct_answer_required": False,
    },
}


# ═══════════════════════════════════════════════════════════════
# SCOPE-SPECIFIC ADJUSTMENTS
# ═══════════════════════════════════════════════════════════════

def _apply_scope_adjustments(bp: ResponseBlueprint, query_scope: str) -> None:
    """Mutate blueprint in-place based on query scope.
    Entity-scoped queries suppress portfolio-level sections."""

    if query_scope == "Entity":
        # Entity queries never need WHY_THIS_MATTERS unless in STRATEGIC mode
        if bp.mode != ReasoningMode.STRATEGIC and bp.mode != ReasoningMode.EXECUTIVE:
            if "WHY_THIS_MATTERS" not in bp.suppressed_sections:
                bp.suppressed_sections.append("WHY_THIS_MATTERS")
            # Remove from optional/required if present
            bp.optional_sections = [s for s in bp.optional_sections if s != "WHY_THIS_MATTERS"]
            bp.required_sections = [s for s in bp.required_sections if s != "WHY_THIS_MATTERS"]


def _apply_confidence_adjustments(bp: ResponseBlueprint, confidence: str) -> None:
    """Mutate blueprint in-place based on confidence level.
    Low confidence promotes governance sections."""

    if confidence == "LOW":
        # Force CRM_HYGIENE visible when confidence is low
        if "CRM_HYGIENE" in bp.suppressed_sections:
            bp.suppressed_sections.remove("CRM_HYGIENE")
        if "CRM_HYGIENE" not in bp.required_sections and "CRM_HYGIENE" not in bp.optional_sections:
            bp.optional_sections.append("CRM_HYGIENE")

        # Ensure CONFIDENCE is always visible
        if "CONFIDENCE" in bp.suppressed_sections:
            bp.suppressed_sections.remove("CONFIDENCE")
        if "CONFIDENCE" not in bp.required_sections and "CONFIDENCE" not in bp.optional_sections:
            bp.optional_sections.append("CONFIDENCE")

        # Reduce action aggressiveness
        bp.max_actions = min(bp.max_actions, 3)

        # Promote governance to inline for strategic queries
        if bp.mode in (ReasoningMode.STRATEGIC, ReasoningMode.EXECUTIVE):
            bp.governance_visibility = "inline"


# ═══════════════════════════════════════════════════════════════
# BLUEPRINT RESOLVER (Public API)
# ═══════════════════════════════════════════════════════════════

def resolve_blueprint(intent: str, query_scope: str, confidence: str = "HIGH") -> ResponseBlueprint:
    """Resolve a ResponseBlueprint from intent + scope + confidence.

    This is the single public entry point. The resolver:
        1. Maps intent + scope → ReasoningMode
        2. Looks up the blueprint template for that mode
        3. Applies scope adjustments (Entity suppresses portfolio sections)
        4. Applies confidence adjustments (LOW promotes governance)

    Returns a fully computed ResponseBlueprint.
    No hardcoded query handling — purely intent/scope/confidence driven.
    """
    mode = _resolve_mode(intent, query_scope)
    template = _BLUEPRINT_TEMPLATES.get(mode, _BLUEPRINT_TEMPLATES[ReasoningMode.OPERATIONAL])

    bp = ResponseBlueprint(
        mode=mode,
        required_sections=list(template["required_sections"]),
        optional_sections=list(template["optional_sections"]),
        suppressed_sections=list(template["suppressed_sections"]),
        max_signals=template["max_signals"],
        max_actions=template["max_actions"],
        narrative_depth=template["narrative_depth"],
        governance_visibility=template["governance_visibility"],
        direct_answer_required=template["direct_answer_required"],
    )

    _apply_scope_adjustments(bp, query_scope)
    _apply_confidence_adjustments(bp, confidence)

    return bp


# ═══════════════════════════════════════════════════════════════
# PHASE 4 — MODE-SPECIFIC IDENTITY PROMPTS
# ═══════════════════════════════════════════════════════════════

PHASE4_IDENTITY_PROMPTS: Dict[ReasoningMode, str] = {
    ReasoningMode.FACTUAL: (
        "You are answering a specific factual question about CRM data. "
        "Lead with the direct answer. Be concise and data-precise. "
        "Do not narrate, strategize, or add governance commentary. "
        "The user asked a simple question — give them a simple, accurate answer."
    ),
    ReasoningMode.OPERATIONAL: (
        "You are presenting operational intelligence — ranked data, pipeline summaries, or listings. "
        "Lead with the key answer or result. Support with ranked data. "
        "Highlight the single most actionable insight. Keep it crisp and scannable."
    ),
    ReasoningMode.STRATEGIC: (
        "You are a strategic account advisor providing evidence-backed counsel. "
        "Balance insight depth with executive readability. "
        "Every recommendation must cite its supporting evidence. "
        "You are interpreting pre-computed intelligence — not inventing analysis."
    ),
    ReasoningMode.EXECUTIVE: (
        "You are delivering an executive portfolio briefing. "
        "Prioritize headline impact, risk signals, and board-ready language. "
        "Be concise but compelling. Frame everything in terms of revenue impact and business risk."
    ),
}


# ═══════════════════════════════════════════════════════════════
# PHASE 4 — SECTION WRITING TEMPLATES (Mode-Variant)
# ═══════════════════════════════════════════════════════════════

SECTION_TEMPLATES: Dict[str, Dict[str, str]] = {

    "DIRECT_ANSWER": {
        "FACTUAL": (
            "__SECTION_DIRECT_ANSWER__\n"
            "[State the exact factual answer from the SIP data. If a contact was asked for, name them with role immediately. "
            "If a list was requested, present it. No preamble, no governance context, no narrative. Just the answer.]\n\n"
        ),
        "OPERATIONAL": (
            "__SECTION_DIRECT_ANSWER__\n"
            "[Present the key ranked result immediately. For example: 'Your top 5 opportunities by value are:' "
            "or 'Pipeline total: $X.XM across N active deals.' Give the user what they asked for first.]\n\n"
        ),
        "STRATEGIC": (
            "__SECTION_DIRECT_ANSWER__\n"
            "[Provide a 1-2 sentence direct response to the user's core question before expanding into strategic analysis.]\n\n"
        ),
        "EXECUTIVE": "",  # Suppressed — EXECUTIVE_SUMMARY leads instead
    },

    "HEADLINE": {
        "FACTUAL": (
            "__SECTION_HEADLINE__\n"
            "[One-line factual summary that directly answers the question.]\n\n"
        ),
        "OPERATIONAL": (
            "__SECTION_HEADLINE__\n"
            "[Single punchy sentence: the top-line finding from the data.]\n\n"
        ),
        "STRATEGIC": (
            "__SECTION_HEADLINE__\n"
            "[High-impact strategic headline with revenue/risk context. Should feel like a newspaper lead.]\n\n"
        ),
        "EXECUTIVE": (
            "__SECTION_HEADLINE__\n"
            "[Board-ready headline: what demands executive attention right now.]\n\n"
        ),
    },

    "EXECUTIVE_SUMMARY": {
        "STRATEGIC": (
            "__SECTION_EXECUTIVE_SUMMARY__\n"
            "[CRITICAL: Maximum 3 bullet points. Provide a high-level executive summary of the most important findings and risks. "
            "Each bullet must reference a specific data fact.]\n\n"
        ),
        "EXECUTIVE": (
            "__SECTION_EXECUTIVE_SUMMARY__\n"
            "[Maximum 3 bullet points. Board-ready findings: revenue at risk, pipeline health, and the single most critical action. "
            "Each bullet must quantify impact.]\n\n"
        ),
    },

    "SUMMARY": {
        "STRATEGIC": (
            "__SECTION_SUMMARY__\n"
            "[Based on situation, contact, and risks from SIP, write a human, professional overview in 3 clear sentences. "
            "Sentence 1: What is happening. Sentence 2: Why it matters. Sentence 3: What should be done.]\n\n"
        ),
    },

    "TABLE_DATA": {
        # Table data is pre-rendered by backend. This is just a hint to the LLM.
        "OPERATIONAL": "",  # Backend yields table data directly, LLM doesn't generate it
        "STRATEGIC": "",
    },

    "SIGNALS": {
        "OPERATIONAL": (
            "__SECTION_SIGNALS__\n"
            "• [Key trend signal 1 — cite specific data evidence]\n"
            "• [Signal 2 — with data evidence]\n\n"
        ),
        "STRATEGIC": (
            "__SECTION_SIGNALS__\n"
            "• [Formulate strategic Business Risk signal 1 based on SIP. Every signal MUST show concrete data evidence. "
            "Place priority badges at the start if available (e.g. 'Priority: CRITICAL').]\n"
            "• [Business Risk Signal 2]\n"
            "• [Business Risk Signal 3]\n\n"
        ),
        "EXECUTIVE": (
            "__SECTION_SIGNALS__\n"
            "• [Priority: CRITICAL/HIGH — Executive-level risk signal with quantified impact]\n"
            "• [Signal 2 — revenue or pipeline impact with evidence]\n"
            "• [Signal 3]\n\n"
        ),
    },

    "WHY_THIS_MATTERS": {
        "STRATEGIC": (
            "__SECTION_WHY_THIS_MATTERS__\n"
            "[A high-impact executive block. Summarize the revenue exposure, forecast impact, and macro importance of the signals. "
            "Explain exactly why this matters to the business in 2-3 compelling sentences, linking raw numbers to quarter-end forecast accuracy.]\n\n"
        ),
        "EXECUTIVE": (
            "__SECTION_WHY_THIS_MATTERS__\n"
            "[2 sentences maximum. Frame the signals in terms of quarterly forecast impact and executive accountability. "
            "Make it feel urgent and consequential.]\n\n"
        ),
    },

    "ACTIONS": {
        "FACTUAL": (
            "__SECTION_ACTIONS__\n"
            "• [Single most relevant follow-up action based on the factual answer — specific, named, time-bound]\n\n"
        ),
        "OPERATIONAL": (
            "__SECTION_ACTIONS__\n"
            "• [Action 1 — specific, named, evidence-backed, time-bound]\n"
            "• [Action 2]\n\n"
        ),
        "STRATEGIC": (
            "__SECTION_ACTIONS__\n"
            "• [Action 1 from SIP actions — MUST cite evidence from CRM. If LOW confidence, recommend validation. "
            "If HIGH confidence, recommend aggressive execution.]\n"
            "• [Action 2 — equally specific and evidence-backed]\n"
            "• [Action 3]\n\n"
        ),
        "EXECUTIVE": (
            "__SECTION_ACTIONS__\n"
            "• [Top priority executive action — who, what, by when, expected impact]\n"
            "• [Action 2 — specific and evidence-backed]\n\n"
        ),
    },

    "CRM_HYGIENE": {
        "STRATEGIC": (
            "__SECTION_CRM_HYGIENE__\n"
            "⚠️ [Data Quality Risk / Hygiene Gap 1]\n"
            "⚠️ [Data Quality Risk / Hygiene Gap 2]\n\n"
        ),
        "EXECUTIVE": (
            "__SECTION_CRM_HYGIENE__\n"
            "⚠️ [Data Quality Risk 1]\n\n"
        ),
    },

    "CONFIDENCE": {
        "_default": (
            '__SECTION_CONFIDENCE__\n'
            '{"score": "<confidence_pct>%", "status": "<confidence_pct>% Grounded (Direct facts from Excel)", "sources": ["Excel Database"]}\n\n'
        ),
    },
}


# ═══════════════════════════════════════════════════════════════
# PHASE 4 — DYNAMIC PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════

# Strict rules appended to every Phase 4 prompt
_STRICT_RULES = """STRICT RULES:
1. Do not output any conversational preambles or postambles. Only output the section headers and content.
2. Use the exact __SECTION_*__ headers as shown above. Do not invent new ones.
3. Replace the "<confidence_pct>" placeholders with the actual confidence percentage from the SIP JSON.
4. Every recommendation MUST cite its supporting evidence from the data. Unearned recommendations are forbidden.
5. Do NOT include sections that are not listed in the RESPONSE CONTRACT above.

__SECTION_END__"""


def build_phase4_prompt(blueprint: ResponseBlueprint) -> str:
    """Dynamically construct the Phase 4 narrative prompt based on the blueprint.

    Only includes section instructions for sections the blueprint allows.
    Different blueprints produce visibly different prompts, ensuring
    narrative variability across query types.
    """
    mode_key = blueprint.mode.value

    # 1. Mode-specific identity
    identity = PHASE4_IDENTITY_PROMPTS.get(blueprint.mode, PHASE4_IDENTITY_PROMPTS[ReasoningMode.OPERATIONAL])

    # 2. Assemble section instructions for allowed sections only
    section_instructions = []
    for section in blueprint.get_ordered_sections():
        templates_for_section = SECTION_TEMPLATES.get(section, {})
        # Try mode-specific template, then _default, then skip
        template_text = templates_for_section.get(mode_key) or templates_for_section.get("_default", "")
        if template_text:
            section_instructions.append(template_text)

    if not section_instructions:
        # Fallback: at least output HEADLINE + CONFIDENCE
        section_instructions.append(
            "__SECTION_HEADLINE__\n[Answer the user's question directly.]\n\n"
        )
        section_instructions.append(
            SECTION_TEMPLATES["CONFIDENCE"]["_default"]
        )

    # 3. Assemble final prompt
    sections_block = "".join(section_instructions)

    prompt = f"""{identity}

## RESPONSE CONTRACT
You MUST structure your response using ONLY these section headers (in this exact order):

{sections_block}
{_STRICT_RULES}"""

    return prompt


# ═══════════════════════════════════════════════════════════════
# CONTEXT ELIGIBILITY RULES
# ═══════════════════════════════════════════════════════════════

# Each intelligence block declares which intents + scopes it is allowed for.
# "*" means always eligible.
CONTEXT_ELIGIBILITY: Dict[str, Dict[str, set]] = {
    "business_decision_context": {
        "intents": {"*"},
        "scopes": {"*"},
    },
    "current_situation": {
        "intents": {"*"},
        "scopes": {"*"},
    },
    "portfolio_metrics": {
        "intents": {"PIPELINE_QUERY", "PIPELINE_SUMMARY_QUERY", "GLOBAL_LIST_QUERY",
                    "ACTION_RECOMMENDATION_QUERY", "ACTION_RECOMMENDATION", "RISK_ANALYSIS_QUERY", "RISK_ANALYSIS"},
        "scopes": {"Portfolio", "Mixed"},
    },
    "stakeholder_recommendations": {
        "intents": {"CONTACT_QUERY", "ACCOUNT_PLAN_QUERY", "ACCOUNT_PLAN",
                    "ACTION_RECOMMENDATION_QUERY", "ACTION_RECOMMENDATION"},
        "scopes": {"Entity", "Mixed"},
    },
    "next_best_actions": {
        "intents": {"*"},
        "scopes": {"*"},
    },
    "consequences_of_inaction": {
        "intents": {"RISK_ANALYSIS_QUERY", "RISK_ANALYSIS", "ACCOUNT_PLAN_QUERY", "ACCOUNT_PLAN",
                    "ACTION_RECOMMENDATION_QUERY", "ACTION_RECOMMENDATION"},
        "scopes": {"*"},
    },
    "risk_implications": {
        "intents": {"RISK_ANALYSIS_QUERY", "RISK_ANALYSIS", "ACCOUNT_PLAN_QUERY", "ACCOUNT_PLAN",
                    "ACTION_RECOMMENDATION_QUERY", "ACTION_RECOMMENDATION"},
        "scopes": {"*"},
    },
    "business_impact": {
        "intents": {"RISK_ANALYSIS_QUERY", "RISK_ANALYSIS", "ACCOUNT_PLAN_QUERY", "ACCOUNT_PLAN",
                    "ACTION_RECOMMENDATION_QUERY", "ACTION_RECOMMENDATION"},
        "scopes": {"*"},
    },
    "reasoning_evidence": {
        "intents": {"*"},
        "scopes": {"*"},
    },
    "portfolio_state": {
        "intents": {"PIPELINE_QUERY", "PIPELINE_SUMMARY_QUERY", "GLOBAL_LIST_QUERY",
                    "ACTION_RECOMMENDATION_QUERY", "ACTION_RECOMMENDATION"},
        "scopes": {"Portfolio", "Mixed"},
    },
    "portfolio_intelligence_signals": {
        "intents": {"PIPELINE_QUERY", "PIPELINE_SUMMARY_QUERY", "GLOBAL_LIST_QUERY",
                    "RISK_ANALYSIS_QUERY", "RISK_ANALYSIS"},
        "scopes": {"Portfolio", "Mixed"},
    },
    "table_hint": {
        "intents": {"*"},
        "scopes": {"*"},
    },
    "strategic_context": {
        "intents": {"PIPELINE_QUERY", "PIPELINE_SUMMARY_QUERY", "GLOBAL_LIST_QUERY",
                    "RISK_ANALYSIS_QUERY", "RISK_ANALYSIS", "ACCOUNT_PLAN_QUERY", "ACCOUNT_PLAN",
                    "ACTION_RECOMMENDATION_QUERY", "ACTION_RECOMMENDATION"},
        "scopes": {"*"},
    },
    "confidence_assessment": {
        "intents": {"*"},
        "scopes": {"*"},
    },
}


def is_context_eligible(block_name: str, intent: str, query_scope: str) -> bool:
    """Check if a context block is eligible for the given intent + scope."""
    rules = CONTEXT_ELIGIBILITY.get(block_name)
    if not rules:
        return True  # Unknown blocks are always eligible (safe default)

    # Check intent eligibility
    allowed_intents = rules.get("intents", {"*"})
    if "*" not in allowed_intents and intent not in allowed_intents:
        return False

    # Check scope eligibility
    allowed_scopes = rules.get("scopes", {"*"})
    if "*" not in allowed_scopes and query_scope not in allowed_scopes:
        return False

    return True
