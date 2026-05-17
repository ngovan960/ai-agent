"""Architectural Law Engine — AI SDLC Governance Layer (Phase 5.2)

Loads laws from governance/laws.yaml, checks code for violations,
and reports compliance results.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from uuid import UUID

import yaml

from shared.schemas.law import Law, LawViolationResponse, ViolationReport

logger = logging.getLogger(__name__)

DEFAULT_LAWS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "governance",
    "laws.yaml",
)

FORBIDDEN_PATTERNS = {
    "hardcoded_secret": re.compile(
        r"""(?i)(password|secret|api_key|apikey|token|credentials?)\s*=\s*['"][^'"]{4,}['"]"""
    ),
    "eval_usage": re.compile(r"""(?<!\w)eval\s*\("""),
    "raw_sql": re.compile(
        r"""(?i)(execute|cursor\.execute|raw_query)\s*\(\s*['"](SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)"""
    ),
    "exec_usage": re.compile(r"""(?<!\w)exec\s*\("""),
}

CONTROLLER_PATTERNS = {
    "business_logic_in_controller": re.compile(
        r"""(?i)(db\.session|session\.query|\.save\(|\.delete\(|transaction|commit|rollback)"""
    ),
}

VALIDATION_PATTERNS = {
    "missing_validation": re.compile(
        r"""(?i)def\s+(get|post|put|patch|delete|api)[_\w]*\s*\([^)]*\)\s*:"""
    ),
    "has_pydantic": re.compile(
        r"""(?i)(BaseModel|Field\(|validator|@validator|@field_validator|Annotated\[.*AfterValidator)"""
    ),
}


@dataclass
class LawViolation:
    law_id: str
    law_name: str
    severity: str
    violation_details: str
    location: str | None = None


@dataclass
class ComplianceReport:
    task_id: UUID | None = None
    violations: list[LawViolation] = field(default_factory=list)
    total_laws_checked: int = 0
    passed_laws: int = 0

    @property
    def violated_count(self) -> int:
        return len(self.violations)

    @property
    def is_compliant(self) -> bool:
        return len(self.violations) == 0


class LawEngine:
    """5.2 — Architectural Law Engine."""

    def __init__(self, laws_path: str | None = None):
        self._laws_path = laws_path or DEFAULT_LAWS_PATH
        self._laws: list[dict] = []
        self._custom_laws: list[dict] = []
        self._load_laws()

    def _load_laws(self) -> None:
        """5.2.1 — Load laws from YAML file."""
        if not os.path.exists(self._laws_path):
            logger.warning(f"Laws file not found: {self._laws_path}")
            self._laws = []
            return
        with open(self._laws_path) as f:
            data = yaml.safe_load(f)
        self._laws = data.get("rules", [])
        logger.info(f"Loaded {len(self._laws)} architectural laws")

    def add_law(self, law: Law) -> Law:
        """Add a custom law (in-memory, persists for server lifetime)."""
        law_dict = {
            "id": law.id,
            "name": law.name,
            "severity": law.severity,
            "description": law.description,
            "check_rule": law.check_rule,
            "category": law.category,
        }
        self._custom_laws.append(law_dict)
        logger.info(f"Custom law added: {law.id} — {law.name}")
        return law

    def get_laws(self) -> list[Law]:
        """Get all loaded laws (YAML + custom)."""
        combined = list(self._laws) + self._custom_laws
        return [
            Law(
                id=law["id"],
                name=law["name"],
                severity=law["severity"],
                description=law["description"],
                check_rule=law["check_rule"],
                category=law["category"],
            )
            for law in combined
        ]

    def check_clean_architecture(self, code: str, filename: str | None = None) -> list[LawViolation]:
        """5.2.2 — Check for business logic in controllers and direct DB access from UI."""
        violations = []

        is_controller = filename and ("controller" in filename.lower() or "view" in filename.lower())
        is_ui = filename and any(kw in filename.lower() for kw in ["template", "html", "jsx", "tsx", "vue", "frontend"])

        if is_controller:
            for match in CONTROLLER_PATTERNS["business_logic_in_controller"].finditer(code):
                violations.append(LawViolation(
                    law_id="LAW-001",
                    law_name="No business logic in controller",
                    severity="high",
                    violation_details=f"Business logic pattern found: '{match.group()}'",
                    location=f"{filename}:{self._line_number(code, match.start())}" if filename else None,
                ))

        if is_ui:
            db_pattern = re.compile(r"""(?i)(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\s+""")
            for match in db_pattern.finditer(code):
                violations.append(LawViolation(
                    law_id="LAW-003",
                    law_name="No direct DB access from UI",
                    severity="high",
                    violation_details=f"Direct DB query found: '{match.group().strip()}'",
                    location=f"{filename}:{self._line_number(code, match.start())}" if filename else None,
                ))

        return violations

    def check_validation(self, code: str, filename: str | None = None) -> list[LawViolation]:
        """5.2.3 — Check that API endpoints have input validation."""
        violations = []
        has_validation = bool(VALIDATION_PATTERNS["has_pydantic"].search(code))
        has_endpoints = bool(VALIDATION_PATTERNS["missing_validation"].search(code))

        if has_endpoints and not has_validation:
            violations.append(LawViolation(
                law_id="LAW-002",
                law_name="All APIs must validate input",
                severity="high",
                violation_details="API endpoints found without Pydantic or equivalent validation",
                location=filename,
            ))

        return violations

    def detect_forbidden_patterns(self, code: str, filename: str | None = None) -> list[LawViolation]:
        """5.2.4 — Detect hardcoded secrets, eval(), raw SQL, etc."""
        violations = []

        LAW_ID_MAP = {
            "hardcoded_secret": "LAW-005",
            "eval_usage": "LAW-006",
            "raw_sql": "LAW-007",
            "exec_usage": "LAW-008",
        }
        for pattern_name, pattern in FORBIDDEN_PATTERNS.items():
            for match in pattern.finditer(code):
                law_id = LAW_ID_MAP.get(pattern_name, "LAW-005")
                violations.append(LawViolation(
                    law_id=law_id,
                    law_name="No hardcoded secrets" if pattern_name == "hardcoded_secret" else f"Forbidden pattern: {pattern_name}",
                    severity="critical" if pattern_name == "hardcoded_secret" else "high",
                    violation_details=f"Found forbidden pattern '{pattern_name}': '{match.group()}'",
                    location=f"{filename}:{self._line_number(code, match.start())}" if filename else None,
                ))

        return violations

    def check_compliance(
        self,
        code: str,
        filename: str | None = None,
        task_id: UUID | None = None,
    ) -> ComplianceReport:
        """Run all applicable law checks and return a compliance report."""
        all_violations: list[LawViolation] = []

        all_violations.extend(self.check_clean_architecture(code, filename))
        all_violations.extend(self.check_validation(code, filename))
        all_violations.extend(self.detect_forbidden_patterns(code, filename))

        return ComplianceReport(
            task_id=task_id,
            violations=all_violations,
            total_laws_checked=len(self._laws),
            passed_laws=len(self._laws) - len(set(v.law_id for v in all_violations)),
        )

    def report_violations(self, report: ComplianceReport) -> ViolationReport:
        """5.2.5 — Format violations into a report."""
        violation_responses = [
            LawViolationResponse(
                task_id=report.task_id,
                law_id=v.law_id,
                law_name=v.law_name,
                severity=v.severity,
                violation_details=v.violation_details,
                location=v.location,
            )
            for v in report.violations
        ]

        critical = sum(1 for v in report.violations if v.severity == "critical")
        high = sum(1 for v in report.violations if v.severity == "high")
        medium = sum(1 for v in report.violations if v.severity == "medium")

        return ViolationReport(
            task_id=report.task_id,
            violations=violation_responses,
            total_violations=len(report.violations),
            critical_count=critical,
            high_count=high,
            medium_count=medium,
        )

    @staticmethod
    def _line_number(code: str, char_index: int) -> int:
        """Get line number from character index."""
        return code[:char_index].count("\n") + 1
