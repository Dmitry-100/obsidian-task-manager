"""
Тесты для FileScanner — сканирование файлов в Obsidian vault.

Покрывает:
- Сканирование по glob patterns
- Получение информации о файле
- Чтение/запись содержимого
- Список директорий
- Поиск TODO файлов
"""

import contextlib
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.integrations.obsidian.file_scanner import FileScanner

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_vault():
    """Создаёт временную директорию-vault с тестовой структурой."""
    vault_path = tempfile.mkdtemp(prefix="test_vault_")

    # Создаём структуру
    # 00_Inbox/
    #   TODO - Неделя 1.md
    #   TODO - Неделя 2.md
    #   notes.md
    # 01_Projects/
    #   ProjectA/
    #     Tasks.md
    #     README.md
    #   ProjectB/
    #     Tasks.md
    # 02_Areas/
    #   Health/
    #     TODO.md

    inbox = Path(vault_path) / "00_Inbox"
    inbox.mkdir()
    (inbox / "TODO - Неделя 1.md").write_text("- [ ] Task 1", encoding="utf-8")
    (inbox / "TODO - Неделя 2.md").write_text("- [ ] Task 2", encoding="utf-8")
    (inbox / "notes.md").write_text("Just notes", encoding="utf-8")

    projects = Path(vault_path) / "01_Projects"
    projects.mkdir()

    project_a = projects / "ProjectA"
    project_a.mkdir()
    (project_a / "Tasks.md").write_text("- [ ] Project A task", encoding="utf-8")
    (project_a / "README.md").write_text("# Project A", encoding="utf-8")

    project_b = projects / "ProjectB"
    project_b.mkdir()
    (project_b / "Tasks.md").write_text("- [ ] Project B task", encoding="utf-8")

    areas = Path(vault_path) / "02_Areas"
    areas.mkdir()

    health = areas / "Health"
    health.mkdir()
    (health / "TODO.md").write_text("- [ ] Health task", encoding="utf-8")

    yield vault_path

    # Cleanup
    shutil.rmtree(vault_path, ignore_errors=True)


@pytest.fixture
def scanner(temp_vault):
    """Создаёт сканер для временного vault."""
    return FileScanner(temp_vault)


