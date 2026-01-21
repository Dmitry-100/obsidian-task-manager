"""
API endpoints для работы с тегами.

Теги интегрируются с Obsidian Second Brain.
Автоматическая нормализация названий (lowercase, пробелы → дефисы).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..services import TagService
from .dependencies import get_tag_service
from .schemas import (
    ErrorResponse,
    TagCreate,
    TagResponse,
    TagUpdate,
    TagWithUsage,
)

router = APIRouter(prefix="/tags", tags=["tags"])


# ============================================================================
# GET ALL TAGS
# ============================================================================


@router.get("", response_model=list[TagResponse], summary="Получить все теги")
async def get_tags(service: TagService = Depends(get_tag_service)) -> list[TagResponse]:
    """
    Получить список всех тегов.

    Пример запроса:
    ```
    GET /tags
    ```
    """
    tags = await service.get_all_tags()
    return [TagResponse.model_validate(t) for t in tags]


# ============================================================================
# GET POPULAR TAGS
# ============================================================================


@router.get(
    "/popular",
    response_model=list[TagWithUsage],
    summary="Получить популярные теги",
    description="Получить самые используемые теги с количеством задач.",
)
async def get_popular_tags(
    limit: int = Query(10, ge=1, le=100, description="Количество тегов"),
    service: TagService = Depends(get_tag_service),
) -> list[TagWithUsage]:
    """
    Получить популярные теги.

    Query параметры:
    - limit: int - количество тегов (1-100, по умолчанию 10)

    Пример запроса:
    ```
    GET /tags/popular?limit=5
    ```

    Пример ответа:
    ```json
    [
        {"id": 1, "name": "python", "usage_count": 15},
        {"id": 2, "name": "backend", "usage_count": 12},
        {"id": 3, "name": "api", "usage_count": 10}
    ]
    ```
    """
    tags_with_usage = await service.get_popular_tags(limit)
    return [
        TagWithUsage(id=tag.id, name=tag.name, created_at=tag.created_at, usage_count=count)
        for tag, count in tags_with_usage
    ]


# ============================================================================
# GET UNUSED TAGS
# ============================================================================


@router.get(
    "/unused",
    response_model=list[TagResponse],
    summary="Получить неиспользуемые теги",
    description="Получить теги, не привязанные ни к одной задаче.",
)
async def get_unused_tags(service: TagService = Depends(get_tag_service)) -> list[TagResponse]:
    """
    Получить неиспользуемые теги.

    Полезно для очистки устаревших тегов.

    Пример запроса:
    ```
    GET /tags/unused
    ```
    """
    tags = await service.get_unused_tags()
    return [TagResponse.model_validate(t) for t in tags]


# ============================================================================
# CREATE TAG
# ============================================================================


@router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать тег",
    description="""
    Создать новый тег.

    Название автоматически нормализуется:
    - Приводится к lowercase
    - Пробелы заменяются на дефисы
    - Спецсимволы удаляются

    Примеры:
    - "Python Programming" → "python-programming"
    - "Web Dev" → "web-dev"
    - "C++" → "c"
    """,
    responses={
        201: {"description": "Тег создан"},
        400: {"model": ErrorResponse, "description": "Тег уже существует"},
    },
)
async def create_tag(
    data: TagCreate, service: TagService = Depends(get_tag_service)
) -> TagResponse:
    """
    Создать новый тег.

    Пример запроса:
    ```json
    {
        "name": "Python Programming"
    }
    ```

    Будет создан тег с именем: "python-programming"
    """
    try:
        tag = await service.create_tag(data.name)
        return TagResponse.model_validate(tag)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# GET TAG BY ID
# ============================================================================


@router.get(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Получить тег по ID",
    responses={
        200: {"description": "Тег найден"},
        404: {"model": ErrorResponse, "description": "Тег не найден"},
    },
)
async def get_tag(tag_id: int, service: TagService = Depends(get_tag_service)) -> TagResponse:
    """
    Получить тег по ID.

    Пример запроса:
    ```
    GET /tags/1
    ```
    """
    try:
        tag = await service.get_tag(tag_id)
        return TagResponse.model_validate(tag)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# UPDATE TAG
# ============================================================================


@router.put(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Переименовать тег",
    description="""
    Переименовать тег.

    ВАЖНО: Переименование влияет на ВСЕ задачи с этим тегом!
    """,
    responses={
        200: {"description": "Тег переименован"},
        400: {"model": ErrorResponse, "description": "Новое имя уже существует"},
        404: {"model": ErrorResponse, "description": "Тег не найден"},
    },
)
async def rename_tag(
    tag_id: int, data: TagUpdate, service: TagService = Depends(get_tag_service)
) -> TagResponse:
    """
    Переименовать тег.

    Пример запроса:
    ```json
    {
        "name": "python3"
    }
    ```

    Все задачи с этим тегом получат новое имя.
    """
    try:
        tag = await service.rename_tag(tag_id, data.name)
        return TagResponse.model_validate(tag)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# DELETE TAG
# ============================================================================


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить тег",
    description="""
    Удалить тег.

    По умолчанию нельзя удалить тег, используемый в задачах.
    Используйте force=true для принудительного удаления.
    """,
    responses={
        204: {"description": "Тег удалён"},
        400: {"model": ErrorResponse, "description": "Тег используется в задачах"},
        404: {"model": ErrorResponse, "description": "Тег не найден"},
    },
)
async def delete_tag(
    tag_id: int,
    force: bool = Query(False, description="Принудительное удаление"),
    service: TagService = Depends(get_tag_service),
):
    """
    Удалить тег.

    Query параметры:
    - force: bool - принудительное удаление (с отвязкой от задач)

    Пример запроса:
    ```
    DELETE /tags/1?force=true
    ```
    """
    try:
        await service.delete_tag(tag_id, force=force)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# MERGE TAGS
# ============================================================================


@router.post(
    "/{source_tag_id}/merge/{target_tag_id}",
    response_model=TagResponse,
    summary="Объединить теги",
    description="""
    Объединить два тега в один.

    Все задачи с source_tag получат target_tag.
    Source_tag будет удалён.

    Пример: объединить "python3" и "python"
    - Все задачи с "python3" получат "python"
    - Тег "python3" удалится
    """,
    responses={
        200: {"description": "Теги объединены"},
        400: {"model": ErrorResponse, "description": "Теги одинаковые"},
        404: {"model": ErrorResponse, "description": "Тег не найден"},
    },
)
async def merge_tags(
    source_tag_id: int, target_tag_id: int, service: TagService = Depends(get_tag_service)
) -> TagResponse:
    """
    Объединить два тега.

    Path параметры:
    - source_tag_id: int - ID исходного тега (будет удалён)
    - target_tag_id: int - ID целевого тега (останется)

    Пример запроса:
    ```
    POST /tags/1/merge/2
    ```

    Где 1 - "python3", 2 - "python"
    Результат: все задачи получат "python", "python3" удалится
    """
    try:
        tag = await service.merge_tags(source_tag_id, target_tag_id)
        return TagResponse.model_validate(tag)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# CLEANUP UNUSED TAGS
# ============================================================================


@router.post(
    "/cleanup",
    summary="Удалить все неиспользуемые теги",
    description="Удалить все теги, не привязанные ни к одной задаче.",
)
async def cleanup_unused_tags(service: TagService = Depends(get_tag_service)):
    """
    Удалить все неиспользуемые теги.

    Полезно для очистки БД от устаревших тегов.

    Пример запроса:
    ```
    POST /tags/cleanup
    ```

    Пример ответа:
    ```json
    {
        "deleted_count": 5
    }
    ```
    """
    count = await service.cleanup_unused_tags()
    return {"deleted_count": count}


# ============================================================================
# TAG STATISTICS
# ============================================================================


@router.get(
    "/{tag_id}/stats",
    summary="Получить статистику тега",
    description="""
    Получить статистику по тегу:
    - Общее количество задач
    - Завершённые задачи
    - Задачи в работе
    - Задачи к выполнению
    """,
)
async def get_tag_statistics(tag_id: int, service: TagService = Depends(get_tag_service)):
    """
    Получить статистику по тегу.

    Пример ответа:
    ```json
    {
        "tag_id": 1,
        "tag_name": "python",
        "total_tasks": 15,
        "completed_tasks": 10,
        "in_progress_tasks": 3,
        "todo_tasks": 2
    }
    ```
    """
    try:
        stats = await service.get_tag_statistics(tag_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
