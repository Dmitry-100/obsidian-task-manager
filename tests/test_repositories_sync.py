"""
Тесты для SyncLogRepository и SyncConflictRepository.

Покрывает:
- CRUD операции
- Специализированные запросы
- start_sync, complete_sync, fail_sync
- resolve, resolve_all_for_sync
"""

from datetime import UTC, date, datetime

import pytest
import pytest_asyncio

from src.models import Project, SyncConflict, SyncLog, Task
from src.models.sync_conflict import ConflictResolution
from src.models.sync_log import SyncStatus, SyncType
from src.repositories import SyncConflictRepository, SyncLogRepository

# =============================================================================
# FIXTURES
# =============================================================================


@pytest_asyncio.fixture
async def sync_log_repo(test_db):
    """Создаёт SyncLogRepository."""
    return SyncLogRepository(test_db)


@pytest_asyncio.fixture
async def sync_conflict_repo(test_db):
    """Создаёт SyncConflictRepository."""
    return SyncConflictRepository(test_db)


@pytest_asyncio.fixture
async def sample_sync_log(test_db):
    """Создаёт тестовый SyncLog."""
    log = SyncLog(
        sync_type=SyncType.IMPORT,
        status=SyncStatus.COMPLETED,
        source_file="/vault/TODO.md",
        tasks_created=5,
        tasks_updated=3,
    )
    test_db.add(log)
    await test_db.flush()
    return log


@pytest_asyncio.fixture
async def project(test_db):
    """Создаёт проект для задач."""
    project = Project(name="Test Project")
    test_db.add(project)
    await test_db.flush()
    return project


@pytest_asyncio.fixture
async def task(test_db, project):
    """Создаёт задачу."""
    task = Task(
        title="Test Task",
        project_id=project.id,
    )
    test_db.add(task)
    await test_db.flush()
    return task


def create_conflict(
    sync_log_id: int,
    title: str = "Test Conflict",
    task_id: int | None = None,
    resolved: bool = False,
) -> SyncConflict:
    """Хелпер для создания конфликта."""
    conflict = SyncConflict(
        sync_log_id=sync_log_id,
        task_id=task_id,
        obsidian_path="/vault/file.md",
        obsidian_line=1,
        obsidian_title=title,
        obsidian_status="todo",
        obsidian_priority="medium",
        obsidian_modified=datetime.now(UTC),
    )
    if resolved:
        conflict.resolution = ConflictResolution.OBSIDIAN
        conflict.resolved_at = datetime.now(UTC)
        conflict.resolved_by = "test"
    return conflict


# =============================================================================
# ТЕСТЫ: SyncLogRepository — базовый CRUD
# =============================================================================


