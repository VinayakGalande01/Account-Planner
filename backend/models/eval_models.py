"""
EVALUATION DATA MODELS (models/eval_models.py)
SQLAlchemy ORM models for AI evaluation pipelines: Golden Datasets,
Evaluation Test Runs, Phase Assertions, and Metric Tracking tables.
"""

# --- SECTION 1: Dependencies & Model Declarations ---
# Imports column types, UUID utilities, and declarative base for evaluation schemas.
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Numeric, JSON
from sqlalchemy.sql import func
from database import Base
import uuid

# --- SECTION 2: Golden Dataset & Test Benchmark Entities ---
# Schema for storing ground-truth expected outputs across all 4 AI pipeline phases.
class GoldenDataset(Base):
    __tablename__ = "eval_golden_dataset"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="ACTIVE")
    source = Column(String(30), nullable=False, default="MANUAL")
    priority = Column(String(10), nullable=False, default="MEDIUM")
    tags = Column(JSON, default=list)  # Stored as JSON array to be SQLite compatible
    owner_id = Column(Integer, nullable=False)

    # Input
    query = Column(Text, nullable=False)
    user_context = Column(JSON, default=dict)

    # Expected Planner Output (Phase 1)
    expected_intent = Column(String(100), nullable=False)
    expected_entities = Column(JSON, default=dict)
    expected_confidence = Column(String(10), default="HIGH")

    # Expected Retriever Output (Phase 2)
    expected_retrieval_ids = Column(JSON, default=dict)
    expected_retrieval_count = Column(Integer, nullable=True)
    expected_filter_keys = Column(JSON, default=dict)

    # Expected Reasoner Output (Phase 3)
    expected_reasoning_confidence_min = Column(Integer, default=60)
    expected_key_findings = Column(JSON, default=dict)

    # Expected Narrator Output (Phase 4)
    expected_json_schema = Column(JSON, default=dict)
    expected_narrative_keywords = Column(JSON, default=list)  # Stored as JSON list
    expected_recommendation_type = Column(String(100), nullable=True)

    # Business expectations
    expected_business_outcome = Column(String(100), nullable=True)
    expected_bis_category = Column(String(20), nullable=True)

    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_type = Column(String(30), nullable=False)  # REGRESSION | FULL | PROMPT_COMPARE | MODEL_COMPARE | SINGLE
    trigger = Column(String(20), nullable=False)  # MANUAL | CI | SCHEDULED | DEVELOPER
    status = Column(String(20), nullable=False, default="PENDING")
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    prompt_versions = Column(JSON, default=dict)  # e.g., {"planner": "v3", "reasoner": "v2"}
    backend_git_commit = Column(String(40), nullable=True)
    golden_tag_filter = Column(JSON, default=list)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)


