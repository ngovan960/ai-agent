import logging
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.task import TaskDependency

logger = logging.getLogger(__name__)


class DependencyGraph:
    def __init__(self):
        self._graph: dict[UUID, set[UUID]] = defaultdict(set)
        self._reverse: dict[UUID, set[UUID]] = defaultdict(set)

    def add_dependency(self, task_id: UUID, depends_on: UUID):
        self._graph[task_id].add(depends_on)
        self._reverse[depends_on].add(task_id)

    def remove_dependency(self, task_id: UUID, depends_on: UUID):
        self._graph[task_id].discard(depends_on)
        self._reverse[depends_on].discard(task_id)

    def has_circular(self, task_id: UUID, depends_on: UUID) -> bool:
        visited = set()
        stack = [depends_on]
        while stack:
            node = stack.pop()
            if node == task_id:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(self._reverse.get(node, set()))
        return False

    def get_dependencies(self, task_id: UUID) -> set[UUID]:
        return self._graph.get(task_id, set())

    def get_dependents(self, task_id: UUID) -> set[UUID]:
        return self._reverse.get(task_id, set())

    def can_start(self, task_id: UUID, completed: set[UUID]) -> bool:
        deps = self._graph.get(task_id, set())
        return deps.issubset(completed)


_graph_store: dict[str, DependencyGraph] = {}


def clear_dependency_cache():
    _graph_store.clear()


async def build_dependency_graph(db: AsyncSession, project_id: UUID | None = None) -> DependencyGraph:
    key = str(project_id) if project_id else "__global__"
    if key in _graph_store:
        return _graph_store[key]

    graph = DependencyGraph()
    if project_id:
        from shared.models.task import Task
        query = select(TaskDependency).join(Task, Task.id == TaskDependency.task_id).where(Task.project_id == project_id)
    else:
        query = select(TaskDependency)
        
    result = await db.execute(query)
    deps = result.scalars().all()
    for dep in deps:
        graph.add_dependency(dep.task_id, dep.depends_on_task_id)
        
    _graph_store[key] = graph
    return graph


async def check_circular(db: AsyncSession, task_id: UUID, depends_on_id: UUID) -> bool:
    graph = await build_dependency_graph(db)
    return graph.has_circular(task_id, depends_on_id)


async def can_start_task(db: AsyncSession, task_id: UUID) -> bool:
    from shared.models.task import Task, TaskStatus
    graph = await build_dependency_graph(db)
    deps = graph.get_dependencies(task_id)
    if not deps:
        return True
    for dep_id in deps:
        result = await db.execute(select(Task).where(Task.id == dep_id))
        dep_task = result.scalar_one_or_none()
        if not dep_task or dep_task.status != TaskStatus.DONE:
            return False
    return True
