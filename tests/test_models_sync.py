"""
Тесты для моделей SyncLog и SyncConflict.

Покрывает:
- Создание моделей
- Enum значения
- Relationships
- Defaults
"""

from datetime import date, datetime

import pytest
import pytest_asyncio

from src.models import Project, SyncConflict, SyncLog, Task
from src.models.sync_conflict import ConflictResolution
from src.models.sync_log import SyncStatus, SyncType

# =============================================================================
# ТЕСТЫ: SyncType Enum
# =============================================================================


class TestSyncTypeEnum:
    """Тесты SyncType enum."""

    def test_import_value(self):
        """SyncType.IMPORT = 'import'."""
        assert SyncType.IMPORT.value == "import"

    def test_export_value(self):
        """SyncType.EXPORT = 'export'."""
        assert SyncType.EXPORT.value == "export"

    def test_full_value(self):
        """SyncType.FULL = 'full'."""
        assert SyncType.FULL.value == "full"

    def test_enum_is_string(self):
        """SyncType наследует str."""
        assert isinstance(SyncType.IMPORT, str)
        assert SyncType.IMPORT == "import"


# =============================================================================
# ТЕСТЫ: SyncStatus Enum
# =============================================================================


class TestSyncStatusEnum:
    """Тесты SyncStatus enum."""

    def test_pending_value(self):
        """SyncStatus.PENDING = 'pending'."""
        assert SyncStatus.PENDING.value == "pending"

    def test_in_progress_value(self):
        """SyncStatus.IN_PROGRESS = 'in_progress'."""
        assert SyncStatus.IN_PROGRESS.value == "in_progress"

    def test_completed_value(self):
        """SyncStatus.COMPLETED = 'completed'."""
        assert SyncStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        """SyncStatus.FAILED = 'failed'."""
        assert SyncStatus.FAILED.value == "failed"

    def test_cancelled_value(self):
        """SyncStatus.CANCELLED = 'cancelled'."""
        assert SyncStatus.CANCELLED.value == "cancelled"


# =============================================================================
# ТЕСТЫ: ConflictResolution Enum
# =============================================================================


class TestConflictResolutionEnum:
    """Тесты ConflictResolution enum."""

    def test_obsidian_value(self):
        """ConflictResolution.OBSIDIAN = 'obsidian'."""
        assert ConflictResolution.OBSIDIAN.value == "obsidian"

    def test_database_value(self):
        """ConflictResolution.DATABASE = 'database'."""
        assert ConflictResolution.DATABASE.value == "database"

    def test_skip_value(self):
        """ConflictResolution.SKIP = 'skip'."""
        assert ConflictResolution.SKIP.value == "skip"

    def test_manual_value(self):
        """ConflictResolution.MANUAL = 'manual'."""
        assert ConflictResolution.MANUAL.value == "manual"


# =============================================================================
# ТЕСТЫ: SyncLog модель
# =============================================================================


class TestSyncLogModel:
    """Тесты модели SyncLog."""

    @pytest_asyncio.fixture
    async def sync_log(self, test_db):
        """Создаёт SyncLog в тестовой БД."""
        log = SyncLog(
            sync_type=SyncType.IMPORT,
            status=SyncStatus.PENDING,
        )
        test_db.add(log)
        await test_db.flush()
        return log

    @pytest.mark.asyncio
    async def test_create_sync_log_minimal(self, test_db):
        """Создание SyncLog с минимальными полями."""
        log = SyncLog(
            sync_type=SyncType.IMPORT,
        )
        test_db.add(log)
        await test_db.flush()

        assert log.id is not None
        assert log.sync_type == SyncType.IMPORT
        assert log.status == SyncStatus.PENDING  # default

    @pytest.mark.asyncio
    async def test_create_sync_log_full(self, test_db):
        """Создание SyncLog со всеми полями."""
        now = datetime.utcnow()
        log = SyncLog(
            sync_type=SyncType.EXPORT,
            status=SyncStatus.COMPLETED,
            source_file="/path/to/file.md",
            tasks_created=5,
            tasks_updated=3,
            tasks_skipped=1,
            conflicts_count=2,
            error_message=None,
            started_at=now,
            completed_at=now,
        )
        test_db.add(log)
        await test_db.flush()

        assert log.id is not None
        assert log.sync_type == SyncType.EXPORT
        assert log.tasks_created == 5
        assert log.started_at == now

    @pytest.mark.asyncio
    async def test_sync_log_default_values(self, test_db):
        """Проверка default значений."""
        log = SyncLog(sync_type=SyncType.FULL)
        test_db.add(log)
        await test_db.flush()

        assert log.status == SyncStatus.PENDING
        assert log.tasks_created == 0
        assert log.tasks_updated == 0
        assert log.tasks_skipped == 0
        assert log.conflicts_count == 0
        assert log.error_message is None
        assert log.started_at is None
        assert log.completed_at is None

    @pytest.mark.asyncio
    async def test_sync_log_with_error(self, test_db):
        """SyncLog с ошибкой."""
        log = SyncLog(
            sync_type=SyncType.IMPORT,
            status=SyncStatus.FAILED,
            error_message="Connection timeout",
        )
        test_db.add(log)
        await test_db.flush()

        assert log.status == SyncStatus.FAILED
        assert log.error_message == "Connection timeout"

    @pytest.mark.asyncio
    async def test_sync_log_repr(self, sync_log):
        """__repr__ возвращает читаемую строку."""
        repr_str = repr(sync_log)

        assert "SyncLog" in repr_str
        assert "import" in repr_str
        assert "pending" in repr_str

    @pytest.mark.asyncio
    async def test_sync_log_timestamps(self, test_db):
        """created_at и updated_at заполняются автоматически."""
        log = SyncLog(sync_type=SyncType.IMPORT)
        test_db.add(log)
        await test_db.flush()

        assert log.created_at is not None
        assert log.updated_at is not None


