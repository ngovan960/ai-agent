import asyncio
import logging
import time
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class CLIResult:
    status: str
    output: str
    error: str | None = None
    duration_ms: float = 0.0


class OpenCodeCLIRunner:
    def __init__(self, project_root: str = "."):
        self.project_root = project_root

    async def execute(self, prompt: str) -> CLIResult:
        start_time = time.time()
        
        try:
            # Run opencode CLI with the prompt and auto-approve permissions
            process = await asyncio.create_subprocess_exec(
                "opencode", "run", "--dangerously-skip-permissions", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root
            )
            
            stdout, stderr = await process.communicate()
            duration_ms = (time.time() - start_time) * 1000
            
            output_str = stdout.decode('utf-8') if stdout else ""
            error_str = stderr.decode('utf-8') if stderr else ""
            
            if process.returncode == 0:
                return CLIResult(
                    status="completed",
                    output=output_str,
                    error=error_str if error_str else None,
                    duration_ms=duration_ms
                )
            else:
                logger.error(f"opencode CLI failed with code {process.returncode}: {error_str}")
                return CLIResult(
                    status="failed",
                    output=output_str,
                    error=error_str,
                    duration_ms=duration_ms
                )
                
        except Exception as e:
            logger.exception(f"Error executing opencode CLI: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return CLIResult(
                status="failed",
                output="",
                error=str(e),
                duration_ms=duration_ms
            )
