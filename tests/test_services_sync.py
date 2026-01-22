"""
Тесты для SyncService — сервис синхронизации с Obsidian.

Покрывает:
- get_status
- import_from_obsidian
- export_to_obsidian
- get_conflicts, resolve_conflict, resolve_all_conflicts
- get_sync_history
- helper методы
"""

import shutil
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import pytest_asyncio

from src.integrations.obsidian.project_resolver import SyncConfig
from src.models import Project, SyncConflict, SyncLog, Task, TaskPriority, TaskStatus
from src.models.sync_conflict import ConflictResolution
from src.models.sync_log import SyncStatus, SyncType
from src.services.sync import SyncResult, SyncService, SyncStatusInfo

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sync_config():
    """Создаёт тестовую конфигурацию."""
    return SyncConfig(
        vault_path="",  # Будет заменён в temp_vault
        sync_sources=["*.md"],
        folder_mapping={},
        tag_mapping={"health": "Здоровье", "work": "Работа"},
        section_mapping={r"Здоровье|Health": "Здоровье"},
        default_project="Inbox",
    )


@pytest.fixture
def temp_vault(sync_config):
    """Создаёт временную директорию vault."""
    vault_path = tempfile.mkdtemp(prefix="test_vault_")
    sync_config.vault_path = vault_path

    yield vault_path

    shutil.rmtree(vault_path, ignore_errors=True)


@pytest_asyncio.fixture
async def sync_service(test_db, sync_config):
    """Создаёт SyncService."""
    return SyncService(test_db, sync_config)


@pytest_asyncio.fixture
async def inbox_project(test_db):
    """Создаёт проект Inbox."""
    project = Project(name="Inbox")
    test_db.add(project)
    await test_db.flush()
    return project


@pytest_asyncio.fixture
async def sample_task(test_db, inbox_project):
    """Создаёт тестовую задачу."""
    task = Task(
        title="Sample Task",
        project_id=inbox_project.id,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    test_db.add(task)
    await test_db.flush()
    return task


@pytest_asyncio.fixture
async def sample_sync_log(test_db):
    """Создаёт тестовый SyncLog."""
    log = SyncLog(
        sync_type=SyncType.IMPORT,
        status=SyncStatus.COMPLETED,
    )
    test_db.add(log)
    await test_db.flush()
    return log


@pytest_asyncio.fixture
async def sample_conflict(test_db, sample_sync_log, sample_task):
    """Создаёт тестовый конфликт."""
    conflict = SyncConflict(
        sync_log_id=sample_sync_log.id,
        task_id=sample_task.id,
        obsidian_path="/vault/file.md",
        obsidian_line=1,
        obsidian_title="Task from Obsidian",
        obsidian_status="done",
        obsidian_due_date=date(2026, 1, 25),
        obsidian_priority="high",
        obsidian_modified=datetime.now(UTC),
    )
    test_db.add(conflict)
    await test_db.flush()
    return conflict


def create_markdown_file(vault_path: str, filename: str, content: str) -> str:
    """Хелпер для создания markdown файла в vault."""
    path = Path(vault_path) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


# =============================================================================
# ТЕСТЫ: SyncResult и SyncStatusInfo dataclasses
# =============================================================================


class TestDataclasses:
    """Тесты dataclasses."""

    def test_sync_result_success(self):
        """SyncResult для успешной синхронизации."""
        result = SyncResult(
            success=True,
            sync_log_id=1,
            tasks_created=5,
            tasks_updated=3,
        )

        assert result.success is True
        assert result.tasks_created == 5
        assert result.error_message is None

    def test_sync_result_failure(self):
        """SyncResult для неудачной синхронизации."""
        result = SyncResult(
            success=False,
            sync_log_id=1,
            error_message="Connection failed",
        )

        assert result.success is False
        assert result.error_message == "Connection failed"

    def test_sync_status_info(self):
        """SyncStatusInfo."""
        status = SyncStatusInfo(
            is_syncing=False,
            last_sync=None,
            unresolved_conflicts=5,
            total_syncs=10,
        )

        assert status.is_syncing is False
        assert status.unresolved_conflicts == 5


# =============================================================================
# ТЕСТЫ: SyncService.get_status
# =============================================================================


class TestGetStatus:
    """Тесты получения статуса синхронизации."""

    @pytest.mark.asyncio
    async def test_get_status_empty(self, sync_service):
        """Статус при отсутствии синхронизаций."""
        status = await sync_service.get_status()

        assert isinstance(status, SyncStatusInfo)
        assert status.is_syncing is False
        assert status.last_sync is None
        assert status.unresolved_conflicts == 0
        assert status.total_syncs == 0

    @pytest.mark.asyncio
    async def test_get_status_with_history(self, sync_service, test_db):
        """Статус с историей синхронизаций."""
        log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.COMPLETED)
        test_db.add(log)
        await test_db.flush()

        status = await sync_service.get_status()

        assert status.last_sync is not None
        assert status.total_syncs == 1

    @pytest.mark.asyncio
    async def test_get_status_is_syncing(self, sync_service, test_db):
        """Статус во время синхронизации."""
        log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.IN_PROGRESS)
        test_db.add(log)
        await test_db.flush()

        status = await sync_service.get_status()

        assert status.is_syncing is True

    @pytest.mark.asyncio
    async def test_get_status_with_conflicts(self, sync_service, sample_sync_log, sample_conflict):
        """Статус с неразрешёнными конфликтами."""
        status = await sync_service.get_status()

        assert status.unresolved_conflicts == 1


