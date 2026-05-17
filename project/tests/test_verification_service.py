from uuid import uuid4

import pytest

from services.orchestrator.services.verification_service import (
    VerificationOutput,
    VerificationPipeline,
    _extract_errors,
    detect_language,
)


class TestDetectLanguage:
    def test_detect_python(self, tmp_path):
        (tmp_path / "test.py").write_text("print('hello')")
        assert detect_language(str(tmp_path)) == "python"

    def test_detect_node(self, tmp_path):
        (tmp_path / "index.js").write_text("console.log('hello')")
        assert detect_language(str(tmp_path)) == "node"

    def test_default_python(self, tmp_path):
        (tmp_path / "readme.md").write_text("# Project")
        assert detect_language(str(tmp_path)) == "python"


class TestExtractErrors:
    def test_extract_python_error(self):
        output = "File 'test.py', line 10, in my_function\nError: something broke"
        errors = _extract_errors(output, "lint")
        assert len(errors) > 0

    def test_extract_no_errors(self):
        errors = _extract_errors("All checks passed", "lint")
        assert len(errors) == 0

    def test_extract_warning(self):
        output = "Warning: deprecated function used"
        errors = _extract_errors(output, "lint")
        warnings = [e for e in errors if e.get("type") == "warning"]
        assert len(warnings) > 0


class TestVerificationPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_creation(self):
        pipeline = VerificationPipeline()
        assert pipeline.fail_fast is True
        assert pipeline.max_retries == 2
        assert pipeline.timeout_seconds == 600
        assert pipeline.score_threshold == 60.0

    @pytest.mark.asyncio
    async def test_empty_code_path(self, tmp_path):
        pipeline = VerificationPipeline()
        result = await pipeline.run_pipeline(
            task_id=uuid4(),
            code_path=str(tmp_path),
            mode="dev",
        )
        assert isinstance(result, VerificationOutput)
        assert result.status in ("verified", "failed")
        assert result.score >= 0

    @pytest.mark.asyncio
    async def test_pipeline_with_python_code(self, tmp_path):
        (tmp_path / "test.py").write_text("x = 1\nprint(x)")
        pipeline = VerificationPipeline()
        result = await pipeline.run_pipeline(
            task_id=uuid4(),
            code_path=str(tmp_path),
            mode="dev",
        )
        assert result.task_id is not None
        assert result.mode == "dev"
        assert len(result.steps) > 0

    @pytest.mark.asyncio
    async def test_pipeline_result_structure(self):
        pipeline = VerificationPipeline()
        task_id = uuid4()
        result = await pipeline.run_pipeline(task_id, "/tmp/nonexistent", "prod")
        assert result.task_id == task_id
        assert result.mode == "prod"
        assert isinstance(result.score, float)
        assert isinstance(result.duration_ms, float)
        assert isinstance(result.logs, str)

    @pytest.mark.asyncio
    async def test_pipeline_weight_calculation(self):
        pipeline = VerificationPipeline()
        result = await pipeline.run_pipeline(uuid4(), "/tmp/nonexistent", "dev")
        assert 0 <= result.score <= 100

    def test_detect_language_empty_dir(self, tmp_path):
        assert detect_language(str(tmp_path)) == "python"

    def test_detect_language_mixed(self, tmp_path):
        (tmp_path / "app.py").write_text("")
        (tmp_path / "index.js").write_text("")
        lang = detect_language(str(tmp_path))
        assert lang == "python"
