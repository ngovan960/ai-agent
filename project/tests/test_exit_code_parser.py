from services.orchestrator.services.exit_code_parser import (
    ErrorInfo,
    ParsedTestSummary,
    extract_errors,
    parse_exit_code,
    parse_test_results,
    update_verification_status,
)


class TestParseExitCode:
    def test_zero_verified(self):
        assert parse_exit_code(0) == "verified"

    def test_nonzero_failed(self):
        assert parse_exit_code(1) == "failed"
        assert parse_exit_code(-1) == "failed"
        assert parse_exit_code(255) == "failed"


class TestExtractErrors:
    def test_no_errors(self):
        errors = extract_errors("All good", "All good", "lint")
        assert len(errors) == 0

    def test_error_extraction(self):
        errors = extract_errors(
            "File 'test.py', line 10, in func\nError: something broke",
            "",
            "lint",
        )
        assert len(errors) >= 1
        assert any("test.py" in e.location for e in errors)

    def test_warning_extraction(self):
        errors = extract_errors(
            "Warning: deprecated call",
            "",
            "lint",
        )
        warnings = [e for e in errors if e.error_type == "warning"]
        assert len(warnings) >= 1

    def test_traceback_extraction(self):
        errors = extract_errors(
            "Traceback (most recent call last):\n  File 'app.py', line 5\nValueError: bad value",
            "",
            "test",
        )
        assert len(errors) >= 1

    def test_result_type(self):
        errors = extract_errors("Error: test", "", "lint")
        assert all(isinstance(e, ErrorInfo) for e in errors)


class TestParseTestResults:
    def test_empty_output(self):
        summary = parse_test_results("")
        assert summary.passed == 0
        assert summary.total == 0

    def test_pytest_output(self):
        output = "= 10 passed, 2 failed, 1 skipped in 5.00s ="
        summary = parse_test_results(output)
        assert summary.passed == 10
        assert summary.failed == 2
        assert summary.skipped == 1

    def test_result_type(self):
        summary = parse_test_results("")
        assert isinstance(summary, ParsedTestSummary)

    def test_json_output(self):
        output = '{"passed": 5, "failed": 1, "num_tests": 6}'
        summary = parse_test_results(output)
        assert summary.passed == 5 or summary.total == 6


class TestUpdateVerificationStatus:
    def test_verified(self):
        assert update_verification_status("verified", 100) == "VERIFIED"

    def test_partial(self):
        assert update_verification_status("failed", 80) == "PARTIAL"

    def test_failed(self):
        assert update_verification_status("failed", 30) == "FAILED"
