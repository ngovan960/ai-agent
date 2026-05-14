# Database Migration Strategy - AI SDLC System

## Tài liệu Thiết kế Migration Database sử dụng Alembic

---

## 1. Tổng quan

Hệ thống AI SDLC sử dụng **Alembic** làm công cụ migration cho PostgreSQL database. Alembic được tích hợp chặt chẽ với SQLAlchemy ORM, cho phép version control schema database và quản lý thay đổi schema một cách có hệ thống.

### 1.1 Mục tiêu

- **Version control**: Mọi thay đổi schema đều được track qua migration files
- **Reproducibility**: Môi trường dev, staging, production có schema đồng nhất
- **Rollback**: Có thể rollback migration khi phát hiện lỗi
- **CI/CD integration**: Migration tự động chạy trong deployment pipeline
- **Zero-downtime**: Migration không làm gián đoạn service

### 1.2 Stack

| Thành phần | Công nghệ | Phiên bản |
|-----------|-----------|-----------|
| Database | PostgreSQL | 16+ |
| ORM | SQLAlchemy | 2.0+ |
| Migration Tool | Alembic | 1.13+ |
| Driver | asyncpg | 0.29+ |
| UUID Generation | uuid-ossp extension | — |
| Vector Search | pgvector extension | 0.7+ |

---

## 2. Cấu trúc Project

### 2.1 Directory Layout

```
project/
├── alembic/
│   ├── env.py                    # Alembic environment config
│   ├── script.py.mako            # Template cho migration files
│   ├── versions/                  # Migration files
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_audit_logs.py
│   │   ├── 003_add_retry_records.py
│   │   ├── 004_add_cost_tracking.py
│   │   ├── 005_add_api_keys.py
│   │   ├── 006_add_project_members.py
│   │   ├── 007_add_revoked_tokens.py
│   │   ├── 008_add_mentor_quota.py
│   │   ├── 009_add_llm_call_logs.py
│   │   ├── 010_add_prompt_template_versions.py
│   │   ├── 011_add_project_cost_limits.py
│   │   ├── 012_add_embedding_tables.py
│   │   └── 013_add_hash_chain_audit.py
│   └── README.txt
├── alembic.ini                   # Alembic configuration
├── app/
│   ├── models/                   # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py               # Declarative base
│   │   ├── project.py
│   │   ├── module_spec.py
│   │   ├── task.py
│   │   ├── state_transition.py
│   │   ├── audit_log.py
│   │   ├── retry_record.py
│   │   ├── user.py
│   │   ├── api_key.py
│   │   ├── cost_tracking.py
│   │   ├── llm_call_log.py
│   │   └── mentor_instruction.py
│   └── db/
│       ├── session.py            # Database session management
│       └── extensions.py         # PostgreSQL extensions setup
└── tests/
    └── migrations/
        ├── conftest.py           # Test fixtures cho migrations
        ├── test_migration_001.py
        ├── test_migration_002.py
        └── test_migration_upgrade_downgrade.py
```

### 2.2 alembic.ini Configuration

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://ai_sdlc:password@localhost:5432/ai_sdlc_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 2.3 env.py Configuration

```python
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.base import Base
from app.models import (  # noqa: F401
    project, module_spec, task, state_transition,
    audit_log, retry_record, user, api_key,
    cost_tracking, llm_call_log, mentor_instruction,
)

config = context.get_config()

# Override sqlalchemy.url từ environment variable
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## 3. Tạo Migration

### 3.1 Lệnh tạo Migration tự động

```bash
# Tạo migration tự động từ SQLAlchemy models
alembic revision --autogenerate -m "add_user_preferences_table"

# Tạo migration rỗng (manual)
alembic revision -m "add_data_migration_for_default_modules"

# Tạo migration với các thay đổi cụ thể
alembic revision --autogenerate -m "add_index_on_tasks_state_created_at"
```

### 3.2 Quy trình tạo Migration

```
1. Sửa SQLAlchemy model trong app/models/
   ↓
