# Testing Strategy

## AI SDLC Orchestrator — Testing Approach

---

## Overview

**Framework**: pytest with async support
**Total Tests**: 478
**Coverage**: 72%
**All tests pass**: ✅

---

## Test Categories

### 1. Unit Tests

| File | Tests | What It Tests |
|------|-------|---------------|
| `test_state_transitions.py` | 22 | All 22 valid transitions, invalid transitions, terminal states |
| `test_schemas.py` | 45 | All Pydantic schemas (project, module, task, audit, retry, etc.) |
| `test_services.py` | 120 | CRUD services (projects, modules, tasks), validation, error handling |
| `test_model_router.py` | 35 | Dynamic Model Router, capability scoring, cost-aware selection |
| `test_verification.py` | 40 | Verification pipeline, mode selection, exit code parsing |
| `test_confidence.py` | 30 | Confidence Engine (TLPA formula), threshold decisions |
| `test_law_engine.py` | 45 | Law Engine (20 laws), pattern detection, compliance reports |
| `test_memory.py` | 52 | Memory system (ledger, embedding, decision, cache, integration) |
| `test_observability.py` | 8 | OpenTelemetry tracing, Prometheus metrics, JSON logging |
| `test_dashboard.py` | 81 | Dashboard API, WebSocket, aggregation, caching, rate limiting |

### 2. Test Fixtures

**Database**: SQLite in-memory database for isolation
```python
@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
```

**Async Mocks**: `AsyncMock` for database operations
```python
db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=0)))
```

---

## Test Configuration

**File**: `pytest.ini` / `pyproject.toml`

```ini
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
```

### Coverage Configuration
```ini
[tool.coverage.run]
source = ["shared", "services"]
omit = ["tests/*", "*/__pycache__/*"]

[tool.coverage.report]
fail_under = 70
show_missing = true
```

---

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -q

# Run with coverage
python -m pytest tests/ -q --cov=shared --cov=services

# Run specific test file
python -m pytest tests/test_state_transitions.py -v

# Run with verbose output
python -m pytest tests/ -v --tb=short

# Run async tests
python -m pytest tests/ -q --asyncio-mode=auto
```

---

## Test Results

```
======================= 478 passed, 8 warnings in 13.50s =======================

Coverage Summary:
  shared/          72%
  services/        68%
  TOTAL            72%
```

---

## CI/CD Integration

**File**: `.github/workflows/verification.yml`

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ruff check .

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest --cov=shared --cov=services

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: python -m build

  security:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: bandit -r .
```

---

## Testing Best Practices

1. **Isolation**: Each test uses a fresh in-memory SQLite database
2. **Async**: All database operations use `AsyncMock` and `asyncio`
3. **Coverage**: Target ≥ 70% code coverage
4. **Fast**: All tests complete in < 15 seconds
5. **Deterministic**: No flaky tests, no external dependencies
6. **Readable**: Test names describe the behavior being tested

---

**Version**: 2.0.0
**Last Updated**: 2026-05-17
**Tests**: 478
**Coverage**: 72%
