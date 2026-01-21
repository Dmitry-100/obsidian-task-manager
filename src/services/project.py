"""Project service with business logic."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Project
from ..repositories import ProjectRepository, TaskRepository


class ProjectService:
    """
    Сервис для работы с проектами.

    Содержит бизнес-логику:
    - Валидация правил
    - Координация между репозиториями
    - Управление транзакциями
    """

    def __init__(self, db: AsyncSession):
        """
        Инициализация сервиса.

        Args:
            db: Асинхронная сессия БД

        Service создаёт нужные репозитории внутри себя.
        """
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.task_repo = TaskRepository(db)

    async def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        obsidian_folder: Optional[str] = None,
        color: Optional[str] = None
    ) -> Project:
        """
        Создать новый проект с валидацией.

        Args:
            name: Название проекта
            description: Описание
            obsidian_folder: Путь к папке в Obsidian
            color: Цвет проекта (hex)

        Returns:
            Созданный проект

        Raises:
            ValueError: Если валидация не прошла

        Бизнес-правила:
        1. Название обязательно и не пустое
        2. Название уникально (нет другого проекта с таким именем)
        3. Цвет должен быть в hex формате (#RRGGBB)
        """
        # 1. ВАЛИДАЦИЯ: Название не пустое
        if not name or not name.strip():
            raise ValueError("Project name cannot be empty")

        # 2. ВАЛИДАЦИЯ: Проверка уникальности названия
        existing = await self.project_repo.search_by_name(name.strip())
        if existing:
            raise ValueError(f"Project with name '{name}' already exists")

        # 3. ВАЛИДАЦИЯ: Формат цвета
        if color and not self._is_valid_hex_color(color):
            raise ValueError(f"Invalid color format: {color}. Use #RRGGBB")

        # 4. СОЗДАНИЕ: Создать проект
        project = Project(
            name=name.strip(),
            description=description.strip() if description else None,
            obsidian_folder=obsidian_folder,
            color=color,
        )

        project = await self.project_repo.create(project)

        # 5. ТРАНЗАКЦИЯ: Commit
        await self.db.flush()

        return project

    async def get_project(self, project_id: int) -> Project:
        """
        Получить проект по ID.

        Args:
            project_id: ID проекта

        Returns:
            Проект

        Raises:
            ValueError: Если проект не найден
        """
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found")
        return project

    async def get_project_with_tasks(self, project_id: int) -> Project:
        """
        Получить проект со всеми задачами (eager loading).

        Args:
            project_id: ID проекта

        Returns:
            Проект с задачами

        Raises:
            ValueError: Если проект не найден
        """
        project = await self.project_repo.get_by_id_with_tasks(project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found")
        return project

    async def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        obsidian_folder: Optional[str] = None
    ) -> Project:
        """
        Обновить проект.

        Args:
            project_id: ID проекта
            name: Новое название (опционально)
            description: Новое описание (опционально)
            color: Новый цвет (опционально)
            obsidian_folder: Новый путь (опционально)

        Returns:
            Обновлённый проект

        Raises:
            ValueError: Если валидация не прошла
        """
        # 1. ПРОВЕРКА: Проект существует
        project = await self.get_project(project_id)

        # 2. ВАЛИДАЦИЯ: Если меняем название - проверить уникальность
        if name and name.strip() != project.name:
            existing = await self.project_repo.search_by_name(name.strip())
            if existing:
                raise ValueError(f"Project with name '{name}' already exists")

        # 3. ВАЛИДАЦИЯ: Формат цвета
        if color and not self._is_valid_hex_color(color):
            raise ValueError(f"Invalid color format: {color}")

        # 4. ОБНОВЛЕНИЕ: Собираем только изменённые поля
        updates = {}
        if name:
            updates["name"] = name.strip()
        if description is not None:  # может быть пустая строка!
            updates["description"] = description.strip() if description else None
        if color:
            updates["color"] = color
        if obsidian_folder is not None:
            updates["obsidian_folder"] = obsidian_folder

        # 5. ОБНОВЛЕНИЕ: Применить изменения
        if updates:
            project = await self.project_repo.update(project_id, **updates)

        await self.db.flush()
        return project

    async def archive_project(self, project_id: int) -> Project:
        """
        Архивировать проект (мягкое удаление).

        Args:
            project_id: ID проекта

        Returns:
            Архивированный проект

        Бизнес-правило:
        - Архивированный проект нельзя изменять
        - Нельзя добавлять новые задачи в архивный проект
        """
        project = await self.get_project(project_id)

        if project.is_archived:
            raise ValueError("Project is already archived")

        project = await self.project_repo.archive_project(project_id)
        await self.db.flush()

        return project

    async def unarchive_project(self, project_id: int) -> Project:
        """
        Восстановить проект из архива.

        Args:
            project_id: ID проекта

        Returns:
            Восстановленный проект
        """
        project = await self.get_project(project_id)

        if not project.is_archived:
            raise ValueError("Project is not archived")

        project = await self.project_repo.unarchive_project(project_id)
        await self.db.flush()

        return project

    async def delete_project(self, project_id: int, force: bool = False) -> bool:
        """
        Удалить проект.

        Args:
            project_id: ID проекта
            force: Принудительное удаление (игнорировать задачи)

        Returns:
            True если удалён

        Raises:
            ValueError: Если есть связанные задачи и force=False

        Бизнес-правило:
        - Нельзя удалить проект с задачами (если не force)
        - Это жёсткое удаление (hard delete)
        """
        project = await self.get_project_with_tasks(project_id)

        # ВАЛИДАЦИЯ: Проверить наличие задач
        if project.tasks and not force:
            raise ValueError(
                f"Cannot delete project with {len(project.tasks)} tasks. "
                "Use force=True to delete anyway."
            )

        # УДАЛЕНИЕ: Cascade удалит все связанные задачи
        deleted = await self.project_repo.delete(project_id)
        await self.db.flush()

        return deleted

    async def get_all_projects(
        self,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 20
    ) -> List[Project]:
        """
        Получить все проекты с пагинацией.

        Args:
            include_archived: Включать ли архивные проекты
            skip: Количество записей для пропуска (offset)
            limit: Максимальное количество записей

        Returns:
            Список проектов
        """
        if include_archived:
            return await self.project_repo.get_all(skip=skip, limit=limit)
        else:
            return await self.project_repo.get_active_projects(skip=skip, limit=limit)

    async def get_project_statistics(self, project_id: int) -> dict:
        """
        Получить статистику по проекту.

        Args:
            project_id: ID проекта

        Returns:
            Словарь со статистикой

        Пример:
            {
                "total_tasks": 15,
                "completed_tasks": 10,
                "in_progress_tasks": 3,
                "todo_tasks": 2,
                "completion_percentage": 66.67
            }

        Это бизнес-логика! Repository не должен знать, как считать процент.
        """
        from ..models import TaskStatus

        # Получаем проект с задачами
        project = await self.get_project_with_tasks(project_id)

        # Подсчитываем статистику
        total = len(project.tasks)
        completed = sum(1 for t in project.tasks if t.status == TaskStatus.DONE)
        in_progress = sum(1 for t in project.tasks if t.status == TaskStatus.IN_PROGRESS)
        todo = sum(1 for t in project.tasks if t.status == TaskStatus.TODO)

        completion_percentage = (completed / total * 100) if total > 0 else 0

        return {
            "project_id": project_id,
            "project_name": project.name,
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress_tasks": in_progress,
            "todo_tasks": todo,
            "completion_percentage": round(completion_percentage, 2),
        }

    # Вспомогательные методы (private)

    def _is_valid_hex_color(self, color: str) -> bool:
        """
        Проверить формат hex цвета.

        Args:
            color: Строка цвета

        Returns:
            True если валидный hex цвет
        """
        import re
        pattern = r'^#[0-9A-Fa-f]{6}$'
        return bool(re.match(pattern, color))
