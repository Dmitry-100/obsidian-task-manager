# ADR 0012: Fully Async Architecture

## Status
Accepted

## Context
Python поддерживает два подхода к I/O операциям:
- **Synchronous**: блокирующие операции (традиционный подход)
- **Asynchronous**: неблокирующие операции с async/await

Для веб-приложения с I/O операциями (БД, HTTP) выбор async/sync критически важен для производительности.

## Decision
Использовать **полностью асинхронный стек**:

```python
# FastAPI - async endpoints
@router.post("/tasks")
async def create_task(
    data: TaskCreate,
    service: TaskService = Depends(get_task_service)
):
    task = await service.create_task(...)  # async
    return task

# Service - async methods
class TaskService:
    async def create_task(self, title: str, ...) -> Task:
        task = await self.task_repo.create(Task(...))  # async
        return task

# Repository - async methods
class TaskRepository:
    async def create(self, task: Task) -> Task:
        self.db.add(task)
        await self.db.flush()  # async
        return task

# SQLAlchemy - async engine
engine = create_async_engine(DATABASE_URL)
```

**async/await везде**: API → Service → Repository → Database

## Alternatives Considered

### 1. Synchronous Stack
```python
# Sync FastAPI
@app.post("/tasks")
def create_task(data: TaskCreate):  # No async
    task = service.create_task(...)  # Blocking
    return task

# Sync SQLAlchemy
engine = create_engine(DATABASE_URL)  # Sync
session = Session(engine)
```
**Отклонено**:
- ❌ Блокирует event loop
- ❌ Плохая производительность для I/O bound операций
- ❌ Не использует преимущества FastAPI
- ❌ Масштабируется хуже

### 2. Mixed Async/Sync
```python
# Async endpoint
@app.post("/tasks")
async def create_task(data: TaskCreate):
    # Sync service (блокирует!)
    task = service.create_task(...)  # ❌ Blocking in async
    return task
```
**Отклонено**:
- ❌ Sync код блокирует async event loop
- ❌ Нужен run_in_executor для sync кода
- ❌ Путаница между async/sync
- ❌ Сложность отладки

### 3. Threading вместо Async
```python
# Sync код с threading
with ThreadPoolExecutor() as executor:
    results = executor.map(create_task, tasks)
```
**Отклонено**:
- ❌ Больше overhead чем async
- ❌ GIL ограничивает производительность
- ❌ Сложнее управлять state
- ❌ Async более pythonic для I/O

## Consequences

### Positive
- ✅ **High Throughput**: тысячи concurrent requests
- ✅ **Non-blocking I/O**: не блокируем event loop
- ✅ **Scalability**: один процесс обрабатывает много запросов
- ✅ **Resource Efficient**: меньше памяти чем threading
- ✅ **Modern Python**: использует async/await (Python 3.7+)
- ✅ **FastAPI Native**: FastAPI оптимизирован для async

### Negative
- ❌ **Learning Curve**: нужно понимать async/await
- ❌ **Debugging**: сложнее отлаживать async код
- ❌ **Async All The Way**: нельзя использовать sync libraries
- ❌ **Greenlet Issues**: специфичные ошибки async SQLAlchemy

### Neutral
- 🔄 **ASGI Required**: нужен ASGI сервер (Uvicorn, Hypercorn)
- 🔄 **Async Libraries**: нужны async версии библиотек (asyncpg, httpx)

## How Async Works

### Synchronous (blocking)
```python
def get_tasks():
    # Request 1
    task1 = db.query(Task).first()  # Блокирует 100ms
    # Request 2 ждёт!

    # Request 2
    task2 = db.query(Task).first()  # Блокирует 100ms
    # Request 3 ждёт!

    # Total: 200ms для 2 requests
```

### Asynchronous (non-blocking)
```python
async def get_tasks():
    # Request 1 starts
    task1 = await db.execute(select(Task))  # Starts, switches context

    # While waiting for DB, handle Request 2
    task2 = await db.execute(select(Task))  # Concurrent!

    # Total: ~100ms для 2 requests (parallel DB queries)
```

## Async Stack Components

### 1. FastAPI (Async Web Framework)
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/tasks")
async def get_tasks():  # async def
    tasks = await task_service.get_all()  # await
    return tasks
```

### 2. SQLAlchemy Async (Database)
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

engine = create_async_engine("postgresql+asyncpg://...")

async def get_task(db: AsyncSession, task_id: int):
    result = await db.execute(  # await
        select(Task).where(Task.id == task_id)
    )
    return result.scalar_one_or_none()
```

### 3. Uvicorn (ASGI Server)
```bash
# ASGI server for async
uvicorn src.main:app --reload
```

