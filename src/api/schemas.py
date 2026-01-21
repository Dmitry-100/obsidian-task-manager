"""
Pydantic схемы для API.

DTOs (Data Transfer Objects) - объекты для передачи данных через HTTP.

Зачем отдельные схемы от моделей SQLAlchemy?
1. Контроль над тем, что видит клиент (можем скрыть поля)
2. Валидация входящих данных
3. Разделение concerns (API ≠ Database)
4. Версионирование API (можем менять схемы без изменения БД)
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from ..models import TaskStatus, TaskPriority


# ============================================================================
# PROJECT SCHEMAS
# ============================================================================

class ProjectBase(BaseModel):
    """Базовые поля проекта (общие для Create и Update)."""
    name: str = Field(..., min_length=1, max_length=200, description="Название проекта")
    description: Optional[str] = Field(None, description="Описание проекта")
    obsidian_folder: Optional[str] = Field(None, max_length=500, description="Путь к папке в Obsidian")
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="Цвет в формате #RRGGBB")


class ProjectCreate(ProjectBase):
    """
    Схема для создания проекта (POST /projects).

    Пример запроса:
    {
        "name": "Вайб-Кодинг",
        "description": "Учебный проект",
        "color": "#3B82F6"
    }
    """
    pass


class ProjectUpdate(BaseModel):
    """
    Схема для обновления проекта (PUT /projects/{id}).

    Все поля опциональные (частичное обновление).

    Пример запроса:
    {
        "name": "Новое название",
        "color": "#FF0000"
    }
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    obsidian_folder: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')


class ProjectResponse(ProjectBase):
    """
    Схема для ответа API (GET /projects/{id}).

    Включает дополнительные поля из БД:
    - id
    - is_archived
    - created_at, updated_at

    Пример ответа:
    {
        "id": 1,
        "name": "Вайб-Кодинг",
        "description": "Учебный проект",
        "color": "#3B82F6",
        "is_archived": false,
        "created_at": "2026-01-18T12:00:00",
        "updated_at": "2026-01-18T12:00:00"
    }
    """
    id: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    # Конфигурация Pydantic v2
    model_config = ConfigDict(from_attributes=True)
    # from_attributes=True позволяет создавать схему из SQLAlchemy модели:
    # ProjectResponse.model_validate(project_model)


class ProjectWithStats(ProjectResponse):
    """
    Расширенная схема проекта со статистикой.

    Используется для GET /projects/{id}/stats
    """
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    completion_percentage: float


# ============================================================================
# TASK SCHEMAS
# ============================================================================

class TaskBase(BaseModel):
    """Базовые поля задачи."""
    title: str = Field(..., min_length=1, max_length=300, description="Название задачи")
    description: Optional[str] = Field(None, description="Описание задачи")
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Статус задачи")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Приоритет")
    due_date: Optional[date] = Field(None, description="Дедлайн")
    obsidian_path: Optional[str] = Field(None, max_length=1000, description="Путь к файлу в Obsidian")
    estimated_hours: Optional[float] = Field(None, gt=0, description="Оценка времени (часы)")


class TaskCreate(TaskBase):
    """
    Схема для создания задачи (POST /tasks).

    Дополнительные поля:
    - project_id (обязательно)
    - parent_task_id (для подзадач)
    - tag_names (список тегов)

    Пример запроса:
    {
        "title": "Создать API",
        "project_id": 1,
        "priority": "high",
        "due_date": "2026-01-25",
        "tag_names": ["python", "fastapi", "backend"]
    }
    """
    project_id: int = Field(..., description="ID проекта")
    parent_task_id: Optional[int] = Field(None, description="ID родительской задачи (для подзадач)")
    tag_names: Optional[List[str]] = Field(default=[], description="Список названий тегов")