# =============================================================================
# ТЕСТЫ: SyncConflict модель
# =============================================================================


class TestSyncConflictModel:
    """Тесты модели SyncConflict."""

    @pytest_asyncio.fixture
    async def sync_log(self, test_db):
        """Создаёт SyncLog для связи с конфликтами."""
        log = SyncLog(sync_type=SyncType.IMPORT)
        test_db.add(log)
        await test_db.flush()
        return log

    @pytest_asyncio.fixture
    async def project(self, test_db):
        """Создаёт проект для задач."""
        project = Project(name="Test Project")
        test_db.add(project)
        await test_db.flush()
        return project

    @pytest_asyncio.fixture
    async def task(self, test_db, project):
        """Создаёт задачу для связи с конфликтом."""
        task = Task(
            title="Test Task",
            project_id=project.id,
        )
        test_db.add(task)
        await test_db.flush()
        return task

    @pytest.mark.asyncio
    async def test_create_conflict_minimal(self, test_db, sync_log):
        """Создание конфликта с минимальными полями."""
        conflict = SyncConflict(
            sync_log_id=sync_log.id,
            obsidian_path="/vault/file.md",
            obsidian_line=10,
            obsidian_title="Task title",
            obsidian_status="todo",
            obsidian_priority="medium",
            obsidian_modified=datetime.utcnow(),
        )
        test_db.add(conflict)
        await test_db.flush()

        assert conflict.id is not None
        assert conflict.sync_log_id == sync_log.id
        assert conflict.obsidian_title == "Task title"

    @pytest.mark.asyncio
    async def test_create_conflict_full(self, test_db, sync_log, task):
        """Создание конфликта со всеми полями."""
        now = datetime.utcnow()
        conflict = SyncConflict(
            sync_log_id=sync_log.id,
            task_id=task.id,
            obsidian_path="/vault/TODO.md",
            obsidian_line=5,
            obsidian_title="Obsidian Title",
            obsidian_status="done",
            obsidian_due_date=date(2026, 1, 25),
            obsidian_priority="high",
            obsidian_modified=now,
            obsidian_raw_line="- [x] Obsidian Title ⏫ 📅 2026-01-25",
            db_title="DB Title",
            db_status="todo",
            db_due_date=date(2026, 1, 30),
            db_priority="medium",
            db_modified=now,
            resolution=ConflictResolution.OBSIDIAN,
            resolved_at=now,
            resolved_by="user",
        )
        test_db.add(conflict)
        await test_db.flush()

        assert conflict.id is not None
        assert conflict.task_id == task.id
        assert conflict.resolution == ConflictResolution.OBSIDIAN

    @pytest.mark.asyncio
    async def test_conflict_without_task(self, test_db, sync_log):
        """Конфликт для новой задачи (без task_id)."""
        conflict = SyncConflict(
            sync_log_id=sync_log.id,
            task_id=None,  # Новая задача
            obsidian_path="/vault/file.md",
            obsidian_line=1,
            obsidian_title="New task",
            obsidian_status="todo",
            obsidian_priority="medium",
            obsidian_modified=datetime.utcnow(),
        )
        test_db.add(conflict)
        await test_db.flush()

        assert conflict.task_id is None

    @pytest.mark.asyncio
    async def test_conflict_unresolved(self, test_db, sync_log):
        """Неразрешённый конфликт."""
        conflict = SyncConflict(
            sync_log_id=sync_log.id,
            obsidian_path="/vault/file.md",
            obsidian_line=1,
            obsidian_title="Conflicting task",
            obsidian_status="todo",
            obsidian_priority="medium",
            obsidian_modified=datetime.utcnow(),
        )
        test_db.add(conflict)
        await test_db.flush()

        assert conflict.resolution is None
        assert conflict.resolved_at is None

    @pytest.mark.asyncio
    async def test_conflict_repr(self, test_db, sync_log):
        """__repr__ возвращает читаемую строку."""
        conflict = SyncConflict(
            sync_log_id=sync_log.id,
            obsidian_path="/vault/file.md",
            obsidian_line=1,
            obsidian_title="A very long task title that should be truncated",
            obsidian_status="todo",
            obsidian_priority="medium",
            obsidian_modified=datetime.utcnow(),
        )
        test_db.add(conflict)
        await test_db.flush()

        repr_str = repr(conflict)

        assert "SyncConflict" in repr_str
        assert "unresolved" in repr_str

    @pytest.mark.asyncio
    async def test_conflict_repr_resolved(self, test_db, sync_log):
        """__repr__ для разрешённого конфликта."""
        conflict = SyncConflict(
            sync_log_id=sync_log.id,
            obsidian_path="/vault/file.md",
            obsidian_line=1,
            obsidian_title="Resolved task",
            obsidian_status="todo",
            obsidian_priority="medium",
            obsidian_modified=datetime.utcnow(),
            resolution=ConflictResolution.DATABASE,
        )
        test_db.add(conflict)
        await test_db.flush()

        repr_str = repr(conflict)

        assert "resolved" in repr_str