### 4. asyncpg / aiosqlite (Async DB Drivers)
```python
# PostgreSQL
pip install asyncpg

# SQLite
pip install aiosqlite
```

## Performance Comparison

### Scenario: 100 concurrent requests, each with 100ms DB query

#### Synchronous (blocking)
```
Thread pool: 10 workers
Time = (100 requests / 10 workers) * 100ms = 1000ms
```

#### Asynchronous (non-blocking)
```
Event loop: 1 process
Time = 100ms (все запросы параллельно)
```

**Async wins**: 10x faster для I/O bound операций

## Async Patterns in Code

### API Layer
```python
@router.post("/projects", response_model=ProjectResponse)
async def create_project(  # async def
    data: ProjectCreate,
    service: ProjectService = Depends(get_project_service)
):
    project = await service.create_project(  # await
        name=data.name,
        color=data.color
    )
    return ProjectResponse.model_validate(project)
```

### Service Layer
```python
class TaskService:
    async def create_task(self, title: str, ...) -> Task:  # async def
        # Async operations
        project = await self.project_repo.get_by_id(project_id)  # await
        task = await self.task_repo.create(Task(...))  # await
        tags = await self.tag_repo.bulk_get_or_create(tag_names)  # await

        await self.db.flush()  # await
        return task
```

### Repository Layer
```python
class TaskRepository(BaseRepository[Task]):
    async def get_by_id(self, id: int) -> Optional[Task]:  # async def
        result = await self.db.execute(  # await
            select(Task).where(Task.id == id)
        )
        return result.scalar_one_or_none()
```

### Dependency Injection
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:  # async def
    async with AsyncSessionLocal() as session:  # async with
        try:
            yield session
            await session.commit()  # await
        except Exception:
            await session.rollback()  # await
            raise
        finally:
            await session.close()  # await
```

## Common Async Pitfalls

### Pitfall 1: Забыть await
```python
# ❌ Wrong - forgot await
async def get_task(task_id: int):
    task = task_repo.get_by_id(task_id)  # Returns coroutine, not Task!
    return task

# ✅ Correct
async def get_task(task_id: int):
    task = await task_repo.get_by_id(task_id)  # Actually execute
    return task
```

### Pitfall 2: Sync код в async
```python
# ❌ Wrong - blocking operation
async def process_tasks():
    tasks = await task_repo.get_all()
    for task in tasks:
        time.sleep(1)  # ❌ Blocks event loop!

# ✅ Correct
async def process_tasks():
    tasks = await task_repo.get_all()
    for task in tasks:
        await asyncio.sleep(1)  # ✅ Non-blocking
```

### Pitfall 3: Неправильный event loop
```python
# ❌ Wrong - can't use asyncio.run in async function
async def main():
    result = asyncio.run(some_async_func())  # Error!

# ✅ Correct
async def main():
    result = await some_async_func()
```

### Pitfall 4: Lazy loading в async SQLAlchemy
```python
# ❌ Wrong - lazy load triggers outside async context
task = await task_repo.get_by_id(1)
print(task.tags)  # Greenlet error!

# ✅ Correct - eager load
result = await db.execute(
    select(Task).options(selectinload(Task.tags)).where(Task.id == 1)
)
task = result.scalar_one()
print(task.tags)  # OK
```

## When to Use Async

### Good Use Cases (I/O Bound)
- ✅ Web APIs (HTTP requests/responses)
- ✅ Database queries
- ✅ File I/O
- ✅ External API calls
- ✅ WebSockets

### Bad Use Cases (CPU Bound)
- ❌ Heavy computations
- ❌ Image/video processing
- ❌ Machine learning inference
- ❌ Cryptography

**For CPU-bound**: use multiprocessing, not async

## Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_create_task():
    # Async test
    service = TaskService(mock_db)
    task = await service.create_task(title="Test")  # await
    assert task.title == "Test"
```

## Async Libraries Used

```python
# Web framework
fastapi  # Async web framework

# Database
sqlalchemy[asyncio]  # Async ORM
asyncpg  # PostgreSQL async driver
aiosqlite  # SQLite async driver

# Server
uvicorn[standard]  # ASGI server

# Testing
pytest-asyncio  # Async test support
```

## Related ADRs
- ADR-0005: FastAPI Framework - async native
- ADR-0008: SQLAlchemy 2.0 Async
- ADR-0007: Transaction Management

## Notes
Async архитектура - фундаментальное решение проекта. Это делает приложение:
- Быстрым для I/O операций
- Scalable для множества concurrent users
- Современным (использует async/await)

Но требует понимания async patterns и использования async библиотек везде.
