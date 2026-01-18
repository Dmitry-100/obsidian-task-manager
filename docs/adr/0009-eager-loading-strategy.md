# ADR 0009: Eager Loading Strategy (selectinload)

## Status
Accepted

## Context
SQLAlchemy relationships по умолчанию используют **lazy loading**:
```python
task = await task_repo.get_by_id(1)
print(task.tags)  # ← Отдельный SQL запрос для загрузки tags
```

Проблема **N+1 queries**:
```python
tasks = await task_repo.get_all()  # 1 query
for task in tasks:
    print(task.tags)  # N queries (по одному на каждую task)
# Итого: 1 + N queries вместо 2
```

В async SQLAlchemy lazy loading вызывает дополнительные проблемы:
- **Greenlet errors** при попытке lazy load вне async контекста
- **Expired relationships** после commit()
- **Performance issues** из-за множества мелких запросов

## Decision
Использовать **Eager Loading** с `selectinload()` для загрузки relationships:

```python
# Repository метод с eager loading
async def get_by_id_full(self, id: int) -> Optional[Task]:
    result = await self.db.execute(
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.tags),
            selectinload(Task.comments),
            selectinload(Task.subtasks)
        )
        .where(Task.id == id)
    )
    return result.scalar_one_or_none()

# Два метода для разных сценариев:
# - get_by_id() - без relationships (быстро)
# - get_by_id_full() - с relationships (полная информация)
```

## Alternatives Considered

### 1. Lazy Loading (по умолчанию)
```python
task = await db.get(Task, 1)
print(task.tags)  # Отдельный запрос
```
**Отклонено**:
- ❌ N+1 query problem
- ❌ Greenlet errors в async
- ❌ Expired relationships после commit
- ❌ Плохая производительность

### 2. joinedload() (JOIN в одном запросе)
```python
result = await db.execute(
    select(Task).options(joinedload(Task.tags))
)
```
**Отклонено для Many-to-Many**:
- ❌ Создаёт дублирующиеся строки (cartesian product)
- ❌ Сложно с несколькими relationships
- ⚠️ Может быть полезен для One-to-Many

### 3. subqueryload() (subquery)
```python
result = await db.execute(
    select(Task).options(subqueryload(Task.tags))
)
```
**Отклонено**:
- ❌ Deprecated в SQLAlchemy 2.0
- ❌ Менее эффективен чем selectinload

### 4. Загружать всё всегда (eager по умолчанию)
```python
class Task(Base):
    tags: Mapped[List["Tag"]] = relationship(lazy="selectin")
```
**Отклонено**:
- ❌ Загружаем relationships даже когда они не нужны
- ❌ Нет гибкости
- ❌ Overhead при простых операциях

## Consequences

### Positive
- ✅ **No N+1 Problem**: предсказуемое количество queries
- ✅ **No Greenlet Errors**: всё загружается в async контексте
- ✅ **Explicit**: понятно где загружаются relationships
- ✅ **Flexible**: можем выбирать что загружать
- ✅ **Performance**: 2-3 queries вместо 1+N

### Negative
- ❌ **Verbose**: нужно явно указывать `.options(selectinload(...))`
- ❌ **Easy to Forget**: можно забыть добавить selectinload
- ❌ **Overhead**: загружаем relationships даже если не используем

### Neutral
- 🔄 **Two Methods Pattern**: get_by_id() vs get_by_id_full()
- 🔄 **Query Count**: всегда 1 + количество relationships

## How selectinload() Works

### SQL Queries Generated
```python
# Code
result = await db.execute(
    select(Task)
    .options(
        selectinload(Task.tags),
        selectinload(Task.comments)
    )
    .where(Task.id == 1)
)

# SQL queries:
# Query 1: Load task
SELECT * FROM tasks WHERE id = 1

# Query 2: Load tags
SELECT tags.* FROM tags
INNER JOIN task_tags ON tags.id = task_tags.tag_id
WHERE task_tags.task_id IN (1)

# Query 3: Load comments
SELECT * FROM task_comments WHERE task_id IN (1)

# Total: 3 queries instead of 1+N
```

### For Multiple Objects
```python
# Code
result = await db.execute(
    select(Task)
    .options(selectinload(Task.tags))
    .where(Task.project_id == 1)
)
tasks = result.scalars().all()  # 10 tasks

# SQL queries:
# Query 1: Load all tasks
SELECT * FROM tasks WHERE project_id = 1  # Returns 10 tasks

# Query 2: Load ALL tags for ALL tasks in one query
SELECT tags.* FROM tags
INNER JOIN task_tags ON tags.id = task_tags.tag_id
WHERE task_tags.task_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

# Total: 2 queries for 10 tasks (instead of 11!)
```

