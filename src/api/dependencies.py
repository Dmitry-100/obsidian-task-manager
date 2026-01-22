"""
Dependencies для FastAPI endpoints.

Dependency Injection (DI) - паттерн для автоматического предоставления зависимостей.

Вместо того чтобы создавать сервисы вручную в каждом endpoint:
    async def create_project(...):
        async with AsyncSessionLocal() as db:
            service = ProjectService(db)
            ...

Мы используем FastAPI Depends():
    async def create_project(
        service: ProjectService = Depends(get_project_service)
    ):
        # service уже создан и готов к использованию!
        ...

Преимущества:
1. Меньше boilerplate кода
2. Автоматическое управление жизненным циклом (создание/закрытие БД)
3. Легко тестировать (можем заменить на mock)
4. Единообразие во всех endpoints
"""

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import AsyncSessionLocal
from ..services import ProjectService, SyncService, TagService, TaskService

# ============================================================================
# API KEY AUTHENTICATION
# ============================================================================

# Определяем схему авторизации для Swagger UI
# name="X-API-Key" - название заголовка, который клиент должен отправить
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,  # Не выбрасывать ошибку автоматически, мы сами обработаем
    description="API ключ для авторизации. Передавайте в заголовке X-API-Key",
)


async def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    """
    Dependency для проверки API ключа.

    Как работает:
    1. Клиент отправляет запрос с заголовком X-API-Key
    2. FastAPI извлекает значение через api_key_header
    3. Мы сравниваем с ключом из настроек
    4. Если не совпадает - возвращаем 401 Unauthorized

    Использование:
        @app.get("/protected")
        async def protected_endpoint(
            api_key: str = Depends(verify_api_key)
        ):
            # Этот код выполнится только если ключ верный
            return {"message": "Вы авторизованы!"}

    Пример запроса:
        curl -H "X-API-Key: your-secret-key" http://localhost:8000/projects
    """
    # Если ключ не передан
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing. Add header: X-API-Key: your-key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Если ключ неверный
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Ключ верный - возвращаем его (можно использовать для логирования)
    return api_key


# ============================================================================
# DATABASE SESSION DEPENDENCY
# ============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии БД.

    Автоматически:
    1. Создаёт сессию
    2. Передаёт в endpoint
    3. Делает commit() при успехе
    4. Делает rollback() при ошибке
    5. Закрывает сессию

    Использование:
        @app.get("/projects")
        async def get_projects(db: AsyncSession = Depends(get_db)):
            # db готова к использованию
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Если endpoint выполнился успешно - commit
            await session.commit()
        except Exception:
            # Если была ошибка - rollback
            await session.rollback()
            raise
        finally:
            # В любом случае закрыть сессию
            await session.close()


# ============================================================================
# SERVICE DEPENDENCIES
# ============================================================================


async def get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    """
    Dependency для ProjectService.

    Автоматически создаёт сервис с БД сессией.

    Использование:
        @app.post("/projects")
        async def create_project(
            service: ProjectService = Depends(get_project_service)
        ):
            # service готов к использованию
            project = await service.create_project(...)
            return project

    Цепочка зависимостей:
        get_project_service зависит от get_db
        → FastAPI автоматически вызовет get_db()
        → Передаст сессию в get_project_service()
        → Вернёт ProjectService в endpoint
    """
    return ProjectService(db)


async def get_task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
    """
    Dependency для TaskService.

    Использование:
        @app.post("/tasks")
        async def create_task(
            service: TaskService = Depends(get_task_service)
        ):
            ...
    """
    return TaskService(db)


async def get_tag_service(db: AsyncSession = Depends(get_db)) -> TagService:
    """
    Dependency для TagService.

    Использование:
        @app.get("/tags")
        async def get_tags(
            service: TagService = Depends(get_tag_service)
        ):
            ...
    """
    return TagService(db)


async def get_sync_service(db: AsyncSession = Depends(get_db)) -> SyncService:
    """
    Dependency для SyncService.

    Использование:
        @app.post("/sync/import")
        async def import_from_obsidian(
            service: SyncService = Depends(get_sync_service)
        ):
            ...
    """
    from ..integrations.obsidian.project_resolver import get_config

    config = get_config()
    return SyncService(db, config)


# ============================================================================
# ПРИМЕР: КАК ЭТО РАБОТАЕТ
# ============================================================================

"""
БЕЗ Dependency Injection (verbose):

@app.post("/projects")
async def create_project(data: ProjectCreate):
    async with AsyncSessionLocal() as db:
        try:
            service = ProjectService(db)
            project = await service.create_project(
                name=data.name,
                description=data.description,
                color=data.color
            )
            await db.commit()
            return project
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            await db.close()

---

С Dependency Injection (clean):

@app.post("/projects")
async def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service)  # ← магия!
):
    try:
        project = await service.create_project(
            name=data.name,
            description=data.description,
            color=data.color
        )
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Вся логика управления БД скрыта в get_db()!
"""
