"""Context Builder — builds agent context with summarization and sliding window."""

import logging
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.module import Module
from shared.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKENS = 8000
SUMMARY_TOKEN_BUDGET = 2000
LAWS_PATH = Path(__file__).parent.parent.parent / "shared" / "config" / "laws.yaml"


async def load_memory_context(db: AsyncSession, task_spec: str) -> dict:
    try:
        result = await db.execute(
            select(Task).where(Task.status == TaskStatus.DONE).order_by(Task.completed_at.desc()).limit(5)
        )
        done_tasks = result.scalars().all()
        return {
            "recent_completed_tasks": [
                {"id": str(t.id), "title": t.title, "description": (t.description or "")[:200]}
                for t in done_tasks
            ]
        }
    except Exception as e:
        logger.warning(f"Failed to load memory context: {e}")
        return {"recent_completed_tasks": []}


def load_laws_context() -> dict:
    try:
        if LAWS_PATH.exists():
            with open(LAWS_PATH) as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load laws.yaml: {e}")
    return {"laws": []}


async def build_context(db: AsyncSession, task_id: UUID) -> dict:
    task = await db.get(Task, task_id)
    if not task:
        return {"error": "Task not found"}

    context = {"task": await _load_task_context(task)}
    if task.module_id:
        context["module"] = await _load_module_context(db, task.module_id)
    context["memory"] = await load_memory_context(db, task.description or task.title)
    context["laws"] = load_laws_context()
    task_spec_str = str(context)
    if _estimate_tokens(task_spec_str) > MAX_CONTEXT_TOKENS:
        context = trim_context(context, MAX_CONTEXT_TOKENS)
    return context


async def _load_task_context(task: Task) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "description": (task.description or "")[:500],
        "expected_output": (task.expected_output or "")[:500],
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "priority": task.priority.value if hasattr(task.priority, "value") else str(task.priority),
        "risk_level": task.risk_level.value if hasattr(task.risk_level, "value") else str(task.risk_level),
    }


async def _load_module_context(db: AsyncSession, module_id: UUID) -> dict:
    module = await db.get(Module, module_id)
    if not module:
        return {}
    result = await db.execute(select(Task).where(Task.module_id == module_id))
    tasks = result.scalars().all()
    return {
        "id": str(module.id),
        "name": module.name,
        "description": (module.description or "")[:300],
        "status": module.status.value if hasattr(module.status, "value") else str(module.status),
        "tasks": [
            {"id": str(t.id), "title": t.title, "status": t.status.value if hasattr(t.status, "value") else str(t.status)}
            for t in tasks[:10]
        ],
    }


def _estimate_tokens(text: str) -> int:
    return len(text) // 2


def _summarize_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    marker = f" [... truncated {len(text) - max_chars} chars ...] "
    available = max_chars - len(marker)
    half = max(1, available // 2)
    return text[:half] + marker + text[-half:]


def trim_context(context: dict, max_tokens: int = MAX_CONTEXT_TOKENS) -> dict:
    """Priority-based trimming with summarization for overflow sections."""
    trimmed = {}
    section_priority = ["task", "laws", "module", "memory"]

    for key in section_priority:
        if key not in context:
            continue

        if max_tokens <= 0:
            trimmed[key] = f"[{key} section omitted due to context limit]"
            continue

        val = context[key]
        val_str = str(val)
        estimated = _estimate_tokens(val_str)

        if estimated <= max_tokens:
            trimmed[key] = val
            max_tokens -= estimated
        elif estimated <= max_tokens + SUMMARY_TOKEN_BUDGET:
            summarized = _summarize_text(val_str, max_tokens * 2)
            trimmed[key] = summarized
            max_tokens = 0
        else:
            trimmed[key] = val_str[:max_tokens * 2]
            max_tokens = 0

    return trimmed