# =============================================================================
# ТЕСТЫ: SyncService.import_from_obsidian
# =============================================================================


class TestImportFromObsidian:
    """Тесты импорта из Obsidian."""

    @pytest.mark.asyncio
    async def test_import_single_file(self, sync_service, temp_vault, test_db):
        """Импорт одного файла."""
        file_path = create_markdown_file(
            temp_vault,
            "tasks.md",
            "- [ ] Новая задача\n",
        )

        result = await sync_service.import_from_obsidian([file_path])

        assert result.success is True
        assert result.tasks_created == 1
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_import_multiple_tasks(self, sync_service, temp_vault, test_db):
        """Импорт нескольких задач из файла."""
        file_path = create_markdown_file(
            temp_vault,
            "tasks.md",
            """# TODO

- [ ] Задача 1
- [ ] Задача 2
- [x] Задача 3
""",
        )

        result = await sync_service.import_from_obsidian([file_path])

        assert result.success is True
        assert result.tasks_created == 3

    @pytest.mark.asyncio
    async def test_import_with_priority_and_date(self, sync_service, temp_vault, test_db):
        """Импорт задачи с приоритетом и датой."""
        file_path = create_markdown_file(
            temp_vault,
            "tasks.md",
            "- [ ] Важная задача ⏫ 📅 2026-01-25\n",
        )

        result = await sync_service.import_from_obsidian([file_path])

        assert result.success is True
        assert result.tasks_created == 1

        # Проверяем созданную задачу
        from src.repositories import TaskRepository

        task_repo = TaskRepository(test_db)
        tasks = await task_repo.search_by_title("Важная задача")
        assert len(tasks) == 1
        assert tasks[0].priority == TaskPriority.HIGH
        assert tasks[0].due_date == date(2026, 1, 25)

    @pytest.mark.asyncio
    async def test_import_nonexistent_file(self, sync_service):
        """Импорт несуществующего файла — пропускается."""
        result = await sync_service.import_from_obsidian(["/nonexistent/file.md"])

        assert result.success is True
        assert result.tasks_created == 0

    @pytest.mark.asyncio
    async def test_import_already_in_progress(self, sync_service, test_db):
        """Импорт когда синхронизация уже идёт."""
        # Создаём запущенную синхронизацию
        log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.IN_PROGRESS)
        test_db.add(log)
        await test_db.flush()

        result = await sync_service.import_from_obsidian([])

        assert result.success is False
        assert "already in progress" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_import_creates_sync_log(self, sync_service, temp_vault, test_db):
        """Импорт создаёт запись в SyncLog."""
        file_path = create_markdown_file(temp_vault, "tasks.md", "- [ ] Task\n")

        result = await sync_service.import_from_obsidian([file_path])

        assert result.sync_log_id is not None

        # Проверяем sync_log
        from src.repositories.sync import SyncLogRepository

        repo = SyncLogRepository(test_db)
        log = await repo.get_by_id(result.sync_log_id)

        assert log is not None
        assert log.sync_type == SyncType.IMPORT
        assert log.status == SyncStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_import_project_from_section(self, sync_service, temp_vault, test_db):
        """Импорт определяет проект по секции."""
        sync_service.config.section_mapping = {r"Здоровье": "Здоровье"}
        sync_service.resolver = __import__(
            "src.integrations.obsidian.project_resolver", fromlist=["ProjectResolver"]
        ).ProjectResolver(sync_service.config)

        file_path = create_markdown_file(
            temp_vault,
            "tasks.md",
            """## Здоровье

- [ ] Записаться к врачу
""",
        )

        result = await sync_service.import_from_obsidian([file_path])

        assert result.success is True
        assert result.tasks_created == 1


