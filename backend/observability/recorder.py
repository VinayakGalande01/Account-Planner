"""
TELEMETRY RECORDER ENGINE (recorder.py)
Implements SQL Storage Telemetry recorders, registering hash templates,
traces, and telemetry metrics directly on the database.
"""

# --- SECTION 1: Dependencies & ORM Telemetry Models ---
# Imports ORM models representing traces, prompts, spans, and metrics.
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from decimal import Decimal

from models.observability_models import (
    ObservabilityPrompt,
    ObservabilityTrace,
    ObservabilitySpan,
    ObservabilityPayload,
    ObservabilityBusinessMetric
)
from database import SessionLocal

logger = logging.getLogger("observability")


def _as_text(value: Any) -> Optional[str]:
    """Text columns: store dicts/lists (e.g. the reasoning plan) as JSON text."""
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _as_json(value: Any) -> Any:
    """JSON columns: drop anything json can't encode (dates, model objects) to strings."""
    return json.loads(json.dumps(value, default=str))

# --- SECTION 2: Telemetry Recorder Interfaces & SQL Implementation ---
# Defines base record methods and SQL persistence implementations.
class TelemetryRecorderInterface(ABC):
    """Abstract interface for decoupling telemetry emission from the storage engine."""
    
    @abstractmethod
    def register_prompt(self, template: str, version: str) -> str:
        """Saves prompt template and returns its SHA256 hash."""
        pass
        
    @abstractmethod
    def record_trace(self, trace_data: Dict[str, Any]) -> None:
        """Saves overall request lifecycle metrics, confidence scores, and intents."""
        pass
        
    @abstractmethod
    def record_spans(self, span_records: List[Dict[str, Any]]) -> None:
        """Saves a batch of stage execution spans (Planner, Reasoner, etc.)."""
        pass
        
    @abstractmethod
    def record_payload(self, payload_data: Dict[str, Any]) -> None:
        """Saves prompt hashes, inputs, context snapshots, and reasoning matrices."""
        pass
        
    @abstractmethod
    def record_business_metric(self, metric_data: Dict[str, Any]) -> None:
        """Records product-specific metrics (e.g. recommendation acceptance)."""
        pass