class TestSyncLogRepositoryCRUD:
    """Тесты базовых CRUD операций."""

    @pytest.mark.asyncio
    async def test_create_sync_log(self, sync_log_repo, test_db):
        """Создание SyncLog."""
        log = SyncLog(sync_type=SyncType.IMPORT)
        result = await sync_log_repo.create(log)

        assert result.id is not None
        assert result.sync_type == SyncType.IMPORT

    @pytest.mark.asyncio
    async def test_get_by_id(self, sync_log_repo, sample_sync_log):
        """Получение по ID."""
        result = await sync_log_repo.get_by_id(sample_sync_log.id)

        assert result is not None
        assert result.id == sample_sync_log.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, sync_log_repo):
        """Несуществующий ID — None."""
        result = await sync_log_repo.get_by_id(99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_sync_log(self, sync_log_repo, sample_sync_log):
        """Обновление SyncLog."""
        result = await sync_log_repo.update(
            sample_sync_log.id,
            status=SyncStatus.FAILED,
            error_message="Test error",
        )

        assert result is not None
        assert result.status == SyncStatus.FAILED
        assert result.error_message == "Test error"

    @pytest.mark.asyncio
    async def test_delete_sync_log(self, sync_log_repo, test_db):
        """Удаление SyncLog."""
        log = SyncLog(sync_type=SyncType.EXPORT)
        log = await sync_log_repo.create(log)
        log_id = log.id

        result = await sync_log_repo.delete(log_id)

        assert result is True
        assert await sync_log_repo.get_by_id(log_id) is None


# =============================================================================
# ТЕСТЫ: SyncLogRepository — специализированные запросы
# =============================================================================


class TestSyncLogRepositoryQueries:
    """Тесты специализированных запросов."""

    @pytest.mark.asyncio
    async def test_get_latest(self, sync_log_repo, test_db):
        """Получение последнего SyncLog."""
        # Создаём несколько логов
        log1 = SyncLog(sync_type=SyncType.IMPORT)
        test_db.add(log1)
        await test_db.flush()

        log2 = SyncLog(sync_type=SyncType.EXPORT)
        test_db.add(log2)
        await test_db.flush()

        result = await sync_log_repo.get_latest()

        assert result is not None
        assert result.id == log2.id  # Последний созданный

    @pytest.mark.asyncio
    async def test_get_latest_empty(self, sync_log_repo):
        """get_latest когда нет логов — None."""
        result = await sync_log_repo.get_latest()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_by_type(self, sync_log_repo, test_db):
        """Получение последнего SyncLog определённого типа."""
        log1 = SyncLog(sync_type=SyncType.IMPORT)
        test_db.add(log1)
        log2 = SyncLog(sync_type=SyncType.EXPORT)
        test_db.add(log2)
        log3 = SyncLog(sync_type=SyncType.IMPORT)
        test_db.add(log3)
        await test_db.flush()

        result = await sync_log_repo.get_latest_by_type(SyncType.IMPORT)

        assert result is not None
        assert result.id == log3.id

    @pytest.mark.asyncio
    async def test_get_by_status(self, sync_log_repo, test_db):
        """Получение логов по статусу."""
        log1 = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.COMPLETED)
        log2 = SyncLog(sync_type=SyncType.EXPORT, status=SyncStatus.FAILED)
        log3 = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.COMPLETED)
        test_db.add_all([log1, log2, log3])
        await test_db.flush()

        result = await sync_log_repo.get_by_status(SyncStatus.COMPLETED)

        assert len(result) == 2
        assert all(r.status == SyncStatus.COMPLETED for r in result)

    @pytest.mark.asyncio
    async def test_get_in_progress(self, sync_log_repo, test_db):
        """Получение текущей синхронизации."""
        log1 = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.COMPLETED)
        log2 = SyncLog(sync_type=SyncType.EXPORT, status=SyncStatus.IN_PROGRESS)
        test_db.add_all([log1, log2])
        await test_db.flush()

        result = await sync_log_repo.get_in_progress()

        assert result is not None
        assert result.id == log2.id

    @pytest.mark.asyncio
    async def test_get_in_progress_none(self, sync_log_repo, test_db):
        """Нет текущей синхронизации — None."""
        log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.COMPLETED)
        test_db.add(log)
        await test_db.flush()

        result = await sync_log_repo.get_in_progress()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_recent(self, sync_log_repo, test_db):
        """Получение недавних логов."""
        for _ in range(15):
            log = SyncLog(sync_type=SyncType.IMPORT)
            test_db.add(log)
        await test_db.flush()

        result = await sync_log_repo.get_recent(limit=10)

        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_get_recent_with_conflicts(self, sync_log_repo, test_db):
        """get_recent загружает конфликты."""
        log = SyncLog(sync_type=SyncType.IMPORT)
        test_db.add(log)
        await test_db.flush()

        conflict = create_conflict(log.id)
        test_db.add(conflict)
        await test_db.flush()

        result = await sync_log_repo.get_recent(limit=10)

        assert len(result) == 1
        # Конфликты должны быть загружены
        assert len(result[0].conflicts) == 1


# =============================================================================
# ТЕСТЫ: SyncLogRepository — workflow методы
# =============================================================================