# =============================================================================
# ТЕСТЫ: SyncService.export_to_obsidian
# =============================================================================


class TestExportToObsidian:
    """Тесты экспорта в Obsidian."""

    @pytest.mark.asyncio
    async def test_export_single_task(
        self, sync_service, temp_vault, test_db, inbox_project, sample_task
    ):
        """Экспорт одной задачи."""
        output_path = str(Path(temp_vault) / "export.md")

        result = await sync_service.export_to_obsidian(output_path=output_path)

        assert result.success is True
        assert result.tasks_updated == 1

        # Проверяем файл
        content = Path(output_path).read_text(encoding="utf-8")
        assert "Sample Task" in content

    @pytest.mark.asyncio
    async def test_export_by_project(
        self, sync_service, temp_vault, test_db, inbox_project, sample_task
    ):
        """Экспорт задач конкретного проекта."""
        output_path = str(Path(temp_vault) / "export.md")

        result = await sync_service.export_to_obsidian(
            project_id=inbox_project.id,
            output_path=output_path,
        )

        assert result.success is True
        assert result.tasks_updated == 1

    @pytest.mark.asyncio
    async def test_export_creates_file(
        self, sync_service, temp_vault, test_db, inbox_project, sample_task
    ):
        """Экспорт создаёт файл."""
        output_path = str(Path(temp_vault) / "new_dir" / "export.md")

        result = await sync_service.export_to_obsidian(output_path=output_path)

        assert result.success is True
        assert Path(output_path).exists()

    @pytest.mark.asyncio
    async def test_export_markdown_format(self, sync_service, temp_vault, test_db):
        """Проверка формата экспортированного markdown."""
        # Создаём проект и задачу
        project = Project(name="Test Project")
        test_db.add(project)
        await test_db.flush()

        task = Task(
            title="Test Task",
            project_id=project.id,
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH,
            due_date=date(2026, 1, 25),
        )
        test_db.add(task)
        await test_db.flush()

        output_path = str(Path(temp_vault) / "export.md")
        await sync_service.export_to_obsidian(output_path=output_path)

        content = Path(output_path).read_text(encoding="utf-8")

        assert "# Exported Tasks" in content
        assert "## Test Project" in content
        assert "[x]" in content  # Done task
        assert "Test Task" in content

    @pytest.mark.asyncio
    async def test_export_already_in_progress(self, sync_service, test_db):
        """Экспорт когда синхронизация уже идёт."""
        log = SyncLog(sync_type=SyncType.EXPORT, status=SyncStatus.IN_PROGRESS)
        test_db.add(log)
        await test_db.flush()

        result = await sync_service.export_to_obsidian()

        assert result.success is False
        assert "already in progress" in result.error_message.lower()


# =============================================================================
# ТЕСТЫ: SyncService.get_conflicts
# =============================================================================


class TestGetConflicts:
    """Тесты получения конфликтов."""

    @pytest.mark.asyncio
    async def test_get_all_unresolved(self, sync_service, sample_sync_log, sample_conflict):
        """Получение всех неразрешённых конфликтов."""
        conflicts = await sync_service.get_conflicts()

        assert len(conflicts) == 1
        assert conflicts[0].id == sample_conflict.id

    @pytest.mark.asyncio
    async def test_get_by_sync_log(self, sync_service, test_db, sample_sync_log, sample_conflict):
        """Получение конфликтов по sync_log_id."""
        # Создаём другой log и конфликт
        other_log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.COMPLETED)
        test_db.add(other_log)
        await test_db.flush()

        other_conflict = SyncConflict(
            sync_log_id=other_log.id,
            obsidian_path="/vault/other.md",
            obsidian_line=1,
            obsidian_title="Other Task",
            obsidian_status="todo",
            obsidian_priority="low",
            obsidian_modified=datetime.now(UTC),
        )
        test_db.add(other_conflict)
        await test_db.flush()

        conflicts = await sync_service.get_conflicts(sync_log_id=sample_sync_log.id)

        assert len(conflicts) == 1
        assert conflicts[0].sync_log_id == sample_sync_log.id

    @pytest.mark.asyncio
    async def test_get_conflicts_empty(self, sync_service):
        """Нет конфликтов."""
        conflicts = await sync_service.get_conflicts()
        assert conflicts == []


