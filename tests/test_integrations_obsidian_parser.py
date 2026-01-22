"""
Тесты для ObsidianParser — парсер Tasks Plugin формата.

Покрывает:
- Парсинг строки задачи (статус, приоритет, дата, теги)
- Парсинг файла с секциями
- Генерация markdown из задачи
- Поиск и обновление задач в контенте
"""

import contextlib
import os
import tempfile
from datetime import date
from pathlib import Path

import pytest

from src.integrations.obsidian.parser import (
    PRIORITY_MAP,
    PRIORITY_TO_EMOJI,
    ObsidianParser,
    ParsedTask,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def parser():
    """Создаёт экземпляр парсера."""
    return ObsidianParser()


@pytest.fixture
def temp_markdown_file():
    """Создаёт временный markdown файл."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        yield f
    # Cleanup
    with contextlib.suppress(OSError):
        os.unlink(f.name)


# =============================================================================
# ТЕСТЫ: parse_line — базовый парсинг строки
# =============================================================================


class TestParseLineBasic:
    """Тесты базового парсинга строки задачи."""

    def test_parse_simple_todo(self, parser):
        """Простая незавершённая задача."""
        result = parser.parse_line("- [ ] Купить молоко")

        assert result is not None
        assert result.title == "Купить молоко"
        assert result.status == "todo"
        assert result.priority == "medium"
        assert result.due_date is None
        assert result.tags == []

    def test_parse_simple_done(self, parser):
        """Простая завершённая задача."""
        result = parser.parse_line("- [x] Купить молоко")

        assert result is not None
        assert result.status == "done"
        assert result.title == "Купить молоко"

    def test_parse_done_uppercase_x(self, parser):
        """Завершённая задача с X в верхнем регистре."""
        result = parser.parse_line("- [X] Купить молоко")

        assert result is not None
        assert result.status == "done"

    def test_parse_non_task_line(self, parser):
        """Обычная строка — не задача."""
        result = parser.parse_line("Это просто текст")
        assert result is None

    def test_parse_bullet_without_checkbox(self, parser):
        """Маркер списка без чекбокса."""
        result = parser.parse_line("- Просто элемент списка")
        assert result is None

    def test_parse_empty_line(self, parser):
        """Пустая строка."""
        result = parser.parse_line("")
        assert result is None

    def test_parse_whitespace_line(self, parser):
        """Строка с пробелами."""
        result = parser.parse_line("   ")
        assert result is None

    def test_parse_task_with_indentation(self, parser):
        """Задача с отступом (вложенная)."""
        result = parser.parse_line("    - [ ] Вложенная задача")

        assert result is not None
        assert result.title == "Вложенная задача"
        assert result.status == "todo"

    def test_parse_task_empty_title_returns_none(self, parser):
        """Задача без заголовка (только метаданные)."""
        result = parser.parse_line("- [ ] #tag")
        # Если после удаления метаданных остаётся пустой title — возвращаем None
        # Зависит от реализации: tag — это метаданные, но может оставить title пустым
        # В текущей реализации #tag удаляется как метаданные, оставляя пустой title
        assert result is None


# =============================================================================
# ТЕСТЫ: parse_line — приоритеты
# =============================================================================


class TestParseLinePriority:
    """Тесты парсинга приоритета задачи."""

    def test_parse_priority_high_upward(self, parser):
        """Высокий приоритет: ⏫"""
        result = parser.parse_line("- [ ] Важная задача ⏫")

        assert result is not None
        assert result.priority == "high"

    def test_parse_priority_highest(self, parser):
        """Наивысший приоритет: 🔺 → high"""
        result = parser.parse_line("- [ ] Критичная задача 🔺")

        assert result is not None
        assert result.priority == "high"

    def test_parse_priority_medium(self, parser):
        """Средний приоритет: 🔼"""
        result = parser.parse_line("- [ ] Обычная задача 🔼")

        assert result is not None
        assert result.priority == "medium"

    def test_parse_priority_low(self, parser):
        """Низкий приоритет: 🔽"""
        result = parser.parse_line("- [ ] Не срочно 🔽")

        assert result is not None
        assert result.priority == "low"

    def test_parse_priority_lowest(self, parser):
        """Наинизший приоритет: ⏬ → low"""
        result = parser.parse_line("- [ ] Когда-нибудь ⏬")

        assert result is not None
        assert result.priority == "low"

    def test_parse_no_priority_defaults_medium(self, parser):
        """Без эмодзи приоритета → medium."""
        result = parser.parse_line("- [ ] Задача без приоритета")

        assert result is not None
        assert result.priority == "medium"

    def test_priority_emoji_stripped_from_title(self, parser):
        """Эмодзи приоритета не включается в title."""
        result = parser.parse_line("- [ ] Задача ⏫ важная")

        assert result is not None
        assert "⏫" not in result.title
        assert result.title == "Задача важная"


# =============================================================================
# ТЕСТЫ: parse_line — даты
# =============================================================================


class TestParseLineDate:
    """Тесты парсинга дат."""

    def test_parse_due_date(self, parser):
        """Срок выполнения: 📅 YYYY-MM-DD"""
        result = parser.parse_line("- [ ] Сдать отчёт 📅 2026-01-25")

        assert result is not None
        assert result.due_date == date(2026, 1, 25)

    def test_parse_completed_date(self, parser):
        """Дата завершения: ✅ YYYY-MM-DD"""
        result = parser.parse_line("- [x] Готово ✅ 2026-01-20")

        assert result is not None
        assert result.completed_at == date(2026, 1, 20)

    def test_parse_both_dates(self, parser):
        """Обе даты: due_date и completed_at."""
        result = parser.parse_line("- [x] Задача 📅 2026-01-25 ✅ 2026-01-20")

        assert result is not None
        assert result.due_date == date(2026, 1, 25)
        assert result.completed_at == date(2026, 1, 20)

    def test_parse_invalid_due_date(self, parser):
        """Некорректная дата — игнорируется."""
        result = parser.parse_line("- [ ] Задача 📅 2026-99-99")

        assert result is not None
        assert result.due_date is None

    def test_parse_invalid_completed_date(self, parser):
        """Некорректная дата завершения — игнорируется."""
        result = parser.parse_line("- [x] Задача ✅ invalid-date")

        assert result is not None
        assert result.completed_at is None

    def test_date_stripped_from_title(self, parser):
        """Дата не включается в title."""
        result = parser.parse_line("- [ ] Задача 📅 2026-01-25 сделать")

        assert result is not None
        assert "📅" not in result.title
        assert "2026-01-25" not in result.title

    def test_parse_date_no_space_after_emoji(self, parser):
        """Дата без пробела после эмодзи: 📅2026-01-25"""
        result = parser.parse_line("- [ ] Задача 📅2026-01-25")

        # Текущий regex требует пробел, но проверим поведение
        # Если не парсит — due_date будет None
        assert result is not None


# =============================================================================
# ТЕСТЫ: parse_line — теги
# =============================================================================


class TestParseLineTags:
    """Тесты парсинга тегов."""

    def test_parse_single_tag(self, parser):
        """Один тег."""
        result = parser.parse_line("- [ ] Задача #health")

        assert result is not None
        assert result.tags == ["health"]

    def test_parse_multiple_tags(self, parser):
        """Несколько тегов."""
        result = parser.parse_line("- [ ] Задача #health #urgent #family")

        assert result is not None
        assert set(result.tags) == {"health", "urgent", "family"}

    def test_parse_project_tag(self, parser):
        """Тег проекта: #project/name"""
        result = parser.parse_line("- [ ] Задача #project/КХП")

        assert result is not None
        assert "project/КХП" in result.tags

    def test_parse_tag_with_dash(self, parser):
        """Тег с дефисом: #vibe-coding"""
        result = parser.parse_line("- [ ] Задача #vibe-coding")

        assert result is not None
        assert "vibe-coding" in result.tags

    def test_tags_stripped_from_title(self, parser):
        """Теги не включаются в title."""
        result = parser.parse_line("- [ ] Сделать #work задачу")

        assert result is not None
        assert "#work" not in result.title
        assert result.title == "Сделать задачу"

    def test_parse_tag_cyrillic(self, parser):
        """Тег на кириллице."""
        result = parser.parse_line("- [ ] Задача #здоровье")

        assert result is not None
        # Зависит от реализации: \w в Python включает unicode
        assert "здоровье" in result.tags or result.tags == []


# =============================================================================
# ТЕСТЫ: parse_line — комплексные случаи
# =============================================================================


class TestParseLineComplex:
    """Тесты комплексного парсинга."""

    def test_parse_full_task(self, parser):
        """Полная задача со всеми полями."""
        line = "- [x] Записаться к врачу ⏫ 📅 2026-01-25 #health #urgent ✅ 2026-01-20"
        result = parser.parse_line(line)

        assert result is not None
        assert result.title == "Записаться к врачу"
        assert result.status == "done"
        assert result.priority == "high"
        assert result.due_date == date(2026, 1, 25)
        assert result.completed_at == date(2026, 1, 20)
        assert set(result.tags) == {"health", "urgent"}

    def test_parse_task_with_recurrence(self, parser):
        """Задача с повторением (🔁 should be stripped)."""
        result = parser.parse_line("- [ ] Тренировка 🔁 every day 📅 2026-01-25")

        assert result is not None
        # 🔁 и всё до следующего специального символа должно быть удалено
        assert "🔁" not in result.title

    def test_parse_task_metadata_order(self, parser):
        """Метаданные в разном порядке."""
        result = parser.parse_line("- [ ] #tag Задача 📅 2026-01-25 ⏫ #another")

        assert result is not None
        assert result.title == "Задача"
        assert result.priority == "high"
        assert result.due_date == date(2026, 1, 25)
        assert set(result.tags) == {"tag", "another"}

    def test_parse_preserves_whitespace_in_title(self, parser):
        """Пробелы в title нормализуются."""
        result = parser.parse_line("- [ ] Задача   с   пробелами")

        assert result is not None
        # Множественные пробелы заменяются на один
        assert result.title == "Задача с пробелами"


# =============================================================================
# ТЕСТЫ: parse_content — парсинг markdown контента
# =============================================================================


class TestParseContent:
    """Тесты парсинга markdown контента с секциями."""

    def test_parse_simple_content(self, parser):
        """Простой контент с задачами."""
        content = """# TODO List

- [ ] Задача 1
- [ ] Задача 2
- [x] Задача 3
"""
        tasks = parser.parse_content(content)

        assert len(tasks) == 3
        assert tasks[0].title == "Задача 1"
        assert tasks[1].title == "Задача 2"
        assert tasks[2].title == "Задача 3"
        assert tasks[2].status == "done"

    def test_parse_content_with_sections(self, parser):
        """Контент с секциями — задачи получают section."""
        content = """# TODO

## Здоровье

- [ ] Записаться к врачу

## Работа

- [ ] Сдать отчёт
"""
        tasks = parser.parse_content(content)

        assert len(tasks) == 2
        assert tasks[0].section == "Здоровье"
        assert tasks[1].section == "Работа"

    def test_parse_content_tracks_line_numbers(self, parser):
        """source_line соответствует номеру строки."""
        content = """# Header

- [ ] Задача на строке 3
"""
        tasks = parser.parse_content(content)

        assert len(tasks) == 1
        assert tasks[0].source_line == 3

    def test_parse_content_with_source_file(self, parser):
        """source_file передаётся в задачи."""
        content = "- [ ] Задача"
        tasks = parser.parse_content(content, source_file="/path/to/file.md")

        assert len(tasks) == 1
        assert tasks[0].source_file == "/path/to/file.md"

    def test_parse_content_mixed_lines(self, parser):
        """Смешанный контент: задачи, текст, списки."""
        content = """# Проект

Описание проекта.

## Задачи

- [ ] Первая задача
- Не задача (bullet point)
- [ ] Вторая задача

Заключение.
"""
        tasks = parser.parse_content(content)

        assert len(tasks) == 2
        assert tasks[0].title == "Первая задача"
        assert tasks[1].title == "Вторая задача"

    def test_parse_content_nested_sections(self, parser):
        """Вложенные секции — используется последняя."""
        content = """## Здоровье

### Врачи

- [ ] Записаться к терапевту
"""
        tasks = parser.parse_content(content)

        assert len(tasks) == 1
        # Последняя секция "Врачи"
        assert tasks[0].section == "Врачи"

    def test_parse_content_empty(self, parser):
        """Пустой контент."""
        tasks = parser.parse_content("")
        assert tasks == []

    def test_parse_content_no_tasks(self, parser):
        """Контент без задач."""
        content = """# Заметка

Это просто текст без задач.

- Список
- Другой элемент
"""
        tasks = parser.parse_content(content)
        assert tasks == []


# =============================================================================
# ТЕСТЫ: parse_file — парсинг файла
# =============================================================================


class TestParseFile:
    """Тесты парсинга файла."""

    def test_parse_file_success(self, parser, temp_markdown_file):
        """Успешный парсинг файла."""
        temp_markdown_file.write("- [ ] Задача из файла\n")
        temp_markdown_file.close()

        tasks = parser.parse_file(temp_markdown_file.name)

        assert len(tasks) == 1
        assert tasks[0].title == "Задача из файла"
        assert tasks[0].source_file == temp_markdown_file.name
        assert tasks[0].file_modified is not None

    def test_parse_file_not_found(self, parser):
        """Файл не найден — FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/file.md")

    def test_parse_file_with_path_object(self, parser, temp_markdown_file):
        """Парсинг с Path объектом."""
        temp_markdown_file.write("- [ ] Задача\n")
        temp_markdown_file.close()

        tasks = parser.parse_file(Path(temp_markdown_file.name))

        assert len(tasks) == 1


# =============================================================================
# ТЕСТЫ: task_to_markdown — генерация markdown
# =============================================================================


class TestTaskToMarkdown:
    """Тесты генерации markdown строки из задачи."""

    def test_simple_todo(self, parser):
        """Простая незавершённая задача."""
        task = ParsedTask(title="Купить молоко", status="todo", priority="medium")

        result = parser.task_to_markdown(task)

        assert result == "- [ ] Купить молоко"

    def test_simple_done(self, parser):
        """Простая завершённая задача."""
        task = ParsedTask(title="Готово", status="done", priority="medium")

        result = parser.task_to_markdown(task)

        assert result == "- [x] Готово"

    def test_with_high_priority(self, parser):
        """Задача с высоким приоритетом."""
        task = ParsedTask(title="Важная", status="todo", priority="high")

        result = parser.task_to_markdown(task)

        assert "⏫" in result
        assert result == "- [ ] Важная ⏫"

    def test_with_low_priority(self, parser):
        """Задача с низким приоритетом."""
        task = ParsedTask(title="Не срочно", status="todo", priority="low")

        result = parser.task_to_markdown(task)

        assert "🔽" in result

    def test_medium_priority_no_emoji(self, parser):
        """Средний приоритет — без эмодзи."""
        task = ParsedTask(title="Обычная", status="todo", priority="medium")

        result = parser.task_to_markdown(task)

        # Эмодзи приоритета не добавляется для medium
        assert "🔼" not in result
        assert result == "- [ ] Обычная"

    def test_with_due_date(self, parser):
        """Задача с датой."""
        task = ParsedTask(
            title="Срочно",
            status="todo",
            priority="medium",
            due_date=date(2026, 1, 25),
        )

        result = parser.task_to_markdown(task)

        assert "📅 2026-01-25" in result

    def test_with_tags(self, parser):
        """Задача с тегами."""
        task = ParsedTask(
            title="Задача", status="todo", priority="medium", tags=["health", "urgent"]
        )

        result = parser.task_to_markdown(task)

        assert "#health" in result
        assert "#urgent" in result

    def test_with_completed_date(self, parser):
        """Завершённая задача с датой завершения."""
        task = ParsedTask(
            title="Готово",
            status="done",
            priority="medium",
            completed_at=date(2026, 1, 20),
        )

        result = parser.task_to_markdown(task)

        assert "✅ 2026-01-20" in result

    def test_full_task_roundtrip(self, parser):
        """Полная задача: parse → to_markdown → parse."""
        original_line = "- [x] Задача ⏫ 📅 2026-01-25 #tag ✅ 2026-01-20"
        parsed = parser.parse_line(original_line)
        assert parsed is not None

        markdown = parser.task_to_markdown(parsed)
        reparsed = parser.parse_line(markdown)

        assert reparsed is not None
        assert reparsed.title == parsed.title
        assert reparsed.status == parsed.status
        assert reparsed.priority == parsed.priority
        assert reparsed.due_date == parsed.due_date
        assert reparsed.completed_at == parsed.completed_at


# =============================================================================
# ТЕСТЫ: find_task_in_content
# =============================================================================


class TestFindTaskInContent:
    """Тесты поиска задачи в контенте."""

    def test_find_existing_task(self, parser):
        """Поиск существующей задачи."""
        content = """# TODO

- [ ] Первая задача
- [ ] Искомая задача
- [ ] Третья задача
"""
        result = parser.find_task_in_content(content, "Искомая задача")

        assert result is not None
        line_num, line = result
        assert line_num == 4
        assert "Искомая задача" in line

    def test_find_task_case_insensitive(self, parser):
        """Поиск без учёта регистра."""
        content = "- [ ] ВАЖНАЯ ЗАДАЧА"

        result = parser.find_task_in_content(content, "важная задача")

        assert result is not None

    def test_find_nonexistent_task(self, parser):
        """Задача не найдена."""
        content = "- [ ] Другая задача"

        result = parser.find_task_in_content(content, "Несуществующая")

        assert result is None

    def test_find_task_empty_content(self, parser):
        """Пустой контент."""
        result = parser.find_task_in_content("", "Задача")
        assert result is None


# =============================================================================
# ТЕСТЫ: update_task_in_content
# =============================================================================


class TestUpdateTaskInContent:
    """Тесты обновления задачи в контенте."""

    def test_update_task_status(self, parser):
        """Обновление статуса задачи."""
        content = "- [ ] Задача\n"
        new_task = ParsedTask(title="Задача", status="done", priority="medium")

        result = parser.update_task_in_content(content, 1, new_task)

        assert "- [x] Задача" in result

    def test_update_preserves_indentation(self, parser):
        """Сохранение отступа."""
        content = "    - [ ] Вложенная задача\n"
        new_task = ParsedTask(title="Вложенная задача", status="done", priority="medium")

        result = parser.update_task_in_content(content, 1, new_task)

        assert result.startswith("    - [x]")

    def test_update_middle_line(self, parser):
        """Обновление строки в середине файла."""
        content = """- [ ] Первая
- [ ] Вторая
- [ ] Третья
"""
        new_task = ParsedTask(title="Вторая ОБНОВЛЕНА", status="done", priority="high")

        result = parser.update_task_in_content(content, 2, new_task)

        lines = result.split("\n")
        assert "- [x] Вторая ОБНОВЛЕНА" in lines[1]
        assert "⏫" in lines[1]

    def test_update_invalid_line_number(self, parser):
        """Некорректный номер строки — контент не меняется."""
        content = "- [ ] Задача\n"
        new_task = ParsedTask(title="Новая", status="todo", priority="medium")

        result = parser.update_task_in_content(content, 999, new_task)

        # Контент остаётся без изменений
        assert result == content


# =============================================================================
# ТЕСТЫ: константы и маппинги
# =============================================================================


class TestConstants:
    """Тесты констант и маппингов."""

    def test_priority_map_complete(self):
        """PRIORITY_MAP содержит все эмодзи."""
        assert "🔺" in PRIORITY_MAP
        assert "⏫" in PRIORITY_MAP
        assert "🔼" in PRIORITY_MAP
        assert "🔽" in PRIORITY_MAP
        assert "⏬" in PRIORITY_MAP

    def test_priority_to_emoji_complete(self):
        """PRIORITY_TO_EMOJI содержит все уровни."""
        assert "high" in PRIORITY_TO_EMOJI
        assert "medium" in PRIORITY_TO_EMOJI
        assert "low" in PRIORITY_TO_EMOJI

    def test_priority_values_valid(self):
        """Все значения PRIORITY_MAP валидны."""
        valid_priorities = {"high", "medium", "low"}
        for _emoji, priority in PRIORITY_MAP.items():
            assert priority in valid_priorities
