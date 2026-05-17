import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from shared.models.registry import AuditLog
from shared.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self, db_session, runtime: Any = None, profile_builder: Any = None):
        self._db = db_session
        self.runtime = runtime
        self.profile_builder = profile_builder

    async def monitor_process(self) -> dict:
        errors = await self.track_errors()
        anomalies = await self.detect_anomalies()
        recommendations = self._generate_recommendations(errors, anomalies)
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "alert" if errors or anomalies else "healthy",
            "errors_found": len(errors),
            "anomalies": anomalies,
            "recommendations": recommendations,
        }

    async def track_errors(self) -> list[dict]:
        result = await self._db.execute(
            select(AuditLog)
            .where(AuditLog.result.in_(["FAILURE", "REJECTED"]))
            .order_by(AuditLog.created_at.desc())
            .limit(20)
        )
        logs = result.scalars().all()
        return [
            {
                "id": str(log.id),
                "task_id": str(log.task_id) if log.task_id else None,
                "action": log.action,
                "actor": log.actor,
                "result": log.result.value if hasattr(log.result, "value") else str(log.result),
                "message": log.message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    async def detect_anomalies(self) -> list[dict]:
        anomalies = []
        failed_count = (await self._db.execute(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.FAILED)
        )).scalar() or 0

        blocked_count = (await self._db.execute(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.BLOCKED)
        )).scalar() or 0

        escalated_count = (await self._db.execute(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.ESCALATED)
        )).scalar() or 0

        if failed_count > 0:
            anomalies.append({
                "type": "high_failure_rate",
                "severity": "high" if failed_count > 3 else "medium",
                "message": f"{failed_count} task(s) have FAILED status",
                "count": failed_count,
            })

        if blocked_count > 0:
            anomalies.append({
                "type": "blocked_tasks",
                "severity": "medium",
                "message": f"{blocked_count} task(s) are BLOCKED",
                "count": blocked_count,
            })

        if escalated_count > 0:
            anomalies.append({
                "type": "escalated_tasks",
                "severity": "high",
                "message": f"{escalated_count} task(s) require MENTOR intervention",
                "count": escalated_count,
            })

        return anomalies

    async def generate_report(self) -> dict:
        total = (await self._db.execute(select(func.count()).select_from(Task))).scalar() or 0
        completed = (await self._db.execute(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.DONE)
        )).scalar() or 0
        failed = (await self._db.execute(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.FAILED)
        )).scalar() or 0
        active = (await self._db.execute(
            select(func.count()).select_from(Task).where(
                Task.status.in_([
                    TaskStatus.ANALYZING, TaskStatus.PLANNING,
                    TaskStatus.IMPLEMENTING, TaskStatus.VERIFYING, TaskStatus.REVIEWING,
                ])
            )
        )).scalar() or 0

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "summary": {
                "tasks_total": total,
                "tasks_completed": completed,
                "tasks_failed": failed,
                "tasks_active": active,
                "completion_rate": round(completed / total * 100, 2) if total > 0 else 0.0,
            },
        }

    def _generate_recommendations(self, errors: list[dict], anomalies: list[dict]) -> list[dict]:
        recommendations = []
        for anomaly in anomalies:
            if anomaly["type"] == "high_failure_rate":
                recommendations.append({
                    "action": "review_failures",
                    "message": "Review failed tasks and consider retrying with adjusted parameters",
                    "priority": "high",
                })
            elif anomaly["type"] == "blocked_tasks":
                recommendations.append({
                    "action": "resolve_blockers",
                    "message": "Check task dependencies and resolve blockers",
                    "priority": "medium",
                })
            elif anomaly["type"] == "escalated_tasks":
                recommendations.append({
                    "action": "mentor_intervention",
                    "message": "Escalated tasks require manual mentor review",
                    "priority": "high",
                })
        return recommendations