# =============================================================================
# ТЕСТЫ: SyncService.resolve_conflict
# =============================================================================


class TestResolveConflict:
    """Тесты разрешения конфликтов."""

    @pytest.mark.asyncio
    async def test_resolve_obsidian(self, sync_service, sample_conflict, sample_task, test_db):
        """Разрешение в пользу Obsidian."""
        resolved = await sync_service.resolve_conflict(
            sample_conflict.id,
            ConflictResolution.OBSIDIAN,
        )

        assert resolved.resolution == ConflictResolution.OBSIDIAN
        assert resolved.resolved_at is not None

        # Проверяем что задача обновлена
        await test_db.refresh(sample_task)
        assert sample_task.status == TaskStatus.DONE
        assert sample_task.priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_resolve_database(self, sync_service, sample_conflict, temp_vault):
        """Разрешение в пользу базы данных."""
        # Создаём файл для обновления
        file_path = create_markdown_file(
            temp_vault,
            "file.md",
            "- [ ] Task from Obsidian\n",
        )
        sample_conflict.obsidian_path = file_path
        sample_conflict.obsidian_line = 1

        resolved = await sync_service.resolve_conflict(
            sample_conflict.id,
            ConflictResolution.DATABASE,
        )

        assert resolved.resolution == ConflictResolution.DATABASE

    @pytest.mark.asyncio
    async def test_resolve_skip(self, sync_service, sample_conflict, sample_task, test_db):
        """Пропуск конфликта."""
        original_status = sample_task.status

        resolved = await sync_service.resolve_conflict(
            sample_conflict.id,
            ConflictResolution.SKIP,
        )

        assert resolved.resolution == ConflictResolution.SKIP

        # Задача не должна измениться
        await test_db.refresh(sample_task)
        assert sample_task.status == original_status

    @pytest.mark.asyncio
    async def test_resolve_not_found(self, sync_service):
        """Разрешение несуществующего конфликта."""
        with pytest.raises(ValueError, match="not found"):
            await sync_service.resolve_conflict(99999, ConflictResolution.OBSIDIAN)

    @pytest.mark.asyncio
    async def test_resolve_already_resolved(self, sync_service, sample_conflict, test_db):
        """Повторное разрешение конфликта."""
        sample_conflict.resolution = ConflictResolution.SKIP
        sample_conflict.resolved_at = datetime.now(UTC)
        await test_db.flush()

        with pytest.raises(ValueError, match="already resolved"):
            await sync_service.resolve_conflict(sample_conflict.id, ConflictResolution.OBSIDIAN)


# =============================================================================
# ТЕСТЫ: SyncService.resolve_all_conflicts
# =============================================================================


class TestResolveAllConflicts:
    """Тесты массового разрешения конфликтов."""

    @pytest.mark.asyncio
    async def test_resolve_all(self, sync_service, test_db, sample_sync_log, sample_task):
        """Массовое разрешение конфликтов."""
        # Создаём несколько конфликтов
        for i in range(3):
            conflict = SyncConflict(
                sync_log_id=sample_sync_log.id,
                task_id=sample_task.id,
                obsidian_path="/vault/file.md",
                obsidian_line=i + 1,
                obsidian_title=f"Task {i}",
                obsidian_status="done",
                obsidian_priority="high",
                obsidian_modified=datetime.now(UTC),
            )
            test_db.add(conflict)
        await test_db.flush()

        count = await sync_service.resolve_all_conflicts(
            sample_sync_log.id,
            ConflictResolution.SKIP,
        )

        assert count == 3

    @pytest.mark.asyncio
    async def test_resolve_all_empty(self, sync_service, sample_sync_log):
        """Массовое разрешение когда нет конфликтов."""
        count = await sync_service.resolve_all_conflicts(
            sample_sync_log.id,
            ConflictResolution.OBSIDIAN,
        )

        assert count == 0


# =============================================================================
# ТЕСТЫ: SyncService.get_sync_history
# =============================================================================


