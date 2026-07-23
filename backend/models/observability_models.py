"""
OBSERVABILITY & TELEMETRY MODELS (models/observability_models.py)
SQLAlchemy ORM models for request tracing, runtime performance tracking,
prompt hash versioning, and token cost telemetry auditing.
"""

# --- SECTION 1: Dependencies & Base Imports ---
# Imports ORM column types, date functions, and declarative base for observability tables.
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, Text, Numeric, JSON
from sqlalchemy.sql import func
from database import Base

# --- SECTION 2: Prompt Hash & Request Tracing Entities ---
# Defines schema for versioned prompt templates and end-to-end telemetry trace records.
class ObservabilityPrompt(Base):
    __tablename__ = "apex_observability_prompts"

    prompt_hash = Column(String(64), primary_key=True)
    prompt_version = Column(String(50), nullable=False)
    prompt_template = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ObservabilityTrace(Base):
    __tablename__ = "apex_observability_traces"

    id = Column(String(36), primary_key=True, server_default=func.now())  # UUID string fallback
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    request_id = Column(String(64), nullable=False)
    session_id = Column(String(255), nullable=False)
    user_id = Column(Integer, nullable=False)
    workspace_id = Column(Integer, nullable=False)
    correlation_id = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_query = Column(Text, nullable=False)
    final_response = Column(Text, nullable=True)
    
    # Performance Metrics
    total_runtime_ms = Column(Integer, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    model_name = Column(String(100), nullable=False)
    calculated_cost_usd = Column(Numeric(10, 6), default=0.000000)
    
    # Decisions, Filters, and Confidence Metrics
    selected_intent = Column(String(100), nullable=False, index=True)
    planner_confidence = Column(String(20), nullable=False)
    extracted_entities = Column(JSON, default={})  # fallback to JSON/JSONB depending on driver
    applied_filters = Column(JSON, default={})
    reasoning_confidence_pct = Column(Integer, default=0)
    
    # Validation, Grounding & Quality Scores
    validation_passed = Column(Boolean, default=True)
    validation_error = Column(Text, nullable=True)
    grounding_score = Column(String(10), default="HIGH")  # Categorized grounding (HIGH/MEDIUM/LOW)
    reflection_triggered = Column(Boolean, default=False)
    
    # Environment & Git Versions
    backend_git_commit = Column(String(40), nullable=False)
    reasoning_engine_version = Column(String(50), nullable=False)


class ObservabilitySpan(Base):
    __tablename__ = "apex_observability_spans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(64), ForeignKey("apex_observability_traces.trace_id", ondelete="CASCADE"), nullable=False, index=True)
    stage_name = Column(String(50), nullable=False) # 'PLANNER', 'RETRIEVER', 'REASONER', 'NARRATOR', 'VALIDATION'
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=False)


class ObservabilityPayload(Base):
    __tablename__ = "apex_observability_payloads"

    trace_id = Column(String(64), ForeignKey("apex_observability_traces.trace_id", ondelete="CASCADE"), primary_key=True)
    planner_prompt_hash = Column(String(64), ForeignKey("apex_observability_prompts.prompt_hash"), nullable=True)
    reasoner_prompt_hash = Column(String(64), ForeignKey("apex_observability_prompts.prompt_hash"), nullable=True)
    narrator_prompt_hash = Column(String(64), ForeignKey("apex_observability_prompts.prompt_hash"), nullable=True)
    
    planner_output = Column(Text, nullable=True)
    retrieved_context_summary = Column(Text, nullable=True)
    retrieved_record_ids = Column(JSON, default={})  # Raw IDs for deterministic replay
    reasoning_package = Column(JSON, default={})  # Output of Reasoning Engine


class ObservabilityBusinessMetric(Base):
    __tablename__ = "apex_observability_business_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(64), ForeignKey("apex_observability_traces.trace_id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, nullable=False)
    action_type = Column(String(100), nullable=False, index=True)
    time_saved_est_sec = Column(Integer, default=0)
    action_metadata = Column(JSON, default={})
