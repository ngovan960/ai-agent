"""Tests for OpenCode LLM Client."""

from unittest.mock import AsyncMock, patch

import pytest

from services.execution.opencode_llm_client import OpenCodeAPIError, OpenCodeLLMClient


class TestOpenCodeLLMClient:
    def test_init_defaults(self):
        client = OpenCodeLLMClient()
        assert client.api_url == "http://localhost:8080"
        assert client.api_key == ""
        assert client.timeout == 120
        assert client.max_retries == 3

    def test_init_custom(self):
        client = OpenCodeLLMClient(
            api_url="http://custom:9000",
            api_key="test-key",
            timeout=60,
            max_retries=5,
        )
        assert client.api_url == "http://custom:9000"
        assert client.api_key == "test-key"
        assert client.timeout == 60
        assert client.max_retries == 5

    def test_build_headers_no_key(self):
        client = OpenCodeLLMClient()
        headers = client._build_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_build_headers_with_key(self):
        client = OpenCodeLLMClient(api_key="secret")
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer secret"

    def test_parse_response_standard_format(self):
        client = OpenCodeLLMClient()
        data = {
            "choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "cost_usd": 0.001,
        }
        resp = client._parse_response(data, "test-model", 100.0)
        assert resp.content == "Hello"
        assert resp.model == "test-model"
        assert resp.input_tokens == 10
        assert resp.output_tokens == 5
        assert resp.total_tokens == 15
        assert resp.cost_usd == 0.001
        assert resp.latency_ms == 100.0
        assert resp.finish_reason == "stop"

    def test_parse_response_simple_format(self):
        client = OpenCodeLLMClient()
        data = {"content": "Hi", "finish_reason": "length"}
        resp = client._parse_response(data, "test-model", 50.0)
        assert resp.content == "Hi"
        assert resp.finish_reason == "length"

    def test_parse_response_fallback_format(self):
        client = OpenCodeLLMClient()
        data = {"text": "Fallback response"}
        resp = client._parse_response(data, "test-model", 25.0)
        assert resp.content == "Fallback response"

    def test_parse_response_empty(self):
        client = OpenCodeLLMClient()
        data = {}
        resp = client._parse_response(data, "test-model", 10.0)
        assert resp.content == ""

    def test_opencode_api_error(self):
        err = OpenCodeAPIError("Test error", status_code=500)
        assert str(err) == "Test error"
        assert err.status_code == 500


@pytest.mark.asyncio
class TestOpenCodeLLMClientAsync:
    @patch("asyncio.create_subprocess_exec")
    async def test_chat_completion_success(self, mock_exec):
        client = OpenCodeLLMClient()

        # Mock the process returned by create_subprocess_exec
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Test output", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        result = await client.chat_completion("test-model", [{"role": "user", "content": "Hi"}])

        assert result.content == "Test output"
        assert result.model == "test-model"
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.cost_usd == 0.0
        assert result.error is None

    @patch("asyncio.create_subprocess_exec")
    async def test_chat_completion_error_returns_error_response(self, mock_exec):
        client = OpenCodeLLMClient(max_retries=1)

        # Mock the process returned by create_subprocess_exec to fail
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Error output", b"Connection refused")
        mock_process.returncode = 1
        mock_exec.return_value = mock_process

        result = await client.chat_completion("test-model", [{"role": "user", "content": "Hi"}])

        assert result.content == "Error output"
        assert result.error is not None
        assert "Connection refused" in result.error

    async def test_close(self):
        client = OpenCodeLLMClient()
        await client.close()  # Should not raise even if no session
