from uuid import uuid4

import pytest

from services.orchestrator.services.rollback_service import (
    RollbackAuditEntry,
    RollbackEngine,
    RollbackRecord,
)


class TestRollbackEngine:
    @pytest.mark.asyncio
    async def test_create_engine(self):
        engine = RollbackEngine()
        assert engine.auto_rollback is True
        assert engine.max_rollbacks == 3

    @pytest.mark.asyncio
    async def test_trigger_in_non_git_dir(self):
        engine = RollbackEngine(config_path="/tmp/nonexistent_config.yaml")
        task_id = uuid4()
        record = await engine.trigger_rollback(
            task_id=task_id,
            reason="Verification failed",
        )
        assert isinstance(record, RollbackRecord)
        assert record.task_id == task_id
        assert record.status in ("completed", "failed", "skipped")

    @pytest.mark.asyncio
    async def test_rollback_audit_logging(self):
        engine = RollbackEngine()
        task_id = uuid4()
        await engine.trigger_rollback(task_id, "Test reason")
        log = engine.get_audit_log()
        assert len(log) > 0
        assert any(str(task_id) in str(e.task_id) for e in log)

    @pytest.mark.asyncio
    async def test_rollback_count(self):
        engine = RollbackEngine()
        task_id = uuid4()
        await engine.trigger_rollback(task_id, "Reason 1")
        assert engine.get_rollback_count(task_id) >= 1

    @pytest.mark.asyncio
    async def test_disabled_auto_rollback(self):
        engine = RollbackEngine(config_path="/tmp/nonexistent.yaml")
        engine.auto_rollback = False
        record = await engine.trigger_rollback(uuid4(), "Disabled test")
        assert record.status == "skipped"

    def test_audit_entry_type(self):
        entry = RollbackAuditEntry(
            rollback_id="test",
            task_id=uuid4(),
            action="revert",
            reason="test",
            result="ok",
            status="completed",
            timestamp="now",
        )
        assert entry.action == "revert"

    def test_rollback_record_type(self):
        record = RollbackRecord(
            rollback_id="test",
            task_id=uuid4(),
            reason="test",
            status="pending",
            action="revert",
        )
        assert record.status == "pending"
