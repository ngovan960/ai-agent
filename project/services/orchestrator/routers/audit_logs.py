import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from services.orchestrator.services import audit_service
from shared.database import get_db
from shared.schemas.audit import AuditLogListResponse, AuditLogResponse

router = APIRouter()


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    task_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await audit_service.get_audit_logs(db, task_id, page, page_size)
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(a) for a in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/audit-logs/export")
async def export_audit_logs(
    db: AsyncSession = Depends(get_db),
    task_id: UUID | None = None,
):
    items, total = await audit_service.get_audit_logs(db, task_id, page=1, page_size=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "task_id", "action", "actor", "actor_type", "result", "message", "created_at"])
    for log in items:
        writer.writerow([str(log.id), str(log.task_id or ""), log.action, log.actor, log.actor_type, log.result, log.message, str(log.created_at)])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit_logs.csv"})
