"""Task repository with specific queries."""

from datetime import UTC, date, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Tag, Task, TaskPriority, TaskStatus
from .base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """
    Репозиторий для работы с задачами.

    Включает методы для:
    - Работы с подзадачами (иерархия)
    - Фильтрации по статусу/приоритету
    - Работы с тегами
    - Поиска и группировки
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Task, db)

    async def get_by_id_full(self, id: int) -> Task | None:
        """
        Получить задачу со ВСЕМИ связанными данными (eager loading).

        Загружает:
        - Проект (project)
        - Подзадачи (subtasks)
        - Родительскую задачу (parent_task)
        - Теги (tags)
        - Комментарии (comments)

        Args:
            id: ID задачи

        Returns:
            Задача со всеми связями или None

        Использование:
            task = await repo.get_by_id_full(1)
            print(task.project.name)  # без дополнительного запроса
            print(task.tags)  # без дополнительного запроса
            for subtask in task.subtasks:  # без дополнительного запроса
                print(subtask.title)
        """
        result = await self.db.execute(
            select(Task)
            .options(
                selectinload(Task.project),
                selectinload(Task.subtasks),
                selectinload(Task.parent_task),
                selectinload(Task.tags),
                selectinload(Task.comments),
            )
            .where(Task.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_project(self, project_id: int, include_completed: bool = True) -> list[Task]:
        """
        Получить все задачи проекта.

        Args:
            project_id: ID проекта
            include_completed: Включать ли завершённые задачи

        Returns:
            Список задач проекта

        SQL эквивалент (без завершённых):
            SELECT * FROM tasks
            WHERE project_id = {project_id}
            AND status != 'done' AND status != 'cancelled';
        """
        query = select(Task).where(Task.project_id == project_id)

        if not include_completed:
            # Исключаем завершённые и отменённые
            query = query.where(
                and_(Task.status != TaskStatus.DONE, Task.status != TaskStatus.CANCELLED)
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_status(self, status: TaskStatus) -> list[Task]:
        """
        Получить все задачи с определённым статусом.

        Args:
            status: Статус задачи (TODO, IN_PROGRESS, DONE, CANCELLED)

        Returns:
            Список задач

        Пример:
            in_progress_tasks = await repo.get_by_status(TaskStatus.IN_PROGRESS)
        """
        result = await self.db.execute(select(Task).where(Task.status == status))
        return list(result.scalars().all())

    async def get_by_priority(self, priority: TaskPriority) -> list[Task]:
        """
        Получить все задачи с определённым приоритетом.

        Args:
            priority: Приоритет (LOW, MEDIUM, HIGH)

        Returns:
            Список задач
        """
        result = await self.db.execute(select(Task).where(Task.priority == priority))
        return list(result.scalars().all())

    async def get_subtasks(self, parent_task_id: int) -> list[Task]:
        """
        Получить все подзадачи для задачи.

        Args:
            parent_task_id: ID родительской задачи

        Returns:
            Список подзадач

        SQL эквивалент:
            SELECT * FROM tasks WHERE parent_task_id = {parent_task_id};

        Пример иерархии:
            Задача #1: "Создать API"
              ├─ Задача #2: "Создать модели" (parent_task_id=1)
              ├─ Задача #3: "Создать endpoints" (parent_task_id=1)
              └─ Задача #4: "Написать тесты" (parent_task_id=1)
        """
        result = await self.db.execute(select(Task).where(Task.parent_task_id == parent_task_id))
        return list(result.scalars().all())

    async def get_root_tasks(self, project_id: int) -> list[Task]:
        """
        Получить задачи верхнего уровня (без родителя) для проекта.

        Args:
            project_id: ID проекта

        Returns:
            Список корневых задач

        SQL эквивалент:
            SELECT * FROM tasks
            WHERE project_id = {project_id}
            AND parent_task_id IS NULL;

        Использование для отображения дерева задач:
            roots = await repo.get_root_tasks(1)
            for root in roots:
                print(root.title)
                for subtask in root.subtasks:  # relationship
                    print(f"  - {subtask.title}")
        """
        result = await self.db.execute(
            select(Task).where(
                and_(
                    Task.project_id == project_id,
                    Task.parent_task_id.is_(None),  # IS NULL
                )
            )
        )
        return list(result.scalars().all())

    async def get_overdue_tasks(self) -> list[Task]:
        """
        Получить все просроченные задачи.

        Returns:
            Список просроченных задач (due_date прошёл, статус не DONE/CANCELLED)

        SQL эквивалент:
            SELECT * FROM tasks
            WHERE due_date < CURRENT_DATE
            AND status NOT IN ('done', 'cancelled');
        """
        today = date.today()

        result = await self.db.execute(
            select(Task).where(
                and_(
                    Task.due_date < today,
                    Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
                )
            )
        )
        return list(result.scalars().all())

    async def get_tasks_by_tag(self, tag_id: int) -> list[Task]:
        """
        Получить все задачи с определённым тегом.

        Args:
            tag_id: ID тега

        Returns:
            Список задач с этим тегом

        SQL эквивалент:
            SELECT tasks.*
            FROM tasks
            JOIN task_tags ON tasks.id = task_tags.task_id
            WHERE task_tags.tag_id = {tag_id};

        Пример:
            # Все задачи с тегом "urgent"
            urgent_tag = await tag_repo.get_by_name("urgent")
            tasks = await task_repo.get_tasks_by_tag(urgent_tag.id)
        """
        result = await self.db.execute(
            select(Task)
            .join(Task.tags)  # JOIN через relationship
            .where(Tag.id == tag_id)
        )
        return list(result.scalars().all())

    async def add_tag(self, task_id: int, tag: Tag) -> Task | None:
        """
        Добавить тег к задаче.

        Args:
            task_id: ID задачи
            tag: Объект тега

        Returns:
            Обновлённая задача или None

        Пример:
            task = await task_repo.get_by_id(1)
            urgent_tag = await tag_repo.get_by_name("urgent")
            await task_repo.add_tag(task.id, urgent_tag)
        """
        # Load task with tags eagerly to avoid lazy loading issues
        result = await self.db.execute(
            select(Task).options(selectinload(Task.tags)).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Проверяем, нет ли уже этого тега
        if tag not in task.tags:
            task.tags.append(tag)  # SQLAlchemy автоматически создаст запись в task_tags
            await self.db.flush()

        return task

    async def remove_tag(self, task_id: int, tag: Tag) -> Task | None:
        """
        Удалить тег у задачи.

        Args:
            task_id: ID задачи
            tag: Объект тега

        Returns:
            Обновлённая задача или None
        """
        # Load task with tags eagerly to avoid lazy loading issues
        result = await self.db.execute(
            select(Task).options(selectinload(Task.tags)).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        if tag in task.tags:
            task.tags.remove(tag)  # SQLAlchemy автоматически удалит из task_tags
            await self.db.flush()

        return task

    async def mark_as_done(self, task_id: int) -> Task | None:
        """
        Пометить задачу как выполненную.

        Args:
            task_id: ID задачи

        Returns:
            Обновлённая задача или None

        Устанавливает:
        - status = DONE
        - completed_at = текущее время
        """
        return await self.update(task_id, status=TaskStatus.DONE, completed_at=datetime.now(UTC))

    async def search_by_title(self, search_term: str) -> list[Task]:
        """
        Поиск задач по названию (регистронезависимый).

        Args:
            search_term: Поисковый запрос

        Returns:
            Список найденных задач

        SQL эквивалент:
            SELECT * FROM tasks
            WHERE LOWER(title) LIKE LOWER('%{search_term}%');
        """
        result = await self.db.execute(select(Task).where(Task.title.ilike(f"%{search_term}%")))
        return list(result.scalars().all())

    async def get_filtered(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        project_id: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Task]:
        """
        Получить задачи с фильтрами и пагинацией.

        Все фильтры комбинируются через AND.

        Args:
            status: Фильтр по статусу (optional)
            priority: Фильтр по приоритету (optional)
            project_id: Фильтр по проекту (optional)
            skip: Пропустить N записей
            limit: Максимум записей

        Returns:
            Список задач, соответствующих фильтрам

        SQL эквивалент:
            SELECT * FROM tasks
            WHERE status = {status}  -- если указан
              AND priority = {priority}  -- если указан
              AND project_id = {project_id}  -- если указан
            OFFSET {skip} LIMIT {limit};
        """
        # Строим базовый запрос
        query = select(Task).options(selectinload(Task.tags))

        # Динамически добавляем фильтры
        conditions = []

        if status is not None:
            conditions.append(Task.status == status)

        if priority is not None:
            conditions.append(Task.priority == priority)

        if project_id is not None:
            conditions.append(Task.project_id == project_id)

        # Применяем все условия через AND
        if conditions:
            query = query.where(and_(*conditions))

        # Пагинация
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())