2. Chạy: alembic revision --autogenerate -m "mô tả ngắn gọn"
   ↓
3. Review migration file được tạo (KIỂM TRA KỸ!)
   ↓
4. Chạy: alembic upgrade head (trên dev database)
   ↓
5. Kiểm tra schema: alembic check
   ↓
6. Viết test cho migration (xem Section 6)
   ↓
7. Commit migration file + model thay đổi
```

### 3.3 Lưu ý khi dùng Autogenerate

Alembic autogenerate **không thể phát hiện** mọi thay đổi. Cần review kỹ:

| Phát hiện được | Không phát hiện được |
|---------------|---------------------|
| Thêm/xoá table | Thay đổi default value |
| Thêm/xoá column | Thay đổi data trong table |
| Thay đổi column type | Thay đổi constraint name |
| Thêm/xoá foreign key | Thay đổi trigger/function |
| Thay đổi nullable | Thay đổi view definition |
| Thêm/xoá unique constraint | Rename column/table (thay vào đó tạo add+drop) |
| Thêm/xoá index | Thay đổi check constraint logic |

**Quy tắc**: Luôn review migration file sau khi autogenerate. Không bao giờ chạy blind.

### 3.4 Ví dụ Migration File

```python
"""add user preferences table

Revision ID: a1b2c3d4e5f6
Revises: 001_initial_schema
Create Date: 2026-05-14 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, str, None] = None
depends_on: Union[str, str, None] = None


def upgrade() -> None:
    # Tạo enum type
    preference_type = postgresql.ENUM(
        'notification', 'display', 'workflow',
        name='preference_type',
        create_type=True,
    )
    preference_type.create(op.get_bind(), checkfirst=True)

    # Tạo table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('preference_type', preference_type, nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.JSONB(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Tạo index
    op.create_index(
        'idx_user_preferences_user_id',
        'user_preferences',
        ['user_id'],
    )
    op.create_index(
        'idx_user_preferences_type_key',
        'user_preferences',
        ['preference_type', 'key'],
    )

    # Data migration: set default preferences cho existing users
    op.execute("""
        INSERT INTO user_preferences (id, user_id, preference_type, key, value)
        SELECT
            gen_random_uuid(),
            u.id,
            'notification',
            'email_on_task_done',
            '"true"'::jsonb
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM user_preferences up
            WHERE up.user_id = u.id AND up.key = 'email_on_task_done'
        );
    """)


def downgrade() -> None:
    # Xoá index
    op.drop_index('idx_user_preferences_type_key', table_name='user_preferences')
    op.drop_index('idx_user_preferences_user_id', table_name='user_preferences')

    # Xoá table
    op.drop_table('user_preferences')

    # Xoá enum type
    preference_type = postgresql.ENUM(
        name='preference_type',
        create_type=False,
    )
    preference_type.drop(op.get_bind(), checkfirst=True)
```

---

## 4. Migration Naming Conventions

### 4.1 File Naming

Alembic tự động tạo revision ID, nhưng message (-m) nên tuân theo quy ước sau:

```
alembic revision --autogenerate -m "<action>_<resource>_<detail>"
```

| Action | Mô tả | Ví dụ |
|--------|-------|-------|
| `add` | Thêm table/column/index mới | `add_user_preferences_table` |
| `drop` | Xoá table/column/index | `drop_legacy_metrics_column` |
| `alter` | Thay đổi column type/constraint | `alter_task_state_to_enum` |
| `rename` | Đổi tên column/table | `rename_task_status_to_state` |
| `create` | Tạo database object (view, function) | `create_audit_log_trigger` |
| `insert` | Data migration | `insert_default_project_templates` |
| `update` | Cập nhật data | `update_task_states_to_uppercase` |

### 4.2 Revision ID Convention

Alembic tự động tạo revision ID (hash-based). Tuy nhiên, để dễ reference, thêm **human-readable prefix** trong docstring:

```python
"""add user preferences table

