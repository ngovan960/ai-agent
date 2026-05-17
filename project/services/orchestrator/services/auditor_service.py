import json
import logging
from typing import Any
from uuid import UUID

from services.orchestrator.services.law_engine import LawEngine

logger = logging.getLogger(__name__)


class AuditorService:
    def __init__(self, db_session, runtime: Any, profile_builder: Any, law_engine: LawEngine | None = None):
        self._db = db_session
        self.runtime = runtime
        self.profile_builder = profile_builder
        self._law_engine = law_engine or LawEngine()

    async def review(
        self,
        task_id: UUID,
        code: str,
        spec: dict,
        test_results: dict,
        laws: str | None = None,
    ) -> dict:
        law_violations = await self.check_laws(task_id, code)

        profile = self.profile_builder.build(
            agent_name="auditor",
            complexity="medium",
            risk_level=spec.get("risk_level", "medium"),
        )

        variables = {
            "code": code[:30000],
            "spec": json.dumps(spec, default=str),
            "test_results": json.dumps(test_results, default=str),
            "laws": laws or "",
            "law_violations": json.dumps(law_violations, default=str),
        }

        result = await self.runtime.execute_agent(
            agent_name="auditor",
            task_id=task_id,
            task_profile=profile,
            variables=variables,
        )

        parsed = result.parsed_output or {}
        verdict = parsed.get("verdict", "ESCALATE")

        return {
            "status": "completed",
            "verdict": verdict,
            "scores": parsed.get("scores", {}),
            "violations": parsed.get("violations", []),
            "law_violations": law_violations,
            "revision_requests": parsed.get("revision_requests", []),
            "model_used": result.model_used,
            "cost_usd": result.cost_usd,
            "latency_ms": result.latency_ms,
            "error": result.error,
        }

    async def check_laws(self, task_id: UUID, code: str) -> list[dict]:
        compliance = self._law_engine.check_compliance(code=code, task_id=task_id)
        report = self._law_engine.report_violations(compliance)
        return [
            {
                "law": v.law_id,
                "law_name": v.law_name,
                "severity": v.severity,
                "violation_details": v.violation_details,
                "location": v.location,
            }
            for v in report.violations
        ]
