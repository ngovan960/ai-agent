from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database import get_db
from shared.schemas.retry_audit import (
    RetryCreate,
    RetryResponse,
    RetryStats,
    AuditLogCreate,
    AuditLogResponse,
    AuditLogQuery,
)
from services.orchestrator.services.retry_audit_service import RetryService, AuditService
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["retry-audit"])


@router.post("/retries", response_model=RetryResponse)
async def create_retry(data: RetryCreate, db: AsyncSession = Depends(get_db)):
    try:
        retry = await RetryService(db).create_retry(data)
        return retry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks/{task_id}/retries", response_model=List[RetryResponse])
async def get_task_retries(task_id, db: AsyncSession = Depends(get_db)):
    retries = await RetryService(db).get_retries_by_task(task_id)
    return retries


@router.get("/tasks/{task_id}/retries/stats", response_model=RetryStats)
async def get_retry_stats(task_id, db: AsyncSession = Depends(get_db)):
    stats = await RetryService(db).get_retry_stats(task_id)
    return stats


@router.get("/tasks/{task_id}/retries/can-retry")
async def can_retry(task_id, db: AsyncSession = Depends(get_db)):
    can = await RetryService(db).can_retry(task_id)
    return {"task_id": task_id, "can_retry": can}


@router.post("/audit-logs", response_model=AuditLogResponse)
async def create_audit_log(data: AuditLogCreate, db: AsyncSession = Depends(get_db)):
    audit = await AuditService(db).create_audit_log(data)
    return audit


@router.get("/audit-logs", response_model=dict)
async def query_audit_logs(
    task_id: str = None,
    actor: str = None,
    actor_type: str = None,
    result: str = None,
    action: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime

    query = AuditLogQuery(
        task_id=task_id,
        actor=actor,
        actor_type=actor_type,
        result=result,
        action=action,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        limit=limit,
        offset=offset,
    )
    logs, total = await AuditService(db).query_audit_logs(query)
    return {
        "logs": [AuditLogResponse.model_validate(log) for log in logs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/tasks/{task_id}/audit-logs", response_model=List[AuditLogResponse])
async def get_task_audit_logs(task_id, db: AsyncSession = Depends(get_db)):
    logs = await AuditService(db).get_audit_logs_by_task(task_id)
    return logs


@router.get("/audit-logs/export/csv")
async def export_audit_logs_csv(
    task_id: str = None,
    actor: str = None,
    result: str = None,
    db: AsyncSession = Depends(get_db),
):
    query = AuditLogQuery(task_id=task_id, actor=actor, result=result, limit=1000)
    csv_content = await AuditService(db).export_audit_logs_csv(query)
    return {"csv": csv_content}
