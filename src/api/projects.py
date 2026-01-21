"""
API endpoints для работы с проектами.

REST API следует принципам:
- GET - получение данных
- POST - создание
- PUT - обновление
- DELETE - удаление

URL структура:
- GET    /projects          - список всех проектов
- GET    /projects/{id}     - один проект
- POST   /projects          - создать проект
- PUT    /projects/{id}     - обновить проект
- DELETE /projects/{id}     - удалить проект
- POST   /projects/{id}/archive   - архивировать
- POST   /projects/{id}/unarchive - восстановить
- GET    /projects/{id}/stats     - статистика
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..services import ProjectService
from .dependencies import get_project_service
from .schemas import (
    ErrorResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithStats,
)

# Создаём роутер для проектов
# prefix="/projects" - все пути будут начинаться с /projects
# tags=["projects"] - группировка в Swagger UI
router = APIRouter(prefix="/projects", tags=["projects"])


# ============================================================================
# CREATE PROJECT
# ============================================================================


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать проект",
    description="""
    Создать новый проект.

    Бизнес-правила:
    - Название обязательно и уникально
    - Цвет в формате #RRGGBB (если указан)
    """,
    responses={
        201: {"description": "Проект успешно создан"},
        400: {"model": ErrorResponse, "description": "Ошибка валидации"},
    },
)
async def create_project(
    data: ProjectCreate, service: ProjectService = Depends(get_project_service)
) -> ProjectResponse:
    """
    Создать новый проект.

    Пример запроса:
    ```json
    {
        "name": "Вайб-Кодинг Week 4",
        "description": "Изучение баз данных",
        "color": "#3B82F6"
    }
    ```
    """
    try:
        project = await service.create_project(
            name=data.name,
            description=data.description,
            obsidian_folder=data.obsidian_folder,
            color=data.color,
        )
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        # Service выбросил ошибку валидации
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# GET ALL PROJECTS (с пагинацией)
# ============================================================================


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="Получить список проектов",
    description="""
    Получить проекты с пагинацией и фильтрацией.

    **Пагинация:**
    - skip: количество записей для пропуска (offset)
    - limit: максимальное количество записей (по умолчанию 20)

    **Фильтрация:**
    - include_archived: включать ли архивные проекты
    """,
)
async def get_projects(
    # Пагинация
    skip: int = Query(
        0,
        ge=0,  # >= 0 (не может быть отрицательным)
        description="Количество записей для пропуска (offset)",
    ),
    limit: int = Query(
        20,
        ge=1,  # >= 1 (хотя бы одна запись)
        le=100,  # <= 100 (защита от слишком больших запросов)
        description="Максимальное количество записей (1-100)",
    ),
    # Фильтрация
    include_archived: bool = Query(False, description="Включать ли архивные проекты"),
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    """
    Получить список проектов с пагинацией.

    Query параметры:
    - skip: int - пропустить N записей (по умолчанию 0)
    - limit: int - максимум записей (по умолчанию 20, макс 100)
    - include_archived: bool - включать архивные (по умолчанию false)

    Примеры запросов:
    ```
    GET /projects                          # первые 20 проектов
    GET /projects?skip=20&limit=10         # проекты 21-30
    GET /projects?include_archived=true    # с архивными
    ```
    """
    projects = await service.get_all_projects(
        include_archived=include_archived, skip=skip, limit=limit
    )
    return [ProjectResponse.model_validate(p) for p in projects]


# ============================================================================
# GET PROJECT BY ID
# ============================================================================


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Получить проект по ID",
    responses={
        200: {"description": "Проект найден"},
        404: {"model": ErrorResponse, "description": "Проект не найден"},
    },
)
async def get_project(
    project_id: int, service: ProjectService = Depends(get_project_service)
) -> ProjectResponse:
    """
    Получить проект по ID.

    Path параметры:
    - project_id: int - ID проекта

    Пример запроса:
    ```
    GET /projects/1
    ```
    """
    try:
        project = await service.get_project(project_id)
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# UPDATE PROJECT
# ============================================================================


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Обновить проект",
    description="Частичное обновление проекта. Можно обновить только нужные поля.",
    responses={
        200: {"description": "Проект обновлён"},
        400: {"model": ErrorResponse, "description": "Ошибка валидации"},
        404: {"model": ErrorResponse, "description": "Проект не найден"},
    },
)
async def update_project(
    project_id: int, data: ProjectUpdate, service: ProjectService = Depends(get_project_service)
) -> ProjectResponse:
    """
    Обновить проект.

    Все поля опциональные - можно обновить только нужные.

    Пример запроса:
    ```json
    {
        "name": "Новое название",
        "color": "#FF0000"
    }
    ```
    """
    try:
        project = await service.update_project(
            project_id=project_id,
            name=data.name,
            description=data.description,
            color=data.color,
            obsidian_folder=data.obsidian_folder,
        )
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        # Определяем тип ошибки по тексту
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# DELETE PROJECT
# ============================================================================


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить проект",
    description="""
    Удалить проект.

    По умолчанию нельзя удалить проект с задачами.
    Используйте force=true для принудительного удаления.
    """,
    responses={
        204: {"description": "Проект удалён"},
        400: {"model": ErrorResponse, "description": "Проект имеет задачи"},
        404: {"model": ErrorResponse, "description": "Проект не найден"},
    },
)
async def delete_project(
    project_id: int,
    force: bool = Query(False, description="Принудительное удаление (с задачами)"),
    service: ProjectService = Depends(get_project_service),
):
    """
    Удалить проект.

    Query параметры:
    - force: bool - принудительное удаление (по умолчанию false)

    Пример запроса:
    ```
    DELETE /projects/1?force=true
    ```
    """
    try:
        await service.delete_project(project_id, force=force)
        # 204 No Content - не возвращаем тело ответа
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# ARCHIVE PROJECT
# ============================================================================


@router.post(
    "/{project_id}/archive",
    response_model=ProjectResponse,
    summary="Архивировать проект",
    description="Мягкое удаление проекта (soft delete).",
    responses={
        200: {"description": "Проект архивирован"},
        400: {"model": ErrorResponse, "description": "Проект уже архивирован"},
        404: {"model": ErrorResponse, "description": "Проект не найден"},
    },
)
async def archive_project(
    project_id: int, service: ProjectService = Depends(get_project_service)
) -> ProjectResponse:
    """
    Архивировать проект (мягкое удаление).

    Архивированный проект:
    - Не отображается в списке по умолчанию
    - Нельзя добавлять новые задачи
    - Можно восстановить через unarchive

    Пример запроса:
    ```
    POST /projects/1/archive
    ```
    """
    try:
        project = await service.archive_project(project_id)
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# UNARCHIVE PROJECT
# ============================================================================


@router.post(
    "/{project_id}/unarchive",
    response_model=ProjectResponse,
    summary="Восстановить проект из архива",
    responses={
        200: {"description": "Проект восстановлен"},
        400: {"model": ErrorResponse, "description": "Проект не архивирован"},
        404: {"model": ErrorResponse, "description": "Проект не найден"},
    },
)
async def unarchive_project(
    project_id: int, service: ProjectService = Depends(get_project_service)
) -> ProjectResponse:
    """
    Восстановить проект из архива.

    Пример запроса:
    ```
    POST /projects/1/unarchive
    ```
    """
    try:
        project = await service.unarchive_project(project_id)
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# GET PROJECT STATISTICS
# ============================================================================


@router.get(
    "/{project_id}/stats",
    response_model=ProjectWithStats,
    summary="Получить статистику проекта",
    description="""
    Получить статистику по проекту:
    - Общее количество задач
    - Завершённые задачи
    - Задачи в работе
    - Задачи к выполнению
    - Процент выполнения
    """,
    responses={
        200: {"description": "Статистика получена"},
        404: {"model": ErrorResponse, "description": "Проект не найден"},
    },
)
async def get_project_statistics(
    project_id: int, service: ProjectService = Depends(get_project_service)
) -> ProjectWithStats:
    """
    Получить статистику по проекту.

    Пример ответа:
    ```json
    {
        "id": 1,
        "name": "Вайб-Кодинг",
        "total_tasks": 10,
        "completed_tasks": 7,
        "in_progress_tasks": 2,
        "todo_tasks": 1,
        "completion_percentage": 70.0
    }
    ```
    """
    try:
        stats = await service.get_project_statistics(project_id)
        return ProjectWithStats(**stats)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
