from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.task import Task, TaskDependency, TaskStatus


async def build_dependency_graph(db: AsyncSession, task_ids: list[UUID]) -> dict[UUID, list[UUID]]:
    """Build a directed dependency graph (adjacency list).
    
    Edge A -> B means A depends on B (B must complete first).
    """
    result = await db.execute(
        select(TaskDependency).where(TaskDependency.task_id.in_(task_ids))
    )
    deps = result.scalars().all()

    graph: dict[UUID, list[UUID]] = defaultdict(list)
    for dep in deps:
        graph[dep.task_id].append(dep.depends_on_task_id)

    for tid in task_ids:
        if tid not in graph:
            graph[tid] = []

    return dict(graph)


async def can_start(db: AsyncSession, task_id: UUID) -> tuple[bool, list[UUID]]:
    """Check if a task can start (all its dependencies are DONE).
    
    Returns:
        Tuple of (can_start, list of blocking dependency IDs)
    """
    result = await db.execute(
        select(TaskDependency).where(TaskDependency.task_id == task_id)
    )
    deps = result.scalars().all()

    if not deps:
        return True, []

    blocked = []
    for dep in deps:
        d_result = await db.execute(
            select(Task.status).where(Task.id == dep.depends_on_task_id)
        )
        dep_status = d_result.scalar_one_or_none()
        if not dep_status or dep_status not in (TaskStatus.DONE,):
            blocked.append(dep.depends_on_task_id)

    return len(blocked) == 0, blocked


async def has_circular_dependency(
    db: AsyncSession, task_id: UUID, candidate_dep_ids: list[UUID]
) -> tuple[bool, list[UUID] | None]:
    """Detect circular dependency using DFS.
    
    Checks if adding candidate_dep_ids as dependencies of task_id
    would create a cycle in the dependency graph.
    
    Returns:
        Tuple of (has_cycle, cycle_path or None)
    """
    result = await db.execute(select(TaskDependency))
    all_deps = result.scalars().all()

    graph: dict[UUID, list[UUID]] = defaultdict(list)
    for dep in all_deps:
        graph[dep.task_id].append(dep.depends_on_task_id)

    for cid in candidate_dep_ids:
        graph[task_id].append(cid)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[UUID, int] = defaultdict(int)
    parent: dict[UUID, UUID | None] = {}

    cycle_path: list[UUID] | None = None

    def dfs(node: UUID) -> bool:
        nonlocal cycle_path
        color[node] = GRAY
        for neighbor in graph.get(node, []):
            if color[neighbor] == GRAY:
                path = [neighbor, node]
                curr = node
                while parent.get(curr) and parent[curr] != neighbor:
                    curr = parent[curr]
                    path.append(curr)
                path.append(neighbor)
                path.reverse()
                cycle_path = path
                return True
            if color[neighbor] == WHITE:
                parent[neighbor] = node
                if dfs(neighbor):
                    return True
        color[node] = BLACK
        return False

    parent[task_id] = None
    if dfs(task_id):
        return True, cycle_path

    return False, None


async def get_task_dependencies(
    db: AsyncSession, task_id: UUID
) -> list[dict]:
    """Get all dependencies of a task with their status."""
    result = await db.execute(
        select(TaskDependency).where(TaskDependency.task_id == task_id)
    )
    deps = result.scalars().all()

    dep_list = []
    for dep in deps:
        d_result = await db.execute(
            select(Task).where(Task.id == dep.depends_on_task_id)
        )
        dep_task = d_result.scalar_one_or_none()
        dep_list.append({
            "dependency_id": dep.id,
            "task_id": str(dep.depends_on_task_id),
            "title": dep_task.title if dep_task else "unknown",
            "status": dep_task.status.value if dep_task and hasattr(dep_task.status, "value") else str(dep_task.status) if dep_task else "unknown",
            "dependency_type": dep.dependency_type,
        })

    return dep_list


async def get_dependent_tasks(
    db: AsyncSession, task_id: UUID
) -> list[dict]:
    """Get all tasks that depend on this task."""
    result = await db.execute(
        select(TaskDependency).where(TaskDependency.depends_on_task_id == task_id)
    )
    deps = result.scalars().all()

    dep_list = []
    for dep in deps:
        d_result = await db.execute(
            select(Task).where(Task.id == dep.task_id)
        )
        waiter = d_result.scalar_one_or_none()
        dep_list.append({
            "dependency_id": dep.id,
            "task_id": str(dep.task_id),
            "title": waiter.title if waiter else "unknown",
            "status": waiter.status.value if waiter and hasattr(waiter.status, "value") else str(waiter.status) if waiter else "unknown",
        })

    return dep_list
