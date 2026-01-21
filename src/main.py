"""
Главный файл FastAPI приложения.

Точка входа в приложение Obsidian Task Manager.

Запуск:
    uvicorn src.main:app --reload

API документация:
    http://localhost:8000/docs       - Swagger UI
    http://localhost:8000/redoc      - ReDoc

Версионирование:
    API доступно по путям /api/v1/...
    Старые пути (/projects, /tasks, /tags) также поддерживаются для обратной совместимости.
"""

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .api import projects_router, tags_router, tasks_router
from .api.dependencies import verify_api_key
from .api.errors import register_error_handlers
from .core.config import settings

# ============================================================================
# RATE LIMITER SETUP
# ============================================================================

# Создаём rate limiter
# key_func определяет по какому ключу группировать запросы (по IP адресу)
limiter = Limiter(key_func=get_remote_address)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Кастомный обработчик превышения лимита запросов.

    Возвращает ошибку в едином формате ErrorResponse.
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Слишком много запросов. Лимит: {exc.detail}",
                "details": [{"field": "rate_limit", "message": str(exc.detail)}],
            }
        },
    )


# ============================================================================
# CREATE APPLICATION
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    Task Manager для интеграции с Obsidian Second Brain.

    ## Возможности

    * **Проекты** - организация задач по проектам
    * **Задачи** - создание задач с подзадачами (иерархия)
    * **Теги** - категоризация через теги (интеграция с Obsidian)
    * **Комментарии** - добавление комментариев к задачам (Markdown)
    * **Связь с Obsidian** - интеграция с файлами и тегами Obsidian

    ## 3-Layer Architecture

    ```
    API Layer (FastAPI) → Service Layer (Business Logic) → Repository Layer (Database)
    ```

    ## Модель данных

    ```
    Projects → Tasks (с подзадачами) → Comments
                ↓
              Tags (M:M)
    ```

    ## Версионирование

    API версия 1 доступна по пути `/api/v1/`.
    Примеры: `/api/v1/projects`, `/api/v1/tasks`, `/api/v1/tags`

    ## Rate Limiting

    API защищено от злоупотреблений:
    - **100 запросов/минуту** для обычных endpoints
    - При превышении лимита вернётся ошибка 429 Too Many Requests
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Подключаем rate limiter к приложению
app.state.limiter = limiter
# slowapi handler имеет специфичный тип, но работает корректно
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)  # type: ignore[arg-type]


# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

# Разрешаем CORS для веб-интерфейса (будет создан позже)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API VERSIONING
# ============================================================================

# Создаём роутер для API v1
api_v1_router = APIRouter(prefix="/api/v1")

# Добавляем все ресурсные роутеры в v1
api_v1_router.include_router(projects_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(tags_router)


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

# Подключаем версионированный API (/api/v1/...)
# dependencies=[Depends(verify_api_key)] - все endpoints роутера требуют авторизации
app.include_router(api_v1_router, dependencies=[Depends(verify_api_key)])

# Для обратной совместимости оставляем старые пути без /api/v1
# В будущем можно убрать (deprecated)
app.include_router(
    projects_router,
    dependencies=[Depends(verify_api_key)],
    deprecated=True,  # Помечаем как deprecated в документации
)
app.include_router(tasks_router, dependencies=[Depends(verify_api_key)], deprecated=True)
app.include_router(tags_router, dependencies=[Depends(verify_api_key)], deprecated=True)

# Регистрируем обработчики ошибок для единого формата
register_error_handlers(app)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================


@app.get("/", tags=["root"], summary="Root endpoint", description="Информация о API")
@limiter.limit("100/minute")
async def root(request: Request):
    """
    Корневой endpoint.

    Возвращает информацию о API и полезные ссылки.
    """
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "api_version": "v1",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "endpoints": {
            "projects": "/api/v1/projects",
            "tasks": "/api/v1/tasks",
            "tags": "/api/v1/tags",
        },
        "deprecated_endpoints": {
            "projects": "/projects (use /api/v1/projects)",
            "tasks": "/tasks (use /api/v1/tasks)",
            "tags": "/tags (use /api/v1/tags)",
        },
        "rate_limit": "100 requests/minute",
        "description": "Task Manager для Obsidian Second Brain",
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================


@app.get(
    "/health", tags=["health"], summary="Health check", description="Проверка работоспособности API"
)
@limiter.limit("100/minute")
async def health_check(request: Request):
    """
    Health check endpoint.

    Используется для мониторинга и проверки доступности API.

    Пример ответа:
    ```json
    {
        "status": "healthy",
        "database": "connected"
    }
    ```
    """
    # TODO: Добавить проверку подключения к БД
    return {
        "status": "healthy",
        "database": "not_checked",  # можно добавить проверку
        "rate_limit": "100/minute",
    }


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """
    Событие при запуске приложения.

    Здесь можно:
    - Инициализировать БД
    - Загрузить кэши
    - Установить соединения
    """
    print(f"🚀 {settings.APP_NAME} started!")
    print("📚 Docs: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("🔒 Rate Limit: 100 requests/minute")
    print("📦 API v1: http://localhost:8000/api/v1/")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Событие при остановке приложения.

    Здесь можно:
    - Закрыть соединения с БД
    - Сохранить кэши
    - Освободить ресурсы
    """
    print(f"👋 {settings.APP_NAME} stopped!")


# ============================================================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ============================================================================

"""
Запуск приложения:

1. Активировать виртуальное окружение:
   ```bash
   source venv/bin/activate
   ```

2. Запустить сервер:
   ```bash
   uvicorn src.main:app --reload
   ```

3. Открыть в браузере:
   - API docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

4. Попробовать endpoints:
   ```bash
   # Создать проект
   curl -X POST http://localhost:8000/projects \\
     -H "Content-Type: application/json" \\
     -d '{"name": "Тестовый проект", "color": "#3B82F6"}'

   # Получить все проекты
   curl http://localhost:8000/projects

   # Создать задачу
   curl -X POST http://localhost:8000/tasks \\
     -H "Content-Type: application/json" \\
     -d '{
       "title": "Моя первая задача",
       "project_id": 1,
       "tag_names": ["python", "backend"]
     }'

   # Получить задачи проекта
   curl http://localhost:8000/tasks/by-project/1
   ```
"""