class TestGetSyncHistory:
    """Тесты получения истории синхронизаций."""

    @pytest.mark.asyncio
    async def test_get_history(self, sync_service, test_db):
        """Получение истории."""
        for _ in range(5):
            log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.COMPLETED)
            test_db.add(log)
        await test_db.flush()

        history = await sync_service.get_sync_history(limit=10)

        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_get_history_with_limit(self, sync_service, test_db):
        """Получение истории с лимитом."""
        for _ in range(10):
            log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.COMPLETED)
            test_db.add(log)
        await test_db.flush()

        history = await sync_service.get_sync_history(limit=5)

        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_get_history_empty(self, sync_service):
        """Пустая история."""
        history = await sync_service.get_sync_history()
        assert history == []


# =============================================================================
# ТЕСТЫ: Helper методы
# =============================================================================


class TestHelperMethods:
    """Тесты вспомогательных методов."""

    def test_map_status_todo(self, sync_service):
        """Маппинг статуса todo."""
        result = sync_service._map_status("todo")
        assert result == TaskStatus.TODO

    def test_map_status_done(self, sync_service):
        """Маппинг статуса done."""
        result = sync_service._map_status("done")
        assert result == TaskStatus.DONE

    def test_map_status_case_insensitive(self, sync_service):
        """Маппинг статуса регистронезависим."""
        assert sync_service._map_status("DONE") == TaskStatus.DONE
        assert sync_service._map_status("Todo") == TaskStatus.TODO

    def test_map_priority_high(self, sync_service):
        """Маппинг приоритета high."""
        result = sync_service._map_priority("high")
        assert result == TaskPriority.HIGH

    def test_map_priority_medium(self, sync_service):
        """Маппинг приоритета medium."""
        result = sync_service._map_priority("medium")
        assert result == TaskPriority.MEDIUM

    def test_map_priority_low(self, sync_service):
        """Маппинг приоритета low."""
        result = sync_service._map_priority("low")
        assert result == TaskPriority.LOW

    def test_map_priority_unknown_defaults_medium(self, sync_service):
        """Неизвестный приоритет → medium."""
        result = sync_service._map_priority("unknown")
        assert result == TaskPriority.MEDIUM

    def test_task_to_parsed(self, sync_service, sample_task):
        """Конвертация Task в ParsedTask."""
        sample_task.status = TaskStatus.DONE
        sample_task.priority = TaskPriority.HIGH
        sample_task.due_date = date(2026, 1, 25)

        parsed = sync_service._task_to_parsed(sample_task)

        assert parsed.title == sample_task.title
        assert parsed.status == "done"
        assert parsed.priority == "high"
        assert parsed.due_date == date(2026, 1, 25)


# =============================================================================
# ТЕСТЫ: Edge cases и Error handling
# =============================================================================


class TestEdgeCases:
    """Тесты граничных случаев."""

    @pytest.mark.asyncio
    async def test_import_file_with_no_tasks(self, sync_service, temp_vault):
        """Импорт файла без задач."""
        file_path = create_markdown_file(
            temp_vault,
            "empty.md",
            "# Just a header\n\nSome text without tasks.",
        )

        result = await sync_service.import_from_obsidian([file_path])

        assert result.success is True
        assert result.tasks_created == 0

    @pytest.mark.asyncio
    async def test_import_file_with_encoding(self, sync_service, temp_vault):
        """Импорт файла с UTF-8 содержимым."""
        file_path = create_markdown_file(
            temp_vault,
            "utf8.md",
            "- [ ] Задача с эмодзи 📅 🔼 #здоровье\n",
        )

        result = await sync_service.import_from_obsidian([file_path])

        assert result.success is True
        assert result.tasks_created == 1

    @pytest.mark.asyncio
    async def test_service_with_default_config(self, test_db):
        """Сервис с default конфигурацией."""
        service = SyncService(test_db)

        assert service.config is not None
        assert service.config.default_project == "Inbox"

    @pytest.mark.asyncio
    async def test_import_creates_project_if_not_exists(self, sync_service, temp_vault, test_db):
        """Импорт создаёт проект если его нет."""
        sync_service.config.tag_mapping = {"newproject": "NewProject"}
        sync_service.resolver = __import__(
            "src.integrations.obsidian.project_resolver", fromlist=["ProjectResolver"]
        ).ProjectResolver(sync_service.config)

        file_path = create_markdown_file(
            temp_vault,
            "tasks.md",
            "- [ ] Task #newproject\n",
        )

        result = await sync_service.import_from_obsidian([file_path])

        assert result.success is True

        # Проверяем что проект создан
        from src.repositories import ProjectRepository

        project_repo = ProjectRepository(test_db)
        projects = await project_repo.search_by_name("NewProject")
        assert len(projects) == 1
