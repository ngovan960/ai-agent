import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ErrorInfo:
    step: str
    error_type: str
    location: str = ""
    description: str = ""


@dataclass
class ParsedTestSummary:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total: int = 0


def parse_exit_code(exit_code: int) -> str:
    return "verified" if exit_code == 0 else "failed"


def extract_errors(stdout: str, stderr: str, step_name: str = "") -> list[ErrorInfo]:
    errors: list[ErrorInfo] = []
    text = f"{stderr}\n{stdout}"

    for match in re.finditer(
        r'(?:File\s+["\']([^"\']+)["\'],\s*line\s+(\d+)|(?:(Error|Exception|Traceback|SyntaxError|TypeError|ValueError|KeyError|IndexError|AttributeError|ImportError|ModuleNotFoundError))\b\s*:\s*(.+))',
        text,
    ):
        location = ""
        desc = ""
        err_type = "error"

        if match.group(1):
            location = f"{match.group(1)}:{match.group(2)}"
            err_type = "syntax_error"
            desc = text[max(0, match.start() - 50):match.end() + 100]
        elif match.group(3):
            err_type = match.group(3).lower()
            desc = match.group(4) if match.group(4) else match.group(3)

        if desc:
            errors.append(ErrorInfo(step=step_name, error_type=err_type, location=location, description=desc[:500]))

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if "warning:" in lower:
            errors.append(ErrorInfo(step=step_name, error_type="warning", description=line[:500]))
        elif "deprecationwarning" in lower.replace(" ", ""):
            errors.append(ErrorInfo(step=step_name, error_type="deprecation", description=line[:500]))

    return errors[:30]


def parse_test_results(output: str) -> ParsedTestSummary:
    summary = ParsedTestSummary()

    pytest_match = re.search(r"=+\s*(\d+)\s+passed", output)
    if pytest_match:
        summary.passed = int(pytest_match.group(1))

    failed_match = re.search(r"(\d+)\s+failed", output)
    if failed_match:
        summary.failed = int(failed_match.group(1))

    skipped_match = re.search(r"(\d+)\s+skipped", output)
    if skipped_match:
        summary.skipped = int(skipped_match.group(1))

    error_match = re.search(r"(\d+)\s+errors?", output)
    if error_match:
        summary.errors = int(error_match.group(1))

    summary.total = summary.passed + summary.failed + summary.skipped + summary.errors

    try:
        data = json.loads(output)
        if isinstance(data, dict):
            summary.passed = data.get("passed", data.get("num_passed", summary.passed))
            summary.failed = data.get("failed", data.get("num_failed", summary.failed))
            summary.total = data.get("total", data.get("num_tests", summary.total))
    except (json.JSONDecodeError, TypeError):
        pass

    return summary


def update_verification_status(
    result_status: str,
    score: float,
    score_threshold: float = 60.0,
) -> str:
    if result_status == "verified":
        return "VERIFIED"
    if score >= score_threshold:
        return "PARTIAL"
    return "FAILED"
