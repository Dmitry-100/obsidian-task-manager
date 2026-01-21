"""
API endpoints для работы с задачами.

Задачи - самая сложная часть API, включающая:
- CRUD операции
- Работу с подзадачами (иерархия)
- Управление тегами
- Комментарии
- Фильтрацию и поиск
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..services import TaskService
from ..models import TaskStatus, TaskPriority
from .dependencies import get_task_service
from .schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskDetailResponse,
    CommentCreate,
    CommentResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ============================================================================
# CREATE TASK
# ============================================================================

@router.post(
    "",
    response_model=TaskDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать задачу",
    description="""
    Создать новую задачу с автоматическим созданием тегов.

    Бизнес-правила:
    - Проект должен существовать и не быть архивным
    - Родительская задача (если указана) должна быть в том же проекте
    - Максимум 2 уровня вложенности (нет подзадач у подзадач)
    - Дедлайн не в прошлом
    """,
    responses={
        201: {"description": "Задача создана"},
        400: {"model": ErrorResponse, "description": "Ошибка валидации"},
    }
)
async def create_task(
    data: TaskCreate,
    service: TaskService = Depends(get_task_service)
) -> TaskDetailResponse:
    """
    Создать новую задачу.

    Пример запроса:
    ```json
    {
        "title": "Создать REST API",
        "description": "Реализовать CRUD endpoints",
        "project_id": 1,
        "priority": "high",
        "due_date": "2026-01-25",
        "tag_names": ["python", "fastapi", "backend"]
    }
    ```

    Теги будут созданы автоматически, если не существуют.
    """
    try:
        task = await service.create_task(
            title=data.title,
            project_id=data.project_id,
            description=data.description,
            parent_task_id=data.parent_task_id,
            status=data.status,
            priority=data.priority,
            due_date=data.due_date,
            tag_names=data.tag_names,
            obsidian_path=data.obsidian_path,
            estimated_hours=data.estimated_hours,
        )
        return TaskDetailResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# GET ALL TASKS (с фильтрацией и пагинацией)
# ============================================================================

@router.get(
    "",
    response_model=List[TaskResponse],
    summary="Получить задачи с фильтрами",
    description="""
    Получить задачи с опциональными фильтрами и пагинацией.

    **Фильтры:**
    - status: фильтр по статусу (todo, in_progress, done, cancelled)
    - priority: фильтр по приоритету (low, medium, high, critical)
    - project_id: фильтр по проекту

    **Пагинация:**
    - skip: пропустить N записей
    - limit: максимум записей (1-100)

    Все фильтры комбинируются через AND.
    """
)
async def get_tasks(
    # Фильтры
    status: Optional[TaskStatus] = Query(
        None,
        description="Фильтр по статусу: todo, in_progress, done, cancelled"
    ),
    priority: Optional[TaskPriority] = Query(
        None,
        description="Фильтр по приоритету: low, medium, high, critical"
    ),
    project_id: Optional[int] = Query(
        None,
        description="Фильтр по проекту"
    ),
    # Пагинация
    skip: int = Query(0, ge=0, description="Пропустить N записей"),
    limit: int = Query(20, ge=1, le=100, description="Максимум записей"),
    service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """
    Получить задачи с фильтрами.

    Примеры запросов:
    ```
    GET /tasks                              # первые 20 задач
    GET /tasks?status=todo                  # только "к выполнению"
    GET /tasks?priority=high&status=todo    # высокий приоритет + к выполнению
    GET /tasks?project_id=1&skip=0&limit=10 # первые 10 задач проекта 1
    ```
    """
    tasks = await service.get_tasks_filtered(
        status=status,
        priority=priority,
        project_id=project_id,
        skip=skip,
        limit=limit
    )
    return [TaskResponse.model_validate(t) for t in tasks]


# ============================================================================
# GET TASK BY ID
# ============================================================================

@router.get(
    "/{task_id}",
    response_model=TaskDetailResponse,
    summary="Получить задачу по ID",
    description="Получить задачу со всеми связями (теги, комментарии).",
    responses={
        200: {"description": "Задача найдена"},
        404: {"model": ErrorResponse, "description": "Задача не найдена"},
    }
)
async def get_task(
    task_id: int,
    service: TaskService = Depends(get_task_service)
) -> TaskDetailResponse:
    """
    Получить задачу по ID.

    Включает все связи:
    - Теги
    - Комментарии
    - Информацию о проекте

    Пример запроса:
    ```
    GET /tasks/1
    ```
    """
    try:
        task = await service.get_task(task_id, full=True)
        return TaskDetailResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# UPDATE TASK
# ============================================================================

@router.put(
    "/{task_id}",
    response_model=TaskDetailResponse,
    summary="Обновить задачу",
    description="""
    Частичное обновление задачи.

    При смене статуса на DONE автоматически устанавливается completed_at.
    """,
    responses={
        200: {"description": "Задача обновлена"},
        400: {"model": ErrorResponse, "description": "Ошибка валидации"},
        404: {"model": ErrorResponse, "description": "Задача не найдена"},
    }
)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    service: TaskService = Depends(get_task_service)
) -> TaskDetailResponse:
    """
    Обновить задачу.

    Все поля опциональные.

    Пример запроса:
    ```json
    {
        "title": "Новое название",
        "status": "in_progress",
        "priority": "high"
    }
    ```
    """
    try:
        task = await service.update_task(
            task_id=task_id,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            due_date=data.due_date,
            estimated_hours=data.estimated_hours,
        )
        return TaskDetailResponse.model_validate(task)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


# ============================================================================
# COMPLETE TASK
# ============================================================================

@router.post(
    "/{task_id}/complete",
    response_model=TaskDetailResponse,
    summary="Завершить задачу",
    description="""
    Пометить задачу как выполненную.

    Бизнес-правило: Нельзя завершить задачу с незавершёнными подзадачами.
    """,
    responses={
        200: {"description": "Задача завершена"},
        400: {"model": ErrorResponse, "description": "Есть незавершённые подзадачи"},
        404: {"model": ErrorResponse, "description": "Задача не найдена"},
    }
)
async def complete_task(
    task_id: int,
    service: TaskService = Depends(get_task_service)
) -> TaskDetailResponse:
    """
    Завершить задачу.

    Устанавливает:
    - status = DONE
    - completed_at = текущее время

    Пример запроса:
    ```
    POST /tasks/1/complete
    ```
    """
    try:
        task = await service.complete_task(task_id)
        return TaskDetailResponse.model_validate(task)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


# ============================================================================
# DELETE TASK
# ============================================================================

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить задачу",
    description="""
    Удалить задачу.

    По умолчанию нельзя удалить задачу с подзадачами.
    Используйте force=true для принудительного удаления.
    """,
    responses={
        204: {"description": "Задача удалена"},
        400: {"model": ErrorResponse, "description": "Задача имеет подзадачи"},
        404: {"model": ErrorResponse, "description": "Задача не найдена"},
    }
)
async def delete_task(
    task_id: int,
    force: bool = Query(False, description="Принудительное удаление"),
    service: TaskService = Depends(get_task_service)
):
    """
    Удалить задачу.

    Query параметры:
    - force: bool - принудительное удаление с подзадачами

    Пример запроса:
    ```
    DELETE /tasks/1?force=true
    ```
    """
    try:
        await service.delete_task(task_id, force=force)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


# ============================================================================
# GET TASKS BY PROJECT
# ============================================================================

@router.get(
    "/by-project/{project_id}",
    response_model=List[TaskResponse],
    summary="Получить задачи проекта",
    description="Получить все задачи проекта с опциональными фильтрами.",
    responses={
        200: {"description": "Список задач"},
        404: {"model": ErrorResponse, "description": "Проект не найден"},
    }
)
async def get_tasks_by_project(
    project_id: int,
    include_completed: bool = Query(False, description="Включать завершённые"),
    root_only: bool = Query(False, description="Только корневые задачи"),
    service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """
    Получить задачи проекта.

    Query параметры:
    - include_completed: bool - включать завершённые задачи
    - root_only: bool - только корневые задачи (без родителя)

    Пример запроса:
    ```
    GET /tasks/by-project/1?include_completed=false&root_only=true
    ```

    Это полезно для отображения дерева задач:
    - Сначала получаем корневые задачи
    - Для каждой корневой задачи получаем subtasks из поля
    """
    try:
        tasks = await service.get_tasks_by_project(
            project_id=project_id,
            include_completed=include_completed,
            root_only=root_only
        )
        return [TaskResponse.model_validate(t) for t in tasks]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# GET OVERDUE TASKS
# ============================================================================

@router.get(
    "/overdue",
    response_model=List[TaskResponse],
    summary="Получить просроченные задачи",
    description="""
    Получить все просроченные задачи.

    Условия:
    - due_date < сегодня
    - статус НЕ DONE и НЕ CANCELLED
    """
)
async def get_overdue_tasks(
    service: TaskService = Depends(get_task_service)
) -> List[TaskResponse]:
    """
    Получить просроченные задачи.

    Пример запроса:
    ```
    GET /tasks/overdue
    ```
    """
    tasks = await service.get_overdue_tasks()
    return [TaskResponse.model_validate(t) for t in tasks]


# ============================================================================
# MANAGE TAGS
# ============================================================================

@router.post(
    "/{task_id}/tags",
    response_model=TaskDetailResponse,
    summary="Добавить теги к задаче",
    description="""
    Добавить теги к задаче.

    Теги создаются автоматически, если не существуют.
    Дубликаты не создаются.
    """,
    responses={
        200: {"description": "Теги добавлены"},
        404: {"model": ErrorResponse, "description": "Задача не найдена"},
    }
)
async def add_tags_to_task(
    task_id: int,
    tag_names: List[str],
    service: TaskService = Depends(get_task_service)
) -> TaskDetailResponse:
    """
    Добавить теги к задаче.

    Пример запроса:
    ```json
    ["python", "backend", "api"]
    ```
    """
    try:
        task = await service.add_tags_to_task(task_id, tag_names)
        return TaskDetailResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/{task_id}/tags/{tag_name}",
    response_model=TaskDetailResponse,
    summary="Удалить тег у задачи",
    responses={
        200: {"description": "Тег удалён"},
        404: {"model": ErrorResponse, "description": "Задача или тег не найдены"},
    }
)
async def remove_tag_from_task(
    task_id: int,
    tag_name: str,
    service: TaskService = Depends(get_task_service)
) -> TaskDetailResponse:
    """
    Удалить тег у задачи.

    Пример запроса:
    ```
    DELETE /tasks/1/tags/python
    ```
    """
    try:
        task = await service.remove_tag_from_task(task_id, tag_name)
        return TaskDetailResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# COMMENTS
# ============================================================================

@router.post(
    "/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить комментарий",
    description="Добавить комментарий к задаче (поддерживает Markdown).",
    responses={
        201: {"description": "Комментарий добавлен"},
        400: {"model": ErrorResponse, "description": "Комментарий пустой"},
        404: {"model": ErrorResponse, "description": "Задача не найдена"},
    }
)
async def add_comment(
    task_id: int,
    data: CommentCreate,
    service: TaskService = Depends(get_task_service)
) -> CommentResponse:
    """
    Добавить комментарий к задаче.

    Поддерживает Markdown форматирование.

    Пример запроса:
    ```json
    {
        "content": "Нашёл баг в авторизации. Нужно **срочно** исправить!"
    }
    ```
    """
    try:
        comment = await service.add_comment(task_id, data.content)
        return CommentResponse.model_validate(comment)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


# ============================================================================
# TASK HIERARCHY
# ============================================================================

@router.get(
    "/{task_id}/hierarchy",
    summary="Получить иерархию задачи",
    description="""
    Получить полную иерархию задачи:
    - Родительская задача (если есть)
    - Текущая задача
    - Подзадачи

    Полезно для отображения дерева задач.
    """
)
async def get_task_hierarchy(
    task_id: int,
    service: TaskService = Depends(get_task_service)
):
    """
    Получить иерархию задачи.

    Пример ответа:
    ```json
    {
        "parent": { "id": 1, "title": "Разработать фичу", ... },
        "task": { "id": 2, "title": "Написать тесты", ... },
        "subtasks": [
            { "id": 3, "title": "Unit тесты", ... },
            { "id": 4, "title": "Integration тесты", ... }
        ]
    }
    ```
    """
    try:
        hierarchy = await service.get_task_hierarchy(task_id)
        return {
            "parent": TaskResponse.model_validate(hierarchy["parent"]) if hierarchy["parent"] else None,
            "task": TaskResponse.model_validate(hierarchy["task"]),
            "subtasks": [TaskResponse.model_validate(t) for t in hierarchy["subtasks"]]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# TASK STATISTICS
# ============================================================================

@router.get(
    "/{task_id}/stats",
    summary="Получить статистику задачи",
    description="""
    Получить статистику по задаче:
    - Количество подзадач
    - Количество комментариев
    - Количество тегов
    - Статус дедлайна
    """
)
async def get_task_statistics(
    task_id: int,
    service: TaskService = Depends(get_task_service)
):
    """
    Получить статистику по задаче.

    Пример ответа:
    ```json
    {
        "task_id": 1,
        "task_title": "Создать API",
        "total_subtasks": 5,
        "completed_subtasks": 3,
        "comments_count": 7,
        "tags_count": 3,
        "is_overdue": false,
        "days_until_due": 5
    }
    ```
    """
    try:
        stats = await service.get_task_statistics(task_id)
        return stats
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