class BenchmarkResult(Base):
    __tablename__ = "eval_benchmark_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False)
    golden_id = Column(String(36), ForeignKey("eval_golden_dataset.id", ondelete="CASCADE"), nullable=False)
    golden_version = Column(Integer, nullable=False)
    trace_id = Column(String(64), nullable=True)

    # Planner Metrics
    intent_match = Column(Boolean, nullable=True)
    entity_precision = Column(Numeric(5, 4), nullable=True)
    entity_recall = Column(Numeric(5, 4), nullable=True)
    entity_f1 = Column(Numeric(5, 4), nullable=True)
    planner_confidence = Column(String(10), nullable=True)

    # Retriever Metrics
    retriever_precision = Column(Numeric(5, 4), nullable=True)
    retriever_recall = Column(Numeric(5, 4), nullable=True)
    retrieval_count_actual = Column(Integer, nullable=True)

    # Narrator Metrics
    json_valid = Column(Boolean, nullable=True)
    json_schema_conformant = Column(Boolean, nullable=True)
    narrative_structure_score = Column(Numeric(5, 4), nullable=True)
    narrative_keyword_score = Column(Numeric(5, 4), nullable=True)

    # Quality Metrics (LLM-as-judge)
    grounding_score = Column(Numeric(5, 4), nullable=True)
    grounding_category = Column(String(10), nullable=True)
    recommendation_score = Column(Numeric(5, 4), nullable=True)

    # Performance Metrics
    total_latency_ms = Column(Integer, nullable=True)
    planner_latency_ms = Column(Integer, nullable=True)
    retriever_latency_ms = Column(Integer, nullable=True)
    narrator_latency_ms = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)

    # Composite
    eqs = Column(Numeric(5, 2), nullable=True)
    pass_fail = Column(String(10), nullable=True)  # PASS | WARN | FAIL

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HumanReview(Base):
    __tablename__ = "eval_human_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    benchmark_result_id = Column(String(36), ForeignKey("eval_benchmark_results.id", ondelete="CASCADE"), nullable=True)
    trace_id = Column(String(64), nullable=True)
    reviewer_id = Column(Integer, nullable=False)
    review_type = Column(String(20), default="BENCHMARK")  # BENCHMARK | PRODUCTION | CALIBRATION

    accuracy_score = Column(Integer, nullable=False)
    business_usefulness = Column(Integer, nullable=False)
    trust_score = Column(Integer, nullable=False)
    readability_score = Column(Integer, nullable=False)
    actionability_score = Column(Integer, nullable=False)
    recommendation_quality = Column(Integer, nullable=False)
    overall_satisfaction = Column(Integer, nullable=False)

    notes = Column(Text, nullable=True)
    flags = Column(JSON, default=list)  # e.g., ["HALLUCINATION"]
    time_spent_seconds = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FailureDatabase(Base):
    __tablename__ = "eval_failure_database"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(String(64), nullable=True)
    golden_id = Column(String(36), ForeignKey("eval_golden_dataset.id", ondelete="SET NULL"), nullable=True)
    source = Column(String(30), nullable=False)  # AUTOMATIC | USER_FEEDBACK | BENCHMARK | HUMAN_REVIEW | MANUAL

    question = Column(Text, nullable=False)
    expected = Column(Text, nullable=True)
    actual = Column(Text, nullable=False)

    root_cause = Column(String(20), nullable=True)  # PLANNER | RETRIEVER | REASONER | NARRATOR | DATA | PROMPT | MODEL | UNKNOWN
    root_cause_detail = Column(Text, nullable=True)
    severity = Column(String(10), nullable=False, default="MEDIUM")  # CRITICAL | HIGH | MEDIUM | LOW

    status = Column(String(20), nullable=False, default="OPEN")  # OPEN | IN_TRIAGE | FIXED | REGRESSION_ADDED
    resolution = Column(Text, nullable=True)
    resolution_commit = Column(String(40), nullable=True)
    resolution_date = Column(DateTime(timezone=True), nullable=True)

    regression_test_id = Column(String(36), ForeignKey("eval_golden_dataset.id", ondelete="SET NULL"), nullable=True)
    owner_id = Column(Integer, nullable=True)
    prevention_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReleaseHistory(Base):
    __tablename__ = "eval_release_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    release_version = Column(String(30), nullable=False)
    backend_git_commit = Column(String(40), nullable=False)
    run_id = Column(String(36), ForeignKey("eval_runs.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False)  # APPROVED | REJECTED | ROLLED_BACK
    eqs_at_release = Column(Numeric(5, 2), nullable=True)
    approved_by = Column(Integer, nullable=True)
    release_notes = Column(Text, nullable=True)
    rollback_reason = Column(Text, nullable=True)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PromptBenchmark(Base):
    __tablename__ = "eval_prompt_benchmarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_phase = Column(String(20), nullable=False)  # PLANNER | REASONER | NARRATOR
    prompt_hashes = Column(JSON, nullable=False)  # {"a": "sha...", "b": "sha..."}
    dataset_ids = Column(JSON, default=list)  # List of UUIDs
    run_ids = Column(JSON, default=dict)  # {"a": "run_uuid", "b": "run_uuid"}
    winner = Column(String(10), nullable=True)  # a | b | c | INCONCLUSIVE
    decision_notes = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ModelBenchmark(Base):
    __tablename__ = "eval_model_benchmarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    models_tested = Column(JSON, default=list)  # List of model names
    prompt_hash = Column(String(64), nullable=True)
    dataset_ids = Column(JSON, default=list)
    run_ids = Column(JSON, default=dict)  # {"llama": "run_uuid", ...}
    winner = Column(String(100), nullable=True)
    decision_notes = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BisRecord(Base):
    __tablename__ = "bis_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(String(64), nullable=True)
    user_id = Column(Integer, nullable=True)
    workspace_id = Column(Integer, nullable=True)
    recommendation_type = Column(String(100), nullable=True)
    signal_events = Column(JSON, default=list)
    weights_version = Column(Integer, nullable=True)
    raw_score = Column(Numeric(5, 2), nullable=True)
    normalized_score = Column(Numeric(5, 2), nullable=True)
    category = Column(String(20), nullable=True)  # VERY_HIGH | HIGH | MEDIUM | LOW | NO_IMPACT | UNKNOWN
    time_saved_est_minutes = Column(Integer, nullable=True)
    revenue_influence_est = Column(Numeric(12, 2), nullable=True)
    calculation_notes = Column(Text, nullable=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BisWeightConfig(Base):
    __tablename__ = "bis_weight_config"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    config = Column(JSON, nullable=False)  # {"DEAL_STAGE_ADVANCED": 0.30, ...}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
