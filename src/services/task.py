"""Task service with business logic."""

from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Task, TaskComment, TaskPriority, TaskStatus
from ..repositories import (
    ProjectRepository,
    TagRepository,
    TaskCommentRepository,
    TaskRepository,
)


class TaskService:
    """
    Сервис для работы с задачами.

    Это самый сложный сервис, так как задачи имеют много связей:
    - Проекты
    - Подзадачи (иерархия)
    - Теги (Many-to-Many)
    - Комментарии
    """

    def __init__(self, db: AsyncSession):
        """Инициализация сервиса с несколькими репозиториями."""
        self.db = db
        self.task_repo = TaskRepository(db)
        self.project_repo = ProjectRepository(db)
        self.tag_repo = TagRepository(db)
        self.comment_repo = TaskCommentRepository(db)

    async def create_task(
        self,
        title: str,
        project_id: int,
        description: str | None = None,
        parent_task_id: int | None = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: date | None = None,
        tag_names: list[str] | None = None,
        obsidian_path: str | None = None,
        estimated_hours: float | None = None,
    ) -> Task:
        """
        Создать новую задачу с валидацией бизнес-правил.

        Args:
            title: Название задачи
            project_id: ID проекта
            description: Описание
            parent_task_id: ID родительской задачи (для подзадач)
            status: Статус задачи
            priority: Приоритет
            due_date: Дедлайн
            tag_names: Список названий тегов
            obsidian_path: Путь к файлу в Obsidian
            estimated_hours: Оценка времени

        Returns:
            Созданная задача

        Raises:
            ValueError: Если валидация не прошла

        Бизнес-правила:
        1. Название обязательно
        2. Проект существует и не архивирован
        3. Родительская задача существует (если указана)
        4. Родитель в том же проекте
        5. Нельзя создать циклическую зависимость
        6. Дедлайн не в прошлом
        """
        # 1. ВАЛИДАЦИЯ: Название
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty")

        # 2. ВАЛИДАЦИЯ: Проект существует и активен
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found")
        if project.is_archived:
            raise ValueError("Cannot add tasks to archived project")

        # 3. ВАЛИДАЦИЯ: Родительская задача (если указана)
        if parent_task_id:
            parent_task = await self.task_repo.get_by_id(parent_task_id)
            if not parent_task:
                raise ValueError(f"Parent task with id {parent_task_id} not found")

            # 4. ВАЛИДАЦИЯ: Родитель в том же проекте
            if parent_task.project_id != project_id:
                raise ValueError(
                    f"Parent task is in different project "
                    f"(parent: {parent_task.project_id}, current: {project_id})"
                )

            # 5. ВАЛИДАЦИЯ: Нельзя создать подзадачу для подзадачи (максимум 2 уровня)
            if parent_task.parent_task_id is not None:
                raise ValueError("Cannot create subtask of subtask. Maximum 2 levels allowed.")

        # 6. ВАЛИДАЦИЯ: Дедлайн не в прошлом
        if due_date and due_date < date.today():
            raise ValueError("Due date cannot be in the past")

        # 7. ВАЛИДАЦИЯ: Estimated hours положительное число
        if estimated_hours is not None and estimated_hours <= 0:
            raise ValueError("Estimated hours must be positive")

        # 8. СОЗДАНИЕ: Создать задачу
        task = Task(
            title=title.strip(),
            description=description.strip() if description else None,
            project_id=project_id,
            parent_task_id=parent_task_id,
            status=status,
            priority=priority,
            due_date=due_date,
            obsidian_path=obsidian_path,
            estimated_hours=estimated_hours,
        )

        task = await self.task_repo.create(task)

        # 9. КООРДИНАЦИЯ: Добавить теги (если указаны)
        if tag_names:
            tags = await self.tag_repo.bulk_get_or_create(tag_names)
            for tag in tags:
                await self.task_repo.add_tag(task.id, tag)

        # 10. FLUSH: Сохранить в БД (commit будет в dependency)
        await self.db.flush()

        # 11. ЗАГРУЗКА: Вернуть задачу со всеми связями
        return await self.task_repo.get_by_id_full(task.id)

    async def get_task(self, task_id: int, full: bool = False) -> Task:
        """
        Получить задачу по ID.

        Args:
            task_id: ID задачи
            full: Загружать ли все связи (eager loading)

        Returns:
            Задача

        Raises:
            ValueError: Если задача не найдена
        """
        if full:
            task = await self.task_repo.get_by_id_full(task_id)
        else:
            task = await self.task_repo.get_by_id(task_id)

        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        return task

    async def update_task(
        self,
        task_id: int,
        title: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        due_date: date | None = None,
        estimated_hours: float | None = None,
    ) -> Task:
        """
        Обновить задачу.

        Args:
            task_id: ID задачи
            title: Новое название
            status: Новый статус
            priority: Новый приоритет
            due_date: Новый дедлайн
            estimated_hours: Новая оценка

        Returns:
            Обновлённая задача

        Raises:
            ValueError: Если валидация не прошла

        Бизнес-правила:
        1. При смене статуса на DONE - установить completed_at
        2. При смене статуса с DONE - сбросить completed_at
        3. Дедлайн не в прошлом
        """
        # 1. ПРОВЕРКА: Задача существует
        task = await self.get_task(task_id)

        # 2. ВАЛИДАЦИЯ: Название
        if title is not None and not title.strip():
            raise ValueError("Task title cannot be empty")

        # 3. ВАЛИДАЦИЯ: Дедлайн
        if due_date and due_date < date.today():
            raise ValueError("Due date cannot be in the past")

        # 4. ВАЛИДАЦИЯ: Estimated hours
        if estimated_hours is not None and estimated_hours <= 0:
            raise ValueError("Estimated hours must be positive")

        # 5. ОБНОВЛЕНИЕ: Собираем изменения
        updates: dict[str, Any] = {}  # Any потому что значения разных типов
        if title:
            updates["title"] = title.strip()
        if description is not None:
            updates["description"] = description.strip() if description else None
        if priority:
            updates["priority"] = priority
        if due_date is not None:
            updates["due_date"] = due_date
        if estimated_hours is not None:
            updates["estimated_hours"] = estimated_hours

        # 6. БИЗНЕС-ЛОГИКА: Управление статусом
        if status:
            updates["status"] = status

            # Если переводим в DONE - установить completed_at
            if status == TaskStatus.DONE and task.status != TaskStatus.DONE:
                updates["completed_at"] = datetime.utcnow()

            # Если убираем из DONE - сбросить completed_at
            if status != TaskStatus.DONE and task.status == TaskStatus.DONE:
                updates["completed_at"] = None

        # 7. ПРИМЕНЕНИЕ: Обновить
        if updates:
            task = await self.task_repo.update(task_id, **updates)

        await self.db.flush()

        return await self.task_repo.get_by_id_full(task_id)

    async def complete_task(self, task_id: int) -> Task:
        """
        Пометить задачу как выполненную.

        Args:
            task_id: ID задачи

        Returns:
            Обновлённая задача

        Бизнес-правило:
        - Если есть невыполненные подзадачи - предупреждение
        """
        task = await self.get_task(task_id, full=True)

        # ВАЛИДАЦИЯ: Проверить подзадачи
        incomplete_subtasks = [
            st for st in task.subtasks if st.status not in [TaskStatus.DONE, TaskStatus.CANCELLED]
        ]

        if incomplete_subtasks:
            raise ValueError(
                f"Cannot complete task with {len(incomplete_subtasks)} incomplete subtasks. "
                f"Complete or cancel them first."
            )

        # Используем repository метод
        task = await self.task_repo.mark_as_done(task_id)
        await self.db.flush()

        return await self.task_repo.get_by_id_full(task_id)

    async def add_tags_to_task(self, task_id: int, tag_names: list[str]) -> Task:
        """
        Добавить теги к задаче.

        Args:
            task_id: ID задачи
            tag_names: Список названий тегов

        Returns:
            Задача с обновлёнными тегами

        Бизнес-логика:
        - Автоматически создаёт несуществующие теги
        - Не дублирует теги
        """
        # Проверяем, что задача существует (get_task выбросит ValueError если нет)
        _task = await self.get_task(task_id)

        # КООРДИНАЦИЯ: Получить/создать теги
        tags = await self.tag_repo.bulk_get_or_create(tag_names)

        # КООРДИНАЦИЯ: Добавить теги
        for tag in tags:
            await self.task_repo.add_tag(task_id, tag)

        await self.db.flush()

        return await self.task_repo.get_by_id_full(task_id)

    async def remove_tag_from_task(self, task_id: int, tag_name: str) -> Task:
        """
        Удалить тег у задачи.

        Args:
            task_id: ID задачи
            tag_name: Название тега

        Returns:
            Задача с обновлёнными тегами

        Raises:
            ValueError: Если тег не найден
        """
        # Проверяем, что задача существует
        _task = await self.get_task(task_id)

        # ПОИСК: Найти тег
        tag = await self.tag_repo.get_by_name(tag_name)
        if not tag:
            raise ValueError(f"Tag '{tag_name}' not found")

        # УДАЛЕНИЕ: Убрать тег
        await self.task_repo.remove_tag(task_id, tag)
        await self.db.flush()

        return await self.task_repo.get_by_id_full(task_id)

    async def add_comment(self, task_id: int, content: str) -> TaskComment:
        """
        Добавить комментарий к задаче.

        Args:
            task_id: ID задачи
            content: Содержимое комментария (Markdown)

        Returns:
            Созданный комментарий

        Raises:
            ValueError: Если валидация не прошла
        """
        # ВАЛИДАЦИЯ: Задача существует
        await self.get_task(task_id)

        # ВАЛИДАЦИЯ: Комментарий не пустой
        if not content or not content.strip():
            raise ValueError("Comment content cannot be empty")

        # СОЗДАНИЕ: Создать комментарий
        comment = TaskComment(task_id=task_id, content=content.strip())

        comment = await self.comment_repo.create(comment)
        await self.db.flush()

        return comment

    async def get_task_hierarchy(self, task_id: int) -> dict:
        """
        Получить полную иерархию задачи (родитель + подзадачи).

        Args:
            task_id: ID задачи

        Returns:
            Словарь с иерархией

        Пример:
            {
                "task": {...},
                "parent": {...} или None,
                "subtasks": [...]
            }

        Это бизнес-логика для отображения дерева задач в UI.
        """
        task = await self.task_repo.get_by_id_full(task_id)
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        return {
            "task": task,
            "parent": task.parent_task,
            "subtasks": task.subtasks,
        }

    async def get_overdue_tasks(self) -> list[Task]:
        """
        Получить все просроченные задачи.

        Returns:
            Список просроченных задач

        Бизнес-логика:
        - Только активные задачи (не DONE, не CANCELLED)
        - due_date < today
        """
        return await self.task_repo.get_overdue_tasks()

    async def get_tasks_by_project(
        self, project_id: int, include_completed: bool = False, root_only: bool = False
    ) -> list[Task]:
        """
        Получить задачи проекта с фильтрами.

        Args:
            project_id: ID проекта
            include_completed: Включать завершённые задачи
            root_only: Только корневые задачи (без родителя)

        Returns:
            Список задач

        Raises:
            ValueError: Если проект не найден
        """
        # ВАЛИДАЦИЯ: Проект существует
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found")

        # ПОЛУЧЕНИЕ: Задачи
        if root_only:
            return await self.task_repo.get_root_tasks(project_id)
        else:
            return await self.task_repo.get_by_project(
                project_id, include_completed=include_completed
            )

    async def delete_task(self, task_id: int, force: bool = False) -> bool:
        """
        Удалить задачу.

        Args:
            task_id: ID задачи
            force: Принудительное удаление (с подзадачами)

        Returns:
            True если удалена

        Raises:
            ValueError: Если есть подзадачи и force=False

        Бизнес-правило:
        - Нельзя удалить задачу с подзадачами (если не force)
        - Cascade удалит комментарии автоматически
        """
        task = await self.task_repo.get_by_id_full(task_id)
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        # ВАЛИДАЦИЯ: Проверить подзадачи
        if task.subtasks and not force:
            raise ValueError(
                f"Cannot delete task with {len(task.subtasks)} subtasks. "
                "Use force=True to delete anyway."
            )

        # УДАЛЕНИЕ: Cascade удалит подзадачи и комментарии
        deleted = await self.task_repo.delete(task_id)
        await self.db.flush()

        return deleted

    async def get_task_statistics(self, task_id: int) -> dict:
        """
        Получить статистику по задаче.

        Args:
            task_id: ID задачи

        Returns:
            Словарь со статистикой

        Пример:
            {
                "total_subtasks": 5,
                "completed_subtasks": 3,
                "comments_count": 7,
                "tags_count": 3,
                "is_overdue": False,
                "days_until_due": 5
            }
        """

        task = await self.task_repo.get_by_id_full(task_id)
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        # Подсчёт подзадач
        total_subtasks = len(task.subtasks)
        completed_subtasks = sum(1 for st in task.subtasks if st.status == TaskStatus.DONE)

        # Подсчёт комментариев
        comments_count = await self.comment_repo.count_by_task(task_id)

        # Проверка дедлайна
        is_overdue = False
        days_until_due = None
        if task.due_date:
            today = date.today()
            is_overdue = task.due_date < today and task.status != TaskStatus.DONE
            days_until_due = (task.due_date - today).days

        return {
            "task_id": task_id,
            "task_title": task.title,
            "total_subtasks": total_subtasks,
            "completed_subtasks": completed_subtasks,
            "comments_count": comments_count,
            "tags_count": len(task.tags),
            "is_overdue": is_overdue,
            "days_until_due": days_until_due,
        }

    async def get_tasks_filtered(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        project_id: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Task]:
        """
        Получить задачи с фильтрами и пагинацией.

        Args:
            status: Фильтр по статусу (todo, in_progress, done, cancelled)
            priority: Фильтр по приоритету (low, medium, high, critical)
            project_id: Фильтр по проекту
            skip: Пропустить N записей (пагинация)
            limit: Максимум записей (пагинация)

        Returns:
            Список задач, соответствующих фильтрам

        Примеры использования:
            # Все задачи "к выполнению"
            tasks = await service.get_tasks_filtered(status=TaskStatus.TODO)

            # Высокоприоритетные задачи проекта 1
            tasks = await service.get_tasks_filtered(
                priority=TaskPriority.HIGH,
                project_id=1
            )
        """
        return await self.task_repo.get_filtered(
            status=status, priority=priority, project_id=project_id, skip=skip, limit=limit
        )
