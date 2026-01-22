"""
Тесты для Sync API endpoints.

Покрывает:
- GET /sync/status
- POST /sync/import
- POST /sync/export
- GET /sync/conflicts
- GET /sync/conflicts/{id}
- POST /sync/conflicts/{id}/resolve
- POST /sync/conflicts/resolve-all
- GET /sync/history
- GET /sync/config
- PUT /sync/config
- Авторизацию и обработку ошибок
"""

import shutil
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models import Project, SyncConflict, SyncLog, Task, TaskPriority, TaskStatus
from src.models.sync_conflict import ConflictResolution
from src.models.sync_log import SyncStatus, SyncType

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_vault():
    """Создаёт временную директорию vault."""
    vault_path = tempfile.mkdtemp(prefix="test_vault_")
    yield vault_path
    shutil.rmtree(vault_path, ignore_errors=True)


@pytest_asyncio.fixture
async def sample_project(test_db):
    """Создаёт тестовый проект."""
    project = Project(name="Test Project")
    test_db.add(project)
    await test_db.flush()
    return project


@pytest_asyncio.fixture
async def sample_task(test_db, sample_project):
    """Создаёт тестовую задачу."""
    task = Task(
        title="Test Task",
        project_id=sample_project.id,
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
        tasks_created=5,
        tasks_updated=3,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
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
        obsidian_title="Obsidian Task",
        obsidian_status="done",
        obsidian_due_date=date(2026, 1, 25),
        obsidian_priority="high",
        obsidian_modified=datetime.now(UTC),
        db_title="DB Task",
        db_status="todo",
        db_priority="medium",
        db_modified=datetime.now(UTC),
    )
    test_db.add(conflict)
    await test_db.flush()
    return conflict


def create_markdown_file(vault_path: str, filename: str, content: str) -> str:
    """Создаёт markdown файл в vault."""
    path = Path(vault_path) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


# =============================================================================
# ТЕСТЫ: Авторизация
# =============================================================================