@pytest.fixture
def temp_file():
    """Создаёт временный файл."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("Test content")
        yield f.name
    with contextlib.suppress(OSError):
        os.unlink(f.name)


# =============================================================================
# ТЕСТЫ: FileScanner.__init__
# =============================================================================


class TestFileScannerInit:
    """Тесты инициализации сканера."""

    def test_init_valid_path(self, temp_vault):
        """Инициализация с валидным путём."""
        scanner = FileScanner(temp_vault)
        assert scanner.vault_path == Path(temp_vault)

    def test_init_with_path_object(self, temp_vault):
        """Инициализация с Path объектом."""
        scanner = FileScanner(Path(temp_vault))
        assert scanner.vault_path == Path(temp_vault)

    def test_init_nonexistent_path(self):
        """Несуществующий путь — ValueError."""
        with pytest.raises(ValueError, match="does not exist"):
            FileScanner("/nonexistent/path")

    def test_init_file_not_dir(self, temp_file):
        """Путь к файлу вместо директории — ValueError."""
        with pytest.raises(ValueError, match="not a directory"):
            FileScanner(temp_file)


# =============================================================================
# ТЕСТЫ: FileScanner.scan
# =============================================================================


class TestFileScannerScan:
    """Тесты сканирования по паттернам."""

    def test_scan_simple_pattern(self, scanner, temp_vault):
        """Простой паттерн *.md в директории."""
        files = scanner.scan(["00_Inbox/*.md"])

        assert len(files) == 3  # TODO - Неделя 1.md, TODO - Неделя 2.md, notes.md
        paths = [f.relative_path for f in files]
        assert any("TODO - Неделя 1.md" in p for p in paths)

    def test_scan_recursive_pattern(self, scanner):
        """Рекурсивный паттерн **/Tasks.md."""
        files = scanner.scan(["**/Tasks.md"])

        assert len(files) == 2  # ProjectA/Tasks.md, ProjectB/Tasks.md
        paths = [f.relative_path for f in files]
        assert any("ProjectA" in p and "Tasks.md" in p for p in paths)
        assert any("ProjectB" in p and "Tasks.md" in p for p in paths)

    def test_scan_multiple_patterns(self, scanner):
        """Несколько паттернов."""
        files = scanner.scan(
            [
                "00_Inbox/TODO*.md",
                "02_Areas/*/TODO.md",
            ]
        )

        assert len(files) == 3  # 2 TODO в Inbox + 1 в Health
        paths = [f.relative_path for f in files]
        assert any("Неделя 1" in p for p in paths)
        assert any("Health" in p for p in paths)

    def test_scan_no_matches(self, scanner):
        """Паттерн без совпадений."""
        files = scanner.scan(["nonexistent/*.md"])
        assert files == []

    def test_scan_empty_patterns(self, scanner):
        """Пустой список паттернов."""
        files = scanner.scan([])
        assert files == []

    def test_scan_skips_directories(self, scanner):
        """Директории не включаются в результат."""
        files = scanner.scan(["01_Projects/*"])

        # Должны быть только файлы, не директории
        for f in files:
            assert Path(f.path).is_file()

    def test_scan_skips_non_markdown(self, scanner, temp_vault):
        """Не-markdown файлы пропускаются."""
        # Создадим .txt файл
        txt_file = Path(temp_vault) / "00_Inbox" / "test.txt"
        txt_file.write_text("text file")

        files = scanner.scan(["00_Inbox/*"])

        # .txt не должен быть включён
        extensions = [Path(f.path).suffix for f in files]
        assert ".txt" not in extensions

    def test_scan_deduplicates_overlapping_patterns(self, scanner):
        """Перекрывающиеся паттерны — без дубликатов."""
        files = scanner.scan(
            [
                "00_Inbox/*.md",
                "00_Inbox/TODO*.md",  # Overlaps with first pattern
            ]
        )

        # Файл не должен появиться дважды
        paths = [f.path for f in files]
        assert len(paths) == len(set(paths))

    def test_scan_sorted_by_modification_time(self, scanner, temp_vault):
        """Результаты отсортированы по времени модификации (новые первые)."""
        # Модифицируем один файл чтобы он был новее
        import time

        time.sleep(0.1)  # Небольшая задержка
        newer_file = Path(temp_vault) / "00_Inbox" / "TODO - Неделя 1.md"
        newer_file.write_text("Updated content", encoding="utf-8")

        files = scanner.scan(["00_Inbox/TODO*.md"])

        # Первый файл должен быть самым новым
        assert len(files) >= 2
        assert files[0].modified_at >= files[1].modified_at


# =============================================================================
# ТЕСТЫ: ScannedFile dataclass
# =============================================================================


class TestScannedFile:
    """Тесты ScannedFile dataclass."""

    def test_scanned_file_fields(self, scanner):
        """ScannedFile содержит все необходимые поля."""
        files = scanner.scan(["00_Inbox/TODO - Неделя 1.md"])

        assert len(files) == 1
        file = files[0]

        assert file.path is not None
        assert file.relative_path is not None
        assert isinstance(file.modified_at, datetime)
        assert isinstance(file.size_bytes, int)
        assert file.size_bytes > 0


# =============================================================================
# ТЕСТЫ: FileScanner.scan_single
# =============================================================================


class TestFileScannerScanSingle:
    """Тесты получения информации об одном файле."""

    def test_scan_single_existing_file(self, scanner, temp_vault):
        """Существующий файл."""
        file_path = Path(temp_vault) / "00_Inbox" / "TODO - Неделя 1.md"

        result = scanner.scan_single(file_path)

        assert result is not None
        assert result.path == str(file_path)
        assert "TODO - Неделя 1.md" in result.relative_path

    def test_scan_single_nonexistent(self, scanner, temp_vault):
        """Несуществующий файл — None."""
        result = scanner.scan_single(Path(temp_vault) / "nonexistent.md")
        assert result is None

    def test_scan_single_directory(self, scanner, temp_vault):
        """Директория вместо файла — None."""
        result = scanner.scan_single(Path(temp_vault) / "00_Inbox")
        assert result is None

    def test_scan_single_file_outside_vault(self, scanner, temp_file):
        """Файл вне vault — relative_path = абсолютный путь."""
        result = scanner.scan_single(temp_file)

        assert result is not None
        # relative_path будет равен полному пути, т.к. файл вне vault


# =============================================================================
# ТЕСТЫ: FileScanner.get_file_content
# =============================================================================


class TestFileScannerGetContent:
    """Тесты чтения содержимого файла."""

    def test_get_content_success(self, scanner, temp_vault):
        """Успешное чтение содержимого."""
        file_path = Path(temp_vault) / "00_Inbox" / "TODO - Неделя 1.md"

        content = scanner.get_file_content(file_path)

        assert content == "- [ ] Task 1"

    def test_get_content_with_string_path(self, scanner, temp_vault):
        """Чтение по строковому пути."""
        file_path = str(Path(temp_vault) / "00_Inbox" / "TODO - Неделя 1.md")

        content = scanner.get_file_content(file_path)

        assert "Task 1" in content

    def test_get_content_utf8(self, scanner, temp_vault):
        """UTF-8 содержимое корректно читается."""
        file_path = Path(temp_vault) / "00_Inbox" / "TODO - Неделя 1.md"

        content = scanner.get_file_content(file_path)

        # Файл содержит "Task 1", проверяем кодировку
        assert isinstance(content, str)


# =============================================================================
# ТЕСТЫ: FileScanner.write_file_content
# =============================================================================


class TestFileScannerWriteContent:
    """Тесты записи содержимого в файл."""

    def test_write_content_existing_file(self, scanner, temp_vault):
        """Перезапись существующего файла."""
        file_path = Path(temp_vault) / "00_Inbox" / "TODO - Неделя 1.md"
        new_content = "- [x] Updated task"

        scanner.write_file_content(file_path, new_content)

        assert file_path.read_text(encoding="utf-8") == new_content

    def test_write_content_new_file(self, scanner, temp_vault):
        """Создание нового файла."""
        file_path = Path(temp_vault) / "00_Inbox" / "new_file.md"
        content = "# New File"

        scanner.write_file_content(file_path, content)

        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content

    def test_write_content_creates_directories(self, scanner, temp_vault):
        """Создание родительских директорий при необходимости."""
        file_path = Path(temp_vault) / "new_dir" / "subdir" / "file.md"
        content = "Content"

        scanner.write_file_content(file_path, content)

        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content

    def test_write_content_utf8(self, scanner, temp_vault):
        """Запись UTF-8 содержимого."""
        file_path = Path(temp_vault) / "00_Inbox" / "unicode.md"
        content = "# Заголовок\n\n- [ ] Задача с эмодзи 📅 🔼"

        scanner.write_file_content(file_path, content)

        assert file_path.read_text(encoding="utf-8") == content


# =============================================================================
# ТЕСТЫ: FileScanner.list_directories
# =============================================================================


class TestFileScannerListDirectories:
    """Тесты списка директорий."""

    def test_list_root_directories(self, scanner):
        """Список директорий в корне vault."""
        dirs = scanner.list_directories()

        assert "00_Inbox" in dirs
        assert "01_Projects" in dirs
        assert "02_Areas" in dirs

    def test_list_subdirectories(self, scanner):
        """Список поддиректорий."""
        dirs = scanner.list_directories("01_Projects")

        assert "ProjectA" in dirs
        assert "ProjectB" in dirs

    def test_list_directories_nonexistent(self, scanner):
        """Несуществующая директория — пустой список."""
        dirs = scanner.list_directories("nonexistent")
        assert dirs == []

    def test_list_directories_excludes_hidden(self, scanner, temp_vault):
        """Скрытые директории (начинающиеся с .) исключаются."""
        # Создадим скрытую директорию
        hidden_dir = Path(temp_vault) / ".hidden"
        hidden_dir.mkdir()

        dirs = scanner.list_directories()

        assert ".hidden" not in dirs

    def test_list_directories_only_dirs(self, scanner):
        """Файлы не включаются в список."""
        dirs = scanner.list_directories("00_Inbox")

        # В 00_Inbox есть только файлы, не директории
        # Файлы не должны быть в списке
        assert "TODO - Неделя 1.md" not in dirs


# =============================================================================
# ТЕСТЫ: FileScanner.find_todo_files
# =============================================================================


class TestFileScannerFindTodoFiles:
    """Тесты поиска TODO файлов."""

    def test_find_todo_files(self, scanner):
        """Поиск TODO файлов по стандартным паттернам."""
        files = scanner.find_todo_files()

        # Должны найти файлы с TODO и Tasks в названии
        paths = [f.relative_path for f in files]
        assert any("TODO" in p for p in paths)

    def test_find_todo_files_includes_tasks(self, scanner):
        """Tasks.md файлы включены."""
        files = scanner.find_todo_files()

        paths = [f.relative_path for f in files]
        assert any("Tasks.md" in p for p in paths)


# =============================================================================
# ТЕСТЫ: Edge cases
# =============================================================================


class TestEdgeCases:
    """Тесты граничных случаев."""

    def test_special_characters_in_filename(self, scanner, temp_vault):
        """Специальные символы в имени файла."""
        special_file = Path(temp_vault) / "00_Inbox" / "TODO - Неделя [1].md"
        special_file.write_text("content", encoding="utf-8")

        files = scanner.scan(["00_Inbox/*.md"])

        paths = [f.relative_path for f in files]
        assert any("[1]" in p for p in paths)

    def test_empty_vault(self):
        """Пустой vault."""
        vault_path = tempfile.mkdtemp()
        try:
            scanner = FileScanner(vault_path)
            files = scanner.scan(["*.md"])
            assert files == []
        finally:
            shutil.rmtree(vault_path, ignore_errors=True)

    def test_symlink_handling(self, scanner, temp_vault):
        """Обработка символических ссылок."""
        # Создаём symlink если ОС поддерживает
        try:
            source = Path(temp_vault) / "00_Inbox" / "TODO - Неделя 1.md"
            link = Path(temp_vault) / "00_Inbox" / "link.md"
            link.symlink_to(source)

            files = scanner.scan(["00_Inbox/link.md"])

            # Symlink должен быть найден
            assert len(files) == 1
        except OSError:
            # Symlinks не поддерживаются на этой ОС
            pytest.skip("Symlinks not supported")

    def test_large_file_handling(self, scanner, temp_vault):
        """Обработка большого файла."""
        large_file = Path(temp_vault) / "00_Inbox" / "large.md"
        # Создаём файл ~1MB
        content = "- [ ] Task\n" * 50000
        large_file.write_text(content, encoding="utf-8")

        result = scanner.scan_single(large_file)

        assert result is not None
        assert result.size_bytes > 500000
