import pytest
import unittest.mock as mock
from datetime import datetime
from database import SessionLocal
from models.eval_models import GoldenDataset, EvalRun, BenchmarkResult
from core.runner import run_benchmark
import httpx

# Mock response generator for Ollama
def mock_httpx_post(url, *args, **kwargs):
    mock_response = mock.Mock()
    mock_response.status_code = 200
    
    json_payload = kwargs.get("json", {})
    prompt = json_payload.get("prompt", "")
    
    if "Auditor" in prompt or "grounding_score" in prompt:
        # Mock LLM-as-judge grounding response
        mock_response.json.return_value = {
            "response": '{\n  "grounding_score": 1.0,\n  "category": "HIGH",\n  "rationale": "Perfect match."\n}'
        }
    elif "Turn 1" in prompt or "DEAL_VELOCITY" in prompt or "Router" in prompt:
        # Mock Router intent classification output
        mock_response.json.return_value = {
            "response": '{"intent": "DEAL_VELOCITY", "complexity": "TACTICAL"}'
        }
    else:
        # Mock Crucible consensus output
        mock_response.json.return_value = {
            "response": '{\n  "executive_brief": {\n    "revenue_at_stake": "$24,363,000.00",\n    "macro_summary": "Test macro summary."\n  },\n  "persona_insights": {\n    "enterprise_ae": " AE contact.",\n    "strategic_director": "No blockers."\n  },\n  "tactical_playbook": [\n    { "day": 1, "action": "Verify ACC017 opportunity.", "owner": "AM", "success_metric": "done" }\n  ]\n}'
        }
    return mock_response


def mock_httpx_get(url, *args, **kwargs):
    mock_response = mock.Mock()
    mock_response.status_code = 200
    return mock_response


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@mock.patch("httpx.Client.post", side_effect=mock_httpx_post)
@mock.patch("httpx.Client.get", side_effect=mock_httpx_get)
@mock.patch("httpx.AsyncClient.post", side_effect=mock_httpx_post)
@mock.patch("httpx.AsyncClient.get", side_effect=mock_httpx_get)
async def test_benchmark_runner_execution(
    mock_async_get, mock_async_post, mock_client_get, mock_client_post, anyio_backend
):
    db_session = SessionLocal()
    
    # 1. CREATE A TEST GOLDEN CASE
    test_case = GoldenDataset(
        query="Test query for Wipro pipeline",
        expected_intent="pipeline_summary",
        expected_entities={"account": "Wipro"},
        expected_confidence="HIGH",
        priority="HIGH",
        tags=["test_runner_subset"],
        expected_narrative_keywords=["wipro", "opportunities"],
        owner_id=2
    )
    
    db_session.add(test_case)
    db_session.commit()
    case_id = test_case.id
    
    try:
        # 2. RUN THE BENCHMARK
        run_id = await run_benchmark(
            tag_filter="test_runner_subset",
            notes="Unit test run validation",
            trigger="DEVELOPER"
        )
        
        # Verify run_id was returned
        assert run_id != "NO_CASES"
        assert isinstance(run_id, str)
        
        # 3. VERIFY EVALRUN RECORD
        eval_run = db_session.query(EvalRun).filter(EvalRun.id == run_id).first()
        assert eval_run is not None
        assert eval_run.status == "COMPLETED"
        assert eval_run.run_type == "FULL"
        assert "test_runner_subset" in eval_run.golden_tag_filter
        
        # 4. VERIFY BENCHMARKRESULT RECORD
        result = db_session.query(BenchmarkResult).filter(BenchmarkResult.run_id == run_id).first()
        assert result is not None
        assert result.golden_id == case_id
        assert result.intent_match is True
        assert float(result.eqs) >= 0.0
        
    finally:
        # 5. CLEAN UP TEST RECORDS
        db_session.query(BenchmarkResult).filter(BenchmarkResult.golden_id == case_id).delete()
        if 'run_id' in locals():
            db_session.query(EvalRun).filter(EvalRun.id == run_id).delete()
        db_session.query(GoldenDataset).filter(GoldenDataset.id == case_id).delete()
        db_session.commit()
        db_session.close()
