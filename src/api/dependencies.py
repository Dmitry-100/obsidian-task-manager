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

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AsyncSessionLocal
from ..services import ProjectService, TaskService, TagService


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

async def get_project_service(
    db: AsyncSession = Depends(get_db)
) -> ProjectService:
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


async def get_task_service(
    db: AsyncSession = Depends(get_db)
) -> TaskService:
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


async def get_tag_service(
    db: AsyncSession = Depends(get_db)
) -> TagService:
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
