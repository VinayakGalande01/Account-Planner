import os
import json
import time
import re
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════
# PYDANTIC OUTPUT MODELS
# ═══════════════════════════════════════════════════════════════

class OpportunityEvidence(BaseModel):
    id: str
    name: str
    stage: Optional[str] = None
    amount: Optional[float] = None
    close_date: Optional[str] = None
    probability: Optional[float] = None
    why_relevant: str

class ContactEvidence(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    role: Optional[str] = None
    why_relevant: str

class CaseEvidence(BaseModel):
    id: str
    severity: Optional[str] = None
    status: Optional[str] = None
    summary: str
    why_relevant: str

class ActivityEvidence(BaseModel):
    id: Optional[str] = None
    summary: str
    date: Optional[str] = None
    why_relevant: str

class EvidenceBundle(BaseModel):
    query_goal: str
    answer_strategy: Literal["DIRECT_LOOKUP", "FILTER_AND_RANK", "TREND_ANALYSIS", "RISK_ASSESSMENT", "EXECUTIVE_SUMMARY"]
    account_name: Optional[str] = None
    scope: Literal["ENTITY", "PORTFOLIO", "GLOBAL"]
    relevant_opportunities: List[OpportunityEvidence] = Field(default_factory=list)
    relevant_contacts: List[ContactEvidence] = Field(default_factory=list)
    relevant_cases: List[CaseEvidence] = Field(default_factory=list)
    relevant_activities: List[ActivityEvidence] = Field(default_factory=list)
    retrieval_gaps: List[str] = Field(default_factory=list)
    contradictory_signals: List[str] = Field(default_factory=list)
    answerability: Literal["HIGH", "MEDIUM", "LOW"]
    answerability_reason: str

class Finding(BaseModel):
    finding_type: Literal["PIPELINE", "RELATIONSHIP", "ACTIVITY", "SUPPORT", "REVENUE", "COMPOSITE"]
    observation: str
    implication: str
    severity: Literal["HIGH", "MEDIUM", "LOW", "POSITIVE"]
    evidence_refs: List[str] = Field(default_factory=list)
    confidence: float

class IntelligenceBrief(BaseModel):
    account_name: Optional[str] = None
    query_type: str
    objective: str
    top_findings: List[Finding] = Field(default_factory=list)
    expansion_signals: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    missing_critical_data: List[str] = Field(default_factory=list)
    recommended_validation_steps: List[str] = Field(default_factory=list)
    dominant_risk_theme: Optional[str] = None
    account_maturity: Literal["ACQUISITION", "GROWTH", "AT_RISK", "STRATEGIC", "CHURNING", "UNKNOWN"]
    answerability: Literal["HIGH", "MEDIUM", "LOW"]
    confidence: float
    confidence_reason: str

class ReasoningPlan(BaseModel):
    decision_task: str
    reasoning_mode: Literal["FACTUAL", "TACTICAL", "ANALYTICAL", "STRATEGIC"]
    key_evidence: List[str] = Field(default_factory=list)
    non_obvious_risks: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    candidate_conclusion: str
    confidence: float
    confidence_reason: str
    needs_persona_critique: bool
    persona_focus: List[Literal["SALES", "TECHNICAL", "FINANCIAL", "EXECUTIVE", "RISK"]] = Field(default_factory=list)
    next_validation_step: Optional[str] = None
    answer_mode: Literal["DIRECT", "CRUCIBLE"]

# ═══════════════════════════════════════════════════════════════
# HELPER & RESILIENCE FUNCS
# ═══════════════════════════════════════════════════════════════

def _call_model(task_type: str, system_prompt: str, user_prompt: str, timeout: int = 15) -> str:
    """Invokes Google Gemini API with task specific token sizing."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY environment variable is not configured.")
    
    # Local import to avoid top-level circular imports
    from reasoning_engine import call_gemini_api
    
    max_tokens = 2048
    if task_type == "evidence_selection":
        max_tokens = 1500
    elif task_type == "intelligence_brief":
        max_tokens = 1500
    elif task_type == "reasoning_plan":
        max_tokens = 1500
        
    print(f"[pre_reasoning_layer] Calling Gemini API for task_type={task_type}...")
    return call_gemini_api(system_prompt, user_prompt, gemini_key, max_tokens=max_tokens, timeout=timeout)

def _clean_and_parse_json(text: str) -> dict:
    """Regex based extraction to safely decode JSON from conversational wrappers."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end+1]
        
    try:
        return json.loads(text)
    except Exception as e:
        try:
            from reasoning_engine import repair_json_string
            repaired = repair_json_string(text)
            return json.loads(repaired)
        except Exception:
            raise e

def _repair_output(raw_output: str, validation_errors: str, schema_cls: Any) -> str:
    """Prompt 3 implementation: generic repair for malformed LLM outputs."""
    system_prompt = """You are a JSON repair assistant for APEX pre-reasoning outputs.
Your task is to repair the provided invalid JSON model output so it conforms exactly to the required Pydantic schema structure.

Rules:
1. Return valid JSON only.
2. Do not include markdown code block syntax (like ```json).
3. Do not add conversational comments, greetings, or post-scripts.
4. If fields are missing, provide standard defaults matching the expected types."""

    user_prompt = f"""Target Pydantic Schema:
{json.dumps(schema_cls.model_json_schema())}

Invalid model output to repair:
{raw_output}

Validation errors encountered:
{validation_errors}

Output repaired JSON matching the schema requirements:"""
    
    return _call_model("repair", system_prompt, user_prompt)

def _run_with_resilience(agent_run_fn, repair_prompt_fn, fallback_fn, schema_cls, task_label: str) -> tuple:
    """Executes agent with validate, retry once, repair, and fallback logic."""
    t0 = time.time()
    telemetry = {
        "task": task_label,
        "schema_valid": False,
        "repair_invoked": False,
        "fallback_used": False,
        "model_name": "gemini-2.5-flash",
        "latency_ms": 0
    }
    
    raw_output = None
    validation_err_msg = ""
    
    # Attempt 1 & 2: Direct call and Retry
    for attempt in range(2):
        try:
            raw_output = agent_run_fn()
            parsed = _clean_and_parse_json(raw_output)
            validated_obj = schema_cls(**parsed)
            telemetry["schema_valid"] = True
            telemetry["latency_ms"] = int((time.time() - t0) * 1000)
            return validated_obj, telemetry
        except Exception as e:
            validation_err_msg = str(e)
            print(f"[pre_reasoning_layer] Attempt {attempt+1} failed for {task_label}: {validation_err_msg}")
            
    # Attempt 3: Repair
    try:
        print(f"[pre_reasoning_layer] Invoking JSON Repair for {task_label}...")
        telemetry["repair_invoked"] = True
        
        repaired_raw = repair_prompt_fn(raw_output or "", validation_err_msg)
        parsed = _clean_and_parse_json(repaired_raw)
        validated_obj = schema_cls(**parsed)
        telemetry["schema_valid"] = True
        telemetry["latency_ms"] = int((time.time() - t0) * 1000)
        return validated_obj, telemetry
    except Exception as repair_err:
        print(f"[pre_reasoning_layer] Repair failed for {task_label}: {repair_err}")
        
    # Attempt 4: Fallback
    print(f"[pre_reasoning_layer] Falling back to deterministic Python construction for {task_label}...")
    telemetry["fallback_used"] = True
    validated_obj = fallback_fn(validation_err_msg)
    telemetry["latency_ms"] = int((time.time() - t0) * 1000)
    return validated_obj, telemetry

# ═══════════════════════════════════════════════════════════════
# AGENTS IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════

class EvidenceSelectorAgent:
    """Prompt 1: Compresses CRM context to a query-focused EvidenceBundle."""
    
    def run(self, user_query: str, intent_json: dict, retrieved_context_json: dict, 
            semantic_activities_json: list, data_sufficiency_score: float) -> tuple:
        
        def agent_fn():
            system_prompt = """You are the APEX Evidence Selector.
Your job is to transform a large CRM retrieval payload into a compact EvidenceBundle for downstream reasoning.

You are not writing an answer for the user.
You are not summarizing everything.
You are selecting only the evidence that is directly useful for answering the query.

Rules:
1. Return valid JSON only.
2. Do not include markdown fences (like ```json).
3. Use exactly the schema provided.
4. Prefer precision over completeness.
5. Include only the most relevant records.
6. If data is missing, record it explicitly in retrieval_gaps.
7. Do not invent fields, IDs, or facts.
8. If the query asks for ranked or filtered results, preserve the ranking/filter logic in query_goal and answer_strategy.
9. If evidence is weak, set answerability accordingly rather than guessing."""

            user_prompt = f"""Task:
Build an EvidenceBundle for the user query using the retrieved CRM context.

Query:
{user_query}

Intent classification:
{json.dumps(intent_json, indent=2)}

Retrieved CRM context:
{json.dumps(retrieved_context_json, indent=2)}

Semantic activities:
{json.dumps(semantic_activities_json, indent=2)}

Data sufficiency score:
{data_sufficiency_score}

Return this exact JSON structure:
{{
  "query_goal": "string",
  "answer_strategy": "DIRECT_LOOKUP | FILTER_AND_RANK | TREND_ANALYSIS | RISK_ASSESSMENT | EXECUTIVE_SUMMARY",
  "account_name": "string or null",
  "scope": "ENTITY | PORTFOLIO | GLOBAL",
  "relevant_opportunities": [
    {{
      "id": "string",
      "name": "string",
      "stage": "string or null",
      "amount": "number or null",
      "close_date": "string or null",
      "probability": "number or null",
      "why_relevant": "string"
    }}
  ],
  "relevant_contacts": [
    {{
      "id": "string",
      "name": "string",
      "title": "string or null",
      "role": "string or null",
      "why_relevant": "string"
    }}
  ],
  "relevant_cases": [
    {{
      "id": "string",
      "severity": "string or null",
      "status": "string or null",
      "summary": "string",
      "why_relevant": "string"
    }}
  ],
  "relevant_activities": [
    {{
      "id": "string or null",
      "summary": "string",
      "date": "string or null",
      "why_relevant": "string"
    }}
  ],
  "retrieval_gaps": ["string"],
  "contradictory_signals": ["string"],
  "answerability": "HIGH | MEDIUM | LOW",
  "answerability_reason": "string"
}}"""
            return _call_model("evidence_selection", system_prompt, user_prompt)
            
        def repair_fn(raw_output, err_msg):
            return _repair_output(raw_output, err_msg, EvidenceBundle)
            
        def fallback_fn(err_msg):
            acc_name = retrieved_context_json.get("account_name")
            opps = []
            for o in retrieved_context_json.get("opportunities", [])[:3]:
                opps.append(OpportunityEvidence(
                    id=o.get("opp_id") or o.get("id") or "unknown",
                    name=o.get("opp_name") or o.get("name") or "unknown",
                    stage=o.get("stage"),
                    amount=o.get("amount_usd") or o.get("amount"),
                    close_date=o.get("close_date"),
                    probability=o.get("probability", 100.0),
                    why_relevant="Fallback matching opportunity"
                ))
            contacts = []
            for c in retrieved_context_json.get("contacts", [])[:3]:
                contacts.append(ContactEvidence(
                    id=c.get("contact_id") or c.get("id") or "unknown",
                    name=c.get("name") or "unknown",
                    title=c.get("title"),
                    role=c.get("role"),
                    why_relevant="Fallback contact"
                ))
            cases = []
            for cs in retrieved_context_json.get("cases", [])[:3]:
                cases.append(CaseEvidence(
                    id=cs.get("case_id") or cs.get("id") or "unknown",
                    severity=cs.get("severity"),
                    status=cs.get("status"),
                    summary=cs.get("subject") or cs.get("summary") or "unknown",
                    why_relevant="Fallback support case"
                ))
            activities = []
            for act in retrieved_context_json.get("activities", [])[:3]:
                activities.append(ActivityEvidence(
                    id=act.get("activity_id") or act.get("id"),
                    summary=act.get("description") or act.get("summary") or "unknown",
                    date=act.get("date"),
                    why_relevant="Fallback activity"
                ))
            return EvidenceBundle(
                query_goal=user_query,
                answer_strategy="DIRECT_LOOKUP",
                account_name=acc_name,
                scope="ENTITY" if acc_name else "GLOBAL",
                relevant_opportunities=opps,
                relevant_contacts=contacts,
                relevant_cases=cases,
                relevant_activities=activities,
                retrieval_gaps=["JSON parsing error triggering fallback"],
                contradictory_signals=[],
                answerability="MEDIUM",
                answerability_reason=f"Generated via Python fallback logic due to parsing errors: {err_msg[:60]}"
            )
            
        return _run_with_resilience(agent_fn, repair_fn, fallback_fn, EvidenceBundle, "evidence_selection")


class IntelligenceBriefAgent:
    """Prompt 2: Converts EvidenceBundle and deterministic alerts into an IntelligenceBrief."""
    
    def run(self, user_query: str, intent_json: dict, evidence_bundle: EvidenceBundle, 
            intelligence_signals: dict, data_sufficiency_score: float) -> tuple:
        
        def agent_fn():
            system_prompt = """You are the APEX Intelligence Brief Builder.
Your job is to convert selected CRM evidence into an intelligence brief for downstream reasoning.

You must identify:
- what matters most
- what is risky
- what is positive
- what is missing
- what should be validated next

You are not the final narrator.
You are not allowed to write conversational prose.
You must produce a compact decision object.

Rules:
1. Return valid JSON only.
2. Use only facts present in the input.
3. If evidence is insufficient, lower confidence and say why.
4. Distinguish observed fact from inferred implication.
5. Do not overstate certainty.
6. Keep findings specific to this account and query.
7. If signals conflict, record them in contradictions."""

            user_prompt = f"""Task:
Build an IntelligenceBrief from the EvidenceBundle and deterministic signals.

User query:
{user_query}

Intent:
{json.dumps(intent_json, indent=2)}

EvidenceBundle:
{evidence_bundle.model_dump_json(indent=2)}

Deterministic intelligence signals:
{json.dumps(intelligence_signals, indent=2)}

Data sufficiency score:
{data_sufficiency_score}

Return this exact JSON structure:
{{
  "account_name": "string or null",
  "query_type": "string",
  "objective": "string",
  "top_findings": [
    {{
      "finding_type": "PIPELINE | RELATIONSHIP | ACTIVITY | SUPPORT | REVENUE | COMPOSITE",
      "observation": "string",
      "implication": "string",
      "severity": "HIGH | MEDIUM | LOW | POSITIVE",
      "evidence_refs": ["string"],
      "confidence": 0.0
    }}
  ],
  "expansion_signals": ["string"],
  "contradictions": ["string"],
  "missing_critical_data": ["string"],
  "recommended_validation_steps": ["string"],
  "dominant_risk_theme": "string or null",
  "account_maturity": "ACQUISITION | GROWTH | AT_RISK | STRATEGIC | CHURNING | UNKNOWN",
  "answerability": "HIGH | MEDIUM | LOW",
  "confidence": 0.0,
  "confidence_reason": "string"
}}"""
            return _call_model("intelligence_brief", system_prompt, user_prompt)
            
        def repair_fn(raw_output, err_msg):
            return _repair_output(raw_output, err_msg, IntelligenceBrief)
            
        def fallback_fn(err_msg):
            findings = []
            for o in evidence_bundle.relevant_opportunities:
                findings.append(Finding(
                    finding_type="PIPELINE",
                    observation=f"Active opportunity '{o.name}' is in stage '{o.stage or 'Unknown'}'.",
                    implication=f"Requires progression steps to close by {o.close_date or 'N/A'}.",
                    severity="MEDIUM" if (o.probability or 100) < 50 else "POSITIVE",
                    evidence_refs=[o.id],
                    confidence=data_sufficiency_score
                ))
            for c in evidence_bundle.relevant_cases:
                findings.append(Finding(
                    finding_type="SUPPORT",
                    observation=f"Support case '{c.id}' is '{c.status or 'open'}' with severity '{c.severity or 'medium'}'.",
                    implication=f"Resolving support issue protects active revenue stream.",
                    severity="HIGH" if c.severity in ["P1", "Critical", "High"] else "MEDIUM",
                    evidence_refs=[c.id],
                    confidence=data_sufficiency_score
                ))
            maturity = "GROWTH" if evidence_bundle.account_name else "UNKNOWN"
            return IntelligenceBrief(
                account_name=evidence_bundle.account_name,
                query_type="PIPELINE_ANALYSIS",
                objective="Analyze active pipeline and risks",
                top_findings=findings,
                expansion_signals=[],
                contradictions=[],
                missing_critical_data=evidence_bundle.retrieval_gaps,
                recommended_validation_steps=["Verify opportunity close dates and support case statuses manually."],
                dominant_risk_theme="Pipeline stagnation" if any(f.severity == "HIGH" for f in findings) else "None",
                account_maturity=maturity,
                answerability=evidence_bundle.answerability,
                confidence=data_sufficiency_score,
                confidence_reason=f"Derived via Python fallback logic due to parsing errors: {err_msg[:60]}"
            )
            
        return _run_with_resilience(agent_fn, repair_fn, fallback_fn, IntelligenceBrief, "intelligence_brief")


class ReasoningPlannerAgent:
    """Prompt 4: Creates a ReasoningPlan deciding decision tasks, persona focuses and answer_mode."""
    
    def run(self, user_query: str, response_mode: str, intent_json: dict, 
            intelligence_brief: IntelligenceBrief) -> tuple:
        
        def agent_fn():
            system_prompt = """You are the APEX Reasoning Planner.
Your job is to decide how the agent should answer the query based on the IntelligenceBrief.

You are not writing the final user-facing answer.
You are deciding:
- what question must be answered
- which evidence matters most
- what risks or ambiguities could change the answer
- what the best candidate conclusion is
- what additional validation is needed

Rules:
1. Return valid JSON only.
2. Base all reasoning on the IntelligenceBrief.
3. Do not restate the entire brief.
4. Focus on decision-making, not summary.
5. If ambiguity is high, say what must be checked next.
6. If confidence is low, prefer a bounded answer with caveats."""

            user_prompt = f"""Task:
Create a reasoning plan from the IntelligenceBrief.

User query:
{user_query}

Response mode:
{response_mode}

Intent:
{json.dumps(intent_json, indent=2)}

IntelligenceBrief:
{intelligence_brief.model_dump_json(indent=2)}

Return this exact JSON structure:
{{
  "decision_task": "string",
  "reasoning_mode": "FACTUAL | TACTICAL | ANALYTICAL | STRATEGIC",
  "key_evidence": ["string"],
  "non_obvious_risks": ["string"],
  "ambiguities": ["string"],
  "candidate_conclusion": "string",
  "confidence": 0.0,
  "confidence_reason": "string",
  "needs_persona_critique": true,
  "persona_focus": ["SALES", "TECHNICAL", "FINANCIAL", "EXECUTIVE", "RISK"],
  "next_validation_step": "string or null",
  "answer_mode": "DIRECT | CRUCIBLE"
}}"""
            return _call_model("reasoning_plan", system_prompt, user_prompt)
            
        def repair_fn(raw_output, err_msg):
            return _repair_output(raw_output, err_msg, ReasoningPlan)
            
        def fallback_fn(err_msg):
            mode = "TACTICAL"
            if response_mode == "executive":
                mode = "STRATEGIC"
            elif response_mode == "analyst":
                mode = "ANALYTICAL"
            return ReasoningPlan(
                decision_task=f"Answer the query: {user_query}",
                reasoning_mode=mode,
                key_evidence=[f.observation for f in intelligence_brief.top_findings[:3]],
                non_obvious_risks=["No direct LLM reasoning could be computed, fallback active."],
                ambiguities=[f"Model execution fallback active: {err_msg[:50]}"],
                candidate_conclusion="Based on CRM records, the pipeline has active deals and contacts.",
                confidence=intelligence_brief.confidence,
                confidence_reason="Propagated from brief confidence score",
                needs_persona_critique=True,
                persona_focus=["SALES", "EXECUTIVE"],
                next_validation_step="Manually verify key CRM updates.",
                answer_mode="CRUCIBLE"
            )
            
        return _run_with_resilience(agent_fn, repair_fn, fallback_fn, ReasoningPlan, "reasoning_plan")


# ═══════════════════════════════════════════════════════════════
# PRE-REASONING TO CONSENSUS DIRECT ROUTER
# ═══════════════════════════════════════════════════════════════

def build_consensus_from_plan(reasoning_plan: ReasoningPlan, intelligence_brief: IntelligenceBrief) -> Any:
    """Bypasses Crucible and returns a fast ConsensusOutput directly from ReasoningPlan."""
    # Local import to avoid circular imports
    from reasoning_engine import ConsensusOutput
    
    # Construct a simplified crucible_data structure so Layer 3 Narrator is completely happy
    crucible_data = {
        "executive_brief": {
            "revenue_at_stake": "Determined via Direct Pathway",
            "macro_summary": reasoning_plan.candidate_conclusion
        },
        "persona_insights": {
            "enterprise_ae": f"Key findings: " + "; ".join([f.observation for f in intelligence_brief.top_findings[:2]]),
            "strategic_director": f"Identified risks: " + "; ".join(reasoning_plan.non_obvious_risks)
        },
        "tactical_playbook": [
            {
                "day": 1,
                "action": reasoning_plan.next_validation_step or "Review core findings and plan immediate validations.",
                "owner": "Account Manager",
                "success_metric": "Validation scheduled"
            }
        ]
    }
    
    return ConsensusOutput(
        consensus_recommendation={
            "action": "Proceed with Plan direct recommendations.",
            "confidence": reasoning_plan.confidence,
            "rationale": reasoning_plan.candidate_conclusion,
            "crucible_data": crucible_data
        },
        thread_agreement={"am": reasoning_plan.confidence, "vp": reasoning_plan.confidence},
        agreement_score=1.0,
        dissenting_views=[],
        confidence_limiting_factors=reasoning_plan.ambiguities,
        final_confidence=reasoning_plan.confidence
    )
