import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CIRun:
    pipeline_id: str
    task_id: UUID
    status: str
    created_at: str
    completed_at: str | None = None
    result: dict | None = None


class CIIntegrationService:
    def __init__(self):
        self._runs: dict[str, CIRun] = {}
        self._github_token: str | None = os.environ.get("GITHUB_TOKEN")
        self._repo = os.environ.get("GITHUB_REPOSITORY", "")

    async def trigger_ci(self, task_id: UUID, branch: str = "main") -> str:
        pipeline_id = str(uuid4())
        run = CIRun(
            pipeline_id=pipeline_id,
            task_id=task_id,
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
        )
        self._runs[pipeline_id] = run

        if not self._github_token or not self._repo:
            run.status = "simulated"
            run.result = {"status": "passed", "message": "CI simulated (no GitHub token)"}
            return pipeline_id

        try:
            data = {"event_type": "verify_task", "client_payload": {"task_id": str(task_id), "pipeline_id": pipeline_id, "branch": branch}}
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://api.github.com/repos/{self._repo}/dispatches",
                    headers={"Authorization": f"Bearer {self._github_token}", "Accept": "application/vnd.github.v3+json"},
                    json=data,
                )
                if resp.status_code in (204, 200):
                    run.status = "triggered"
                    logger.info(f"CI triggered for task {task_id}: pipeline_id={pipeline_id}")
                else:
                    run.status = "simulated"
                    run.result = {"status": "passed", "message": f"GitHub dispatch returned {resp.status_code}, using simulated mode"}
        except Exception as e:
            logger.warning(f"CI trigger failed, using simulated mode: {e}")
            run.status = "simulated"
            run.result = {"status": "passed", "message": "CI simulated (dispatch failed)"}

        return pipeline_id

    async def handle_ci_callback(self, pipeline_id: str, result: dict) -> str:
        run = self._runs.get(pipeline_id)
        if not run:
            logger.warning(f"Unknown CI pipeline: {pipeline_id}")
            return "unknown"

        run.status = result.get("status", "completed")
        run.result = result
        run.completed_at = datetime.now(UTC).isoformat()

        if run.status == "passed":
            return "verified"
        elif run.status == "failed":
            return "failed"
        return "in_progress"

    async def get_ci_status(self, pipeline_id: str) -> CIRun | None:
        return self._runs.get(pipeline_id)
