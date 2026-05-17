import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class WorkflowOptimizerService:
    def __init__(self, db_session):
        self._db = db_session

    async def analyze_workflow_performance(self, session) -> dict:
        from sqlalchemy import text

        result = await session.execute(
            text("""
                SELECT
                    COUNT(*) AS total_tasks,
                    SUM(CASE WHEN status = 'DONE' THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
                    AVG(CASE WHEN completed_at IS NOT NULL AND created_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (completed_at - created_at)) END) AS avg_duration_seconds
                FROM tasks
            """)
        )
        row = result.fetchone()
        total = row.total_tasks or 0
        completed = row.completed or 0
        failed = row.failed or 0

        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "success_rate": round(completed / total * 100, 2) if total > 0 else 0.0,
            "avg_duration_seconds": round(row.avg_duration_seconds, 2) if row.avg_duration_seconds else 0.0,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def suggest_optimizations(self, session) -> list[dict]:
        from sqlalchemy import text

        retry_result = await session.execute(
            text("""
                SELECT ct.model, COUNT(*) AS call_count,
                       AVG(ct.cost_usd) AS avg_cost
                FROM cost_tracking ct
                GROUP BY ct.model
                ORDER BY call_count DESC
            """)
        )
        model_stats = retry_result.fetchall()

        suggestions = []

        for ms in model_stats:
            if ms.avg_cost and ms.avg_cost > 0.001:
                suggestions.append({
                    "type": "model_routing",
                    "target": ms.model,
                    "suggestion": f"Consider switching to a cheaper model for routine calls. "
                                  f"Current avg cost: ${ms.avg_cost:.4f} per call",
                    "confidence": 0.7,
                })

        task_result = await session.execute(
            text("""
                SELECT status, COUNT(*) AS cnt
                FROM tasks
                WHERE status IN ('FAILED', 'BLOCKED', 'ESCALATED')
                GROUP BY status
                ORDER BY cnt DESC
                LIMIT 5
            """)
        )
        bottleneck_states = task_result.fetchall()
        if bottleneck_states:
            state_names = [f"{row.status}({row.cnt})" for row in bottleneck_states]
            suggestions.append({
                "type": "workflow",
                "target": "state_transitions",
                "suggestion": f"Bottleneck states detected: {', '.join(state_names)}. "
                              f"Consider reviewing transition rules or increasing retries.",
                "confidence": 0.8,
            })

        return suggestions

    async def optimize_prompts(self, historical_data: list[dict]) -> list[dict]:
        suggestions = []
        total = len(historical_data)
        if total == 0:
            return suggestions
        failures = sum(1 for h in historical_data if h.get("status") == "FAILED")
        failure_rate = failures / total
        if failure_rate > 0.3:
            suggestions.append({
                "type": "prompt",
                "target": "agent_prompts",
                "suggestion": f"Failure rate is {failure_rate:.0%}. "
                              f"Consider adding more explicit validation steps to agent prompts.",
                "confidence": 0.75,
            })
        return suggestions

    async def apply_adjustment(self, suggestion: dict, auto_apply: bool = False) -> dict:
        if auto_apply and suggestion.get("confidence", 0) > 0.8:
            return {
                "status": "applied",
                "suggestion": suggestion["suggestion"],
                "applied_at": datetime.now(UTC).isoformat(),
            }
        return {
            "status": "requires_approval",
            "suggestion": suggestion["suggestion"],
            "reason": f"Confidence too low ({suggestion.get('confidence', 0):.2f}) or auto-apply disabled",
        }
