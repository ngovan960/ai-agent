import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import yaml

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    step_name: str
    status: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    errors: list[dict] = field(default_factory=list)


@dataclass
class VerificationOutput:
    task_id: UUID
    mode: str
    status: str
    score: float = 0.0
    steps: list[StepResult] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    logs: str = ""
    duration_ms: float = 0.0


LANG_DETECTORS = {
    "python": [".py", ".pyx", ".ipynb"],
    "node": [".js", ".ts", ".jsx", ".tsx", ".mjs"],
}


def detect_language(code_path: str) -> str:
    for lang, exts in LANG_DETECTORS.items():
        for ext in exts:
            if any(f.endswith(ext) for f in _walk_files(code_path)):
                return lang
    return "python"


def _walk_files(path: str) -> list[str]:
    files = []
    try:
        for root, _, filenames in os.walk(path):
            for f in filenames:
                files.append(os.path.join(root, f))
    except Exception:
        pass
    return files


def _load_pipeline_config(config_path: str | None = None) -> dict:
    if config_path:
        paths = [config_path]
    else:
        paths = [
            Path(__file__).parent.parent / "config" / "pipeline_config.yaml",
            Path("services/orchestrator/config/pipeline_config.yaml"),
        ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    logger.warning("pipeline_config.yaml not found, using defaults")
    return {
        "pipeline": {
            "steps": [
                {"name": "lint", "order": 1, "critical": False, "timeout_seconds": 120, "weight": 15, "commands": {"python": "ruff check {code_path} --quiet", "node": "eslint {code_path} --quiet"}},
                {"name": "unit_test", "order": 2, "critical": True, "timeout_seconds": 300, "weight": 40, "commands": {"python": "pytest {code_path}/tests/ -x --tb=short -q 2>&1", "node": "cd {code_path} && npm test -- --run 2>&1"}},
                {"name": "integration_test", "order": 3, "critical": True, "timeout_seconds": 300, "weight": 25, "commands": {"python": "pytest {code_path}/tests/integration/ -x --tb=short -q 2>&1", "node": "cd {code_path} && npm run test:integration 2>&1"}},
                {"name": "build", "order": 4, "critical": True, "timeout_seconds": 120, "weight": 10, "commands": {"python": "python -m build {code_path} --outdir {code_path}/dist 2>&1", "node": "cd {code_path} && npm run build 2>&1"}},
                {"name": "security_scan", "order": 5, "critical": True, "timeout_seconds": 120, "weight": 10, "commands": {"python": "bandit -r {code_path} -f json -q 2>&1", "node": "cd {code_path} && npm audit --json 2>&1"}},
            ],
            "fail_fast": True,
            "max_retries": 2,
            "timeout_seconds": 600,
            "score_threshold": 60.0,
        }
    }


class VerificationPipeline:
    def __init__(self, config_path: str | None = None):
        config = _load_pipeline_config(config_path)
        pipeline = config.get("pipeline", {})
        self.steps_config = sorted(pipeline.get("steps", []), key=lambda s: s.get("order", 99))
        self.fail_fast = pipeline.get("fail_fast", True)
        self.max_retries = pipeline.get("max_retries", 2)
        self.timeout_seconds = pipeline.get("timeout_seconds", 600)
        self.score_threshold = pipeline.get("score_threshold", 60.0)

    async def run_pipeline(
        self,
        task_id: UUID,
        code_path: str,
        mode: str = "dev",
    ) -> VerificationOutput:
        start = datetime.now(UTC)
        lang = detect_language(code_path)
        step_results: list[StepResult] = []
        all_errors: list[dict] = []
        logs: list[str] = []
        passed_weight = 0.0
        total_weight = 0.0

        for step_cfg in self.steps_config:
            total_weight += step_cfg.get("weight", 0)

        for step_cfg in self.steps_config:
            step_name = step_cfg.get("name", "unknown")
            cmd_template = step_cfg.get("commands", {}).get(lang, "")
            if not cmd_template:
                sr = StepResult(step_name=step_name, status="skipped", exit_code=0)
                step_results.append(sr)
                continue

            command = cmd_template.format(code_path=code_path)
            timeout = step_cfg.get("timeout_seconds", 120)
            is_critical = step_cfg.get("critical", False)
            weight = step_cfg.get("weight", 0)

            step_start = datetime.now(UTC)
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=timeout,
                )
                step_duration = (datetime.now(UTC) - step_start).total_seconds() * 1000
                log_entry = f"[{step_name}] exit_code={result.returncode} ({step_duration:.0f}ms)"
                logs.append(log_entry)

                if result.returncode == 0:
                    step_status = "passed"
                    passed_weight += weight
                    errors: list[dict] = []
                else:
                    step_status = "failed" if step_cfg.get("critical", False) else "warning"
                    errors = _extract_errors(result.stderr or result.stdout, step_name)
                    all_errors.extend(errors)

                sr = StepResult(
                    step_name=step_name,
                    status=step_status,
                    exit_code=result.returncode,
                    stdout=result.stdout[:5000],
                    stderr=result.stderr[:5000],
                    duration_ms=step_duration,
                    errors=errors,
                )
                step_results.append(sr)

                if step_status == "failed" and self.fail_fast and is_critical:
                    logs.append(f"[pipeline] FAIL_FAST: {step_name} failed, stopping pipeline")
                    break

            except subprocess.TimeoutExpired:
                step_duration = (datetime.now(UTC) - step_start).total_seconds() * 1000
                logs.append(f"[{step_name}] TIMEOUT after {timeout}s")
                all_errors.append({"step": step_name, "type": "timeout", "message": f"Timed out after {timeout}s"})
                sr = StepResult(
                    step_name=step_name, status="failed", exit_code=-1,
                    stderr=f"Command timed out after {timeout}s",
                    duration_ms=step_duration,
                    errors=[{"step": step_name, "type": "timeout", "message": f"Timed out after {timeout}s"}],
                )
                step_results.append(sr)
                if self.fail_fast and is_critical:
                    break

            except Exception as e:
                logs.append(f"[{step_name}] ERROR: {e}")
                all_errors.append({"step": step_name, "type": "exception", "message": str(e)})
                sr = StepResult(
                    step_name=step_name, status="failed", exit_code=-1,
                    stderr=str(e), errors=[{"step": step_name, "type": "exception", "message": str(e)}],
                )
                step_results.append(sr)

        total_duration = (datetime.now(UTC) - start).total_seconds() * 1000
        score = (passed_weight / total_weight * 100) if total_weight > 0 else 0
        overall = "verified" if score >= self.score_threshold else "failed"

        return VerificationOutput(
            task_id=task_id,
            mode=mode,
            status=overall,
            score=round(score, 1),
            steps=step_results,
            errors=all_errors,
            logs="\n".join(logs),
            duration_ms=total_duration,
        )


def _extract_errors(output: str, step_name: str) -> list[dict]:
    errors = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(kw in lower for kw in ["error:", "traceback", "failed", "exception", "syntaxerror"]):
            errors.append({"step": step_name, "type": "error", "message": line[:500]})
        elif any(kw in lower for kw in ["warning:", "deprecated"]):
            errors.append({"step": step_name, "type": "warning", "message": line[:500]})
    return errors[:20]
