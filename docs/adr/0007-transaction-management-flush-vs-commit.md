# ADR 0007: Transaction Management - flush() vs commit()

## Status
Accepted

## Context
В асинхронном SQLAlchemy приложении нужно управлять транзакциями. Основные вопросы:
- Кто отвечает за `commit()` - Repository, Service или Dependency?
- Когда использовать `flush()` vs `commit()`?
- Как обеспечить атомарность операций?
- Как избежать проблем с expired relationships после commit?

Первоначальная реализация вызывала проблемы:
```python
# Service делал commit
await self.db.commit()

# Dependency тоже делал commit
async def get_db():
    yield session
    await session.commit()  # Double commit!

# Результат: expired relationships, greenlet errors
```

## Decision
Принято решение о **чётком разделении ответственности**:

1. **Repository**: использует `flush()` для сохранения в БД (но не commit)
2. **Service**: использует `flush()` для координации между репозиториями
3. **Dependency (get_db)**: делает единственный `commit()` или `rollback()`

```python
# Repository
async def create(self, obj: ModelType) -> ModelType:
    self.db.add(obj)
    await self.db.flush()  # Только flush
    await self.db.refresh(obj)
    return obj

# Service
async def create_task(self, ...):
    task = await self.task_repo.create(Task(...))
    tags = await self.tag_repo.bulk_get_or_create(tag_names)
    await self.db.flush()  # Только flush
    return task

# Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Единственный commit
        except Exception:
            await session.rollback()
            raise
```

## Alternatives Considered

### 1. Commit в Repository
```python
async def create(self, obj: ModelType) -> ModelType:
    self.db.add(obj)
    await self.db.commit()  # ❌
    return obj
```
**Отклонено**:
- ❌ Невозможно координировать несколько операций
- ❌ Каждая операция в отдельной транзакции
- ❌ Нет атомарности для сложных операций
- ❌ Service не может управлять границами транзакции

### 2. Commit в Service
```python
async def create_task(self, ...):
    task = await self.task_repo.create(Task(...))
    tags = await self.tag_repo.bulk_get_or_create(tag_names)
    await self.db.commit()  # ❌
    return task
```
**Отклонено**:
- ❌ Double commit с Dependency
- ❌ Expired relationships после commit
- ❌ Greenlet errors при доступе к relationships
- ❌ Ответственность размазана

### 3. Автоматический commit после каждой операции
**Отклонено**:
- ❌ Нет контроля над транзакциями
- ❌ Невозможно откатить несколько операций
- ❌ Проблемы с атомарностью

### 4. Manual transaction управление в каждом endpoint
```python
@router.post("/tasks")
async def create_task(...):
    try:
        result = await service.create_task(...)
        await db.commit()
    except:
        await db.rollback()
```
**Отклонено**:
- ❌ Дублирование кода в каждом endpoint
- ❌ Легко забыть commit/rollback

## Consequences

### Positive
- ✅ **Single Responsibility**: только Dependency управляет commit/rollback
- ✅ **Atomicity**: все операции в request в одной транзакции
- ✅ **No Expired Relations**: объекты остаются "alive" до конца request
- ✅ **Error Handling**: автоматический rollback при любой ошибке
- ✅ **Testability**: можно тестировать Service без реального commit
- ✅ **Coordination**: Service может координировать несколько Repository операций

### Negative
- ❌ **Implicit Commit**: не очевидно, где происходит commit
- ❌ **Long Transactions**: вся обработка request в одной транзакции
- ❌ **Learning Curve**: нужно понимать разницу flush/commit

### Neutral
- 🔄 **flush() для ID**: после flush() получаем generated ID
- 🔄 **refresh() после flush()**: нужно обновить объект для relationships

## What is flush() vs commit()?

### flush()
- Отправляет SQL в БД (INSERT/UPDATE/DELETE)
- НЕ делает COMMIT транзакции
- Генерирует ID для auto-increment полей
- Объекты остаются в session
- Можно откатить через rollback()

```python
task = Task(title="New task")
self.db.add(task)
await self.db.flush()
print(task.id)  # 1 - ID уже есть!
# Но транзакция ещё не committed
```

