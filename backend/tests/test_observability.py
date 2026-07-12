import pytest
import httpx
from database import SessionLocal
from main import app
from models.observability_models import ObservabilityTrace, ObservabilitySpan
from auth.dependencies import get_current_user
from models.user import User

# Mock the dependency to bypass auth verification for tests
def mock_get_current_user():
    return User(id=1, name="Default Admin", email="admin@apex.com")

app.dependency_overrides[get_current_user] = mock_get_current_user

# Restrict anyio tests to the asyncio loop only (prevents trio ModuleNotFoundError)
@pytest.fixture
def anyio_backend():
    return "asyncio"

def test_observability_endpoint_and_table_initialization():
    # 1. Assert tables are initialized
    db = SessionLocal()
    try:
        # Check if tracing tables exist by querying them
        traces = db.query(ObservabilityTrace).limit(1).all()
        assert isinstance(traces, list)
        
        spans = db.query(ObservabilitySpan).limit(1).all()
        assert isinstance(spans, list)
    finally:
        db.close()

@pytest.mark.anyio
async def test_trace_parent_header_generation(anyio_backend):
    # Configure ASGI transport explicitly to handle requests inside the async test loop
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Send a request with x-test-mock header to verify middleware intercept
        response = await client.post(
            "/api/chat",
            headers={"x-test-mock": "true", "x-session-id": "test_sess_123"},
            json={
                "query": "hello, are you there?",
                "session_id": "test_sess_123"
            }
        )
        assert response.status_code == 200
        
        # Assert trace IDs are returned in response headers
        assert "X-Trace-ID" in response.headers
        assert "traceparent" in response.headers
        assert response.headers["X-Trace-ID"].startswith("tr_")
