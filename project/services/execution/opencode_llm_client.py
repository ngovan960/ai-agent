"""
OpenCode LLM Client - AI SDLC System

Calls OpenCode's LLM API directly for all model requests.
Replaces LiteLLM as the sole LLM provider.

All LLM calls go through OpenCode, which manages model routing,
rate limiting, and cost tracking internally.
"""

import asyncio
import contextlib
import json
import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    error: str | None = None


class OpenCodeLLMClient:
    """
    LLM client that calls OpenCode's API directly.

    OpenCode provides a unified API endpoint for all models.
    The model parameter determines which backend model is used.
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 120,
        max_retries: int = 3,
    ):
        self.api_url = api_url or os.environ.get("OPENCODE_API_URL", "http://localhost:8080")
        self.api_key = api_key or os.environ.get("OPENCODE_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = None

    async def _ensure_session(self):
        """Create aiohttp session if not exists."""
        is_closed = getattr(self._session, "is_closed", getattr(self._session, "closed", True))
        if self._session is None or is_closed:
            try:
                import aiohttp
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers=self._build_headers(),
                )
            except ImportError:
                # Fallback: use httpx if aiohttp not available
                import httpx
                self._session = httpx.AsyncClient(
                    timeout=self.timeout,
                    headers=self._build_headers(),
                )

    def _build_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat_completion(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 8192,
        top_p: float = 1.0,
        stop: list[str] | None = None,
        timeout: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Call OpenCode LLM API with chat completion.

        Args:
            model: Model name (e.g., "qwen-3.6-plus", "deepseek-v4-pro")
            messages: List of {role, content} dicts
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            **kwargs: Additional parameters passed to API

        Returns:
            LLMResponse with content, tokens, cost, latency
        """
        start = time.monotonic()
        effective_timeout = timeout or self.timeout
        
        # Convert messages to a single prompt string
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            prompt_parts.append(f"[{role}]\n{content}")
        
        full_prompt = "\n\n".join(prompt_parts)

        try:
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "opencode", "run", "--dangerously-skip-permissions", full_prompt,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=effective_timeout,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=effective_timeout,
            )
        except TimeoutError:
            return LLMResponse(
                content="",
                model=model,
                latency_ms=(time.monotonic() - start) * 1000,
                error=f"OpenCode CLI timed out after {effective_timeout}s",
            )
        
        latency_ms = (time.monotonic() - start) * 1000
        output_str = stdout.decode('utf-8') if stdout else ""
        error_str = stderr.decode('utf-8') if stderr else ""
        
        if process.returncode != 0:
            logger.warning(f"OpenCode CLI call failed: {error_str}")
            return LLMResponse(
                content=output_str,
                model=model,
                latency_ms=latency_ms,
                error=error_str or f"opencode failed with code {process.returncode}"
            )
            
        return LLMResponse(
            content=output_str,
            model=model,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cost_usd=0.0,
            latency_ms=latency_ms,
            finish_reason="stop"
        )

    async def _post(self, path: str, payload: dict) -> dict:
        """Make POST request to OpenCode API."""
        url = f"{self.api_url}{path}"

        # Try aiohttp first, fall back to httpx
        try:
            import aiohttp  # noqa: F401
            if hasattr(self._session, 'post'):
                async with self._session.post(url, json=payload) as resp:
                    body = await resp.text()
                    if resp.status >= 400:
                        raise OpenCodeAPIError(
                            f"API error {resp.status}: {body}",
                            status_code=resp.status,
                        )
                    return json.loads(body)
        except ImportError:
            pass

        # Fallback to httpx
        try:
            import httpx  # noqa: F401
            if hasattr(self._session, 'post'):
                resp = await self._session.post(url, json=payload)
                if resp.status_code >= 400:
                    raise OpenCodeAPIError(
                        f"API error {resp.status_code}: {resp.text}",
                        status_code=resp.status_code,
                    )
                return resp.json()
        except ImportError:
            pass

        # Final fallback: use subprocess to curl (for environments without async HTTP libs)
        return await self._curl_fallback(url, payload)

    async def _curl_fallback(self, url: str, payload: dict) -> dict:
        """Fallback: use curl via subprocess for HTTP requests."""
        import subprocess

        cmd = [
            "curl", "-s", "-X", "POST", url,
            "-H", "Content-Type: application/json",
        ]
        if self.api_key:
            cmd.extend(["-H", f"Authorization: Bearer {self.api_key}"])
        cmd.extend(["-d", json.dumps(payload)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
        if result.returncode != 0:
            raise OpenCodeAPIError(f"curl failed: {result.stderr}")

        data = json.loads(result.stdout)
        if isinstance(data, dict) and data.get("error"):
            raise OpenCodeAPIError(f"API error: {data['error']}")
        return data

    def _parse_response(self, data: dict, model: str, latency_ms: float) -> LLMResponse:
        """Parse OpenCode API response into LLMResponse."""
        # Standard OpenAI-compatible format
        if "choices" in data:
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason", "stop")
        elif "content" in data:
            content = data["content"]
            finish_reason = data.get("finish_reason", "stop")
        else:
            content = data.get("text", "")
            finish_reason = "stop"

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        cost = data.get("cost_usd", 0.0)

        return LLMResponse(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
        )

    async def close(self):
        """Close HTTP session."""
        if self._session is not None:
            with contextlib.suppress(Exception):
                if hasattr(self._session, 'closed') and not self._session.closed:
                    await self._session.close()
                elif hasattr(self._session, 'is_closed') and not self._session.is_closed:
                    await self._session.aclose()
            self._session = None

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, *args):
        await self.close()


class OpenCodeAPIError(Exception):
    """Raised when OpenCode API returns an error."""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code
