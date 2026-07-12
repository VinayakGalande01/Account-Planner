import time
import logging
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.background import BackgroundTasks

from observability.context import initialize_trace_context, trace_id_var, request_id_var
from observability.recorder import get_telemetry_recorder
from observability.tracking import get_git_revision_hash

logger = logging.getLogger("observability")

class TelemetryTracingMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware to propagate trace propagation context and record execution stats."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Skip assets, system health, and non-API calls
        if not request.url.path.startswith("/api"):
            return await call_next(request)
            
        # 2. Extract correlation context headers
        session_id = request.headers.get("x-session-id", "default_session")
        correlation_id = request.headers.get("x-correlation-id", "")
        
        # User details extraction (Defensive default)
        user_id = 1
        workspace_id = 1
        
        # Extract from FastAPI request state ifauth has run previously
        # Note: Middleware runs before route path executes, so we look at authorization headers directly if needed
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # Decipher user id from token (optional optimization, otherwise default user ID is tracked)
                pass
            except Exception:
                pass
                
        # 3. Generate Trace and Request IDs
        trace_id, request_id = initialize_trace_context(
            session_id=session_id,
            user_id=user_id,
            workspace_id=workspace_id,
            correlation_id=correlation_id
        )
        
        start_time = time.time()
        
        # 4. Inject traceparent header for client propagation
        # W3C Trace Parent: 00-{trace_id_hex}-{span_id_hex}-01
        traceparent = f"00-{trace_id.replace('tr_', '').ljust(32, '0')}-00f067aa0ba902b7-01"
        
        logger.info(f"[TelemetryTracingMiddleware] Request Started. Trace ID: {trace_id}")
        
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            if response:
                response.headers["X-Trace-ID"] = trace_id
                response.headers["traceparent"] = traceparent
            
            logger.info(f"[TelemetryTracingMiddleware] Request Completed. Trace ID: {trace_id} | Duration: {duration_ms}ms")
