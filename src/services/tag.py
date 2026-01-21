"""Tag service with business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Tag
from ..repositories import TagRepository, TaskRepository


class TagService:
    """
    Сервис для работы с тегами.

    Особенность: интеграция с Obsidian Second Brain.
    Теги синхронизируются с тегами из Obsidian.
    """

    def __init__(self, db: AsyncSession):
        """Инициализация сервиса."""
        self.db = db
        self.tag_repo = TagRepository(db)
        self.task_repo = TaskRepository(db)

    async def create_tag(self, name: str) -> Tag:
        """
        Создать новый тег.

        Args:
            name: Название тега

        Returns:
            Созданный тег

        Raises:
            ValueError: Если валидация не прошла

        Бизнес-правила:
        1. Название обязательно
        2. Название уникально
        3. Название в нижнем регистре (lowercase)
        4. Без пробелов (заменяются на дефисы)
        """
        # 1. ВАЛИДАЦИЯ: Название не пустое
        if not name or not name.strip():
            raise ValueError("Tag name cannot be empty")

        # 2. НОРМАЛИЗАЦИЯ: Приводим к формату Obsidian
        normalized_name = self._normalize_tag_name(name)

        # 3. ВАЛИДАЦИЯ: Проверка уникальности
        existing = await self.tag_repo.get_by_name(normalized_name)
        if existing:
            raise ValueError(f"Tag '{normalized_name}' already exists")

        # 4. СОЗДАНИЕ: Создать тег
        tag = Tag(name=normalized_name)
        tag = await self.tag_repo.create(tag)

        await self.db.flush()
        return tag

    async def get_or_create_tag(self, name: str) -> Tag:
        """
        Получить тег или создать, если не существует.

        Args:
            name: Название тега

        Returns:
            Существующий или новый тег

        Это основной метод для работы с тегами!
        Используется при импорте из Obsidian и создании задач.
        """
        if not name or not name.strip():
            raise ValueError("Tag name cannot be empty")

        # Нормализуем название
        normalized_name = self._normalize_tag_name(name)

        # Используем repository метод get_or_create
        tag = await self.tag_repo.get_or_create(normalized_name)
        await self.db.flush()

        return tag

    async def get_tag(self, tag_id: int) -> Tag:
        """
        Получить тег по ID.

        Args:
            tag_id: ID тега

        Returns:
            Тег

        Raises:
            ValueError: Если тег не найден
        """
        tag = await self.tag_repo.get_by_id(tag_id)
        if not tag:
            raise ValueError(f"Tag with id {tag_id} not found")
        return tag

    async def get_tag_by_name(self, name: str) -> Tag | None:
        """
        Получить тег по названию.

        Args:
            name: Название тега

        Returns:
            Тег или None
        """
        normalized_name = self._normalize_tag_name(name)
        return await self.tag_repo.get_by_name(normalized_name)

    async def get_all_tags(self) -> list[Tag]:
        """
        Получить все теги.

        Returns:
            Список всех тегов
        """
        return await self.tag_repo.get_all()

    async def get_popular_tags(self, limit: int = 10) -> list[tuple[Tag, int]]:
        """
        Получить самые популярные теги.

        Args:
            limit: Количество тегов

        Returns:
            Список кортежей (тег, количество_использований)

        Пример:
            [(Tag('python'), 15), (Tag('backend'), 10), ...]

        Бизнес-логика для отображения "облака тегов" в UI.
        """
        return await self.tag_repo.get_popular_tags(limit)

    async def get_unused_tags(self) -> list[Tag]:
        """
        Получить неиспользуемые теги.

        Returns:
            Список тегов без задач

        Бизнес-логика для очистки устаревших тегов.
        """
        return await self.tag_repo.get_unused_tags()

    async def rename_tag(self, tag_id: int, new_name: str) -> Tag:
        """
        Переименовать тег.

        Args:
            tag_id: ID тега
            new_name: Новое название

        Returns:
            Обновлённый тег

        Raises:
            ValueError: Если валидация не прошла

        Бизнес-правило:
        - Переименование влияет на ВСЕ задачи с этим тегом
        - Новое название должно быть уникальным
        """
        # 1. ВАЛИДАЦИЯ: Тег существует
        tag = await self.get_tag(tag_id)

        # 2. ВАЛИДАЦИЯ: Новое название не пустое
        if not new_name or not new_name.strip():
            raise ValueError("Tag name cannot be empty")

        # 3. НОРМАЛИЗАЦИЯ
        normalized_name = self._normalize_tag_name(new_name)

        # 4. ВАЛИДАЦИЯ: Новое название уникально
        if normalized_name != tag.name:
            existing = await self.tag_repo.get_by_name(normalized_name)
            if existing:
                raise ValueError(f"Tag '{normalized_name}' already exists")

            # 5. ОБНОВЛЕНИЕ
            tag = await self.tag_repo.update(tag_id, name=normalized_name)
            await self.db.flush()

        return tag

    async def merge_tags(self, source_tag_id: int, target_tag_id: int) -> Tag:
        """
        Объединить два тега в один.

        Args:
            source_tag_id: ID исходного тега (будет удалён)
            target_tag_id: ID целевого тега (останется)

        Returns:
            Целевой тег

        Raises:
            ValueError: Если теги не найдены или одинаковые

        Бизнес-логика:
        1. Все задачи с source_tag получают target_tag
        2. source_tag удаляется
        3. Дубликаты тегов у задач не создаются

        Пример:
            merge_tags(tag_id=1 "python3", tag_id=2 "python")
            → Все задачи с "python3" получат "python"
            → Тег "python3" удалится
        """
        # 1. ВАЛИДАЦИЯ: Теги существуют
        if source_tag_id == target_tag_id:
            raise ValueError("Cannot merge tag with itself")

        source_tag = await self.get_tag(source_tag_id)
        target_tag = await self.get_tag(target_tag_id)

        # 2. КООРДИНАЦИЯ: Получить все задачи с исходным тегом
        tasks_with_source = await self.task_repo.get_tasks_by_tag(source_tag_id)

        # 3. КООРДИНАЦИЯ: Переназначить тег на всех задачах
        for task in tasks_with_source:
            # Убираем старый тег
            await self.task_repo.remove_tag(task.id, source_tag)
            # Добавляем новый тег (если ещё нет)
            await self.task_repo.add_tag(task.id, target_tag)

        # 4. УДАЛЕНИЕ: Удалить исходный тег
        await self.tag_repo.delete(source_tag_id)

        await self.db.flush()

        return target_tag

    async def delete_tag(self, tag_id: int, force: bool = False) -> bool:
        """
        Удалить тег.

        Args:
            tag_id: ID тега
            force: Принудительное удаление (даже если есть задачи)

        Returns:
            True если удалён

        Raises:
            ValueError: Если тег используется и force=False

        Бизнес-правило:
        - Нельзя удалить тег, который используется в задачах
        - force=True удаляет связи с задачами автоматически
        """
        # 1. ВАЛИДАЦИЯ: Тег существует
        tag = await self.get_tag(tag_id)

        # 2. ВАЛИДАЦИЯ: Проверить использование
        tasks_with_tag = await self.task_repo.get_tasks_by_tag(tag_id)

        if tasks_with_tag and not force:
            raise ValueError(
                f"Cannot delete tag '{tag.name}' used in {len(tasks_with_tag)} tasks. "
                "Use force=True to delete anyway."
            )

        # 3. УДАЛЕНИЕ: Cascade удалит связи в task_tags
        deleted = await self.tag_repo.delete(tag_id)
        await self.db.flush()

        return deleted

    async def cleanup_unused_tags(self) -> int:
        """
        Удалить все неиспользуемые теги.

        Returns:
            Количество удалённых тегов

        Бизнес-логика для очистки БД от устаревших тегов.
        """
        unused_tags = await self.get_unused_tags()

        count = 0
        for tag in unused_tags:
            await self.tag_repo.delete(tag.id)
            count += 1

        await self.db.flush()

        return count

    async def search_tags(self, query: str) -> list[Tag]:
        """
        Поиск тегов по названию.

        Args:
            query: Поисковый запрос

        Returns:
            Список найденных тегов
        """
        if not query or not query.strip():
            return []

        return await self.tag_repo.search_tags(query.strip())

    async def get_tag_statistics(self, tag_id: int) -> dict:
        """
        Получить статистику по тегу.

        Args:
            tag_id: ID тега

        Returns:
            Словарь со статистикой

        Пример:
            {
                "tag_name": "python",
                "total_tasks": 15,
                "completed_tasks": 10,
                "in_progress_tasks": 3,
                "todo_tasks": 2
            }

        Бизнес-логика для отображения информации о теге.
        """
        from ..models import TaskStatus

        # Получаем тег
        tag = await self.get_tag(tag_id)

        # Получаем все задачи с этим тегом
        tasks = await self.task_repo.get_tasks_by_tag(tag_id)

        # Подсчитываем статистику
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
        todo = sum(1 for t in tasks if t.status == TaskStatus.TODO)

        return {
            "tag_id": tag_id,
            "tag_name": tag.name,
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress_tasks": in_progress,
            "todo_tasks": todo,
        }

    # Вспомогательные методы (private)

    def _normalize_tag_name(self, name: str) -> str:
        """
        Нормализовать название тега для соответствия формату Obsidian.

        Args:
            name: Исходное название

        Returns:
            Нормализованное название

        Правила:
        - Lowercase (нижний регистр)
        - Пробелы → дефисы
        - Множественные дефисы → один дефис
        - Убрать спецсимволы (кроме дефиса и подчёркивания)

        Примеры:
            "Python Programming" → "python-programming"
            "Web  Dev" → "web-dev"
            "C++" → "c"
            "Test_Tag" → "test_tag"
        """
        import re

        # 1. Lowercase
        normalized = name.lower()

        # 2. Пробелы → дефисы
        normalized = normalized.replace(" ", "-")

        # 3. Оставляем только буквы, цифры, дефисы, подчёркивания
        normalized = re.sub(r"[^a-z0-9\-_]", "", normalized)

        # 4. Множественные дефисы → один дефис
        normalized = re.sub(r"-+", "-", normalized)

        # 5. Убрать дефисы с краёв
        normalized = normalized.strip("-")

        return normalized
