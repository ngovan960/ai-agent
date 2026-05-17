from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from services.orchestrator.services.dependency_service import (
    DependencyGraph,
    build_dependency_graph,
    check_circular,
)


class TestDependencyGraph:
    def test_add_dependency(self):
        g = DependencyGraph()
        t1, t2 = uuid4(), uuid4()
        g.add_dependency(t1, t2)
        assert t2 in g.get_dependencies(t1)
        assert t1 in g.get_dependents(t2)

    def test_remove_dependency(self):
        g = DependencyGraph()
        t1, t2 = uuid4(), uuid4()
        g.add_dependency(t1, t2)
        g.remove_dependency(t1, t2)
        assert t2 not in g.get_dependencies(t1)

    def test_no_circular(self):
        g = DependencyGraph()
        t1, t2, t3 = uuid4(), uuid4(), uuid4()
        g.add_dependency(t1, t2)
        g.add_dependency(t2, t3)
        assert g.has_circular(t3, t1) is False

    def test_circular_detected(self):
        g = DependencyGraph()
        t1, t2 = uuid4(), uuid4()
        g.add_dependency(t1, t2)
        g.add_dependency(t2, t1)
        assert g.has_circular(t1, t2) is True

    def test_can_start_no_deps(self):
        g = DependencyGraph()
        assert g.can_start(uuid4(), set()) is True

    def test_can_start_with_met_deps(self):
        g = DependencyGraph()
        t1, t2 = uuid4(), uuid4()
        g.add_dependency(t1, t2)
        assert g.can_start(t1, {t2}) is True

    def test_can_start_with_unmet_deps(self):
        g = DependencyGraph()
        t1, t2 = uuid4(), uuid4()
        g.add_dependency(t1, t2)
        assert g.can_start(t1, set()) is False


class MockResult:
    def scalars(self):
        return self
    def all(self):
        return []


class TestDependencyService:
    @pytest.mark.asyncio
    async def test_build_graph(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())
        graph = await build_dependency_graph(mock_db)
        assert graph is not None

    @pytest.mark.asyncio
    async def test_check_circular(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MockResult())
        result = await check_circular(mock_db, uuid4(), uuid4())
        assert result is False
