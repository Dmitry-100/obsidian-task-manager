# ADR 0015: Explicit Junction Table for Many-to-Many

## Status
Accepted

## Context
Задачи (Tasks) и Теги (Tags) имеют Many-to-Many relationship:
- Одна задача может иметь много тегов
- Один тег может быть у многих задач

SQLAlchemy поддерживает два подхода для M:M:
1. **Автоматическая junction table** (SQLAlchemy создаёт сам)
2. **Явная junction table** (мы создаём `Table` явно)

Также нужно решить:
- Добавлять ли дополнительные поля в junction table?
- Нужна ли аудит информация (когда связь создана)?

## Decision
Использовать **явную junction table** с полем `created_at`:

```python
# Explicit junction table
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)

# Models
class Task(Base):
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary=task_tags,
        back_populates="tasks"
    )

class Tag(Base):
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        secondary=task_tags,
        back_populates="tags"
    )
```

## Alternatives Considered

### 1. Автоматическая Junction Table
```python
class Task(Base):
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="task_tags",  # SQLAlchemy creates table
        back_populates="tasks"
    )

# SQLAlchemy auto-creates:
# CREATE TABLE task_tags (
#     task_id INTEGER,
#     tag_id INTEGER,
#     PRIMARY KEY (task_id, tag_id)
# )
```
**Отклонено**:
- ❌ Нельзя добавить дополнительные поля (created_at)
- ❌ Меньше контроля над таблицей
- ❌ Сложнее добавить индексы или constraints

### 2. Association Object (ORM Model)
```python
class TaskTag(Base):
    __tablename__ = "task_tags"

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="task_tags")
    tag: Mapped["Tag"] = relationship(back_populates="task_tags")

class Task(Base):
    task_tags: Mapped[List["TaskTag"]] = relationship(back_populates="task")

class Tag(Base):
    task_tags: Mapped[List["TaskTag"]] = relationship(back_populates="tag")
```
**Отклонено**:
- ❌ Сложнее использовать: `task.task_tags[0].tag.name` вместо `task.tags[0].name`
- ❌ Больше boilerplate кода
- ❌ Нужен для сложных M:M (с дополнительными полями), но у нас только `created_at`
- ⚠️ Полезен если есть другие поля (priority, order, etc.)

### 3. Две отдельные таблицы (Denormalized)
```python
# task_tags table
# tag_tasks table (reverse direction)
```
**Отклонено**:
- ❌ Дублирование данных
- ❌ Сложность синхронизации
- ❌ Нарушает нормализацию

## Consequences

### Positive
- ✅ **Explicit Control**: полный контроль над junction table
- ✅ **Audit Trail**: можем отслеживать когда тег добавлен к задаче
- ✅ **Extensible**: легко добавить поля в будущем
- ✅ **Simple Usage**: `task.tags` работает как обычный relationship
- ✅ **Composite Primary Key**: автоматически предотвращает дубликаты

### Negative
- ❌ **Boilerplate**: нужно явно определить Table
- ❌ **No ORM Model**: нельзя query TaskTag напрямую (хотя редко нужно)

### Neutral
- 🔄 **created_at**: полезно для аудита, но пока не используется
- 🔄 **Migration**: Alembic автоматически создаст таблицу

## Junction Table Structure

### SQL Schema
```sql
CREATE TABLE task_tags (
    task_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id, tag_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_task_tags_task_id ON task_tags(task_id);
CREATE INDEX idx_task_tags_tag_id ON task_tags(tag_id);
```

### Composite Primary Key
```python
# (task_id, tag_id) = PRIMARY KEY
# This automatically prevents:
(1, 1)  # ✅ OK
(1, 1)  # ❌ DUPLICATE - rejected by DB
(1, 2)  # ✅ OK - different tag
(2, 1)  # ✅ OK - different task
```

## Usage Examples

### Adding Tags to Task
```python
# Service layer
async def create_task(self, title: str, tag_names: List[str], ...):
    # Create task
    task = await self.task_repo.create(Task(title=title, ...))

    # Get or create tags
    tags = await self.tag_repo.bulk_get_or_create(tag_names)

    # Add tags to task
    for tag in tags:
        await self.task_repo.add_tag(task.id, tag)

    await self.db.flush()
    return task
```

### Repository Implementation
```python
class TaskRepository:
    async def add_tag(self, task_id: int, tag: Tag) -> Optional[Task]:
        # Load task with tags
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.tags))
            .where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Check if tag already exists
        if tag not in task.tags:
            task.tags.append(tag)  # SQLAlchemy handles junction table
            await self.db.flush()

        return task
```

### SQLAlchemy Generated SQL
```python
# task.tags.append(tag)
# SQLAlchemy generates:
INSERT INTO task_tags (task_id, tag_id, created_at)
VALUES (1, 5, '2026-01-19 00:00:00')
```

