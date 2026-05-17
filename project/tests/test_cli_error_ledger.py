"""Tests for CLI Error Ledger (Security Fix #3)."""

from uuid import uuid4

from services.execution.cli_error_ledger import CliErrorLedger


class TestErrorRecording:
    def setup_method(self):
        self.ledger = CliErrorLedger()
        self.task_id = uuid4()

    def test_record_syntax_error(self):
        record = self.ledger.record_error(
            task_id=self.task_id,
            file_path="src/main.py",
            command="pytest tests/test_main.py",
            exit_code=1,
            error_message="SyntaxError: invalid syntax on line 10",
        )
        assert record.error_type == "SyntaxError"
        assert record.file_path == "src/main.py"
        assert record.exit_code == 1

    def test_record_import_error(self):
        record = self.ledger.record_error(
            task_id=self.task_id,
            file_path="src/utils.py",
            command="python src/utils.py",
            exit_code=1,
            error_message="ModuleNotFoundError: No module named 'flask'",
        )
        assert record.error_type == "ImportError"

    def test_record_assertion_error(self):
        record = self.ledger.record_error(
            task_id=self.task_id,
            file_path="tests/test_main.py",
            command="pytest tests/test_main.py",
            exit_code=1,
            error_message="AssertionError: assert 1 == 2",
        )
        assert record.error_type == "AssertionError"

    def test_record_lint_error(self):
        record = self.ledger.record_error(
            task_id=self.task_id,
            file_path="src/main.py",
            command="ruff check src/main.py",
            exit_code=1,
            error_message="F401: 'os' imported but unused",
        )
        assert record.error_type == "LintError"

    def test_record_test_failure(self):
        record = self.ledger.record_error(
            task_id=self.task_id,
            file_path="tests/test_main.py",
            command="pytest tests/",
            exit_code=1,
            error_message="FAILED tests/test_main.py::test_something",
        )
        assert record.error_type == "TestFailure"

    def test_record_unknown_error(self):
        record = self.ledger.record_error(
            task_id=self.task_id,
            file_path="src/main.py",
            command="python src/main.py",
            exit_code=1,
            error_message="Something went wrong",
        )
        assert record.error_type == "UnknownError"

    def test_error_message_truncated(self):
        long_message = "x" * 10000
        record = self.ledger.record_error(
            task_id=self.task_id,
            file_path="src/main.py",
            command="pytest",
            exit_code=1,
            error_message=long_message,
        )
        assert len(record.error_message) <= 5000


class TestFileHistoryCheck:
    def setup_method(self):
        self.ledger = CliErrorLedger()
        self.task_id = uuid4()

    def test_find_matching_file(self):
        self.ledger.record_error(
            task_id=self.task_id,
            file_path="src/main.py",
            command="pytest",
            exit_code=1,
            error_message="SyntaxError",
        )
        matches = self.ledger.check_file_history("src/main.py")
        assert len(matches) == 1

    def test_no_matching_file(self):
        self.ledger.record_error(
            task_id=self.task_id,
            file_path="src/main.py",
            command="pytest",
            exit_code=1,
            error_message="SyntaxError",
        )
        matches = self.ledger.check_file_history("src/other.py")
        assert len(matches) == 0

    def test_partial_match(self):
        self.ledger.record_error(
            task_id=self.task_id,
            file_path="src/main.py",
            command="pytest",
            exit_code=1,
            error_message="SyntaxError",
        )
        matches = self.ledger.check_file_history("src/main.py.bak")
        assert len(matches) >= 1


class TestWarningsGeneration:
    def setup_method(self):
        self.ledger = CliErrorLedger()
        self.task_id = uuid4()

    def test_generate_warnings(self):
        self.ledger.record_error(
            task_id=self.task_id,
            file_path="src/main.py",
            command="pytest tests/test_main.py",
            exit_code=1,
            error_message="SyntaxError: invalid syntax",
        )
        warnings = self.ledger.get_warnings_for_task(["src/main.py"])
        assert len(warnings) == 1
        assert "src/main.py" in warnings[0]
        assert "SyntaxError" in warnings[0]

    def test_no_warnings_for_clean_file(self):
        warnings = self.ledger.get_warnings_for_task(["src/clean.py"])
        assert len(warnings) == 0


class TestErrorStats:
    def setup_method(self):
        self.ledger = CliErrorLedger()

    def test_stats_empty(self):
        stats = self.ledger.get_stats()
        assert stats["total_errors"] == 0

    def test_stats_with_errors(self):
        task_id_1 = uuid4()
        task_id_2 = uuid4()
        self.ledger.record_error(task_id_1, "src/main.py", "pytest", 1, "SyntaxError")
        self.ledger.record_error(task_id_1, "src/utils.py", "ruff check", 1, "LintError")
        self.ledger.record_error(task_id_2, "src/main.py", "pytest", 1, "AssertionError")

        stats = self.ledger.get_stats()
        assert stats["total_errors"] == 3
        assert stats["unique_files"] == 2
        assert stats["unique_tasks"] == 2
        assert stats["by_type"]["SyntaxError"] == 1
        assert stats["by_type"]["LintError"] == 1
        assert stats["by_type"]["AssertionError"] == 1


class TestErrorRetrieval:
    def setup_method(self):
        self.ledger = CliErrorLedger()
        self.task_id = uuid4()

    def test_get_recent_errors(self):
        for i in range(15):
            self.ledger.record_error(
                task_id=self.task_id,
                file_path=f"src/file{i}.py",
                command="pytest",
                exit_code=1,
                error_message="Error",
            )
        recent = self.ledger.get_recent_errors(limit=5)
        assert len(recent) == 5

    def test_get_errors_by_type(self):
        self.ledger.record_error(self.task_id, "src/a.py", "pytest", 1, "SyntaxError")
        self.ledger.record_error(self.task_id, "src/b.py", "pytest", 1, "SyntaxError")
        self.ledger.record_error(self.task_id, "src/c.py", "ruff", 1, "LintError")

        syntax_errors = self.ledger.get_errors_by_type("SyntaxError")
        assert len(syntax_errors) == 2

    def test_get_all_errors(self):
        self.ledger.record_error(self.task_id, "src/a.py", "pytest", 1, "Error")
        all_errors = self.ledger.get_all_errors()
        assert len(all_errors) == 1


class TestClearErrors:
    def setup_method(self):
        self.ledger = CliErrorLedger()

    def test_clear_errors_for_task(self):
        task_id_1 = uuid4()
        task_id_2 = uuid4()
        self.ledger.record_error(task_id_1, "src/a.py", "pytest", 1, "Error")
        self.ledger.record_error(task_id_1, "src/b.py", "pytest", 1, "Error")
        self.ledger.record_error(task_id_2, "src/c.py", "pytest", 1, "Error")

        cleared = self.ledger.clear_errors_for_task(task_id_1)
        assert cleared == 2
        assert self.ledger.get_stats()["total_errors"] == 1
