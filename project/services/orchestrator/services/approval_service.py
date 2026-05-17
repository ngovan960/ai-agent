import json
import logging
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

_DATA_FILE = os.environ.get("APPROVAL_DATA_FILE", "/app/data/approval_data.json")


def _load_data():
    try:
        with open(_DATA_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"pending": [], "history": []}


def _save_data(pending: list[dict], history: list[dict]):
    try:
        dir_name = os.path.dirname(_DATA_FILE)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(_DATA_FILE, "w") as f:
            json.dump({"pending": pending, "history": history}, f, default=str)
    except Exception as e:
        logger.warning(f"Failed to persist approval data: {e}")


class ApprovalService:
    def __init__(self, approval_timeout_hours: int = 24):
        data = _load_data()
        self._pending: list[dict] = data.get("pending", [])
        self._history: list[dict] = data.get("history", [])
        self._timeout_hours = approval_timeout_hours

    def _persist(self):
        _save_data(self._pending, self._history)

    def require_approval(self, deployment_id: str, task_id: UUID, reason: str, risk_level: str) -> dict:
        approval_id = str(uuid4())
        request = {
            "approval_id": approval_id,
            "deployment_id": deployment_id,
            "task_id": str(task_id),
            "reason": reason,
            "risk_level": risk_level,
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=self._timeout_hours)).isoformat(),
        }
        self._pending.append(request)
        self._persist()
        logger.info(f"Approval required: {approval_id} for deployment {deployment_id}")
        return request

    def approve(self, approval_id: str, approver: str) -> dict:
        request = self._find_pending(approval_id)
        if not request:
            return {"status": "error", "message": "Approval request not found"}
        self._pending.remove(request)
        request["status"] = "approved"
        request["approver"] = approver
        request["approved_at"] = datetime.now(UTC).isoformat()
        self._history.append(request)
        self._persist()
        logger.info(f"Approval granted: {approval_id} by {approver}")
        return {"status": "approved", "approval_id": approval_id, "approver": approver}

    def reject(self, approval_id: str, reason: str) -> dict:
        request = self._find_pending(approval_id)
        if not request:
            return {"status": "error", "message": "Approval request not found"}
        self._pending.remove(request)
        request["status"] = "rejected"
        request["rejection_reason"] = reason
        request["rejected_at"] = datetime.now(UTC).isoformat()
        self._history.append(request)
        self._persist()
        logger.info(f"Approval rejected: {approval_id} reason: {reason}")
        return {"status": "rejected", "approval_id": approval_id, "rejection_reason": reason}

    def check_pending_approvals(self) -> list[dict]:
        now = datetime.now(UTC)
        timed_out = []
        for req in self._pending[:]:
            expires = datetime.fromisoformat(req["expires_at"])
            if now > expires:
                self._pending.remove(req)
                req["status"] = "timed_out"
                self._history.append(req)
                timed_out.append(req)
        if timed_out:
            self._persist()
        return timed_out

    def get_pending(self) -> list[dict]:
        self.check_pending_approvals()
        return self._pending.copy()

    def get_history(self) -> list[dict]:
        return self._history.copy()

    def _find_pending(self, approval_id: str) -> dict | None:
        for req in self._pending:
            if req["approval_id"] == approval_id:
                return req
        return None
