import pytest
import httpx
from database import SessionLocal
from main import app
from models.eval_models import GoldenDataset
from auth.dependencies import get_current_user
from models.user import User

# Mock the dependency to bypass auth verification for tests
def mock_get_current_user():
    return User(id=1, name="Default Admin", email="admin@apex.com")

app.dependency_overrides[get_current_user] = mock_get_current_user

@pytest.fixture
def anyio_backend():
    return "asyncio"

def test_golden_dataset_tables_exist():
    db = SessionLocal()
    try:
        # Check if golden dataset table exists by querying it
        cases = db.query(GoldenDataset).limit(1).all()
        assert isinstance(cases, list)
    finally:
        db.close()

@pytest.mark.anyio
async def test_golden_dataset_crud(anyio_backend):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        
        # 1. CREATE
        new_case_payload = {
            "query": "Test query for upsell opportunity",
            "expected_intent": "opportunity_expansion",
            "expected_entities": {"account": "Wipro"},
            "expected_confidence": "HIGH",
            "priority": "HIGH",
            "tags": ["test", "upsell"],
            "expected_recommendation_type": "GROWTH_STRATEGY"
        }
        
        create_response = await client.post(
            "/api/eval/golden",
            json=new_case_payload
        )
        assert create_response.status_code == 201
        created_case = create_response.json()
        assert created_case["query"] == new_case_payload["query"]
        assert created_case["expected_intent"] == new_case_payload["expected_intent"]
        assert created_case["version"] == 1
        case_id = created_case["id"]
        
        # 2. READ (SINGLE)
        get_response = await client.get(f"/api/eval/golden/{case_id}")
        assert get_response.status_code == 200
        fetched_case = get_response.json()
        assert fetched_case["id"] == case_id
        assert fetched_case["query"] == new_case_payload["query"]
        
        # 3. LIST
        list_response = await client.get("/api/eval/golden")
        assert list_response.status_code == 200
        cases_list = list_response.json()
        assert len(cases_list) >= 1
        assert any(c["id"] == case_id for c in cases_list)
        
        # 4. UPDATE (and check version increment)
        update_payload = {
            "query": "Updated test query for Wipro upsell",
            "priority": "CRITICAL"
        }
        update_response = await client.put(
            f"/api/eval/golden/{case_id}",
            json=update_payload
        )
        assert update_response.status_code == 200
        updated_case = update_response.json()
        assert updated_case["query"] == update_payload["query"]
        assert updated_case["priority"] == update_payload["priority"]
        assert updated_case["version"] == 2  # Incremented from 1
        
        # 5. DELETE (ARCHIVE)
        delete_response = await client.delete(f"/api/eval/golden/{case_id}")
        assert delete_response.status_code == 200
        assert "archived" in delete_response.json()["detail"]
        
        # Verify status is now DEPRECATED and version is incremented
        get_archived_response = await client.get(f"/api/eval/golden/{case_id}")
        assert get_archived_response.status_code == 200
        archived_case = get_archived_response.json()
        assert archived_case["status"] == "DEPRECATED"
        assert archived_case["version"] == 3  # Incremented from 2
        
        # 6. HARD DELETE
        hard_delete_response = await client.delete(f"/api/eval/golden/{case_id}?hard_delete=true")
        assert hard_delete_response.status_code == 200
        assert "deleted successfully" in hard_delete_response.json()["detail"]
        
        # Verify it no longer exists
        get_deleted_response = await client.get(f"/api/eval/golden/{case_id}")
        assert get_deleted_response.status_code == 404
