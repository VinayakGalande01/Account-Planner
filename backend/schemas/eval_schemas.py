from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class GoldenDatasetBase(BaseModel):
    query: str
    user_context: Optional[Dict[str, Any]] = {}
    expected_intent: str
    expected_entities: Optional[Dict[str, Any]] = {}
    expected_confidence: Optional[str] = "HIGH"
    expected_retrieval_ids: Optional[Dict[str, Any]] = {}
    expected_retrieval_count: Optional[int] = None
    expected_filter_keys: Optional[Dict[str, Any]] = {}
    expected_reasoning_confidence_min: Optional[int] = 60
    expected_key_findings: Optional[Dict[str, Any]] = {}
    expected_json_schema: Optional[Dict[str, Any]] = {}
    expected_narrative_keywords: Optional[List[str]] = []
    expected_recommendation_type: Optional[str] = None
    expected_business_outcome: Optional[str] = None
    expected_bis_category: Optional[str] = None
    status: Optional[str] = "ACTIVE"
    source: Optional[str] = "MANUAL"
    priority: Optional[str] = "MEDIUM"
    tags: Optional[List[str]] = []
    review_notes: Optional[str] = None

class GoldenDatasetCreate(GoldenDatasetBase):
    pass

class GoldenDatasetUpdate(BaseModel):
    query: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    expected_intent: Optional[str] = None
    expected_entities: Optional[Dict[str, Any]] = None
    expected_confidence: Optional[str] = None
    expected_retrieval_ids: Optional[Dict[str, Any]] = None
    expected_retrieval_count: Optional[int] = None
    expected_filter_keys: Optional[Dict[str, Any]] = None
    expected_reasoning_confidence_min: Optional[int] = None
    expected_key_findings: Optional[Dict[str, Any]] = None
    expected_json_schema: Optional[Dict[str, Any]] = None
    expected_narrative_keywords: Optional[List[str]] = None
    expected_recommendation_type: Optional[str] = None
    expected_business_outcome: Optional[str] = None
    expected_bis_category: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    review_notes: Optional[str] = None

class GoldenDatasetResponse(GoldenDatasetBase):
    id: str
    version: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
