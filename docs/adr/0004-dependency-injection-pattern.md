# ADR 0004: Dependency Injection Pattern

## Status
Accepted

## Context
В FastAPI endpoints нужно получать доступ к:
- Database session
- Service instances (ProjectService, TaskService, TagService)

Проблемы без DI:
- Каждый endpoint создаёт сессию вручную
- Boilerplate код управления транзакциями в каждом endpoint
- Сложно тестировать (нельзя подменить зависимости)
- Ответственность за lifecycle разбросана по коду

## Decision
Использовать **Dependency Injection** через FastAPI `Depends()`:

```python
# Dependencies
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)

# API Endpoint
@router.post("/projects")
async def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service)
):
    project = await service.create_project(...)
    return ProjectResponse.model_validate(project)
```

## Alternatives Considered

1. **Manual Session Management в каждом endpoint**:
   ```python
   @router.post("/projects")
   async def create_project(data: ProjectCreate):
       async with AsyncSessionLocal() as db:
           try:
               service = ProjectService(db)
               project = await service.create_project(...)
               await db.commit()
               return project
           except:
               await db.rollback()
               raise
   ```
   - Отклонено: много boilerplate, трудно тестировать

2. **Global Service Instances**:
   ```python
   project_service = ProjectService(global_db)
   ```
   - Отклонено: проблемы с async, lifecycle, тестированием

3. **Context Manager в каждом endpoint**:
   - Отклонено: дублирование кода, сложность

4. **Service Locator Pattern**:
   - Отклонено: скрытые зависимости, сложность тестирования

## Consequences

### Positive
- ✅ **Clean Code**: endpoints становятся тонкими и читаемыми
- ✅ **Testability**: легко подменить зависимости в тестах
- ✅ **Lifecycle Management**: FastAPI автоматически управляет созданием/закрытием
- ✅ **Centralized Transaction Management**: commit/rollback в одном месте
- ✅ **Type Safety**: IDE подсказывает типы зависимостей
- ✅ **Reusability**: одна dependency используется во многих endpoints
- ✅ **Dependency Chain**: `get_project_service` автоматически получает `get_db`

### Negative
- ❌ **Magic**: новичкам непонятно, откуда берутся аргументы
- ❌ **Debugging**: сложнее отследить создание зависимостей
- ❌ **FastAPI Coupling**: зависимость от фреймворка

### Neutral
- 🔄 **Testing**: нужно использовать `app.dependency_overrides` для подмены зависимостей
- 🔄 **Async**: все dependencies должны быть async для правильной работы

## Examples

### Database Dependency
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Создаёт сессию БД для request.
    Автоматически:
    - Создаёт сессию
    - Делает commit() при успехе
    - Делает rollback() при ошибке
    - Закрывает сессию
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commit если endpoint успешен
        except Exception:
            await session.rollback()  # Rollback при ошибке
            raise
        finally:
            await session.close()  # Всегда закрыть
```

### Service Dependency Chain
```python
# get_project_service зависит от get_db
async def get_project_service(
    db: AsyncSession = Depends(get_db)
) -> ProjectService:
    return ProjectService(db)

# Endpoint автоматически получит и db, и service
@router.post("/projects")
async def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service)
    # FastAPI автоматически:
    # 1. Вызовет get_db()
    # 2. Передаст db в get_project_service()
    # 3. Передаст service в endpoint
):
    project = await service.create_project(...)
    return project
```

### Testing with Dependency Override
```python
# Test
def test_create_project():
    # Mock service
    mock_service = MockProjectService()

    # Override dependency
    app.dependency_overrides[get_project_service] = lambda: mock_service

    # Test endpoint
    response = client.post("/projects", json={"name": "Test"})
    assert response.status_code == 201
```

## Dependency Lifecycle

```
Request arrives
    ↓
FastAPI calls get_db()
    ↓
Session created (async with AsyncSessionLocal())
    ↓
FastAPI calls get_project_service(db)
    ↓
ProjectService(db) created
    ↓
Endpoint executes
    ↓
If success: session.commit()
If error: session.rollback()
    ↓
session.close()
    ↓
Response sent
```

## Benefits over Manual Management

### Before (Manual)
```python
@router.post("/projects")
async def create_project(data: ProjectCreate):
    async with AsyncSessionLocal() as db:  # 5 lines
        try:
            service = ProjectService(db)
            project = await service.create_project(...)
            await db.commit()
            return project
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()
```

### After (DI)
```python
@router.post("/projects")
async def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service)
):  # 2 lines
    project = await service.create_project(...)
    return project
```

## Related ADRs
- ADR-0001: Three-Layer Architecture - DI связывает слои
- ADR-0007: Transaction Management - commit/rollback в get_db()

## Notes
Dependency Injection - один из ключевых паттернов FastAPI. Он делает код чище и позволяет легко тестировать endpoints через подмену зависимостей.
