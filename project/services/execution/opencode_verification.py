import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from services.execution.opencode_adapter import OpenCodeAdapter

logger = logging.getLogger(__name__)


@dataclass
class DevVerificationStep:
    step_name: str
    status: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0


@dataclass
class DevVerificationResult:
    status: str
    steps: list[DevVerificationStep] = field(default_factory=list)
    logs: str = ""
    duration_ms: float = 0.0


LINT_CMDS = {
    "python": ["ruff check {path} --quiet", "flake8 {path} --quiet"],
    "node": ["eslint {path} --quiet", "tsc --noEmit --project {path}"],
}

TEST_CMDS = {
    "python": "pytest {path}/tests/ -x --tb=short -q 2>&1",
    "node": "cd {path} && npm test -- --run 2>&1",
}

BUILD_CMDS = {
    "python": "python -m build {path} --outdir {path}/dist 2>&1",
    "node": "cd {path} && npm run build 2>&1",
}

SECURITY_CMDS = {
    "python": "bandit -r {path} -f json -q 2>&1 || true",
    "node": "cd {path} && npm audit --json 2>&1 || true",
}


class OpenCodeVerification:
    def __init__(self, adapter: OpenCodeAdapter | None = None):
        self.adapter = adapter or OpenCodeAdapter()

    async def verify_dev_mode(
        self,
        code_path: str,
        language: str = "python",
        timeout: int = 600,
    ) -> DevVerificationResult:
        start = datetime.now(UTC)
        steps: list[DevVerificationStep] = []
        logs: list[str] = []

        lint_result = await self._run_lint(code_path, language)
        steps.append(lint_result)
        logs.append(f"[lint] exit_code={lint_result.exit_code} ({lint_result.duration_ms:.0f}ms)")

        test_result = await self._run_tests(code_path, language)
        steps.append(test_result)
        logs.append(f"[unit_test] exit_code={test_result.exit_code} ({test_result.duration_ms:.0f}ms)")

        build_result = await self._run_build(code_path, language)
        steps.append(build_result)
        logs.append(f"[build] exit_code={build_result.exit_code} ({build_result.duration_ms:.0f}ms)")

        security_result = await self._run_security(code_path, language)
        steps.append(security_result)
        logs.append(f"[security] exit_code={security_result.exit_code} ({security_result.duration_ms:.0f}ms)")

        total_duration = (datetime.now(UTC) - start).total_seconds() * 1000
        all_pass = all(s.exit_code == 0 for s in steps)
        overall = "verified" if all_pass else "failed"

        return DevVerificationResult(
            status=overall,
            steps=steps,
            logs="\n".join(logs),
            duration_ms=total_duration,
        )

    async def _run_lint(self, code_path: str, lang: str) -> DevVerificationStep:
        cmds = LINT_CMDS.get(lang, LINT_CMDS["python"])
        start = datetime.now(UTC)
        for cmd_template in cmds:
            cmd = cmd_template.format(path=code_path)
            result = await self.adapter.run_bash(cmd, timeout=120)
            if result["exit_code"] != 0:
                duration = (datetime.now(UTC) - start).total_seconds() * 1000
                return DevVerificationStep(
                    step_name="lint", status="failed",
                    exit_code=result["exit_code"],
                    stdout=result.get("stdout", ""),
                    stderr=result.get("stderr", ""),
                    duration_ms=duration,
                )
        duration = (datetime.now(UTC) - start).total_seconds() * 1000
        return DevVerificationStep(step_name="lint", status="passed", exit_code=0, duration_ms=duration)

    async def _run_tests(self, code_path: str, lang: str) -> DevVerificationStep:
        cmd_template = TEST_CMDS.get(lang, TEST_CMDS["python"])
        cmd = cmd_template.format(path=code_path)
        start = datetime.now(UTC)
        result = await self.adapter.run_bash(cmd, timeout=300)
        duration = (datetime.now(UTC) - start).total_seconds() * 1000
        return DevVerificationStep(
            step_name="unit_test",
            status="passed" if result["exit_code"] == 0 else "failed",
            exit_code=result["exit_code"],
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            duration_ms=duration,
        )

    async def _run_build(self, code_path: str, lang: str) -> DevVerificationStep:
        cmd_template = BUILD_CMDS.get(lang, BUILD_CMDS["python"])
        cmd = cmd_template.format(path=code_path)
        start = datetime.now(UTC)
        result = await self.adapter.run_bash(cmd, timeout=120)
        duration = (datetime.now(UTC) - start).total_seconds() * 1000
        return DevVerificationStep(
            step_name="build",
            status="passed" if result["exit_code"] == 0 else "failed",
            exit_code=result["exit_code"],
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            duration_ms=duration,
        )

    async def _run_security(self, code_path: str, lang: str) -> DevVerificationStep:
        cmd_template = SECURITY_CMDS.get(lang, SECURITY_CMDS["python"])
        cmd = cmd_template.format(path=code_path)
        start = datetime.now(UTC)
        result = await self.adapter.run_bash(cmd, timeout=120)
        duration = (datetime.now(UTC) - start).total_seconds() * 1000
        scan_passed = True
        if result["stdout"] and lang == "python":
            try:
                vulns = json.loads(result["stdout"])
                scan_passed = len(vulns.get("results", [])) == 0
            except (json.JSONDecodeError, AttributeError):
                pass
        return DevVerificationStep(
            step_name="security_scan",
            status="passed" if scan_passed and result["exit_code"] == 0 else "failed",
            exit_code=result["exit_code"],
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            duration_ms=duration,
        )
