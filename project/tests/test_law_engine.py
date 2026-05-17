"""Tests for Architectural Law Engine (Phase 5.2)."""


import pytest

from services.orchestrator.services.law_engine import (
    LawEngine,
)


@pytest.fixture
def laws_yaml_path(tmp_path):
    laws_file = tmp_path / "laws.yaml"
    laws_file.write_text("""
rules:
  - id: LAW-001
    name: No business logic in controller
    severity: high
    description: Controllers must only receive requests and call services.
    check_rule: "controller must not contain business logic"
    category: architecture
  - id: LAW-002
    name: All APIs must validate input
    severity: high
    description: Every API endpoint must validate input.
    check_rule: "all endpoints must have input validation"
    category: security
  - id: LAW-005
    name: No hardcoded secrets
    severity: critical
    description: Secrets must never be hardcoded.
    check_rule: "no hardcoded secrets in source code"
    category: security
""")
    return str(laws_file)


@pytest.fixture
def law_engine(laws_yaml_path):
    return LawEngine(laws_path=laws_yaml_path)


class TestLawLoading:
    def test_load_laws(self, law_engine):
        laws = law_engine.get_laws()
        assert len(laws) == 3

    def test_law_structure(self, law_engine):
        laws = law_engine.get_laws()
        law = laws[0]
        assert law.id == "LAW-001"
        assert law.name == "No business logic in controller"
        assert law.severity == "high"
        assert law.category == "architecture"

    def test_missing_laws_file(self):
        engine = LawEngine(laws_path="/nonexistent/path/laws.yaml")
        assert engine.get_laws() == []


class TestCleanArchitectureCheck:
    def test_controller_with_business_logic(self, law_engine):
        code = """
def get_user(request):
    db.session.query(User).filter_by(id=1).first()
    return response
"""
        violations = law_engine.check_clean_architecture(code, filename="user_controller.py")
        assert len(violations) >= 1
        assert any(v.law_id == "LAW-001" for v in violations)

    def test_controller_without_business_logic(self, law_engine):
        code = """
def get_user(request):
    return user_service.get_user(request.user_id)
"""
        violations = law_engine.check_clean_architecture(code, filename="user_controller.py")
        assert len(violations) == 0

    def test_ui_with_direct_db(self, law_engine):
        code = """
const users = db.query("SELECT * FROM users");
"""
        violations = law_engine.check_clean_architecture(code, filename="template.html")
        assert len(violations) >= 1
        assert any(v.law_id == "LAW-003" for v in violations)

    def test_clean_code(self, law_engine):
        code = """
def get_user(request):
    return user_service.get_user(request.user_id)
"""
        violations = law_engine.check_clean_architecture(code, filename="service.py")
        assert len(violations) == 0


class TestValidationCheck:
    def test_endpoint_without_validation(self, law_engine):
        code = """
def post_create_user(request):
    data = request.body
    return create_user(data)
"""
        violations = law_engine.check_validation(code)
        assert len(violations) >= 1
        assert any(v.law_id == "LAW-002" for v in violations)

    def test_endpoint_with_pydantic(self, law_engine):
        code = """
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str

def post_create_user(data: UserCreate):
    return create_user(data)
"""
        violations = law_engine.check_validation(code)
        assert len(violations) == 0


class TestForbiddenPatterns:
    def test_hardcoded_secret(self, law_engine):
        code = """
API_KEY = "sk-1234567890abcdef"
password = "super_secret_password"
"""
        violations = law_engine.detect_forbidden_patterns(code)
        assert len(violations) >= 1
        assert any(v.law_id == "LAW-005" for v in violations)

    def test_eval_usage(self, law_engine):
        code = """
result = eval(user_input)
"""
        violations = law_engine.detect_forbidden_patterns(code)
        assert len(violations) >= 1

    def test_raw_sql(self, law_engine):
        code = """
cursor.execute("SELECT * FROM users WHERE id = 1")
"""
        violations = law_engine.detect_forbidden_patterns(code)
        assert len(violations) >= 1

    def test_exec_usage(self, law_engine):
        code = """
exec(some_code)
"""
        violations = law_engine.detect_forbidden_patterns(code)
        assert len(violations) >= 1

    def test_clean_code(self, law_engine):
        code = """
import os
API_KEY = os.environ.get("API_KEY")
result = safe_parse(user_input)
"""
        violations = law_engine.detect_forbidden_patterns(code)
        assert len(violations) == 0


class TestComplianceReport:
    def test_compliant_code(self, law_engine):
        code = """
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str

def get_user(request):
    return user_service.get_user(request.user_id)
"""
        report = law_engine.check_compliance(code, filename="service.py")
        assert report.is_compliant
        assert report.violated_count == 0

    def test_non_compliant_code(self, law_engine):
        code = """
API_KEY = "sk-1234567890"
def post_user(request):
    data = request.body
    db.session.query(User).all()
"""
        report = law_engine.check_compliance(code, filename="user_controller.py")
        assert not report.is_compliant
        assert report.violated_count >= 1

    def test_report_violations_format(self, law_engine):
        code = 'password = "secret123"'
        report = law_engine.check_compliance(code)
        violation_report = law_engine.report_violations(report)
        assert violation_report.total_violations >= 1
        assert violation_report.critical_count >= 1
        assert violation_report.violations[0].law_id == "LAW-005"

    def test_violation_location(self, law_engine):
        code = "line1\nline2\neval(bad)\nline4"
        violations = law_engine.detect_forbidden_patterns(code, filename="test.py")
        assert len(violations) >= 1
        assert violations[0].location is not None
        assert "3" in violations[0].location
