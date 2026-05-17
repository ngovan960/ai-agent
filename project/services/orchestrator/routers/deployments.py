from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.orchestrator.services.approval_service import ApprovalService
from services.orchestrator.services.deployment_service import DeploymentService
from services.orchestrator.services.rollback_service import RollbackEngine

router = APIRouter()

_deployment_service: DeploymentService | None = None
_approval_service: ApprovalService | None = None
_rollback_engine: RollbackEngine | None = None


class StagingDeployRequest(BaseModel):
    task_id: UUID
    image_tag: str
    code_path: str = "/app"
    staging_host: str = "localhost"
    staging_port: int = 8081


class ProductionApprovalRequest(BaseModel):
    deployment_id: str
    task_id: UUID
    reason: str = "Production deployment"
    risk_level: str = "CRITICAL"


class ApprovalAction(BaseModel):
    approval_id: str
    approver: str | None = "system"


class RejectionAction(BaseModel):
    approval_id: str
    reason: str = "Rejected by user"


class RollbackRequest(BaseModel):
    task_id: UUID
    reason: str = "Manual rollback"


def init_deployment(deployment_service: DeploymentService, approval_service: ApprovalService, rollback_engine: RollbackEngine):
    global _deployment_service, _approval_service, _rollback_engine
    _deployment_service = deployment_service
    _approval_service = approval_service
    _rollback_engine = rollback_engine


@router.post("/deploy/staging", tags=["deploy"])
async def deploy_staging(req: StagingDeployRequest):
    if not _deployment_service:
        raise HTTPException(status_code=503, detail="Deployment service not initialized")
    build_tag = await _deployment_service.build_image(req.code_path, req.image_tag)
    deploy_result = await _deployment_service.deploy_staging(
        build_tag, code_path=req.code_path,
        staging_host=req.staging_host, staging_port=req.staging_port,
    )
    verify_result = await _deployment_service.verify_staging(
        deploy_result.get("staging_url", "http://localhost:8000")
    )
    return {
        "deployment": deploy_result,
        "build_tag": build_tag,
        "verification": verify_result,
    }


@router.get("/deploy/staging/{deployment_id}", tags=["deploy"])
async def get_staging_deployment(deployment_id: str):
    if not _deployment_service:
        raise HTTPException(status_code=503, detail="Deployment service not initialized")
    result = _deployment_service.get_deployment_log(deployment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return result


@router.post("/deploy/production/request", tags=["deploy"])
async def request_production_approval(req: ProductionApprovalRequest):
    if not _approval_service:
        raise HTTPException(status_code=503, detail="Approval service not initialized")
    approval = _approval_service.require_approval(
        req.deployment_id, req.task_id, req.reason, req.risk_level
    )
    return approval


@router.post("/deploy/production/approve", tags=["deploy"])
async def approve_production(req: ApprovalAction):
    if not _approval_service:
        raise HTTPException(status_code=503, detail="Approval service not initialized")
    result = _approval_service.approve(req.approval_id, req.approver or "system")
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.post("/deploy/production/reject", tags=["deploy"])
async def reject_production(req: RejectionAction):
    if not _approval_service:
        raise HTTPException(status_code=503, detail="Approval service not initialized")
    result = _approval_service.reject(req.approval_id, req.reason)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.get("/deploy/pending-approvals", tags=["deploy"])
async def get_pending_approvals():
    if not _approval_service:
        raise HTTPException(status_code=503, detail="Approval service not initialized")
    return _approval_service.get_pending()


@router.get("/deploy/approval-history", tags=["deploy"])
async def get_approval_history():
    if not _approval_service:
        raise HTTPException(status_code=503, detail="Approval service not initialized")
    return _approval_service.get_history()


@router.post("/deploy/rollback", tags=["deploy"])
async def manual_rollback(req: RollbackRequest):
    if not _rollback_engine:
        raise HTTPException(status_code=503, detail="Rollback engine not initialized")
    record = await _rollback_engine.trigger_rollback(req.task_id, req.reason)
    return {
        "rollback_id": record.rollback_id,
        "status": record.status,
        "result": record.result,
    }


@router.get("/deploy/rollback/{rollback_id}", tags=["deploy"])
async def get_rollback_status(rollback_id: str):
    if not _rollback_engine:
        raise HTTPException(status_code=503, detail="Rollback engine not initialized")
    for entry in _rollback_engine.get_audit_log():
        if entry.rollback_id == rollback_id:
            return {
                "rollback_id": entry.rollback_id,
                "task_id": str(entry.task_id),
                "action": entry.action,
                "reason": entry.reason,
                "result": entry.result,
                "status": entry.status,
                "timestamp": entry.timestamp,
            }
    raise HTTPException(status_code=404, detail="Rollback not found")


@router.get("/deploy/metrics", tags=["deploy"])
async def get_deployment_metrics():
    if not _approval_service or not _rollback_engine or not _deployment_service:
        raise HTTPException(status_code=503, detail="Services not initialized")
    history = _approval_service.get_history()
    pending = _approval_service.get_pending()
    deployments = _deployment_service.get_all_deployments()
    return {
        "total_approvals": len(history),
        "pending_approvals": len(pending),
        "approved": sum(1 for h in history if h["status"] == "approved"),
        "rejected": sum(1 for h in history if h["status"] == "rejected"),
        "total_rollbacks": len(_rollback_engine.get_audit_log()),
        "total_deployments": len(deployments),
    }
