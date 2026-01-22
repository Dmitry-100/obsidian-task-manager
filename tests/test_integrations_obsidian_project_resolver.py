"""
Тесты для ProjectResolver — определение проекта для задачи.

Покрывает:
- Каскадную логику определения проекта
- Резолвинг по project tag, section, folder, tag mapping
- Загрузку конфигурации
- SyncConfig dataclass
"""

import contextlib
import os
import tempfile
from pathlib import Path

import pytest

from src.integrations.obsidian.parser import ParsedTask
from src.integrations.obsidian.project_resolver import (
    ProjectResolver,
    SyncConfig,
    create_default_config,
    get_config,
    load_sync_config,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def default_config():
    """Создаёт конфигурацию по умолчанию."""
    return create_default_config()


@pytest.fixture
def custom_config():
    """Создаёт кастомную конфигурацию для тестов."""
    return SyncConfig(
        vault_path="/test/vault",
        sync_sources=["00_Inbox/*.md", "01_Projects/**/Tasks.md"],
        folder_mapping={
            "01_Projects/КХП": "Столовая КХП",
            "01_Projects/Crypto": "Крипто",
            "02_Areas/Health": "Здоровье",
        },
        tag_mapping={
            "health": "Здоровье",
            "crypto": "Крипто",
            "work": "Работа",
            "khp": "Столовая КХП",
        },
        section_mapping={
            r"Здоровье|Health": "Здоровье",
            r"Крипто|Crypto|Polkadot": "Крипто",
            r"КХП|Столовая": "Столовая КХП",
        },
        default_project="Inbox",
        default_conflict_resolution="ask",
    )


@pytest.fixture
def resolver(custom_config):
    """Создаёт резолвер с кастомной конфигурацией."""
    return ProjectResolver(custom_config)


@pytest.fixture
def temp_config_file():
    """Создаёт временный YAML файл конфигурации."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        yield f
    with contextlib.suppress(OSError):
        os.unlink(f.name)


# =============================================================================
# ТЕСТЫ: SyncConfig dataclass
# =============================================================================


class TestSyncConfig:
    """Тесты SyncConfig dataclass."""

    def test_create_config_minimal(self):
        """Минимальная конфигурация."""
        config = SyncConfig(
            vault_path="/path/to/vault",
            sync_sources=["*.md"],
            folder_mapping={},
            tag_mapping={},
            section_mapping={},
        )

        assert config.vault_path == "/path/to/vault"
        assert config.default_project == "Inbox"
        assert config.default_conflict_resolution == "ask"

    def test_create_config_full(self):
        """Полная конфигурация."""
        config = SyncConfig(
            vault_path="/vault",
            sync_sources=["a.md", "b.md"],
            folder_mapping={"folder": "Project"},
            tag_mapping={"tag": "Project"},
            section_mapping={"section": "Project"},
            default_project="Custom",
            default_conflict_resolution="obsidian",
        )

        assert config.default_project == "Custom"
        assert config.default_conflict_resolution == "obsidian"


# =============================================================================
# ТЕСТЫ: create_default_config
# =============================================================================


class TestCreateDefaultConfig:
    """Тесты создания конфигурации по умолчанию."""

    def test_default_config_structure(self, default_config):
        """Структура default конфигурации."""
        assert default_config.vault_path == ""
        assert default_config.default_project == "Inbox"
        assert len(default_config.sync_sources) > 0
        assert len(default_config.folder_mapping) > 0
        assert len(default_config.tag_mapping) > 0
        assert len(default_config.section_mapping) > 0

    def test_default_config_has_common_mappings(self, default_config):
        """Default конфиг содержит типичные маппинги."""
        # Tag mappings
        assert "health" in default_config.tag_mapping
        assert "family" in default_config.tag_mapping

        # Section mappings (regex patterns as keys)
        section_keys = list(default_config.section_mapping.keys())
        assert any("Здоровье" in k or "Health" in k for k in section_keys)


# =============================================================================
# ТЕСТЫ: load_sync_config
# =============================================================================


class TestLoadSyncConfig:
    """Тесты загрузки конфигурации из YAML."""

    def test_load_valid_config(self, temp_config_file):
        """Загрузка валидного YAML."""
        yaml_content = """
vault_path: "/path/to/vault"
sync_sources:
  - "*.md"
  - "**/*.md"
folder_mapping:
  "01_Projects/Test": "Test Project"
tag_mapping:
  test: "Test Project"
section_mapping:
  "Test|Testing": "Test Project"
default_project: "Inbox"
default_conflict_resolution: "database"
"""
        temp_config_file.write(yaml_content)
        temp_config_file.close()

        config = load_sync_config(temp_config_file.name)

        assert config.vault_path == "/path/to/vault"
        assert len(config.sync_sources) == 2
        assert config.folder_mapping["01_Projects/Test"] == "Test Project"
        assert config.tag_mapping["test"] == "Test Project"
        assert config.default_conflict_resolution == "database"

    def test_load_config_file_not_found(self):
        """Файл не найден — FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_sync_config("/nonexistent/path/config.yaml")

    def test_load_config_with_path_object(self, temp_config_file):
        """Загрузка с Path объектом."""
        temp_config_file.write(
            "vault_path: /vault\nsync_sources: []\nfolder_mapping: {}\ntag_mapping: {}\nsection_mapping: {}"
        )
        temp_config_file.close()

        config = load_sync_config(Path(temp_config_file.name))

        assert config.vault_path == "/vault"

    def test_load_config_defaults_for_missing_keys(self, temp_config_file):
        """Отсутствующие ключи получают дефолтные значения."""
        yaml_content = """
vault_path: "/vault"
"""
        temp_config_file.write(yaml_content)
        temp_config_file.close()

        config = load_sync_config(temp_config_file.name)

        assert config.sync_sources == []
        assert config.folder_mapping == {}
        assert config.default_project == "Inbox"


# =============================================================================
# ТЕСТЫ: ProjectResolver._resolve_from_project_tag
# =============================================================================


class TestResolveFromProjectTag:
    """Тесты резолвинга по явному #project/name тегу."""

    def test_project_tag_found(self, resolver):
        """#project/name найден."""
        task = ParsedTask(
            title="Задача",
            status="todo",
            priority="medium",
            tags=["other", "project/КХП", "urgent"],
        )

        result = resolver._resolve_from_project_tag(task.tags)

        assert result == "КХП"

    def test_project_tag_not_found(self, resolver):
        """#project/name не найден."""
        task = ParsedTask(
            title="Задача",
            status="todo",
            priority="medium",
            tags=["health", "urgent"],
        )

        result = resolver._resolve_from_project_tag(task.tags)

        assert result is None

    def test_project_tag_empty_tags(self, resolver):
        """Пустой список тегов."""
        result = resolver._resolve_from_project_tag([])
        assert result is None

    def test_project_tag_multiple_projects(self, resolver):
        """Несколько project tags — первый побеждает."""
        tags = ["project/First", "project/Second"]

        result = resolver._resolve_from_project_tag(tags)

        assert result == "First"


# =============================================================================
# ТЕСТЫ: ProjectResolver._resolve_from_section
# =============================================================================


class TestResolveFromSection:
    """Тесты резолвинга по секции файла."""

    def test_section_exact_match(self, resolver):
        """Точное совпадение секции."""
        result = resolver._resolve_from_section("Здоровье")
        assert result == "Здоровье"

    def test_section_regex_match(self, resolver):
        """Regex совпадение."""
        result = resolver._resolve_from_section("Health")
        assert result == "Здоровье"

    def test_section_no_match(self, resolver):
        """Секция не соответствует ни одному паттерну."""
        result = resolver._resolve_from_section("Неизвестная секция")
        assert result is None

    def test_section_case_insensitive(self, resolver):
        """Регистронезависимое сопоставление."""
        result = resolver._resolve_from_section("ЗДОРОВЬЕ")
        assert result == "Здоровье"

    def test_section_partial_match(self, resolver):
        """Частичное совпадение (regex search)."""
        # Если в mapping есть "Polkadot" и секция "Polkadot Ecosystem"
        result = resolver._resolve_from_section("Polkadot Ecosystem")
        assert result == "Крипто"


# =============================================================================
# ТЕСТЫ: ProjectResolver._resolve_from_folder
# =============================================================================


class TestResolveFromFolder:
    """Тесты резолвинга по папке файла."""

    def test_folder_match(self, resolver):
        """Папка соответствует маппингу."""
        result = resolver._resolve_from_folder("/test/vault/01_Projects/КХП/file.md")
        assert result == "Столовая КХП"

    def test_folder_no_match(self, resolver):
        """Папка не соответствует маппингу."""
        result = resolver._resolve_from_folder("/test/vault/03_Resources/file.md")
        assert result is None

    def test_folder_file_not_in_vault(self, resolver):
        """Файл вне vault — None."""
        result = resolver._resolve_from_folder("/other/path/file.md")
        assert result is None

    def test_folder_nested_path(self, resolver):
        """Вложенный путь — совпадение по префиксу."""
        result = resolver._resolve_from_folder("/test/vault/02_Areas/Health/subdir/file.md")
        assert result == "Здоровье"


# =============================================================================
# ТЕСТЫ: ProjectResolver._resolve_from_tags
# =============================================================================


class TestResolveFromTags:
    """Тесты резолвинга по обычным тегам."""

    def test_tag_found(self, resolver):
        """Тег найден в маппинге."""
        result = resolver._resolve_from_tags(["health"])
        assert result == "Здоровье"

    def test_tag_not_found(self, resolver):
        """Тег не найден."""
        result = resolver._resolve_from_tags(["unknown"])
        assert result is None

    def test_tag_case_insensitive(self, resolver):
        """Регистронезависимый поиск."""
        result = resolver._resolve_from_tags(["HEALTH"])
        assert result == "Здоровье"

    def test_tag_first_match_wins(self, resolver):
        """Первый совпавший тег побеждает."""
        result = resolver._resolve_from_tags(["crypto", "health"])
        assert result == "Крипто"

    def test_tag_project_prefix_skipped(self, resolver):
        """Теги с project/ пропускаются."""
        result = resolver._resolve_from_tags(["project/Test", "health"])
        assert result == "Здоровье"

    def test_tag_empty_list(self, resolver):
        """Пустой список тегов."""
        result = resolver._resolve_from_tags([])
        assert result is None


# =============================================================================
# ТЕСТЫ: ProjectResolver.resolve — каскадная логика
# =============================================================================


class TestResolveCascade:
    """Тесты полной каскадной логики резолвинга."""

    def test_cascade_project_tag_wins(self, resolver):
        """#project/name имеет наивысший приоритет."""
        task = ParsedTask(
            title="Задача",
            status="todo",
            priority="medium",
            tags=["project/CustomProject", "health"],
            section="Крипто",
            source_file="/test/vault/01_Projects/КХП/file.md",
        )

        result = resolver.resolve(task)

        assert result == "CustomProject"

    def test_cascade_section_after_project_tag(self, resolver):
        """Секция проверяется если нет project tag."""
        task = ParsedTask(
            title="Задача",
            status="todo",
            priority="medium",
            tags=["health"],
            section="Крипто",
            source_file="/test/vault/01_Projects/КХП/file.md",
        )

        result = resolver.resolve(task)

        assert result == "Крипто"

    def test_cascade_folder_after_section(self, resolver):
        """Папка проверяется если нет section match."""
        task = ParsedTask(
            title="Задача",
            status="todo",
            priority="medium",
            tags=["health"],
            section="Неизвестная секция",
            source_file="/test/vault/01_Projects/КХП/file.md",
        )

        result = resolver.resolve(task)

        assert result == "Столовая КХП"

    def test_cascade_tag_after_folder(self, resolver):
        """Тег проверяется если нет folder match."""
        task = ParsedTask(
            title="Задача",
            status="todo",
            priority="medium",
            tags=["health"],
            section="Неизвестная",
            source_file="/test/vault/03_Resources/file.md",
        )

        result = resolver.resolve(task)

        assert result == "Здоровье"

    def test_cascade_default_fallback(self, resolver):
        """Default project если ничего не совпало."""
        task = ParsedTask(
            title="Задача",
            status="todo",
            priority="medium",
            tags=["unknown"],
            section=None,
            source_file="/other/path/file.md",
        )

        result = resolver.resolve(task)

        assert result == "Inbox"

    def test_cascade_no_metadata(self, resolver):
        """Задача без метаданных — default."""
        task = ParsedTask(
            title="Простая задача",
            status="todo",
            priority="medium",
        )

        result = resolver.resolve(task)

        assert result == "Inbox"


# =============================================================================
# ТЕСТЫ: ProjectResolver.get_tags_for_project
# =============================================================================


class TestGetTagsForProject:
    """Тесты получения тегов по имени проекта."""

    def test_get_tags_single(self, resolver):
        """Один тег для проекта."""
        tags = resolver.get_tags_for_project("Работа")
        assert "work" in tags

    def test_get_tags_multiple(self, custom_config):
        """Несколько тегов для проекта."""
        # Добавим дополнительный тег для Здоровье
        custom_config.tag_mapping["fitness"] = "Здоровье"
        resolver = ProjectResolver(custom_config)

        tags = resolver.get_tags_for_project("Здоровье")

        assert "health" in tags
        assert "fitness" in tags

    def test_get_tags_none(self, resolver):
        """Проект без тегов."""
        tags = resolver.get_tags_for_project("НесуществующийПроект")
        assert tags == []


# =============================================================================
# ТЕСТЫ: ProjectResolver с regex паттернами
# =============================================================================


class TestRegexPatterns:
    """Тесты regex паттернов в section_mapping."""

    def test_regex_or_pattern(self, resolver):
        """Паттерн с | (or)."""
        # "Здоровье|Health" → "Здоровье"
        assert resolver._resolve_from_section("Здоровье") == "Здоровье"
        assert resolver._resolve_from_section("Health") == "Здоровье"

    def test_invalid_regex_escaped(self):
        """Невалидный regex экранируется как литерал."""
        config = SyncConfig(
            vault_path="/vault",
            sync_sources=[],
            folder_mapping={},
            tag_mapping={},
            section_mapping={"[invalid": "Project"},  # Невалидный regex
        )
        resolver = ProjectResolver(config)

        # Должен работать как литеральная строка
        result = resolver._resolve_from_section("[invalid")
        assert result == "Project"


# =============================================================================
# ТЕСТЫ: get_config (глобальная функция)
# =============================================================================


class TestGetConfig:
    """Тесты глобальной функции get_config."""

    def test_get_config_returns_sync_config(self):
        """get_config возвращает SyncConfig."""
        config = get_config()

        assert isinstance(config, SyncConfig)
        assert config.default_project is not None

    def test_get_config_fallback_to_default(self):
        """При отсутствии файла — default config."""
        # get_config должен не падать, а вернуть default
        config = get_config()
        assert config is not None


# =============================================================================
# ТЕСТЫ: Edge cases
# =============================================================================


class TestEdgeCases:
    """Тесты граничных случаев."""

    def test_empty_config(self):
        """Пустая конфигурация."""
        config = SyncConfig(
            vault_path="",
            sync_sources=[],
            folder_mapping={},
            tag_mapping={},
            section_mapping={},
            default_project="Default",
        )
        resolver = ProjectResolver(config)

        task = ParsedTask(title="Task", status="todo", priority="medium")
        result = resolver.resolve(task)

        assert result == "Default"

    def test_task_with_none_values(self, resolver):
        """Задача с None значениями."""
        task = ParsedTask(
            title="Task",
            status="todo",
            priority="medium",
            tags=[],
            section=None,
            source_file="",
        )

        result = resolver.resolve(task)

        assert result == "Inbox"

    def test_unicode_in_mappings(self):
        """Unicode в маппингах."""
        config = SyncConfig(
            vault_path="/vault",
            sync_sources=[],
            folder_mapping={"01_Projects/Проект": "Проект"},
            tag_mapping={"тег": "Проект"},
            section_mapping={"Секция": "Проект"},
            default_project="Inbox",
        )
        resolver = ProjectResolver(config)

        task = ParsedTask(
            title="Задача",
            status="todo",
            priority="medium",
            section="Секция",
        )

        result = resolver.resolve(task)
        assert result == "Проект"