class TestSyncLogRepositoryWorkflow:
    """Тесты workflow методов."""

    @pytest.mark.asyncio
    async def test_start_sync(self, sync_log_repo):
        """Начало синхронизации."""
        result = await sync_log_repo.start_sync(
            SyncType.IMPORT,
            source_file="/vault/TODO.md",
        )

        assert result.id is not None
        assert result.sync_type == SyncType.IMPORT
        assert result.status == SyncStatus.IN_PROGRESS
        assert result.source_file == "/vault/TODO.md"
        assert result.started_at is not None

    @pytest.mark.asyncio
    async def test_complete_sync(self, sync_log_repo):
        """Завершение синхронизации."""
        log = await sync_log_repo.start_sync(SyncType.IMPORT)

        result = await sync_log_repo.complete_sync(
            log.id,
            tasks_created=10,
            tasks_updated=5,
            tasks_skipped=2,
            conflicts_count=1,
        )

        assert result is not None
        assert result.status == SyncStatus.COMPLETED
        assert result.tasks_created == 10
        assert result.tasks_updated == 5
        assert result.tasks_skipped == 2
        assert result.conflicts_count == 1
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_fail_sync(self, sync_log_repo):
        """Ошибка синхронизации."""
        log = await sync_log_repo.start_sync(SyncType.EXPORT)

        result = await sync_log_repo.fail_sync(log.id, "Connection timeout")

        assert result is not None
        assert result.status == SyncStatus.FAILED
        assert result.error_message == "Connection timeout"
        assert result.completed_at is not None


# =============================================================================
# ТЕСТЫ: SyncConflictRepository — базовый CRUD
# =============================================================================


class TestSyncConflictRepositoryCRUD:
    """Тесты базовых CRUD операций для конфликтов."""

    @pytest.mark.asyncio
    async def test_create_conflict(self, sync_conflict_repo, sample_sync_log):
        """Создание конфликта."""
        conflict = create_conflict(sample_sync_log.id)
        result = await sync_conflict_repo.create(conflict)

        assert result.id is not None
        assert result.sync_log_id == sample_sync_log.id

    @pytest.mark.asyncio
    async def test_get_by_id(self, sync_conflict_repo, test_db, sample_sync_log):
        """Получение конфликта по ID."""
        conflict = create_conflict(sample_sync_log.id)
        test_db.add(conflict)
        await test_db.flush()

        result = await sync_conflict_repo.get_by_id(conflict.id)

        assert result is not None
        assert result.id == conflict.id

    @pytest.mark.asyncio
    async def test_delete_conflict(self, sync_conflict_repo, test_db, sample_sync_log):
        """Удаление конфликта."""
        conflict = create_conflict(sample_sync_log.id)
        test_db.add(conflict)
        await test_db.flush()
        conflict_id = conflict.id

        result = await sync_conflict_repo.delete(conflict_id)

        assert result is True
        assert await sync_conflict_repo.get_by_id(conflict_id) is None


# =============================================================================
# ТЕСТЫ: SyncConflictRepository — специализированные запросы
# =============================================================================


