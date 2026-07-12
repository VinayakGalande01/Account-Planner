import time
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import contextvars

from observability.context import (
    trace_id_var,
    request_id_var,
    span_id_var,
    session_id_var,
    user_id_var,
    workspace_id_var,
    correlation_id_var,
    active_spans_var
)
from observability.recorder import get_telemetry_recorder

logger = logging.getLogger("observability")

# Global prompt cache registry mapping prompt identifiers to hashes
_registered_prompt_hashes: Dict[str, str] = {}

def get_git_revision_hash() -> str:
    """Retrieves the current Git commit hash from the repository."""
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL).decode('ascii').strip()
    except Exception:
        return "unknown_commit"

def calculate_token_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Heuristic cost calculator per token for common models."""
    model = model_name.lower()
    
    # Cost per 1M tokens
    pricing = {
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
        "llama": {"input": 0.1, "output": 0.2},
        "phi": {"input": 0.05, "output": 0.1}
    }
    
    # Match prefix
    matched_pricing = {"input": 0.0, "output": 0.0} # local Ollama is default free
    for key, price in pricing.items():
        if key in model:
            matched_pricing = price
            break
            
    input_cost = (prompt_tokens / 1_000_000) * matched_pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * matched_pricing["output"]
    return input_cost + output_cost

def classify_grounding(score: int) -> str:
    """Classifies grounding percentage into simple categorical bands (12.6 strategy)."""
    if score >= 90:
        return "HIGH"
    elif score >= 60:
        return "MEDIUM"
    return "LOW"


class TraceSpanContext:
    """Context manager to measure start time, end time, and duration for pipeline stages."""
    
    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.start_time = None
        self.end_time = None
        self.duration_ms = 0
        
    def __enter__(self):
        self.start_time = datetime.now()
        trace_id = trace_id_var.get()
        if trace_id:
            logger.debug(f"[TraceSpanContext] Starting span {self.stage_name} for trace {trace_id}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        
        trace_id = trace_id_var.get()
        if not trace_id:
            return # Telemetry not initialized
            
        span_record = {
            "trace_id": trace_id,
            "stage_name": self.stage_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms
        }
        
        # Track active spans inside task context
        spans = active_spans_var.get()
        spans.append(span_record)
        active_spans_var.set(spans)
        logger.debug(f"[TraceSpanContext] Completed span {self.stage_name} for trace {trace_id} in {self.duration_ms}ms")


def register_prompt_in_registry(prompt_id: str, template: str, version: str) -> str:
    """Registers prompt in database and caches hash for this session (12.2 strategy)."""
    if prompt_id in _registered_prompt_hashes:
        return _registered_prompt_hashes[prompt_id]
        
    recorder = get_telemetry_recorder()
    prompt_hash = recorder.register_prompt(template, version)
    _registered_prompt_hashes[prompt_id] = prompt_hash
    return prompt_hash