class PostgreSQLTelemetryRecorder(TelemetryRecorderInterface):
    """PostgreSQL storage adapter implementation for TelemetryRecorderInterface."""

    def _hash_prompt(self, template: str) -> str:
        return hashlib.sha256(template.encode("utf-8")).hexdigest()

    def register_prompt(self, template: str, version: str) -> str:
        prompt_hash = self._hash_prompt(template)
        db: Session = SessionLocal()
        db.info["user_id"] = "1"  # System operation context
        try:
            # Check if prompt hash already exists to prevent duplicate writes
            existing = db.query(ObservabilityPrompt).filter(ObservabilityPrompt.prompt_hash == prompt_hash).first()
            if not existing:
                prompt_obj = ObservabilityPrompt(
                    prompt_hash=prompt_hash,
                    prompt_version=version,
                    prompt_template=template
                )
                db.add(prompt_obj)
                db.commit()
            return prompt_hash
        except Exception as e:
            logger.error(f"[TelemetryRecorder] Failed to register prompt: {e}")
            db.rollback()
            return prompt_hash
        finally:
            db.close()

    def record_trace(self, trace_data: Dict[str, Any]) -> None:
        db: Session = SessionLocal()
        db.info["user_id"] = str(trace_data.get("user_id", "1"))
        try:
            # PII Sanitization
            query_sanitized = self._sanitize_pii(trace_data.get("user_query", ""))
            response_sanitized = self._sanitize_pii(trace_data.get("final_response", ""))
            
            trace = ObservabilityTrace(
                trace_id=trace_data["trace_id"],
                request_id=trace_data["request_id"],
                session_id=trace_data["session_id"],
                user_id=trace_data["user_id"],
                workspace_id=trace_data["workspace_id"],
                correlation_id=trace_data.get("correlation_id"),
                user_query=query_sanitized,
                final_response=response_sanitized,
                
                total_runtime_ms=trace_data["total_runtime_ms"],
                prompt_tokens=trace_data.get("prompt_tokens", 0),
                completion_tokens=trace_data.get("completion_tokens", 0),
                model_name=trace_data["model_name"],
                calculated_cost_usd=Decimal(str(trace_data.get("calculated_cost_usd", 0.0))),
                
                selected_intent=trace_data["selected_intent"],
                planner_confidence=trace_data["planner_confidence"],
                extracted_entities=trace_data.get("extracted_entities", {}),
                applied_filters=trace_data.get("applied_filters", {}),
                reasoning_confidence_pct=trace_data.get("reasoning_confidence_pct", 0),
                
                validation_passed=trace_data.get("validation_passed", True),
                validation_error=trace_data.get("validation_error"),
                grounding_score=trace_data.get("grounding_score", "HIGH"),
                reflection_triggered=trace_data.get("reflection_triggered", False),
                
                backend_git_commit=trace_data.get("backend_git_commit", "unknown"),
                reasoning_engine_version=trace_data.get("reasoning_engine_version", "1.0.0")
            )
            db.add(trace)
            db.commit()
        except Exception as e:
            logger.error(f"[TelemetryRecorder] Failed to record trace: {e}")
            db.rollback()
        finally:
            db.close()

    def record_spans(self, span_records: List[Dict[str, Any]]) -> None:
        db: Session = SessionLocal()
        db.info["user_id"] = "1"  # System context for span mapping
        try:
            spans = []
            for record in span_records:
                span = ObservabilitySpan(
                    trace_id=record["trace_id"],
                    stage_name=record["stage_name"],
                    start_time=record["start_time"],
                    end_time=record["end_time"],
                    duration_ms=record["duration_ms"]
                )
                spans.append(span)
            db.bulk_save_objects(spans)
            db.commit()
        except Exception as e:
            logger.error(f"[TelemetryRecorder] Failed to record spans: {e}")
            db.rollback()
        finally:
            db.close()

    def record_payload(self, payload_data: Dict[str, Any]) -> None:
        db: Session = SessionLocal()
        db.info["user_id"] = "1"  # System context for payload mapping
        try:
            # Extract and sanitize summary PII
            summary_sanitized = self._sanitize_pii(payload_data.get("retrieved_context_summary", ""))
            
            payload = ObservabilityPayload(
                trace_id=payload_data["trace_id"],
                planner_prompt_hash=payload_data.get("planner_prompt_hash"),
                reasoner_prompt_hash=payload_data.get("reasoner_prompt_hash"),
                narrator_prompt_hash=payload_data.get("narrator_prompt_hash"),
                planner_output=_as_text(payload_data.get("planner_output")),
                retrieved_context_summary=summary_sanitized,
                retrieved_record_ids=_as_json(payload_data.get("retrieved_record_ids", {})),
                reasoning_package=_as_json(payload_data.get("reasoning_package", {}))
            )
            db.add(payload)
            db.commit()
        except Exception as e:
            logger.error(f"[TelemetryRecorder] Failed to record payload: {e}")
            db.rollback()
        finally:
            db.close()

    def record_business_metric(self, metric_data: Dict[str, Any]) -> None:
        db: Session = SessionLocal()
        db.info["user_id"] = str(metric_data.get("user_id", "1"))
        try:
            metric = ObservabilityBusinessMetric(
                trace_id=metric_data.get("trace_id"),
                user_id=metric_data["user_id"],
                action_type=metric_data["action_type"],
                time_saved_est_sec=metric_data.get("time_saved_est_sec", 0),
                action_metadata=metric_data.get("metadata", {})
            )
            db.add(metric)
            db.commit()
        except Exception as e:
            logger.error(f"[TelemetryRecorder] Failed to record business metric: {e}")
            db.rollback()
        finally:
            db.close()

    def _sanitize_pii(self, text: str) -> str:
        """Lightweight PII scrub utility for names, phone numbers, and emails."""
        if not text:
            return ""
        import re
        # Scrub email
        scrubbed = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
        # Scrub standard US phone pattern
        scrubbed = re.sub(r'\b(?:\+?1[-.●?]?)?\(?([0-9]{3})\)?[-.●?]?([0-9]{3})[-.●?]?([0-9]{4})\b', '[REDACTED_PHONE]', scrubbed)
        return scrubbed


# Global singleton adapter for the application
_default_recorder: TelemetryRecorderInterface = PostgreSQLTelemetryRecorder()

def get_telemetry_recorder() -> TelemetryRecorderInterface:
    return _default_recorder