# =============================================================================
# ТЕСТЫ: Relationships
# =============================================================================


class TestSyncRelationships:
    """Тесты связей между моделями."""

    @pytest.mark.asyncio
    async def test_sync_log_has_conflicts(self, test_db):
        """SyncLog.conflicts содержит связанные конфликты."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        log = SyncLog(sync_type=SyncType.IMPORT)
        test_db.add(log)
        await test_db.flush()

        conflict1 = SyncConflict(
            sync_log_id=log.id,
            obsidian_path="/vault/file1.md",
            obsidian_line=1,
            obsidian_title="Conflict 1",
            obsidian_status="todo",
            obsidian_priority="medium",
            obsidian_modified=datetime.utcnow(),
        )
        conflict2 = SyncConflict(
            sync_log_id=log.id,
            obsidian_path="/vault/file2.md",
            obsidian_line=2,
            obsidian_title="Conflict 2",
            obsidian_status="done",
            obsidian_priority="high",
            obsidian_modified=datetime.utcnow(),
        )
        test_db.add_all([conflict1, conflict2])
        await test_db.flush()

        # Load with selectinload to avoid greenlet issues
        result = await test_db.execute(
            select(SyncLog).where(SyncLog.id == log.id).options(selectinload(SyncLog.conflicts))
        )
        loaded_log = result.scalar_one()

        assert len(loaded_log.conflicts) == 2

    @pytest.mark.asyncio
    async def test_conflict_has_sync_log(self, test_db):
        """SyncConflict.sync_log ссылается на SyncLog."""
        log = SyncLog(sync_type=SyncType.IMPORT)
        test_db.add(log)
        await test_db.flush()

        conflict = SyncConflict(
            sync_log_id=log.id,
            obsidian_path="/vault/file.md",
            obsidian_line=1,
            obsidian_title="Conflict",
            obsidian_status="todo",
            obsidian_priority="medium",
            obsidian_modified=datetime.utcnow(),
        )
        test_db.add(conflict)
        await test_db.flush()

        # Refresh to load relationship
        await test_db.refresh(conflict)

        assert conflict.sync_log is not None
        assert conflict.sync_log.id == log.id

    @pytest.mark.asyncio
    async def test_cascade_delete(self, test_db):
        """Удаление SyncLog удаляет связанные конфликты."""
        log = SyncLog(sync_type=SyncType.IMPORT)
        test_db.add(log)
        await test_db.flush()

        conflict = SyncConflict(
            sync_log_id=log.id,
            obsidian_path="/vault/file.md",
            obsidian_line=1,
            obsidian_title="Conflict",
            obsidian_status="todo",
            obsidian_priority="medium",
            obsidian_modified=datetime.utcnow(),
        )
        test_db.add(conflict)
        await test_db.flush()
        conflict_id = conflict.id

        # Удаляем SyncLog
        await test_db.delete(log)
        await test_db.flush()

        # Конфликт тоже должен быть удалён (cascade)
        result = await test_db.get(SyncConflict, conflict_id)
        assert result is None
