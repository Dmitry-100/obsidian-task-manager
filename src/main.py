"""
Главный файл FastAPI приложения.

Точка входа в приложение Obsidian Task Manager.

Запуск:
    uvicorn src.main:app --reload

API документация:
    http://localhost:8000/docs       - Swagger UI
    http://localhost:8000/redoc      - ReDoc
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api import projects_router, tasks_router, tags_router
from .api.errors import register_error_handlers


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
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


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
# INCLUDE ROUTERS
# ============================================================================

# Подключаем роутеры для каждого ресурса
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(tags_router)

# Регистрируем обработчики ошибок для единого формата
register_error_handlers(app)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get(
    "/",
    tags=["root"],
    summary="Root endpoint",
    description="Информация о API"
)
async def root():
    """
    Корневой endpoint.

    Возвращает информацию о API и полезные ссылки.
    """
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "endpoints": {
            "projects": "/projects",
            "tasks": "/tasks",
            "tags": "/tags",
        },
        "description": "Task Manager для Obsidian Second Brain"
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Проверка работоспособности API"
)
async def health_check():
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
        "database": "not_checked"  # можно добавить проверку
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
    print(f"📚 Docs: http://localhost:8000/docs")
    print(f"📖 ReDoc: http://localhost:8000/redoc")


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
