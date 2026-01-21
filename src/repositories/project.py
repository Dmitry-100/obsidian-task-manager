"""Project repository with specific queries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Project
from .base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """
    Репозиторий для работы с проектами.

    Наследуется от BaseRepository, получая все CRUD операции,
    и добавляет специфичные методы для проектов.
    """

    def __init__(self, db: AsyncSession):
        """
        Инициализация репозитория проектов.

        Args:
            db: Асинхронная сессия базы данных

        Обратите внимание: передаём модель Project автоматически,
        чтобы не писать ProjectRepository(Project, db) каждый раз.
        """
        super().__init__(Project, db)

    async def get_by_id_with_tasks(self, id: int) -> Project | None:
        """
        Получить проект с загруженными задачами (eager loading).

        Args:
            id: ID проекта

        Returns:
            Проект с задачами или None

        Пример:
            project = await repo.get_by_id_with_tasks(1)
            for task in project.tasks:  # БД не трогаем, данные уже загружены
                print(task.title)

        SQL эквивалент:
            SELECT projects.*, tasks.*
            FROM projects
            LEFT JOIN tasks ON tasks.project_id = projects.id
            WHERE projects.id = {id};
        """
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.tasks))  # загружаем tasks сразу
            .where(Project.id == id)
        )
        return result.scalar_one_or_none()

    async def get_active_projects(self, skip: int = 0, limit: int = 20) -> list[Project]:
        """
        Получить активные (не архивированные) проекты с пагинацией.

        Args:
            skip: Количество записей для пропуска (offset)
            limit: Максимальное количество записей

        Returns:
            Список активных проектов

        SQL эквивалент:
            SELECT * FROM projects
            WHERE is_archived = false
            OFFSET {skip} LIMIT {limit};
        """
        result = await self.db.execute(
            select(Project).where(Project.is_archived == False).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_archived_projects(self) -> list[Project]:
        """
        Получить все архивированные проекты.

        Returns:
            Список архивированных проектов
        """
        result = await self.db.execute(select(Project).where(Project.is_archived == True))
        return list(result.scalars().all())

    async def archive_project(self, id: int) -> Project | None:
        """
        Архивировать проект (soft delete).

        Args:
            id: ID проекта

        Returns:
            Архивированный проект или None

        Это "мягкое удаление" - запись остаётся в БД,
        но помечается как архивная.
        """
        return await self.update(id, is_archived=True)

    async def unarchive_project(self, id: int) -> Project | None:
        """
        Разархивировать проект.

        Args:
            id: ID проекта

        Returns:
            Восстановленный проект или None
        """
        return await self.update(id, is_archived=False)

    async def get_by_obsidian_folder(self, folder_path: str) -> Project | None:
        """
        Найти проект по пути к папке Obsidian.

        Args:
            folder_path: Путь к папке в Obsidian

        Returns:
            Проект или None

        Пример:
            project = await repo.get_by_obsidian_folder(
                "01_Projects/Вайб-Кодинг"
            )
        """
        result = await self.db.execute(
            select(Project).where(Project.obsidian_folder == folder_path)
        )
        return result.scalar_one_or_none()

    async def search_by_name(self, search_term: str) -> list[Project]:
        """
        Поиск проектов по имени (регистронезависимый, частичное совпадение).

        Args:
            search_term: Поисковый запрос

        Returns:
            Список найденных проектов

        SQL эквивалент:
            SELECT * FROM projects
            WHERE LOWER(name) LIKE LOWER('%{search_term}%');

        Пример:
            # Найдёт "Вайб-Кодинг", "вайб кодинг week1", etc.
            projects = await repo.search_by_name("вайб")
        """
        result = await self.db.execute(
            select(Project).where(
                Project.name.ilike(f"%{search_term}%")  # ilike = case-insensitive LIKE
            )
        )
        return list(result.scalars().all())
