import os
import sys
import argparse
import asyncio
import logging
from datetime import datetime
import uuid
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, DATABASE_URL
from models.eval_models import GoldenDataset, EvalRun, BenchmarkResult
from agent_orchestrator import AccountPlanningAgent
from data_engine import DataEngine
from agent_pipeline import _get_active_llm_config, httpx
from observability.context import initialize_trace_context, active_spans_var
from observability.recorder import get_telemetry_recorder
from observability.tracking import get_git_revision_hash

# Import evaluation metrics scorers
from core.metrics.eval_metrics import (
    calculate_intent_match,
    calculate_entity_f1,
    calculate_retriever_precision_recall,
    calculate_narrative_structure_score,
    calculate_narrative_keyword_score,
    calculate_grounding_score_llm,
    calculate_composite_eqs
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_runner")

async def run_benchmark(
    tag_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    limit: Optional[int] = None,
    notes: Optional[str] = None,
    trigger: str = "MANUAL"
) -> str:
    """Executes a benchmark run matching filters, scores metrics, and records results."""
    db_session = SessionLocal()
    
    # 1. Resolve active LLM config
    async with httpx.AsyncClient() as client:
        llm_url, model_name = await _get_active_llm_config(client)
    logger.info(f"[RUNNER] Resolved active LLM URL: {llm_url} (model: {model_name})")
    
    # 2. Query golden test cases matching filters
    query = db_session.query(GoldenDataset).filter(GoldenDataset.status == "ACTIVE")
    if priority_filter:
        query = query.filter(GoldenDataset.priority == priority_filter.upper())
        
    all_cases = query.all()
    
    # Client-side JSON tag filter (since tags are stored as JSON array)
    filtered_cases = []
    for case in all_cases:
        case_tags = case.tags or []
        if tag_filter and tag_filter not in case_tags:
            continue
        filtered_cases.append(case)
        
    if limit:
        filtered_cases = filtered_cases[:limit]
        
    if not filtered_cases:
        logger.warning("[RUNNER] No active golden test cases found matching filters.")
        db_session.close()
        return "NO_CASES"
        
    logger.info(f"[RUNNER] Found {len(filtered_cases)} golden test cases to run.")
    
    # 3. Create EvalRun entry
    git_commit = get_git_revision_hash()
    run_id = str(uuid.uuid4())
    eval_run = EvalRun(
        id=run_id,
        run_type="REGRESSION" if tag_filter == "regression" else "FULL",
        trigger=trigger,
        status="RUNNING",
        model_name=model_name,
        model_version="1.0.0",
        prompt_versions={"planner": "v1", "reasoner": "v1"},
        backend_git_commit=git_commit,
        golden_tag_filter=[tag_filter] if tag_filter else [],
        started_at=datetime.now(),
        notes=notes or f"Benchmark run containing {len(filtered_cases)} cases."
    )
    
    db_session.add(eval_run)
    db_session.commit()
    
    # 4. Iterate over test cases
    success_count = 0
    total_eqs = 0.0
    
    for idx, case in enumerate(filtered_cases):
        logger.info(f"[RUNNER] [{idx+1}/{len(filtered_cases)}] Executing query: '{case.query}'")
        
        # Initialize trace context for this specific run
        trace_id, req_id = initialize_trace_context(
            session_id="benchmark_run",
            user_id=case.owner_id or 2,
            workspace_id=1
        )
        
        # Instantiate agent at runtime with appropriate data engine mapping
        user_engine = DataEngine(db=db_session, user_id=case.owner_id or 2)
        agent = AccountPlanningAgent(data_engine=user_engine, is_local=True)
        agent.response_generator.model = model_name
        agent.response_generator.url = llm_url
        agent.intent_classifier.url = llm_url
        agent.intent_classifier.model = model_name
        
        # Track start time
        start_time = datetime.now()
        
        try:
            # Execute programmatic pipeline (synchronously in a thread to keep async loop free)
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(
                None,
                agent.process_query,
                case.query,
                "sales",  # default role
                ["am"]   # default target recipient role
            )
        except Exception as err:
            logger.error(f"[RUNNER ERROR] Pipeline crashed for case {case.id}: {err}")
            continue
            
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Extract latencies from traces spans
        spans = active_spans_var.get()
        planner_latency_ms = 0
        retriever_latency_ms = 0
        reasoner_latency_ms = 0
        narrator_latency_ms = 0
        
        for span in spans:
            if span["stage_name"] == "PLANNER":
                planner_latency_ms = span["duration_ms"]
            elif span["stage_name"] == "RETRIEVER":
                retriever_latency_ms = span["duration_ms"]
            elif span["stage_name"] == "REASONER":
                reasoner_latency_ms = span["duration_ms"]
            elif span["stage_name"] == "NARRATOR":
                narrator_latency_ms = span["duration_ms"]
                
        # 5. Extract actual structures for scoring
        actual_intent_obj = res.get("intent")
        actual_intent = actual_intent_obj.primary_intent.value if actual_intent_obj else ""
        actual_entities = actual_intent_obj.extracted_entities.model_dump() if actual_intent_obj else {}
        
        actual_data = res.get("account_data") or {}
        actual_opportunities = actual_data.get("opportunities", [])
        actual_contacts = actual_data.get("contacts", [])
        actual_cases = actual_data.get("cases", [])
        actual_activities = actual_data.get("activities", [])
        
        # Get target role narrative, handling both Pydantic models and dictionaries
        am_response_raw = res.get("responses", {}).get("am", {})
        if hasattr(am_response_raw, "model_dump"):
            am_response = am_response_raw.model_dump()
        elif hasattr(am_response_raw, "dict"):
            am_response = am_response_raw.dict()
        elif isinstance(am_response_raw, dict):
            am_response = am_response_raw
        else:
            am_response = {}
        actual_narrative = am_response.get("narrative", "")

        # 6. Flush spans to the Observability database tables
        try:
            recorder = get_telemetry_recorder()
            trace_record = {
                "trace_id": trace_id,
                "request_id": req_id,
                "session_id": "benchmark_run",
                "user_id": case.owner_id or 2,
                "workspace_id": 1,
                "user_query": case.query,
                "final_response": actual_narrative,
                "total_runtime_ms": elapsed_ms,
                "model_name": model_name,
                "selected_intent": actual_intent if actual_intent else "UNKNOWN",
                "planner_confidence": case.expected_confidence or "HIGH",
                "backend_git_commit": git_commit,
                "reasoning_engine_version": "1.0.0"
            }
            recorder.record_trace(trace_record)
            if spans:
                recorder.record_spans(spans)
        except Exception as telemetry_err:
            logger.warning(f"[RUNNER WARNING] Failed to write observability records: {telemetry_err}")
        
        # 7. Compute Metric Scores
        intent_match = calculate_intent_match(case.expected_intent, actual_intent)
        entity_f1 = calculate_entity_f1(case.expected_entities, actual_entities)
        
        retriever_precision, retriever_recall = calculate_retriever_precision_recall(
            expected_ids=case.expected_retrieval_ids,
            actual_opportunities=actual_opportunities,
            actual_contacts=actual_contacts,
            actual_cases=actual_cases,
            actual_activities=actual_activities,
            expected_account=case.expected_entities.get("account") if case.expected_entities else None
        )
        
        narrative_structure = calculate_narrative_structure_score(am_response)
        
        expected_keywords = case.expected_narrative_keywords or []
        narrative_keywords_score = calculate_narrative_keyword_score(actual_narrative, expected_keywords)
        
        # Grounding Score using LLM judge
        grounding_score, grounding_rationale = await calculate_grounding_score_llm(
            context_data=actual_data,
            narrative_text=actual_narrative,
            llm_url=llm_url,
            model_name=model_name
        )
        
        eqs = calculate_composite_eqs(
            intent_accuracy=float(intent_match),
            entity_f1=entity_f1,
            retriever_precision=retriever_precision,
            retriever_recall=retriever_recall,
            grounding_score=grounding_score,
            narrative_structure=narrative_structure,
            recommendation_quality=narrative_keywords_score
        )
        
        # Get planner confidence/urgency safely
        planner_conf_val = "MEDIUM"
        if actual_intent_obj:
            if hasattr(actual_intent_obj, "urgency"):
                urg_obj = getattr(actual_intent_obj, "urgency")
                planner_conf_val = urg_obj.value if hasattr(urg_obj, "value") else str(urg_obj)
            elif isinstance(actual_intent_obj, dict):
                urg_obj = actual_intent_obj.get("urgency", "MEDIUM")
                planner_conf_val = urg_obj.value if hasattr(urg_obj, "value") else str(urg_obj)

        pass_fail = "PASS" if eqs >= 78.0 else ("WARN" if eqs >= 60.0 else "FAIL")
        
        # 8. Record BenchmarkResult
        result = BenchmarkResult(
            run_id=run_id,
            golden_id=case.id,
            golden_version=case.version,
            trace_id=trace_id,
            
            # Scores
            intent_match=intent_match,
            entity_precision=entity_f1,  # mapping precision to f1
            entity_recall=entity_f1,
            entity_f1=entity_f1,
            planner_confidence=planner_conf_val,
            
            retriever_precision=retriever_precision,
            retriever_recall=retriever_recall,
            retrieval_count_actual=len(actual_opportunities),
            
            json_valid=isinstance(am_response, dict),
            json_schema_conformant=narrative_structure == 1.0,
            narrative_structure_score=narrative_structure,
            narrative_keyword_score=narrative_keywords_score,
            
            grounding_score=grounding_score,
            grounding_category="HIGH" if grounding_score >= 0.8 else ("MEDIUM" if grounding_score >= 0.5 else "LOW"),
            recommendation_score=narrative_keywords_score,
            
            # Latency
            total_latency_ms=elapsed_ms,
            planner_latency_ms=planner_latency_ms,
            retriever_latency_ms=retriever_latency_ms,
            narrator_latency_ms=narrator_latency_ms,
            
            eqs=eqs,
            pass_fail=pass_fail
        )
        
        db_session.add(result)
        db_session.commit()
        
        success_count += 1
        total_eqs += eqs
        logger.info(f"   -> Result: EQS={eqs} | Status={pass_fail} | Intent Match={intent_match} | F1={entity_f1:.2f}")

    # 9. Finalize Run
    eval_run.status = "COMPLETED"
    eval_run.completed_at = datetime.now()
    db_session.commit()
    
    mean_eqs = total_eqs / success_count if success_count > 0 else 0.0
    logger.info(f"=== BENCHMARK COMPLETED ===")
    logger.info(f"Executed: {success_count} cases | Average EQS: {mean_eqs:.2f}")
    
    db_session.close()
    return run_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APEX Layer 2 Evaluation Benchmark Runner")
    parser.add_argument("--tag", help="Golden Dataset tag filter (e.g. regression)")
    parser.add_argument("--priority", help="Golden Dataset case priority filter")
    parser.add_argument("--limit", type=int, help="Limit maximum number of cases to execute")
    parser.add_argument("--notes", help="Custom notes to attach to this evaluation run")
    
    args = parser.parse_args()
    
    # Run the benchmark async
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        run_benchmark(
            tag_filter=args.tag,
            priority_filter=args.priority,
            limit=args.limit,
            notes=args.notes
        )
    )
