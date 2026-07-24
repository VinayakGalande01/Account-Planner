"""
TELEMETRY CONTEXT VARIABLES (context.py)
Declares thread-local and async ContextVar primitives mapping active requests,
user identifiers, session histories, and span logs.
"""

# --- SECTION 1: Dependencies & ContextVars Declarations ---
# Imports ContextVar handlers, UUID markers, and declares trace variables.
import contextvars
import uuid
import time

trace_id_var = contextvars.ContextVar("trace_id", default="")
request_id_var = contextvars.ContextVar("request_id", default="")
span_id_var = contextvars.ContextVar("span_id", default="")
session_id_var = contextvars.ContextVar("session_id", default="")
user_id_var = contextvars.ContextVar("user_id", default=0)
workspace_id_var = contextvars.ContextVar("workspace_id", default=0)
correlation_id_var = contextvars.ContextVar("correlation_id", default="")

active_spans_var = contextvars.ContextVar("active_spans", default=[])

# --- SECTION 2: Trace Context Initialization Routine ---
# Instantiates unique trace IDs and binds parameters to task contexts.
def initialize_trace_context(session_id: str = "default_session", user_id: int = 1, workspace_id: int = 1, correlation_id: str = ""):
    """Generates identifiers and initializes tracing context variables."""
    trace_id = f"tr_{uuid.uuid4().hex[:12]}"
    req_id = f"req_{uuid.uuid4().hex[:12]}"
    
    trace_id_var.set(trace_id)
    request_id_var.set(req_id)
    session_id_var.set(session_id)
    user_id_var.set(user_id)
    workspace_id_var.set(workspace_id)
    correlation_id_var.set(correlation_id)
    span_id_var.set("")
    active_spans_var.set([])
    return trace_id, req_id
