import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class MultiProjectService:
    def __init__(self, db_session):
        self._db = db_session

    async def get_all_projects_status(self, session) -> list[dict]:
        from sqlalchemy import func, select

        from shared.models.project import Project
        from shared.models.task import Task

        stmt = (
            select(
                Project.id,
                Project.name,
                Project.status,
                func.count(Task.id).label("task_count"),
            )
            .outerjoin(Task, Task.project_id == Project.id)
            .group_by(Project.id)
        )
        result = await session.execute(stmt)
        rows = result.fetchall()
        return [
            {
                "id": str(row.id),
                "name": row.name,
                "status": row.status,
                "task_count": row.task_count,
                "completion_rate": 0.0,
            }
            for row in rows
        ]

    async def allocate_resources(self, projects: list[dict]) -> dict:
        priorities = await self._calculate_priorities(projects)
        total_projects = len(priorities)
        if total_projects == 0:
            return {"allocation": []}

        sorted_projects = sorted(priorities, key=lambda x: x["score"], reverse=True)
        allocation = []
        for rank, p in enumerate(sorted_projects, 1):
            agent_pool = max(1, 7 - rank * 2)
            allocation.append({
                "project_id": p["project_id"],
                "project_name": p["name"],
                "priority_score": round(p["score"], 2),
                "rank": rank,
                "agents_allocated": agent_pool,
                "compute_priority": "high" if rank <= 1 else "medium" if rank <= 3 else "low",
            })
        return {
            "allocation": allocation,
            "total_projects": total_projects,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _calculate_priorities(self, projects: list[dict]) -> list[dict]:
        priorities = []
        for project in projects:
            score = 0.0
            if project.get("status") == "ACTIVE":
                score += 5.0
            elif project.get("status") == "COMPLETED":
                score += 1.0
            score += min(project.get("task_count", 0) * 0.1, 3.0)
            completion = project.get("completion_rate", 0.0)
            score += completion * 2.0
            priorities.append({
                "project_id": project["id"],
                "name": project["name"],
                "score": round(score, 2),
            })
        return priorities

    async def check_cross_project_dependencies(self, session) -> list[dict]:
        from sqlalchemy import text

        result = await session.execute(
            text("""
                SELECT t1.project_id AS source_project,
                       t2.project_id AS target_project,
                       COUNT(*) AS dep_count
                FROM tasks t1
                JOIN task_dependencies td ON t1.id = td.task_id
                JOIN tasks t2 ON td.depends_on_task_id = t2.id
                WHERE t1.project_id != t2.project_id
                GROUP BY t1.project_id, t2.project_id
            """)
        )
        rows = result.fetchall()
        return [
            {
                "source_project": str(row.source_project),
                "target_project": str(row.target_project),
                "dependency_count": row.dep_count,
            }
            for row in rows
        ]

    async def get_workload_summary(self, session) -> dict:
        from sqlalchemy import func, select

        from shared.models.project import Project

        result = await session.execute(
            select(Project.status, func.count(Project.id)).group_by(Project.status)
        )
        rows = result.fetchall()
        status_counts = {row[0]: row[1] for row in rows}
        return {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
            "timestamp": datetime.now(UTC).isoformat(),
        }