### commit()
- Делает COMMIT транзакции в БД
- Изменения становятся permanent
- Объекты expire (relationships становятся недоступны)
- Откатить уже нельзя

```python
await self.db.commit()
# Теперь изменения в БД навсегда
print(task.tags)  # ❌ Error: relationship expired!
```

## Examples

### Coordinated Operations with flush()
```python
async def create_task(self, title: str, tag_names: List[str], ...):
    # 1. Create task
    task = Task(title=title, ...)
    task = await self.task_repo.create(task)  # flush() inside
    # task.id теперь доступен

    # 2. Get or create tags
    tags = await self.tag_repo.bulk_get_or_create(tag_names)  # flush() inside

    # 3. Link task and tags
    for tag in tags:
        await self.task_repo.add_tag(task.id, tag)  # flush() inside

    # 4. Final flush
    await self.db.flush()

    # 5. Return with relationships loaded
    return await self.task_repo.get_by_id_full(task.id)
    # Relationships still available - NO commit yet!
```

### Automatic Commit/Rollback in Dependency
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Endpoint выполнился успешно
            await session.commit()  # Commit всех flush()
        except Exception as e:
            # Любая ошибка в endpoint
            await session.rollback()  # Откатить ВСЁ
            raise  # Пробросить ошибку
        finally:
            await session.close()
```

### Transaction Lifecycle

```
Request arrives
    ↓
Dependency: session created
    ↓
Service: task_repo.create()
    ├─ db.add()
    └─ db.flush() ← SQL INSERT, ID generated, NO COMMIT
    ↓
Service: tag_repo.bulk_get_or_create()
    ├─ db.add()
    └─ db.flush() ← SQL INSERT, NO COMMIT
    ↓
Service: task_repo.add_tag()
    └─ db.flush() ← SQL INSERT into junction table, NO COMMIT
    ↓
Endpoint returns successfully
    ↓
Dependency: session.commit() ← COMMIT all changes
    ↓
Response sent
```

### Error Rollback Example
```python
async def create_task(self, title: str, tag_names: List[str]):
    # Создаём task
    task = await self.task_repo.create(Task(title=title))  # flush()

    # Создаём tags
    tags = await self.tag_repo.bulk_get_or_create(tag_names)  # flush()

    # Ошибка!
    if some_error:
        raise ValueError("Something went wrong")

    # Этот код не выполнится
    await self.task_repo.add_tag(task.id, tags[0])

# Dependency автоматически сделает rollback():
# - task НЕ будет в БД
# - tags НЕ будут в БД
# - Всё откатится
```

## Why Not commit() in Service?

### Problem: Double Commit
```python
# Service
async def create_project(self, ...):
    project = await self.project_repo.create(...)
    await self.db.commit()  # Commit #1
    return project

# Dependency
async def get_db():
    yield session
    await session.commit()  # Commit #2 - но уже nothing to commit

# Result: relationships expired after first commit
```

### Problem: Expired Relationships
```python
# Service делает commit
await self.db.commit()

# Пытаемся вернуть объект с relationships
return await self.task_repo.get_by_id_full(task.id)

# ❌ Error: task.tags expired, нужен новый запрос
# ❌ Greenlet errors при попытке lazy load
```

## Testing Benefits

```python
# Test без реального commit
async def test_create_task():
    # Setup
    mock_db = MockSession()
    service = TaskService(mock_db)

    # Test
    task = await service.create_task(title="Test")

    # Assert
    assert task.title == "Test"
    # NO commit happened, всё в памяти
    # Можно откатить после теста
```

## Related ADRs
- ADR-0001: Three-Layer Architecture
- ADR-0002: Repository Pattern
- ADR-0003: Service Layer
- ADR-0004: Dependency Injection
- ADR-0008: SQLAlchemy 2.0 Async

## Notes
Это решение было принято после реального bug'а в проекте:
- Изначально Service делал commit()
- Dependency тоже делал commit()
- Результат: greenlet errors и expired relationships

Разделение flush/commit критически важно для правильной работы async SQLAlchemy.
