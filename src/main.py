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

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from .api import projects_router, sync_router, tags_router, tasks_router
from .api.dependencies import verify_api_key
from .api.errors import register_error_handlers
from .api.middleware import RequestLoggingMiddleware
from .core.config import settings
from .core.database import AsyncSessionLocal
from .core.logging import get_logger, setup_logging

# Инициализируем логирование при импорте модуля
# LOG_LEVEL: DEBUG/INFO/WARNING/ERROR - что логировать
# LOG_FORMAT: json (production) / simple (development)
setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

# Создаём логгер для этого модуля
logger = get_logger(__name__)

# ============================================================================
# APPLICATION METADATA
# ============================================================================

APP_VERSION = "1.0.0"
APP_START_TIME: float = 0.0  # Will be set on startup

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
# LIFESPAN EVENT HANDLER
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for startup/shutdown events.

    Startup: инициализация ресурсов
    Shutdown: освобождение ресурсов
    """
    global APP_START_TIME

    # Startup
    APP_START_TIME = time.time()

    # Логируем запуск приложения (структурированно)
    logger.info(
        "Application started",
        extra={
            "app_name": settings.APP_NAME,
            "version": APP_VERSION,
            "debug": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
        },
    )

    # Также выводим в консоль для удобства разработки
    print(f"🚀 {settings.APP_NAME} v{APP_VERSION} started!")
    print("📚 Docs: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("🔒 Rate Limit: 100 requests/minute")
    print("📦 API v1: http://localhost:8000/api/v1/")

    yield  # Application runs here

    # Shutdown
    uptime = int(time.time() - APP_START_TIME)
    logger.info("Application stopped", extra={"uptime_seconds": uptime})
    print(f"👋 {settings.APP_NAME} stopped! (uptime: {uptime}s)")


# ============================================================================
# CREATE APPLICATION
# ============================================================================

app = FastAPI(
    lifespan=lifespan,
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
    version=APP_VERSION,
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

# Добавляем middleware для логирования HTTP запросов
# Каждый запрос будет залогирован с методом, путём, статусом и временем
app.add_middleware(RequestLoggingMiddleware)


# ============================================================================
# API VERSIONING
# ============================================================================

# Создаём роутер для API v1
api_v1_router = APIRouter(prefix="/api/v1")

# Добавляем все ресурсные роутеры в v1
api_v1_router.include_router(projects_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(tags_router)
api_v1_router.include_router(sync_router)


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
        "version": APP_VERSION,
        "api_version": "v1",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "endpoints": {
            "projects": "/api/v1/projects",
            "tasks": "/api/v1/tasks",
            "tags": "/api/v1/tags",
            "sync": "/api/v1/sync",
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
    Проверяет подключение к базе данных.

    Пример ответа (200 OK):
    ```json
    {
        "status": "ok",
        "checks": {
            "database": "connected",
            "version": "1.0.0",
            "uptime_seconds": 3600
        },
        "timestamp": "2026-01-22T12:00:00Z"
    }
    ```

    Пример ответа (503 Service Unavailable):
    ```json
    {
        "status": "error",
        "checks": {
            "database": "disconnected",
            "version": "1.0.0",
            "uptime_seconds": 3600
        },
        "timestamp": "2026-01-22T12:00:00Z"
    }
    ```
    """
    from fastapi.responses import JSONResponse

    # Calculate uptime
    uptime_seconds = int(time.time() - APP_START_TIME) if APP_START_TIME > 0 else 0

    # Check database connection
    db_status = "disconnected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Build response
    checks = {
        "database": db_status,
        "version": APP_VERSION,
        "uptime_seconds": uptime_seconds,
    }

    timestamp = datetime.now(UTC).isoformat()
    overall_status = "ok" if db_status == "connected" else "error"
    status_code = 200 if overall_status == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "checks": checks,
            "timestamp": timestamp,
        },
    )


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