## Two Methods Pattern

### Lean Method (without relationships)
```python
async def get_by_id(self, id: int) -> Optional[Task]:
    """Быстрая загрузка без relationships."""
    result = await self.db.execute(
        select(Task).where(Task.id == id)
    )
    return result.scalar_one_or_none()

# Use case: просто получить task без связанных данных
task = await task_repo.get_by_id(1)
print(task.title)  # OK
# print(task.tags)  # ❌ Error или lazy load
```

### Full Method (with relationships)
```python
async def get_by_id_full(self, id: int) -> Optional[Task]:
    """Полная загрузка с relationships."""
    result = await self.db.execute(
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.tags),
            selectinload(Task.comments),
            selectinload(Task.subtasks)
        )
        .where(Task.id == id)
    )
    return result.scalar_one_or_none()

# Use case: нужны все связанные данные (для API response)
task = await task_repo.get_by_id_full(1)
print(task.title)  # OK
print(task.tags)  # OK - уже загружены
```

### When to Use Which?

**Use `get_by_id()`**:
- Проверка существования
- Обновление полей самой entity
- Внутренняя валидация

**Use `get_by_id_full()`**:
- API responses (нужны nested objects)
- Сложная бизнес-логика с relationships
- Display в UI

## Examples

### API Endpoint Pattern
```python
@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: int,
    service: TaskService = Depends(get_task_service)
):
    # Service вызывает get_by_id_full()
    task = await service.get_task(task_id, full=True)
    if not task:
        raise HTTPException(status_code=404)

    # Response schema включает tags, comments
    return TaskDetailResponse.model_validate(task)
```

### Nested Relationships
```python
# Загрузка с несколькими уровнями вложенности
result = await db.execute(
    select(Project)
    .options(
        selectinload(Project.tasks).selectinload(Task.tags),
        selectinload(Project.tasks).selectinload(Task.comments)
    )
    .where(Project.id == 1)
)
project = result.scalar_one()

# Теперь доступны:
# - project.tasks (all tasks)
# - task.tags (tags for each task)
# - task.comments (comments for each task)
```

### Dynamic Loading Decision
```python
async def get_tasks(self, project_id: int, include_details: bool = False) -> List[Task]:
    query = select(Task).where(Task.project_id == project_id)

    if include_details:
        # Загружаем relationships только если нужно
        query = query.options(
            selectinload(Task.tags),
            selectinload(Task.comments)
        )

    result = await self.db.execute(query)
    return list(result.scalars().all())
```

## Performance Comparison

### Without selectinload (N+1 problem)
```python
tasks = await db.execute(select(Task).where(Task.project_id == 1))
for task in tasks.scalars():  # 10 tasks
    print(task.tags)  # 10 additional queries

# Total: 11 queries (1 + 10)
```

### With selectinload
```python
tasks = await db.execute(
    select(Task)
    .options(selectinload(Task.tags))
    .where(Task.project_id == 1)
)
for task in tasks.scalars():  # 10 tasks
    print(task.tags)  # No additional queries

# Total: 2 queries (1 + 1)
```

## Fix for add_tag() Method

Изначально метод `add_tag()` вызывал lazy loading:
```python
# ❌ Проблема
async def add_tag(self, task_id: int, tag: Tag):
    task = await self.get_by_id(task_id)  # Без relationships
    if tag not in task.tags:  # ← Lazy load! Greenlet error!
        task.tags.append(tag)
```

Решение - eager loading:
```python
# ✅ Решение
async def add_tag(self, task_id: int, tag: Tag):
    result = await self.db.execute(
        select(Task)
        .options(selectinload(Task.tags))  # Eager load
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if tag not in task.tags:  # OK - tags уже загружены
        task.tags.append(tag)
```

## Related ADRs
- ADR-0007: Transaction Management
- ADR-0008: SQLAlchemy 2.0 Async
- ADR-0002: Repository Pattern

## Notes
selectinload() - критически важная техника для async SQLAlchemy. Без неё приложение будет падать с greenlet errors или иметь N+1 проблему.

Pattern "два метода" (get_by_id vs get_by_id_full) даёт баланс между производительностью и удобством.