### Querying Tasks by Tag
```python
async def get_tasks_by_tag(self, tag_id: int) -> List[Task]:
    result = await self.db.execute(
        select(Task)
        .join(Task.tags)  # Automatic JOIN через relationship
        .where(Tag.id == tag_id)
    )
    return list(result.scalars().all())

# Generates SQL:
# SELECT tasks.*
# FROM tasks
# INNER JOIN task_tags ON tasks.id = task_tags.task_id
# WHERE task_tags.tag_id = ?
```

### Removing Tag from Task
```python
async def remove_tag(self, task_id: int, tag: Tag):
    result = await self.db.execute(
        select(Task)
        .options(selectinload(Task.tags))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if tag in task.tags:
        task.tags.remove(tag)  # SQLAlchemy handles DELETE
        await self.db.flush()

# Generates SQL:
# DELETE FROM task_tags
# WHERE task_id = ? AND tag_id = ?
```

## Composite Primary Key Benefits

### Automatic Duplicate Prevention
```python
# Try to add same tag twice
task.tags.append(tag1)  # ✅ INSERT
task.tags.append(tag1)  # 🔄 No-op (already in list)
await db.flush()

# If somehow we bypass check:
# INSERT INTO task_tags (task_id, tag_id) VALUES (1, 1);  # ✅ OK
# INSERT INTO task_tags (task_id, tag_id) VALUES (1, 1);  # ❌ UNIQUE violation
```

### Data Integrity
- Cannot have (NULL, 1) or (1, NULL) - both columns NOT NULL
- Cannot have orphaned entries (foreign key constraints)
- Cannot have duplicates (primary key constraint)

## Cascade Deletes

```python
# Foreign key with CASCADE
ForeignKey("tasks.id", ondelete="CASCADE")
ForeignKey("tags.id", ondelete="CASCADE")
```

### Behavior
```python
# Delete task
await task_repo.delete(task_id=1)

# Automatically deletes:
# - Row from tasks table
# - All rows in task_tags where task_id = 1 (CASCADE)
# - Tags themselves are NOT deleted (just the association)

# Delete tag
await tag_repo.delete(tag_id=5)

# Automatically deletes:
# - Row from tags table
# - All rows in task_tags where tag_id = 5 (CASCADE)
# - Tasks themselves are NOT deleted
```

## created_at Field Usage

### Current Use Case
```python
# Audit: when was tag added to task?
result = await db.execute(
    select(task_tags.c.created_at)
    .where(
        task_tags.c.task_id == 1,
        task_tags.c.tag_id == 5
    )
)
created_at = result.scalar_one()
# "Tag #python was added to 'Build API' on 2026-01-19"
```

### Future Use Cases
- **Analytics**: "Which tags are added most often?"
- **Timeline**: "Show task history including tag changes"
- **Reporting**: "Tags added this month"

### Querying via Raw SQL (if needed)
```python
# Query junction table directly
result = await db.execute(text("""
    SELECT task_id, tag_id, created_at
    FROM task_tags
    WHERE created_at > :date
"""), {"date": datetime(2026, 1, 1)})
```

## Future Extensions

Если потребуется больше полей:

### Option 1: Add Fields to Table
```python
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("created_by", String(100)),  # Who added the tag
    Column("importance", Integer),  # How important is this tag for this task
)
```

### Option 2: Convert to Association Object
```python
# If we need complex logic on the relationship
class TaskTag(Base):
    __tablename__ = "task_tags"
    # ... full ORM model
```

## Performance Considerations

### Indexes
```sql
-- Already have PRIMARY KEY index on (task_id, tag_id)

-- Additional indexes for common queries:
CREATE INDEX idx_task_tags_task_id ON task_tags(task_id);  -- Get tags for task
CREATE INDEX idx_task_tags_tag_id ON task_tags(tag_id);    -- Get tasks for tag
CREATE INDEX idx_task_tags_created_at ON task_tags(created_at);  -- Time-based queries
```

### Query Optimization
```python
# ❌ N+1 problem
tasks = await task_repo.get_all()
for task in tasks:
    print(task.tags)  # Separate query for EACH task

# ✅ Eager loading
result = await db.execute(
    select(Task).options(selectinload(Task.tags))
)
tasks = result.scalars().all()
for task in tasks:
    print(task.tags)  # Already loaded
```

## Comparison with Association Object

| Feature | Explicit Table | Association Object |
|---------|---------------|-------------------|
| **Usage** | `task.tags` | `task.task_tags[0].tag` |
| **Simplicity** | ✅ Simple | ❌ Complex |
| **Extra Fields** | ⚠️ Limited | ✅ Unlimited |
| **Query Junction** | ❌ Raw SQL needed | ✅ ORM queries |
| **Overhead** | ✅ Low | ❌ Higher |
| **Use Case** | Simple M:M | Complex M:M |

**Our Choice**: Explicit Table (достаточно для `created_at`, проще использовать)

## Related ADRs
- ADR-0008: SQLAlchemy 2.0 Async
- ADR-0009: Eager Loading Strategy

## Notes
Explicit junction table с `created_at` - золотая середина:
- Проще чем Association Object
- Мощнее чем автоматическая таблица
- Достаточно для аудита
- Легко расширить в будущем

Если потребуется больше полей или сложная логика - можно мигрировать на Association Object.