class TaskUpdate(BaseModel):
    """
    Схема для обновления задачи (PUT /tasks/{id}).

    Все поля опциональные.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, gt=0)


class TagResponse(BaseModel):
    """
    Схема для тега в ответе.

    Используется внутри TaskResponse.
    """
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(BaseModel):
    """
    Схема для комментария в ответе.

    Используется внутри TaskResponse.
    """
    id: int
    task_id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskResponse(TaskBase):
    """
    Схема для ответа API (GET /tasks/{id}).

    Включает:
    - Все поля задачи
    - Связанные объекты (теги, проект)
    - Метаданные (id, timestamps)
    """
    id: int
    project_id: int
    parent_task_id: Optional[int]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Связанные объекты (опционально загружаются)
    tags: List[TagResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TaskDetailResponse(TaskResponse):
    """
    Детальная схема задачи со ВСЕМИ связями.

    Используется для GET /tasks/{id} (с expand=true)

    Включает:
    - Комментарии
    - Подзадачи
    - Информацию о проекте
    """
    comments: List[CommentResponse] = []
    # subtasks можно добавить, если нужно


# ============================================================================
# TAG SCHEMAS
# ============================================================================

class TagCreate(BaseModel):
    """
    Схема для создания тега (POST /tags).

    Пример:
    {
        "name": "Python Programming"
    }

    Будет нормализовано в: "python-programming"
    """
    name: str = Field(..., min_length=1, max_length=50, description="Название тега")


class TagUpdate(BaseModel):
    """Схема для обновления тега."""
    name: str = Field(..., min_length=1, max_length=50)


class TagWithUsage(TagResponse):
    """
    Тег с количеством использований.

    Используется для GET /tags/popular
    """
    usage_count: int = Field(..., description="Количество задач с этим тегом")


# ============================================================================
# COMMENT SCHEMAS
# ============================================================================

class CommentCreate(BaseModel):
    """
    Схема для создания комментария (POST /tasks/{task_id}/comments).

    Пример:
    {
        "content": "Нашёл баг в авторизации"
    }
    """
    content: str = Field(..., min_length=1, description="Содержимое комментария (Markdown)")


# ============================================================================
# COMMON SCHEMAS
# ============================================================================

class ErrorDetail(BaseModel):
    """
    Детали ошибки для конкретного поля.

    Используется когда ошибка связана с конкретным полем запроса.

    Пример:
    {
        "field": "email",
        "message": "Некорректный формат email"
    }
    """
    field: str = Field(..., description="Название поля с ошибкой")
    message: str = Field(..., description="Описание ошибки")


class ErrorBody(BaseModel):
    """
    Тело ошибки с кодом и деталями.

    Структурированный формат позволяет клиенту:
    1. Определить тип ошибки по code
    2. Показать пользователю message
    3. Подсветить проблемные поля из details

    Примеры кодов:
    - VALIDATION_ERROR: ошибка валидации полей
    - NOT_FOUND: ресурс не найден
    - ALREADY_EXISTS: ресурс уже существует
    - INTERNAL_ERROR: внутренняя ошибка сервера
    """
    code: str = Field(..., description="Код ошибки (VALIDATION_ERROR, NOT_FOUND, etc.)")
    message: str = Field(..., description="Человекочитаемое сообщение")
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="Список ошибок по полям (для валидации)"
    )


class ErrorResponse(BaseModel):
    """
    Единый формат ответа для всех ошибок API.

    Пример ошибки валидации:
    {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Ошибка валидации входных данных",
            "details": [
                {"field": "name", "message": "Название не может быть пустым"},
                {"field": "email", "message": "Некорректный формат email"}
            ]
        }
    }

    Пример ошибки "не найдено":
    {
        "error": {
            "code": "NOT_FOUND",
            "message": "Проект с id=999 не найден",
            "details": null
        }
    }
    """
    error: ErrorBody


# Для обратной совместимости оставляем старый формат
class SimpleErrorResponse(BaseModel):
    """
    Простой формат ошибки (для обратной совместимости).

    Пример:
    {
        "detail": "Project not found"
    }
    """
    detail: str


class SuccessResponse(BaseModel):
    """
    Схема для успешных операций без возврата данных.

    Пример:
    {
        "message": "Project archived successfully"
    }
    """
    message: str


class PaginatedResponse(BaseModel):
    """
    Схема для пагинированных ответов.

    Generic схема для списков с пагинацией.
    """
    items: List  # Список элементов (любого типа)
    total: int  # Всего элементов
    skip: int  # Пропущено
    limit: int  # Лимит на странице