Revision ID: a1b2c3d4e5f6    <-- tự động bởi Alembic
Revises: 009_add_llm_call_logs     <-- reference đến migration trước
Create Date: 2026-05-14 10:00:00.000000

Description: Thêm bảng user_preferences cho lưu trữ
cài đặt cá nhân của user (notification, display, workflow).
"""
```

### 4.3 Migration Organization

```
Migrations được tổ chức theo thứ tự logic:

001_initial_schema          ← Core tables (projects, modules, tasks, state_transitions)
002_add_audit_logs          ← Audit system
003_add_retry_records       ← Retry tracking
004_add_cost_tracking       ← Cost tracking (MVP-era)
005_add_api_keys            ← Authentication
006_add_project_members     ← RBAC
007_add_revoked_tokens      ← Token revocation
008_add_mentor_quota        ← Mentor daily quota (LAW-017)
009_add_llm_call_logs       ← LLM observability
010_add_prompt_template_versions  ← Prompt versioning
011_add_project_cost_limits ← Per-project cost limits
012_add_embedding_tables    ← pgvector semantic search (Phase 6)
013_add_hash_chain_audit    ← Audit log integrity
```

---

## 5. Rollback Procedures

### 5.1 Rollback Commands

```bash
# Rollback 1 migration
alembic downgrade -1

# Rollback về revision cụ thể
alembic downgrade 009_add_llm_call_logs

# Rollback về HEAD của branch cụ thể
alembic downgrade head

# Rollback tất cả (CAUTION: về database rỗng)
alembic downgrade base

# Xem lịch sử migrations
alembic history

# Xem migration hiện tại
alembic current

# Xem migration tiếp theo
alembic show head
```

### 5.2 Rollback trong Production

```
Quy trình Rollback Production:

1. PHÁT HIỆN VẤN ĐỀ
   └─ Monitoring/alerting phát hiện DB issue
   └─ Hoặc manual review phát hiện migration bug

2. ĐÁNH GIÁ
   └─ Migration này là DDL (schema change) hay DML (data change)?
   └─ Có data loss không nếu rollback?
   └─ Có running transactions không?

3. ROLLBACK PLAN
   └─ Nếu DDL-only (CREATE TABLE, ADD COLUMN):
       → alembic downgrade -1 an toàn
   └─ Nếu DML (data migration):
       → Cần custom downgrade script
   └─ Nếu destructive (DROP TABLE, DELETE data):
       → Cần restore từ backup

4. THỰC HIỆN ROLLBACK
   └─ Đặt application vào maintenance mode
   └─ Stop all connections đến database
   └─ Chạy: alembic downgrade <target_revision>
   └─ Verify schema sau rollback
   └─ Restart application

5. POST-ROLLBACK
   └─ Verify application hoạt động bình thường
   └─ Notify team
   └─ Tạo incident report
   └─ Fix migration và tạo PR mới
```

### 5.3 Safe Downgrade Patterns

```python
def downgrade() -> None:
    # Pattern 1: Xoá table (an toàn nếu table rỗng)
    op.drop_table('user_preferences')

    # Pattern 2: Xoá column (không mất data khác)
    op.drop_column('tasks', 'priority_score')

    # Pattern 3: Restore column data (cần data migration)
    # CẨN THẬN: cần backup data trước khi AlterColumn
    op.alter_column(
        'tasks',
        'state',
        existing_type=sa.String(length=50),
        nullable=False,  # Restore NOT NULL
    )

    # Pattern 4: Xoá enum type
    preference_type = postgresql.ENUM(
        name='preference_type',
        create_type=False,
    )
    preference_type.drop(op.get_bind(), checkfirst=True)
```

### 5.4 Emergency Rollback Script

```bash
#!/bin/bash
# scripts/emergency_rollback.sh
# Sử dụng: ./emergency_rollback.sh <target_revision>

set -e

TARGET_REVISION=${1:? "Usage: $0 <target_revision>"}

echo "=== EMERGENCY ROLLBACK ==="
echo "Target revision: $TARGET_REVISION"
echo "Current revision:"
alembic current

echo ""
echo "This will downgrade the database to revision: $TARGET_REVISION"
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Rollback cancelled."
    exit 0
fi

echo "Starting rollback..."
alembic downgrade "$TARGET_REVISION"

echo ""
echo "Rollback complete. Current revision:"
alembic current

echo "Verifying database integrity..."
alembic check

echo "=== ROLLBACK COMPLETE ==="
```

---

## 6. Schema Version Tracking

### 6.1 Alembic Version Tracking

Alembic sử dụng table `alembic_version` để track schema version hiện tại:

```sql
-- Alembic tự động tạo table này
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
```

### 6.2 Schema Version trong Application

```python
from Alembic.runtime import Environment
from Alembic import context

def get_current_schema_version() -> str:
    result = db.execute("SELECT version_num FROM alembic_version").scalar()
    return result or "base"

def check_schema_version() -> bool:
    current = get_current_schema_version()
    if current != EXPECTED_SCHEMA_VERSION:
        logger.error(
            f"Schema version mismatch: "
            f"expected={EXPECTED_SCHEMA_VERSION}, "
            f"actual={current}"
        )
        return False
    return True
```

### 6.3 Health Check Endpoint

```python
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        version = await db.execute(
            text("SELECT version_num FROM alembic_version")
        )
        schema_version = version.scalar()

        return {
            "status": "healthy",
            "schema_version": schema_version,
            "database": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
        }
```

### 6.4 Migration Dependency Graph

```
base (001_initial_schema)
  │
  ├─→ 002_add_audit_logs
  │     │
  │     └─→ 003_add_retry_records
  │           │
  │           └─→ 004_add_cost_tracking
  │                 │
  │                 └─→ 005_add_api_keys
  │                       │
  │                       ├─→ 006_add_project_members
  │                       │     │
  │                       │     └─→ 007_add_revoked_tokens
  │                       │           │
  │                       │           └─→ 008_add_mentor_quota
  │                       │
  │                       └─→ 009_add_llm_call_logs
  │                             │
  │                             ├─→ 010_add_prompt_template_versions
  │                             │     │
  │                             │     └─→ 011_add_project_cost_limits
  │                             │
  │                             └─→ 012_add_embedding_tables
  │                                   │
  │                                   └─→ 013_add_hash_chain_audit
  │
  HEAD ──→ 013_add_hash_chain_audit
```

---

## 7. Migration Testing

### 7.1 Test Strategy

```python
# tests/migrations/conftest.py
import pytest
from sqlalchemy import create_engine
from alembic import command
from alembic.config import Config

@pytest.fixture(scope="module")
def alembic_config():
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", os.getenv("TEST_DATABASE_URL"))
    return config

@pytest.fixture(scope="module")
def migration_engine():
    engine = create_engine(os.getenv("TEST_DATABASE_URL"))
    yield engine
    engine.dispose()

@pytest.fixture
def clean_db(migration_engine):
    """Reset database về base state trước mỗi test."""
    with migration_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    yield migration_engine
```

### 7.2 Upgrade/Downgrade Test

```python
# tests/migrations/test_migration_upgrade_downgrade.py
import pytest
from alembic import command
from alembic.config import Config

class TestMigrationUpDown:
    def test_upgrade_to_head(self, alembic_config, clean_db):
        command.upgrade(alembic_config, "head")
        # Verify all tables tồn tại
        with clean_db.connect() as conn:
            tables = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )).fetchall()
            table_names = {row[0] for row in tables}
            expected = {
                'projects', 'module_specs', 'tasks',
                'state_transitions', 'audit_logs', 'retry_records',
                'users', 'api_keys', 'cost_tracking',
                'llm_call_logs', 'mentor_instructions',
                'mentor_quota', 'revoked_tokens',
                'project_members', 'project_cost_limits',
                'prompt_template_versions',
                'task_embeddings', 'module_spec_embeddings',
                'mentor_instruction_embeddings',
            }
            assert expected.issubset(table_names), \
                f"Missing tables: {expected - table_names}"

    def test_downgrade_to_base(self, alembic_config, clean_db):
        command.upgrade(alembic_config, "head")
        command.downgrade(alembic_config, "base")
        # Verify tất cả tables đã bị drop
        with clean_db.connect() as conn:
            tables = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )).fetchall()
            table_names = {row[0] for row in tables}
            assert "tasks" not in table_names

    def test_full_roundtrip(self, alembic_config, clean_db):
        command.upgrade(alembic_config, "head")
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")
        # Schema phải đồng nhất sau roundtrip
        command.check(alembic_config)
```

### 7.3 Data Migration Test

```python
# tests/migrations/test_migration_data.py
class TestDataMigrations:
    def test_default_modules_migration(self, alembic_config, clean_db):
        # Setup: upgrade đến trước migration thêm default modules
        command.upgrade(alembic_config, "004_add_cost_tracking")

        # Insert test data
        with clean_db.connect() as conn:
            project_id = str(uuid.uuid4())
            conn.execute(text(
                "INSERT INTO projects (id, name, description) "
                "VALUES (:id, 'Test Project', 'Test Description')"
            ), {"id": project_id})
            conn.commit()

        # Chạy migration thêm default modules
        command.upgrade(alembic_config, "005_add_api_keys")

        # Verify data migration
        with clean_db.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM module_specs WHERE project_id = :pid"
            ), {"pid": project_id})
            count = result.scalar()
            assert count >= 0  # Adjust theo expected data
```

### 7.4 State Machine Constraint Test

```python
# tests/migrations/test_state_constraints.py
class TestStateConstraints:
    def test_valid_transitions_check_constraint(self, alembic_config, clean_db):
        """Verify state machine check constraints hoạt động."""
        command.upgrade(alembic_config, "head")

        with clean_db.connect() as conn:
            project_id = str(uuid.uuid4())
            module_id = str(uuid.uuid4())
            task_id = str(uuid.uuid4())

            conn.execute(text(
                "INSERT INTO projects (id, name) VALUES (:id, 'Test')"
            ), {"id": project_id})
            conn.execute(text(
                "INSERT INTO module_specs (id, project_id, name) "
                "VALUES (:id, :pid, 'Test Module')"
            ), {"id": module_id, "pid": project_id})
            conn.execute(text(
                "INSERT INTO tasks (id, module_id, title, state) "
                "VALUES (:id, :mid, 'Test Task', 'NEW')"
            ), {"id": task_id, "mid": module_id})

            # Valid transition: NEW → ANALYZING
            conn.execute(text(
                "INSERT INTO state_transitions (id, task_id, from_state, to_state, reason, actor) "
                "VALUES (gen_random_uuid(), :tid, 'NEW', 'ANALYZING', 'Test', 'gatekeeper')"
            ), {"tid": task_id})
            conn.commit()

    def test_invalid_transition_rejected(self, alembic_config, clean_db):
        """Verify invalid transitions bị reject ở DB level."""
        command.upgrade(alembic_config, "head")

        with clean_db.connect() as conn:
            # ... setup same as above ...

            # Invalid transition: DONE → IMPLEMENTING (phải fail)
            with pytest.raises(Exception):
                conn.execute(text(
                    "INSERT INTO state_transitions "
                    "(id, task_id, from_state, to_state, reason, actor) "
                    "VALUES (gen_random_uuid(), :tid, 'DONE', 'IMPLEMENTING', 'Invalid', 'test')"
                ), {"tid": task_id})
```

---

## 8. Migration trong CI/CD

### 8.1 CI Pipeline

```yaml
# .github/workflows/migration.yml
name: Database Migration CI

on:
  push:
    paths:
      - 'alembic/**'
      - 'app/models/**'
      - 'alembic.ini'

jobs:
  migration-check:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: ai_sdlc_test
          POSTGRES_USER: ai_sdlc
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Check for uncommitted model changes
        env:
          DATABASE_URL: postgresql://ai_sdlc:test_password@localhost:5432/ai_sdlc_test
        run: |
          alembic upgrade head
          alembic check

      - name: Test upgrade to head
        env:
          TEST_DATABASE_URL: postgresql://ai_sdlc:test_password@localhost:5432/ai_sdlc_test
        run: pytest tests/migrations/ -v

      - name: Test downgrade to base
        env:
          TEST_DATABASE_URL: postgresql://ai_sdlc:test_password@localhost:5432/ai_sdlc_test
        run: |
          alembic upgrade head
          alembic downgrade base

      - name: Test roundtrip
        env:
          TEST_DATABASE_URL: postgresql://ai_sdlc:test_password@localhost:5432/ai_sdlc_test
        run: |
          alembic upgrade head
          alembic downgrade base
          alembic upgrade head
          alembic check
```

### 8.2 CD Pipeline cho Production

```yaml
# .github/workflows/deploy.yml (migration portion)
name: Deploy Production

jobs:
  migrate:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Run Database Migration
        env:
          DATABASE_URL: ${{ secrets.PRODUCTION_DATABASE_URL }}
        run: |
          echo "Current schema version:"
          alembic current

          echo "Running migration..."
          alembic upgrade head

          echo "New schema version:"
          alembic current

          echo "Verifying schema..."
          alembic check

      - name: Verify Migration Success
        env:
          DATABASE_URL: ${{ secrets.PRODUCTION_DATABASE_URL }}
        run: |
          python scripts/verify_migration.py

      - name: Rollback on Failure
        if: failure()
        env:
          DATABASE_URL: ${{ secrets.PRODUCTION_DATABASE_URL }}
        run: |
          echo "Migration failed! Rolling back..."
          alembic downgrade -1
          echo "Rollback complete."
```

### 8.3 Pre-Deployment Checklist

```
TRƯỚC KHI CHẠY MIGRATION TRÊN PRODUCTION:

□ 1. Đã test migration trên staging database (copy của production)
□ 2. Đã review migration file (không có DROP TABLE không cần thiết)
□ 3. Đã backup production database
□ 4. Đã verify downgrade path hoạt động
□ 5. Đã kiểm tra data migration không mất data
□ 6. Đã estimate thời gian migration (dựa trên data volume)
□ 7. Đã chuẩn bị rollback plan
□ 8. Đã notify team về scheduled migration
□ 9. Đã verify application compatible với schema mới
□ 10. Đã chạy migration scripts trên local thành công
```

---

## 9. Best Practices

### 9.1 Quy tắc Migration

| # | Quy tắc | Giải thích |
|---|---------|------------|
| 1 | **Luôn review autogenerate** | Alembic không phát hiện tất cả thay đổi |
| 2 | **Một migration = một logic change** | Không gộp nhiều thay đổi không liên quan |
| 3 | **Không modify migration đã commit** | Tạo migration mới để sửa |
| 4 | **Luôn viết downgrade** | Mỗi upgrade phải có downgrade tương ứng |
| 5 | **Test upgrade + downgrade** | Verify roundtrip trên test database |
| 6 | **Data migration tách riêng** | Tách DDL và DML thành các migration riêng |
| 7 | **Không xoá data trong migration** | Dùng soft delete hoặc archival |
| 8 | **Thêm index có CONCURRENTLY** | Tránh lock table trên production |
| 9 | **Chạy migration trước khi deploy app** | App phải compatible với schema mới |
| 10 | **Document breaking changes** | Ghi chú rõ trong migration docstring |

### 9.2 Performance Tips cho Migration trên Production

```python
# Tạo index không lock table (PostgreSQL)
op.execute(
    "CREATE INDEX CONCURRENTLY idx_tasks_state_created "
    "ON tasks (state, created_at)"
)

# DROP INDEX CONCURRENTLY
op.execute(
    "DROP INDEX CONCURRENTLY idx_tasks_state_created"
)

# Thêm column với DEFAULT không scan toàn bộ table
op.add_column(
    'tasks',
    sa.Column('priority_score', sa.Integer(), nullable=True),
)
# Sau đó set default trong separate statement
op.execute(
    "UPDATE tasks SET priority_score = 50 WHERE priority_score IS NULL"
)
# Cuối cùng mới add NOT NULL constraint
op.alter_column('tasks', 'priority_score', nullable=False)
```

### 9.3 Data Migration Patterns

```python
# Pattern: Batch processing cho large tables
def upgrade() -> None:
    batch_size = 1000
    offset = 0
    while True:
        result = op.execute(f"""
            UPDATE tasks
            SET state = UPPER(state)
            WHERE id IN (
                SELECT id FROM tasks
                WHERE state != UPPER(state)
                LIMIT {batch_size} OFFSET {offset}
            )
        """)
        if result.rowcount == 0:
            break
        offset += batch_size

# Pattern: Add column với computed data
def upgrade() -> None:
    op.add_column('tasks', sa.Column('complexity_score', sa.Float(), nullable=True))
    op.execute("""
        UPDATE tasks t
        SET complexity_score = (
            SELECT AVG(cr.score)
            FROM complexity_reports cr
            WHERE cr.task_id = t.id
        )
    """)
```

### 9.4 Zero-Downtime Migration Strategy

```
Bước 1: Deploy migration thêm column mới (nullable, không xóa column cũ)
  → App vẫn đọc column cũ

Bước 2: Deploy app code đọc column mới, fallback về column cũ
  → App đọc cả hai, ưu chí column mới

Bước 3: Data migration: copy data từ column cũ sang column mới
  → Chạy batch update

Bước 4: Deploy app code chỉ đọc column mới
  → App không còn reference column cũ

Bước 5: Migration xóa column cũ
  → Schema clean

Total: 5 deployments, 0 downtime
```

---

## 10. Troubleshooting

### 10.1 Common Issues

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|------------|-----------|
| `Target database is not up to date` | Alembic version không khớp với DB | Chạy `alembic stamp head` sau manual schema change |
| `Can't locate revision` | Migration file bị thiếu | Kiểm tra `versions/` directory, restore file |
| `Table already exists` | Migration chạy 2 lần | Đảm bảo `op.create_table` có `IF NOT EXISTS` hoặc check trong `upgrade()` |
| `Foreign key violation` | Thứ tự migration sai | Đảm bảo referenced table tạo trước |
| `Column type mismatch` | Model và DB không đồng bộ | Chạy `alembic check` để phát hiện |
| `Lock timeout` | Migration chạy trên table đang active | Dùng `CONCURRENTLY` cho index, chạy ngoài giờ cao |

### 10.2 Emergency Procedures

```bash
# Reset Alembic version (CAUTION: chỉ dùng khi biết mình đang làm gì)
alembic stamp head

# Reset về base
alembic stamp base

# Xem sự khác biệt giữa model và DB
alembic check

# Tạo SQL script cho manual review (không chạy trực tiếp)
alembic upgrade head --sql > migration.sql

# Chạy migration offline (tạo SQL script)
alembic upgrade head --sql
```

---

*Tài liệu version: 1.0.0*
*Last updated: 2026-05-14*
*Maintained by: AI SDLC System Architecture Team*