class TestSyncConflictRepositoryQueries:
    """Тесты специализированных запросов для конфликтов."""

    @pytest.mark.asyncio
    async def test_get_by_sync_log(self, sync_conflict_repo, test_db, sample_sync_log):
        """Получение конфликтов по sync_log_id."""
        conflict1 = create_conflict(sample_sync_log.id, title="Conflict 1")
        conflict2 = create_conflict(sample_sync_log.id, title="Conflict 2")
        test_db.add_all([conflict1, conflict2])
        await test_db.flush()

        result = await sync_conflict_repo.get_by_sync_log(sample_sync_log.id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_unresolved(self, sync_conflict_repo, test_db, sample_sync_log):
        """Получение неразрешённых конфликтов."""
        conflict1 = create_conflict(sample_sync_log.id, resolved=False)
        conflict2 = create_conflict(sample_sync_log.id, resolved=True)
        conflict3 = create_conflict(sample_sync_log.id, resolved=False)
        test_db.add_all([conflict1, conflict2, conflict3])
        await test_db.flush()

        result = await sync_conflict_repo.get_unresolved()

        assert len(result) == 2
        assert all(r.resolution is None for r in result)

    @pytest.mark.asyncio
    async def test_get_unresolved_by_sync_log(self, sync_conflict_repo, test_db, sample_sync_log):
        """Получение неразрешённых конфликтов для конкретного sync_log."""
        # Создаём другой sync_log
        other_log = SyncLog(sync_type=SyncType.EXPORT)
        test_db.add(other_log)
        await test_db.flush()

        conflict1 = create_conflict(sample_sync_log.id, resolved=False)
        conflict2 = create_conflict(sample_sync_log.id, resolved=True)
        conflict3 = create_conflict(other_log.id, resolved=False)
        test_db.add_all([conflict1, conflict2, conflict3])
        await test_db.flush()

        result = await sync_conflict_repo.get_unresolved_by_sync_log(sample_sync_log.id)

        assert len(result) == 1
        assert result[0].sync_log_id == sample_sync_log.id

    @pytest.mark.asyncio
    async def test_count_unresolved(self, sync_conflict_repo, test_db, sample_sync_log):
        """Подсчёт неразрешённых конфликтов."""
        conflict1 = create_conflict(sample_sync_log.id, resolved=False)
        conflict2 = create_conflict(sample_sync_log.id, resolved=True)
        conflict3 = create_conflict(sample_sync_log.id, resolved=False)
        test_db.add_all([conflict1, conflict2, conflict3])
        await test_db.flush()

        result = await sync_conflict_repo.count_unresolved()

        assert result == 2

    @pytest.mark.asyncio
    async def test_find_by_task(self, sync_conflict_repo, test_db, sample_sync_log, task):
        """Поиск конфликтов по task_id."""
        conflict1 = create_conflict(sample_sync_log.id, task_id=task.id)
        conflict2 = create_conflict(sample_sync_log.id, task_id=None)
        test_db.add_all([conflict1, conflict2])
        await test_db.flush()

        result = await sync_conflict_repo.find_by_task(task.id)

        assert len(result) == 1
        assert result[0].task_id == task.id

    @pytest.mark.asyncio
    async def test_find_by_obsidian_path(self, sync_conflict_repo, test_db, sample_sync_log):
        """Поиск конфликтов по пути в Obsidian."""
        conflict1 = create_conflict(sample_sync_log.id)
        conflict1.obsidian_path = "/vault/specific.md"
        conflict2 = create_conflict(sample_sync_log.id)
        conflict2.obsidian_path = "/vault/other.md"
        test_db.add_all([conflict1, conflict2])
        await test_db.flush()

        result = await sync_conflict_repo.find_by_obsidian_path("/vault/specific.md")

        assert len(result) == 1
        assert result[0].obsidian_path == "/vault/specific.md"


# =============================================================================
# ТЕСТЫ: SyncConflictRepository — resolution
# =============================================================================


class TestSyncConflictRepositoryResolution:
    """Тесты разрешения конфликтов."""

    @pytest.mark.asyncio
    async def test_resolve_conflict(self, sync_conflict_repo, test_db, sample_sync_log):
        """Разрешение одного конфликта."""
        conflict = create_conflict(sample_sync_log.id)
        test_db.add(conflict)
        await test_db.flush()

        result = await sync_conflict_repo.resolve(
            conflict.id,
            ConflictResolution.OBSIDIAN,
            resolved_by="user",
        )

        assert result is not None
        assert result.resolution == ConflictResolution.OBSIDIAN
        assert result.resolved_at is not None
        assert result.resolved_by == "user"

    @pytest.mark.asyncio
    async def test_resolve_conflict_database(self, sync_conflict_repo, test_db, sample_sync_log):
        """Разрешение в пользу базы данных."""
        conflict = create_conflict(sample_sync_log.id)
        test_db.add(conflict)
        await test_db.flush()

        result = await sync_conflict_repo.resolve(
            conflict.id,
            ConflictResolution.DATABASE,
        )

        assert result.resolution == ConflictResolution.DATABASE

    @pytest.mark.asyncio
    async def test_resolve_conflict_skip(self, sync_conflict_repo, test_db, sample_sync_log):
        """Пропуск конфликта."""
        conflict = create_conflict(sample_sync_log.id)
        test_db.add(conflict)
        await test_db.flush()

        result = await sync_conflict_repo.resolve(
            conflict.id,
            ConflictResolution.SKIP,
        )

        assert result.resolution == ConflictResolution.SKIP

    @pytest.mark.asyncio
    async def test_resolve_all_for_sync(self, sync_conflict_repo, test_db, sample_sync_log):
        """Массовое разрешение конфликтов."""
        conflict1 = create_conflict(sample_sync_log.id, resolved=False)
        conflict2 = create_conflict(sample_sync_log.id, resolved=False)
        conflict3 = create_conflict(sample_sync_log.id, resolved=True)  # Already resolved
        test_db.add_all([conflict1, conflict2, conflict3])
        await test_db.flush()

        count = await sync_conflict_repo.resolve_all_for_sync(
            sample_sync_log.id,
            ConflictResolution.DATABASE,
            resolved_by="auto",
        )

        assert count == 2

        # Проверяем что разрешены
        unresolved = await sync_conflict_repo.get_unresolved_by_sync_log(sample_sync_log.id)
        assert len(unresolved) == 0

    @pytest.mark.asyncio
    async def test_resolve_all_empty(self, sync_conflict_repo, sample_sync_log):
        """Массовое разрешение когда нет конфликтов."""
        count = await sync_conflict_repo.resolve_all_for_sync(
            sample_sync_log.id,
            ConflictResolution.OBSIDIAN,
        )

        assert count == 0


# =============================================================================
# ТЕСТЫ: Edge cases
# =============================================================================


class TestEdgeCases:
    """Тесты граничных случаев."""

    @pytest.mark.asyncio
    async def test_sync_log_long_source_file(self, sync_log_repo):
        """Длинный путь к файлу."""
        long_path = "/vault/" + "a" * 900 + ".md"
        log = await sync_log_repo.start_sync(SyncType.IMPORT, source_file=long_path)

        assert log.source_file == long_path

    @pytest.mark.asyncio
    async def test_conflict_with_all_fields(
        self, sync_conflict_repo, test_db, sample_sync_log, task
    ):
        """Конфликт со всеми заполненными полями."""
        now = datetime.now(UTC)
        conflict = SyncConflict(
            sync_log_id=sample_sync_log.id,
            task_id=task.id,
            obsidian_path="/vault/file.md",
            obsidian_line=10,
            obsidian_title="Obsidian Title",
            obsidian_status="done",
            obsidian_due_date=date(2026, 1, 25),
            obsidian_priority="high",
            obsidian_modified=now,
            obsidian_raw_line="- [x] Obsidian Title",
            db_title="DB Title",
            db_status="todo",
            db_due_date=date(2026, 1, 30),
            db_priority="medium",
            db_modified=now,
        )
        result = await sync_conflict_repo.create(conflict)

        assert result.id is not None
        assert result.obsidian_due_date == date(2026, 1, 25)
        assert result.db_due_date == date(2026, 1, 30)

    @pytest.mark.asyncio
    async def test_update_nonexistent_sync_log(self, sync_log_repo):
        """Обновление несуществующего SyncLog."""
        result = await sync_log_repo.update(99999, status=SyncStatus.FAILED)
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_conflict(self, sync_conflict_repo):
        """Разрешение несуществующего конфликта."""
        result = await sync_conflict_repo.resolve(99999, ConflictResolution.SKIP)
        assert result is None
