import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import yaml

logger = logging.getLogger(__name__)


@dataclass
class RollbackRecord:
    rollback_id: str
    task_id: UUID
    reason: str
    status: str
    action: str
    result: str = ""
    created_at: str = ""


@dataclass
class RollbackAuditEntry:
    rollback_id: str
    task_id: UUID
    action: str
    reason: str
    result: str
    status: str
    timestamp: str


def _load_rollback_config(config_path: str | None = None) -> dict:
    if config_path:
        paths = [Path(config_path)]
    else:
        paths = [
            Path(__file__).parent.parent / "config" / "rollback_config.yaml",
            Path("services/orchestrator/config/rollback_config.yaml"),
        ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {
        "auto_rollback": True,
        "manual_approval": False,
        "max_rollbacks": 3,
        "revert_method": "git_revert",
    }


class RollbackEngine:
    def __init__(self, config_path: str | None = None):
        config = _load_rollback_config(config_path)
        self.auto_rollback = config.get("auto_rollback", True)
        self.manual_approval = config.get("manual_approval", False)
        self.max_rollbacks = config.get("max_rollbacks", 3)
        self.revert_method = config.get("revert_method", "git_revert")
        self._audit_log: list[RollbackAuditEntry] = []

    async def revert_branch(
        self,
        task_id: UUID,
        branch: str = "main",
        commit_hash: str | None = None,
    ) -> RollbackRecord:
        rollback_id = str(uuid4())
        record = RollbackRecord(
            rollback_id=rollback_id,
            task_id=task_id,
            reason=f"Verification failed for task {task_id}",
            status="pending",
            action="revert_branch",
            created_at=datetime.now(UTC).isoformat(),
        )

        try:
            cmd = ["git", "revert", "--no-edit", commit_hash] if commit_hash else ["git", "reset", "--hard", "HEAD~1"]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            except TimeoutError:
                proc.kill()
                record.status = "failed"
                record.result = "Git revert timed out"
                self._log_audit(RollbackAuditEntry(
                    rollback_id=rollback_id,
                    task_id=task_id,
                    action="revert_branch",
                    reason=record.reason,
                    result=record.result,
                    status=record.status,
                    timestamp=record.created_at,
                ))
                return record

            if proc.returncode == 0:
                record.status = "completed"
                record.result = stdout.decode()[:2000]
            else:
                record.status = "failed"
                record.result = stderr.decode()[:2000]

            self._log_audit(RollbackAuditEntry(
                rollback_id=rollback_id,
                task_id=task_id,
                action="revert_branch",
                reason=record.reason,
                result=record.result,
                status=record.status,
                timestamp=record.created_at,
            ))
            return record

        except Exception as e:
            record.status = "failed"
            record.result = str(e)
            return record

    async def restore_snapshot(self, snapshot_id: str) -> RollbackRecord:
        rollback_id = str(uuid4())
        record = RollbackRecord(
            rollback_id=rollback_id,
            task_id=uuid4(),
            reason=f"Restore snapshot {snapshot_id}",
            status="pending",
            action="restore_snapshot",
            created_at=datetime.now(UTC).isoformat(),
        )

        try:
            db_url = os.environ.get("DATABASE_URL", "")
            if not db_url:
                record.status = "completed"
                record.result = "Snapshot restore skipped: DATABASE_URL not set"
                return record

            cmd = ["pg_restore", "--clean", f"--dbname={db_url}", snapshot_id]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            except TimeoutError:
                proc.kill()
                record.status = "failed"
                record.result = "Snapshot restore timed out"
                return record

            if proc.returncode == 0:
                record.status = "completed"
                record.result = stdout.decode()[:2000] or "Snapshot restore completed"
            else:
                record.status = "failed"
                record.result = stderr.decode()[:2000]
        except Exception as e:
            record.status = "failed"
            record.result = str(e)

        return record

    async def trigger_rollback(
        self,
        task_id: UUID,
        reason: str,
        commit_hash: str | None = None,
        snapshot_id: str | None = None,
    ) -> RollbackRecord:
        if not self.auto_rollback:
            return RollbackRecord(
                rollback_id=str(uuid4()),
                task_id=task_id,
                reason=reason,
                status="skipped",
                action="trigger_rollback",
                result="Auto-rollback disabled",
                created_at=datetime.now(UTC).isoformat(),
            )

        if snapshot_id:
            record = await self.restore_snapshot(snapshot_id)
        else:
            record = await self.revert_branch(task_id, commit_hash=commit_hash)
        record.reason = reason
        return record

    async def verify_rollback(self, rollback_id: str, staging_url: str | None = None) -> dict:
        import httpx
        for entry in self._audit_log:
            if entry.rollback_id == rollback_id and entry.status == "completed":
                if staging_url:
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            resp = await client.get(f"{staging_url}/health")
                            healthy = resp.status_code == 200
                    except Exception:
                        healthy = False
                    return {
                        "rollback_id": rollback_id,
                        "verified": healthy,
                        "message": "Rollback verified successfully" if healthy else "Health check failed after rollback",
                    }
                return {
                    "rollback_id": rollback_id,
                    "verified": True,
                    "message": "Rollback completed (no health check)",
                }
        return {"rollback_id": rollback_id, "verified": False, "message": "Rollback not found or not completed"}

    def _log_audit(self, entry: RollbackAuditEntry) -> None:
        self._audit_log.append(entry)
        logger.info(f"Rollback audit: {entry.action} for task {entry.task_id} -> {entry.status}")

    def get_rollback_history(self, task_id: str | None = None) -> list[RollbackAuditEntry]:
        if task_id:
            return [e for e in self._audit_log if str(e.task_id) == task_id]
        return self._audit_log.copy()

    def get_audit_log(self) -> list[RollbackAuditEntry]:
        return self._audit_log.copy()

    def get_rollback_count(self, task_id: UUID) -> int:
        return sum(1 for e in self._audit_log if str(e.task_id) == str(task_id))
