from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class TraceMetadataCreate(BaseModel):
    trace_id: str
    request_id: str
    session_id: str
    user_id: int
    workspace_id: int
    correlation_id: Optional[str] = None
    user_query: str
    final_response: Optional[str] = None
    total_runtime_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model_name: str
    calculated_cost_usd: float = 0.0
    
    selected_intent: str
    planner_confidence: str
    extracted_entities: Dict[str, Any] = {}
    applied_filters: Dict[str, Any] = {}
    reasoning_confidence_pct: int = 0
    
    validation_passed: bool = True
    validation_error: Optional[str] = None
    grounding_score: str = "HIGH"
    reflection_triggered: bool = False
    
    backend_git_commit: str
    reasoning_engine_version: str


class SpanCreate(BaseModel):
    trace_id: str
    stage_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: int


class PayloadCreate(BaseModel):
    trace_id: str
    planner_prompt_hash: Optional[str] = None
    reasoner_prompt_hash: Optional[str] = None
    narrator_prompt_hash: Optional[str] = None
    planner_output: Optional[str] = None
    retrieved_context_summary: Optional[str] = None
    retrieved_record_ids: Dict[str, Any] = {}
    reasoning_package: Dict[str, Any] = {}
