"""Tag repository with specific queries."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Tag
from .base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """
    Репозиторий для работы с тегами.

    Теги интегрируются с Obsidian Second Brain,
    поэтому здесь методы для синхронизации и поиска.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Tag, db)

    async def get_by_name(self, name: str) -> Tag | None:
        """
        Получить тег по имени.

        Args:
            name: Имя тега (например, "urgent", "backend")

        Returns:
            Тег или None

        SQL эквивалент:
            SELECT * FROM tags WHERE name = {name};

        Пример:
            urgent_tag = await repo.get_by_name("urgent")
        """
        result = await self.db.execute(select(Tag).where(Tag.name == name))
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str) -> Tag:
        """
        Получить тег по имени или создать, если не существует.

        Args:
            name: Имя тега

        Returns:
            Существующий или новый тег

        Паттерн "get or create" очень полезен для тегов,
        так как мы не хотим создавать дубликаты.

        Пример:
            # Если тег "urgent" существует - вернёт его
            # Если не существует - создаст и вернёт
            tag = await repo.get_or_create("urgent")
        """
        # Пытаемся найти
        tag = await self.get_by_name(name)

        # Если не нашли - создаём
        if not tag:
            tag = Tag(name=name)
            tag = await self.create(tag)

        return tag

    async def get_popular_tags(self, limit: int = 10) -> list[tuple[Tag, int]]:
        """
        Получить самые популярные теги (по количеству использований).

        Args:
            limit: Сколько тегов вернуть

        Returns:
            Список кортежей (тег, количество_использований)

        SQL эквивалент:
            SELECT tags.*, COUNT(task_tags.task_id) as usage_count
            FROM tags
            LEFT JOIN task_tags ON tags.id = task_tags.tag_id
            GROUP BY tags.id
            ORDER BY usage_count DESC
            LIMIT {limit};

        Пример использования:
            popular = await repo.get_popular_tags(5)
            for tag, count in popular:
                print(f"{tag.name}: {count} задач")

        Вывод:
            urgent: 15 задач
            backend: 12 задач
            frontend: 8 задач
        """
        from ..models import task_tags

        result = await self.db.execute(
            select(Tag, func.count(task_tags.c.task_id).label("usage_count"))
            .outerjoin(task_tags, Tag.id == task_tags.c.tag_id)
            .group_by(Tag.id)
            .order_by(func.count(task_tags.c.task_id).desc())
            .limit(limit)
        )

        # result возвращает кортежи (Tag, count)
        return [(row[0], row[1]) for row in result.all()]

    async def get_unused_tags(self) -> list[Tag]:
        """
        Получить неиспользуемые теги (не привязаны ни к одной задаче).

        Returns:
            Список неиспользуемых тегов

        Полезно для очистки БД от устаревших тегов.

        SQL эквивалент:
            SELECT tags.*
            FROM tags
            LEFT JOIN task_tags ON tags.id = task_tags.tag_id
            WHERE task_tags.tag_id IS NULL;
        """
        from ..models import task_tags

        result = await self.db.execute(
            select(Tag)
            .outerjoin(task_tags, Tag.id == task_tags.c.tag_id)
            .where(task_tags.c.tag_id.is_(None))
        )
        return list(result.scalars().all())

    async def search_tags(self, search_term: str) -> list[Tag]:
        """
        Поиск тегов по имени.

        Args:
            search_term: Поисковый запрос

        Returns:
            Список найденных тегов

        SQL эквивалент:
            SELECT * FROM tags
            WHERE LOWER(name) LIKE LOWER('%{search_term}%');
        """
        result = await self.db.execute(select(Tag).where(Tag.name.ilike(f"%{search_term}%")))
        return list(result.scalars().all())

    async def bulk_get_or_create(self, tag_names: list[str]) -> list[Tag]:
        """
        Массовое получение/создание тегов.

        Args:
            tag_names: Список имён тегов

        Returns:
            Список тегов (существующих или новых)

        Оптимизированный метод для работы со множеством тегов
        (например, при импорте из Obsidian).

        Пример:
            # Вместо 5 запросов к БД - делаем 2
            tags = await repo.bulk_get_or_create(
                ["urgent", "backend", "api", "database", "testing"]
            )
        """
        # Получаем все существующие теги за один запрос
        result = await self.db.execute(select(Tag).where(Tag.name.in_(tag_names)))
        existing_tags = list(result.scalars().all())
        existing_names = {tag.name for tag in existing_tags}

        # Определяем, какие теги нужно создать
        new_tag_names = set(tag_names) - existing_names

        # Создаём новые теги
        new_tags = []
        for name in new_tag_names:
            tag = Tag(name=name)
            self.db.add(tag)
            new_tags.append(tag)

        if new_tags:
            await self.db.flush()
            for tag in new_tags:
                await self.db.refresh(tag)

        # Возвращаем все теги
        return existing_tags + new_tags
