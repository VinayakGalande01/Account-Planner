"""
GOLDEN DATASET API (api/golden_dataset.py)
REST endpoints for managing evaluation golden datasets, ground-truth benchmarks,
and automated test expectations for AI reasoning verification.
"""

# --- SECTION 1: Dependencies & Router Initialization ---
# Imports FastAPI router, SQLAlchemy sessions, auth dependencies, and schemas.
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from database import get_db, current_user_id_var
from auth.dependencies import get_current_user
from models.user import User
from models.eval_models import GoldenDataset
from schemas.eval_schemas import GoldenDatasetCreate, GoldenDatasetUpdate, GoldenDatasetResponse

router = APIRouter(prefix="/api/eval/golden", tags=["Golden Dataset"])

def set_db_user_context(db: Session, user_id: int):
    current_user_id_var.set(str(user_id))
    db.info["user_id"] = str(user_id)

# --- SECTION 2: Evaluation Benchmark Endpoints ---
# Endpoints for creating, fetching, updating, and deleting golden dataset test cases.
@router.post("", response_model=GoldenDatasetResponse, status_code=status.HTTP_201_CREATED)
def create_golden_case(
    case_in: GoldenDatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    set_db_user_context(db, current_user.id)
    
    db_case = GoldenDataset(
        query=case_in.query,
        user_context=case_in.user_context,
        expected_intent=case_in.expected_intent,
        expected_entities=case_in.expected_entities,
        expected_confidence=case_in.expected_confidence,
        expected_retrieval_ids=case_in.expected_retrieval_ids,
        expected_retrieval_count=case_in.expected_retrieval_count,
        expected_filter_keys=case_in.expected_filter_keys,
        expected_reasoning_confidence_min=case_in.expected_reasoning_confidence_min,
        expected_key_findings=case_in.expected_key_findings,
        expected_json_schema=case_in.expected_json_schema,
        expected_narrative_keywords=case_in.expected_narrative_keywords,
        expected_recommendation_type=case_in.expected_recommendation_type,
        expected_business_outcome=case_in.expected_business_outcome,
        expected_bis_category=case_in.expected_bis_category,
        status=case_in.status or "ACTIVE",
        source=case_in.source or "MANUAL",
        priority=case_in.priority or "MEDIUM",
        tags=case_in.tags or [],
        review_notes=case_in.review_notes,
        owner_id=current_user.id,
        version=1
    )
    
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@router.get("", response_model=List[GoldenDatasetResponse])
def list_golden_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    intent: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    set_db_user_context(db, current_user.id)
    query = db.query(GoldenDataset)
    
    if status:
        query = query.filter(GoldenDataset.status == status)
    if priority:
        query = query.filter(GoldenDataset.priority == priority)
    if intent:
        query = query.filter(GoldenDataset.expected_intent == intent)
    
    results = query.all()
    
    # Client-side filtering for tags to remain SQLite-compatible (JSON lists)
    if tag:
        tag_lower = tag.lower()
        filtered_results = []
        for case in results:
            case_tags = case.tags or []
            if any(t.lower() == tag_lower for t in case_tags):
                filtered_results.append(case)
        return filtered_results
        
    return results

@router.get("/{case_id}", response_model=GoldenDatasetResponse)
def get_golden_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    set_db_user_context(db, current_user.id)
    db_case = db.query(GoldenDataset).filter(GoldenDataset.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Golden testcase with ID {case_id} not found."
        )
    return db_case

@router.put("/{case_id}", response_model=GoldenDatasetResponse)
def update_golden_case(
    case_id: str,
    case_update: GoldenDatasetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    set_db_user_context(db, current_user.id)
    db_case = db.query(GoldenDataset).filter(GoldenDataset.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Golden testcase with ID {case_id} not found."
        )
        
    update_data = case_update.model_dump(exclude_unset=True)
    if not update_data:
        return db_case
        
    # Increment version upon modification
    db_case.version += 1
    
    for key, value in update_data.items():
        setattr(db_case, key, value)
        
    db.commit()
    db.refresh(db_case)
    return db_case

@router.delete("/{case_id}")
def delete_golden_case(
    case_id: str,
    hard_delete: bool = Query(False, description="Set to true to physically delete from database"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    set_db_user_context(db, current_user.id)
    db_case = db.query(GoldenDataset).filter(GoldenDataset.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Golden testcase with ID {case_id} not found."
        )
        
    if hard_delete:
        db.delete(db_case)
        db.commit()
        return {"detail": f"Golden testcase {case_id} deleted successfully."}
    else:
        # Archive by deprecating status
        db_case.status = "DEPRECATED"
        db_case.version += 1
        db.commit()
        db.refresh(db_case)
        return {"detail": f"Golden testcase {case_id} archived (status set to DEPRECATED)."}
