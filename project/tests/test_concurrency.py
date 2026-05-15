import pytest
from shared.concurrency import OptimisticLockError, retry_on_conflict


class TestOptimisticLockError:
    def test_default_message(self):
        error = OptimisticLockError()
        assert str(error) == "Record was modified by another process"

    def test_custom_message(self):
        error = OptimisticLockError("Custom message")
        assert str(error) == "Custom message"


class TestRetryOnConflict:
    @pytest.mark.asyncio
    async def test_no_retry_on_success(self):
        call_count = 0

        @retry_on_conflict(max_retries=3)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_conflict_then_success(self):
        call_count = 0

        @retry_on_conflict(max_retries=3, base_delay=0.01)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OptimisticLockError("Conflict")
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        call_count = 0

        @retry_on_conflict(max_retries=2, base_delay=0.01)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise OptimisticLockError("Always fails")

        with pytest.raises(OptimisticLockError):
            await always_fail()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_other_exception(self):
        call_count = 0

        @retry_on_conflict(max_retries=3)
        async def value_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a conflict")

        with pytest.raises(ValueError):
            await value_error_func()

        assert call_count == 1
