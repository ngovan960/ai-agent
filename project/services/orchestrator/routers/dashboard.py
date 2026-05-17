"""7.4 — Dashboard API: real-time WebSocket + aggregation endpoints."""

import asyncio
import json
import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.project import Project
from shared.models.registry import AuditLog, CostTracking, Decision, MentorInstruction
from shared.models.task import Task, TaskStatus
from shared.observability.metrics import get_metrics

logger = logging.getLogger(__name__)

router = APIRouter()

active_connections: list[WebSocket] = []
_ws_lock = asyncio.Lock()
_cache: dict[str, tuple[float, dict]] = {}
_cache_ttl = 15
_rate_limit: dict[str, list[float]] = defaultdict(list)
_rate_limit_max = 30
_rate_limit_window = 60


def _rate_check(key: str) -> bool:
    now = time.time()
    window = [t for t in _rate_limit[key] if now - t < _rate_limit_window]
    _rate_limit[key] = window
    if len(window) >= _rate_limit_max:
        return False
    _rate_limit[key].append(now)
    return True


async def _cached_or_fetch(cache_key: str, fetcher, ttl: int = _cache_ttl):
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key][0] < ttl:
        return _cache[cache_key][1]
    result = await fetcher()
    _cache[cache_key] = (now, result)
    return result


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                msg = json.loads(data)
                await websocket.send_json({"type": "ack", "data": msg})
            except TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except (WebSocketDisconnect, Exception) as e:
        logger.warning("WebSocket error: %s", e)
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast(message: dict):
    async with _ws_lock:
        disconnected = []
        for conn in active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            active_connections.remove(conn)


@router.get("/dashboard/summary")
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    if not _rate_check("summary"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})
    async def _fetch():
        project_count = (await db.execute(select(func.count()).select_from(Project))).scalar()
        task_count = (await db.execute(select(func.count()).select_from(Task))).scalar()
        active_tasks = (await db.execute(
            select(func.count()).select_from(Task).where(
                Task.status.in_([
                    TaskStatus.ANALYZING, TaskStatus.PLANNING,
                    TaskStatus.IMPLEMENTING, TaskStatus.VERIFYING, TaskStatus.REVIEWING,
                ])
            )
        )).scalar()
        instructions_count = (await db.execute(select(func.count()).select_from(MentorInstruction))).scalar()
        decisions_count = (await db.execute(select(func.count()).select_from(Decision))).scalar()
        cost_total = (await db.execute(select(func.coalesce(func.sum(CostTracking.cost_usd), 0)))).scalar()
        return {
            "projects": project_count,
            "tasks": task_count,
            "active_tasks": active_tasks,
            "instructions": instructions_count,
            "decisions": decisions_count,
            "total_cost": round(float(cost_total), 4),
        }
    return await _cached_or_fetch("dashboard_summary", _fetch)


@router.get("/dashboard/tasks-by-status")
async def tasks_by_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task.status, func.count()).group_by(Task.status)
    )
    rows = result.fetchall()
    return [{"status": row[0].value if hasattr(row[0], "value") else str(row[0]), "count": row[1]} for row in rows]


@router.get("/dashboard/cost-breakdown")
async def cost_breakdown(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CostTracking.model, func.sum(CostTracking.cost_usd))
        .group_by(CostTracking.model)
    )
    rows = result.fetchall()
    return [{"model": row[0], "cost": round(float(row[1]), 4)} for row in rows]


@router.get("/dashboard/recent-activity")
async def recent_activity(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "actor": log.actor,
            "result": log.result.value if hasattr(log.result, "value") else str(log.result),
            "message": log.message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/metrics")
async def prometheus_metrics():
    return get_metrics()