class TestSyncAuth:
    """Тесты авторизации для sync endpoints."""

    @pytest.mark.asyncio
    async def test_sync_status_without_auth(self):
        """GET /sync/status без авторизации → 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/sync/status")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sync_import_without_auth(self):
        """POST /api/v1/sync/import без авторизации → 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/sync/import")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sync_conflicts_without_auth(self):
        """GET /api/v1/sync/conflicts без авторизации → 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/sync/conflicts")

        assert response.status_code == 401


# =============================================================================
# ТЕСТЫ: GET /sync/status
# =============================================================================


class TestGetSyncStatus:
    """Тесты получения статуса синхронизации."""

    @pytest.mark.asyncio
    async def test_get_status_empty(self, test_client: AsyncClient):
        """GET /sync/status при отсутствии синхронизаций."""
        response = await test_client.get("/api/v1/sync/status")

        assert response.status_code == 200
        data = response.json()

        assert data["is_syncing"] is False
        assert data["last_sync"] is None
        assert data["unresolved_conflicts"] == 0
        assert data["total_syncs"] == 0

    @pytest.mark.asyncio
    async def test_get_status_with_history(self, test_client: AsyncClient, sample_sync_log):
        """GET /sync/status с историей."""
        response = await test_client.get("/api/v1/sync/status")

        assert response.status_code == 200
        data = response.json()

        assert data["last_sync"] is not None
        assert data["total_syncs"] == 1

    @pytest.mark.asyncio
    async def test_get_status_with_conflicts(
        self, test_client: AsyncClient, sample_sync_log, sample_conflict
    ):
        """GET /sync/status с конфликтами."""
        response = await test_client.get("/api/v1/sync/status")

        data = response.json()
        assert data["unresolved_conflicts"] == 1

    @pytest.mark.asyncio
    async def test_get_status_is_syncing(self, test_client: AsyncClient, test_db):
        """GET /sync/status во время синхронизации."""
        log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.IN_PROGRESS)
        test_db.add(log)
        await test_db.flush()

        response = await test_client.get("/api/v1/sync/status")

        data = response.json()
        assert data["is_syncing"] is True


# =============================================================================
# ТЕСТЫ: POST /sync/import
# =============================================================================


class TestSyncImport:
    """Тесты импорта из Obsidian."""

    @pytest.mark.asyncio
    async def test_import_empty_request(self, test_client: AsyncClient):
        """POST /sync/import без параметров."""
        response = await test_client.post("/api/v1/sync/import")

        # Должен работать (использует config по умолчанию)
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_import_with_files(self, test_client: AsyncClient, temp_vault):
        """POST /sync/import с указанием файлов."""
        file_path = create_markdown_file(
            temp_vault,
            "tasks.md",
            "- [ ] Test task\n",
        )

        response = await test_client.post(
            "/api/v1/sync/import",
            json={"source_files": [file_path]},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["sync_log_id"] is not None
        assert data["tasks_created"] == 1

    @pytest.mark.asyncio
    async def test_import_creates_sync_log(self, test_client: AsyncClient, temp_vault):
        """POST /sync/import создаёт запись в истории."""
        file_path = create_markdown_file(temp_vault, "tasks.md", "- [ ] Task\n")

        response = await test_client.post(
            "/api/v1/sync/import",
            json={"source_files": [file_path]},
        )

        assert response.status_code == 200

        # Проверяем историю
        history_response = await test_client.get("/api/v1/sync/history")
        history = history_response.json()

        assert len(history) >= 1
        assert history[0]["sync_type"] == "import"

    @pytest.mark.asyncio
    async def test_import_when_already_syncing(self, test_client: AsyncClient, test_db):
        """POST /sync/import когда синхронизация уже идёт → 400."""
        log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.IN_PROGRESS)
        test_db.add(log)
        await test_db.flush()

        response = await test_client.post("/api/v1/sync/import")

        assert response.status_code == 400
        assert "already in progress" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_import_response_format(self, test_client: AsyncClient, temp_vault):
        """POST /sync/import возвращает правильный формат."""
        file_path = create_markdown_file(temp_vault, "tasks.md", "- [ ] Task\n")

        response = await test_client.post(
            "/api/v1/sync/import",
            json={"source_files": [file_path]},
        )

        data = response.json()

        assert "success" in data
        assert "sync_log_id" in data
        assert "tasks_created" in data
        assert "tasks_updated" in data
        assert "tasks_skipped" in data
        assert "conflicts_count" in data


# =============================================================================
# ТЕСТЫ: POST /sync/export
# =============================================================================


class TestSyncExport:
    """Тесты экспорта в Obsidian."""

    @pytest.mark.asyncio
    async def test_export_with_output_path(
        self, test_client: AsyncClient, temp_vault, sample_project, sample_task
    ):
        """POST /sync/export с указанием пути."""
        output_path = str(Path(temp_vault) / "export.md")

        response = await test_client.post(
            "/api/v1/sync/export",
            json={"output_path": output_path},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert Path(output_path).exists()

    @pytest.mark.asyncio
    async def test_export_by_project(
        self, test_client: AsyncClient, temp_vault, sample_project, sample_task
    ):
        """POST /sync/export для конкретного проекта."""
        output_path = str(Path(temp_vault) / "export.md")

        response = await test_client.post(
            "/api/v1/sync/export",
            json={"project_id": sample_project.id, "output_path": output_path},
        )

        assert response.status_code == 200

        content = Path(output_path).read_text()
        assert "Test Task" in content

    @pytest.mark.asyncio
    async def test_export_creates_file(
        self, test_client: AsyncClient, temp_vault, sample_project, sample_task
    ):
        """POST /sync/export создаёт файл."""
        output_path = str(Path(temp_vault) / "new_dir" / "export.md")

        response = await test_client.post(
            "/api/v1/sync/export",
            json={"output_path": output_path},
        )

        assert response.status_code == 200
        assert Path(output_path).exists()


# =============================================================================
# ТЕСТЫ: GET /sync/conflicts
# =============================================================================


class TestGetConflicts:
    """Тесты получения списка конфликтов."""

    @pytest.mark.asyncio
    async def test_get_conflicts_empty(self, test_client: AsyncClient):
        """GET /sync/conflicts при отсутствии конфликтов."""
        response = await test_client.get("/api/v1/sync/conflicts")

        assert response.status_code == 200
        data = response.json()

        assert data == []

    @pytest.mark.asyncio
    async def test_get_conflicts_list(
        self, test_client: AsyncClient, sample_sync_log, sample_conflict
    ):
        """GET /sync/conflicts возвращает список."""
        response = await test_client.get("/api/v1/sync/conflicts")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["id"] == sample_conflict.id
        assert data[0]["obsidian_title"] == "Obsidian Task"

    @pytest.mark.asyncio
    async def test_get_conflicts_by_sync_log(
        self, test_client: AsyncClient, test_db, sample_sync_log, sample_conflict
    ):
        """GET /sync/conflicts?sync_log_id=X фильтрует по sync_log."""
        # Создаём другой sync_log с конфликтом
        other_log = SyncLog(sync_type=SyncType.EXPORT, status=SyncStatus.COMPLETED)
        test_db.add(other_log)
        await test_db.flush()

        other_conflict = SyncConflict(
            sync_log_id=other_log.id,
            obsidian_path="/vault/other.md",
            obsidian_line=1,
            obsidian_title="Other",
            obsidian_status="todo",
            obsidian_priority="low",
            obsidian_modified=datetime.now(UTC),
        )
        test_db.add(other_conflict)
        await test_db.flush()

        response = await test_client.get(f"/api/v1/sync/conflicts?sync_log_id={sample_sync_log.id}")

        data = response.json()
        assert len(data) == 1
        assert data[0]["sync_log_id"] == sample_sync_log.id

    @pytest.mark.asyncio
    async def test_get_conflicts_response_format(
        self, test_client: AsyncClient, sample_sync_log, sample_conflict
    ):
        """GET /sync/conflicts возвращает правильный формат."""
        response = await test_client.get("/api/v1/sync/conflicts")

        data = response.json()[0]

        assert "id" in data
        assert "sync_log_id" in data
        assert "obsidian_path" in data
        assert "obsidian_title" in data
        assert "obsidian_status" in data
        assert "obsidian_priority" in data
        assert "db_title" in data
        assert "resolution" in data


# =============================================================================
# ТЕСТЫ: GET /sync/conflicts/{id}
# =============================================================================


class TestGetConflictById:
    """Тесты получения конфликта по ID."""

    @pytest.mark.asyncio
    async def test_get_conflict_success(
        self, test_client: AsyncClient, sample_sync_log, sample_conflict
    ):
        """GET /sync/conflicts/{id} возвращает конфликт."""
        response = await test_client.get(f"/api/v1/sync/conflicts/{sample_conflict.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == sample_conflict.id

    @pytest.mark.asyncio
    async def test_get_conflict_not_found(self, test_client: AsyncClient):
        """GET /sync/conflicts/{id} для несуществующего → 404."""
        response = await test_client.get("/api/v1/sync/conflicts/99999")

        assert response.status_code == 404


# =============================================================================
# ТЕСТЫ: POST /sync/conflicts/{id}/resolve
# =============================================================================


class TestResolveConflict:
    """Тесты разрешения конфликта."""

    @pytest.mark.asyncio
    async def test_resolve_obsidian(
        self, test_client: AsyncClient, sample_sync_log, sample_conflict
    ):
        """POST /sync/conflicts/{id}/resolve с resolution=obsidian."""
        response = await test_client.post(
            f"/api/v1/sync/conflicts/{sample_conflict.id}/resolve",
            json={"resolution": "obsidian"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resolution"] == "obsidian"
        assert data["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_resolve_database(
        self, test_client: AsyncClient, sample_sync_log, sample_conflict
    ):
        """POST /sync/conflicts/{id}/resolve с resolution=database."""
        response = await test_client.post(
            f"/api/v1/sync/conflicts/{sample_conflict.id}/resolve",
            json={"resolution": "database"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resolution"] == "database"

    @pytest.mark.asyncio
    async def test_resolve_skip(self, test_client: AsyncClient, sample_sync_log, sample_conflict):
        """POST /sync/conflicts/{id}/resolve с resolution=skip."""
        response = await test_client.post(
            f"/api/v1/sync/conflicts/{sample_conflict.id}/resolve",
            json={"resolution": "skip"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resolution"] == "skip"

    @pytest.mark.asyncio
    async def test_resolve_not_found(self, test_client: AsyncClient):
        """POST /sync/conflicts/{id}/resolve для несуществующего → 404."""
        response = await test_client.post(
            "/api/v1/sync/conflicts/99999/resolve",
            json={"resolution": "skip"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_resolve_already_resolved(
        self, test_client: AsyncClient, test_db, sample_sync_log, sample_conflict
    ):
        """POST /sync/conflicts/{id}/resolve для уже разрешённого → 400."""
        sample_conflict.resolution = ConflictResolution.SKIP
        sample_conflict.resolved_at = datetime.now(UTC)
        await test_db.flush()

        response = await test_client.post(
            f"/api/v1/sync/conflicts/{sample_conflict.id}/resolve",
            json={"resolution": "obsidian"},
        )

        assert response.status_code == 400
        assert "already resolved" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resolve_invalid_resolution(
        self, test_client: AsyncClient, sample_sync_log, sample_conflict
    ):
        """POST /sync/conflicts/{id}/resolve с невалидным resolution → 400/422."""
        response = await test_client.post(
            f"/api/v1/sync/conflicts/{sample_conflict.id}/resolve",
            json={"resolution": "invalid"},
        )

        # Может вернуть 400 или 422 в зависимости от валидации
        assert response.status_code in [400, 422]


# =============================================================================
# ТЕСТЫ: POST /sync/conflicts/resolve-all
# =============================================================================


class TestResolveAllConflicts:
    """Тесты массового разрешения конфликтов."""

    @pytest.mark.asyncio
    async def test_resolve_all_success(
        self, test_client: AsyncClient, test_db, sample_sync_log, sample_task
    ):
        """POST /sync/conflicts/resolve-all разрешает все конфликты."""
        # Создаём несколько конфликтов
        for i in range(3):
            conflict = SyncConflict(
                sync_log_id=sample_sync_log.id,
                task_id=sample_task.id,
                obsidian_path="/vault/file.md",
                obsidian_line=i + 1,
                obsidian_title=f"Task {i}",
                obsidian_status="todo",
                obsidian_priority="medium",
                obsidian_modified=datetime.now(UTC),
            )
            test_db.add(conflict)
        await test_db.flush()

        response = await test_client.post(
            f"/api/v1/sync/conflicts/resolve-all?sync_log_id={sample_sync_log.id}",
            json={"resolution": "skip"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resolved_count"] == 3
        assert data["resolution"] == "skip"

    @pytest.mark.asyncio
    async def test_resolve_all_empty(self, test_client: AsyncClient, sample_sync_log):
        """POST /sync/conflicts/resolve-all когда нет конфликтов."""
        response = await test_client.post(
            f"/api/v1/sync/conflicts/resolve-all?sync_log_id={sample_sync_log.id}",
            json={"resolution": "obsidian"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["resolved_count"] == 0

    @pytest.mark.asyncio
    async def test_resolve_all_missing_sync_log_id(self, test_client: AsyncClient):
        """POST /sync/conflicts/resolve-all без sync_log_id → 422."""
        response = await test_client.post(
            "/api/v1/sync/conflicts/resolve-all",
            json={"resolution": "skip"},
        )

        assert response.status_code == 422


# =============================================================================
# ТЕСТЫ: GET /sync/history
# =============================================================================


class TestGetSyncHistory:
    """Тесты получения истории синхронизаций."""

    @pytest.mark.asyncio
    async def test_get_history_empty(self, test_client: AsyncClient):
        """GET /sync/history при пустой истории."""
        response = await test_client.get("/api/v1/sync/history")

        assert response.status_code == 200
        data = response.json()

        assert data == []

    @pytest.mark.asyncio
    async def test_get_history_list(self, test_client: AsyncClient, sample_sync_log):
        """GET /sync/history возвращает список."""
        response = await test_client.get("/api/v1/sync/history")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["id"] == sample_sync_log.id

    @pytest.mark.asyncio
    async def test_get_history_with_limit(self, test_client: AsyncClient, test_db):
        """GET /sync/history?limit=N ограничивает результаты."""
        for _ in range(10):
            log = SyncLog(sync_type=SyncType.IMPORT, status=SyncStatus.COMPLETED)
            test_db.add(log)
        await test_db.flush()

        response = await test_client.get("/api/v1/sync/history?limit=5")

        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_get_history_response_format(self, test_client: AsyncClient, sample_sync_log):
        """GET /sync/history возвращает правильный формат."""
        response = await test_client.get("/api/v1/sync/history")

        data = response.json()[0]

        assert "id" in data
        assert "sync_type" in data
        assert "status" in data
        assert "tasks_created" in data
        assert "tasks_updated" in data
        assert "created_at" in data


# =============================================================================
# ТЕСТЫ: GET /sync/config
# =============================================================================


class TestGetSyncConfig:
    """Тесты получения конфигурации."""

    @pytest.mark.asyncio
    async def test_get_config(self, test_client: AsyncClient):
        """GET /sync/config возвращает конфигурацию."""
        response = await test_client.get("/api/v1/sync/config")

        assert response.status_code == 200
        data = response.json()

        assert "vault_path" in data
        assert "sync_sources" in data
        assert "folder_mapping" in data
        assert "tag_mapping" in data
        assert "section_mapping" in data
        assert "default_project" in data

    @pytest.mark.asyncio
    async def test_get_config_has_defaults(self, test_client: AsyncClient):
        """GET /sync/config содержит default значения."""
        response = await test_client.get("/api/v1/sync/config")

        data = response.json()

        assert data["default_project"] is not None


# =============================================================================
# ТЕСТЫ: PUT /sync/config
# =============================================================================


class TestUpdateSyncConfig:
    """Тесты обновления конфигурации."""

    @pytest.mark.asyncio
    async def test_update_vault_path(self, test_client: AsyncClient):
        """PUT /sync/config обновляет vault_path."""
        response = await test_client.put(
            "/api/v1/sync/config",
            json={"vault_path": "/new/vault/path"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["vault_path"] == "/new/vault/path"

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, test_client: AsyncClient):
        """PUT /sync/config обновляет несколько полей."""
        response = await test_client.put(
            "/api/v1/sync/config",
            json={
                "default_project": "NewDefault",
                "sync_sources": ["*.md", "**/*.md"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["default_project"] == "NewDefault"
        assert data["sync_sources"] == ["*.md", "**/*.md"]

    @pytest.mark.asyncio
    async def test_update_preserves_unspecified(self, test_client: AsyncClient):
        """PUT /sync/config сохраняет неуказанные поля."""
        # Получаем текущую конфигурацию
        get_response = await test_client.get("/api/v1/sync/config")
        original = get_response.json()

        # Обновляем только vault_path
        put_response = await test_client.put(
            "/api/v1/sync/config",
            json={"vault_path": "/updated/path"},
        )

        updated = put_response.json()

        # default_project должен остаться прежним
        assert updated["default_project"] == original["default_project"]

    @pytest.mark.asyncio
    async def test_update_tag_mapping(self, test_client: AsyncClient):
        """PUT /sync/config обновляет tag_mapping."""
        new_mapping = {
            "newtag": "NewProject",
            "anothertag": "AnotherProject",
        }

        response = await test_client.put(
            "/api/v1/sync/config",
            json={"tag_mapping": new_mapping},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["tag_mapping"] == new_mapping


# =============================================================================
# ТЕСТЫ: Edge cases и валидация
# =============================================================================


class TestEdgeCases:
    """Тесты граничных случаев."""

    @pytest.mark.asyncio
    async def test_import_with_empty_files_list(self, test_client: AsyncClient):
        """POST /sync/import с пустым списком файлов."""
        response = await test_client.post(
            "/api/v1/sync/import",
            json={"source_files": []},
        )

        # Должен работать
        assert response.status_code == 200
        data = response.json()
        # Когда source_files пустой, сервис может использовать config sources
        # поэтому не проверяем конкретное количество tasks_created
        assert "tasks_created" in data

    @pytest.mark.asyncio
    async def test_history_limit_validation(self, test_client: AsyncClient):
        """GET /sync/history с невалидным limit → 422."""
        response = await test_client.get("/api/v1/sync/history?limit=0")
        assert response.status_code == 422

        response = await test_client.get("/api/v1/sync/history?limit=1000")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_export_nonexistent_project(self, test_client: AsyncClient, temp_vault):
        """POST /sync/export для несуществующего проекта."""
        output_path = str(Path(temp_vault) / "export.md")

        response = await test_client.post(
            "/api/v1/sync/export",
            json={"project_id": 99999, "output_path": output_path},
        )

        # Должен работать, просто экспортировать пустой файл
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unicode_in_config(self, test_client: AsyncClient):
        """PUT /sync/config с unicode значениями."""
        response = await test_client.put(
            "/api/v1/sync/config",
            json={
                "tag_mapping": {
                    "здоровье": "Здоровье",
                    "работа": "Работа",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "здоровье" in data["tag_mapping"]
