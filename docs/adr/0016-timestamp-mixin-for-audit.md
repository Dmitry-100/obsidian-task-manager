# ADR 0016: TimestampMixin for Audit Trail

## Status
Accepted

## Context
Почти все entity в системе (Project, Task, Tag, Comment) нуждаются в:
- **created_at**: когда запись создана
- **updated_at**: когда последний раз изменена

Варианты реализации:
1. Дублировать код в каждой модели
2. Использовать Mixin класс
3. Использовать database triggers
4. Не хранить эту информацию вообще

## Decision
Использовать **TimestampMixin** - reusable mixin class:

```python
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

class TimestampMixin:
    """
    Mixin для автоматических timestamp полей.

    Добавляет:
    - created_at: время создания (устанавливается один раз)
    - updated_at: время последнего изменения (обновляется автоматически)
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

# Usage in models
class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # created_at и updated_at автоматически добавлены через Mixin!

class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    # ... same, created_at and updated_at included

class Tag(Base, TimestampMixin):
    # ... same
```

## Alternatives Considered

### 1. Дублирование кода в каждой модели
```python
class Project(Base):
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Task(Base):
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # Duplicate!
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Duplicate!

class Tag(Base):
    # ... same duplication
```
**Отклонено**:
- ❌ Нарушает DRY principle
- ❌ Copy-paste errors
- ❌ Сложнее поддерживать (изменение в 5 местах)
- ❌ Можно забыть добавить в новую модель

### 2. Database Triggers
```sql
-- PostgreSQL trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER projects_updated_at
BEFORE UPDATE ON projects
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```
**Отклонено**:
- ❌ Database-specific (не работает одинаково в SQLite и PostgreSQL)
- ❌ Логика скрыта от приложения
- ❌ Сложнее тестировать
- ❌ Нужны migrations для triggers

### 3. SQLAlchemy Events (альтернативный подход к Mixin)
```python
from sqlalchemy import event

@event.listens_for(Project, 'before_update')
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()
```
**Отклонено**:
- ❌ Нужен event listener для каждой модели
- ❌ Больше boilerplate
- ❌ Mixin проще и декларативнее

### 4. Не хранить timestamps
**Отклонено**:
- ❌ Теряем audit trail
- ❌ Нельзя отследить когда создано/изменено
- ❌ Сложнее debugging
- ❌ Нет данных для аналитики

## Consequences

### Positive
- ✅ **DRY**: код написан один раз, используется везде
- ✅ **Consistency**: все модели имеют одинаковые timestamp поля
- ✅ **Automatic**: не нужно вручную устанавливать timestamps
- ✅ **Database Agnostic**: работает с любой БД (SQLite, PostgreSQL)
- ✅ **Easy to Extend**: можно добавить другие поля в Mixin
- ✅ **Type Safety**: Mapped[datetime] обеспечивает type hints

### Negative
- ❌ **Implicit Fields**: не очевидно что модель имеет created_at/updated_at (нужно знать про Mixin)
- ❌ **Limited Control**: все модели с Mixin имеют одинаковую логику

### Neutral
- 🔄 **Multiple Inheritance**: модель наследует и Base, и TimestampMixin
- 🔄 **UTC Timezone**: используем utcnow() (нужна consistency в приложении)

## How It Works

### Object Creation
```python
# Create project
project = Project(name="Test Project")
db.add(project)
await db.flush()

# Automatically set:
# project.created_at = datetime.utcnow()  # e.g. 2026-01-19 00:00:00
# project.updated_at = datetime.utcnow()  # e.g. 2026-01-19 00:00:00
```

### Object Update
```python
# Update project
project.name = "Updated Name"
await db.flush()

# Automatically updated:
# project.created_at = 2026-01-19 00:00:00  # Unchanged!
# project.updated_at = 2026-01-19 01:00:00  # Updated!
```

### SQL Generated
```sql
-- INSERT
INSERT INTO projects (name, created_at, updated_at)
VALUES ('Test Project', '2026-01-19 00:00:00', '2026-01-19 00:00:00');

-- UPDATE
UPDATE projects
SET name = 'Updated Name',
    updated_at = '2026-01-19 01:00:00'  -- Автоматически обновлено!
WHERE id = 1;
```

## Mixin Pattern in Python

### What is a Mixin?
Mixin - класс, который добавляет функциональность другим классам через множественное наследование.

```python
# Mixin class
class TimestampMixin:
    created_at: Mapped[datetime] = ...
    updated_at: Mapped[datetime] = ...

# Target class uses Mixin
class Project(Base, TimestampMixin):
    # Inherits:
    # - Base: declarative_base functionality
    # - TimestampMixin: created_at and updated_at fields
    pass
```

### Multiple Mixins Example
```python
class TimestampMixin:
    created_at: Mapped[datetime] = ...
    updated_at: Mapped[datetime] = ...

class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(default=False)
    deleted_at: Mapped[Optional[datetime]] = ...

# Combine multiple mixins
class Project(Base, TimestampMixin, SoftDeleteMixin):
    # Has:
    # - created_at, updated_at (from TimestampMixin)
    # - is_deleted, deleted_at (from SoftDeleteMixin)
    pass
```

## Usage Examples

### All Models with TimestampMixin
```python
# Project
class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    is_archived: Mapped[bool] = mapped_column(default=False)
    # + created_at: Mapped[datetime]
    # + updated_at: Mapped[datetime]

# Task
class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    # + created_at: Mapped[datetime]
    # + updated_at: Mapped[datetime]

# Tag
class Tag(Base, TimestampMixin):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    # + created_at: Mapped[datetime]
    # + updated_at: Mapped[datetime]

# Comment
class TaskComment(Base, TimestampMixin):
    __tablename__ = "task_comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    # + created_at: Mapped[datetime]
    # + updated_at: Mapped[datetime]
```

### Querying by Timestamps
```python
# Get projects created today
today = datetime.utcnow().date()
result = await db.execute(
    select(Project).where(
        func.date(Project.created_at) == today
    )
)

# Get tasks updated in last hour
one_hour_ago = datetime.utcnow() - timedelta(hours=1)
result = await db.execute(
    select(Task).where(
        Task.updated_at > one_hour_ago
    )
)

# Sort by creation date
result = await db.execute(
    select(Task).order_by(Task.created_at.desc())
)
```

### API Response with Timestamps
```python
# Pydantic schema includes timestamps
class ProjectResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

# API endpoint
@router.get("/projects/{id}")
async def get_project(id: int):
    project = await project_repo.get_by_id(id)
    return {
        "id": project.id,
        "name": project.name,
        "created_at": project.created_at,  # From TimestampMixin
        "updated_at": project.updated_at   # From TimestampMixin
    }
```

## Timezone Considerations

### Using UTC
```python
# ✅ Good: Use UTC consistently
created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.utcnow  # UTC time
)
```

### Why UTC?
- ✅ Consistent across timezones
- ✅ Easy to convert to user's timezone in frontend
- ✅ Avoids DST (daylight saving time) issues
- ✅ Standard practice for backend APIs

### Frontend Conversion
```javascript
// Backend sends UTC: "2026-01-19T00:00:00"
// Frontend converts to user timezone
const date = new Date("2026-01-19T00:00:00Z");
const userTime = date.toLocaleString();  // "1/19/2026, 3:00:00 AM" (if user in GMT+3)
```

## Testing TimestampMixin

```python
import pytest
from datetime import datetime

@pytest.mark.asyncio
async def test_timestamps_on_create():
    project = Project(name="Test")
    db.add(project)
    await db.flush()

    # Check timestamps are set
    assert project.created_at is not None
    assert project.updated_at is not None
    assert project.created_at == project.updated_at  # Same on creation

@pytest.mark.asyncio
async def test_updated_at_changes():
    # Create
    project = Project(name="Test")
    db.add(project)
    await db.flush()
    created_at = project.created_at
    updated_at = project.updated_at

    # Wait and update
    await asyncio.sleep(0.1)
    project.name = "Updated"
    await db.flush()

    # Check updated_at changed
    assert project.created_at == created_at  # Unchanged
    assert project.updated_at > updated_at  # Changed!
```

## Advanced: Custom Timestamp Mixin

```python
class AuditMixin(TimestampMixin):
    """Extended mixin with user tracking."""

    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    updated_by: Mapped[Optional[str]] = mapped_column(String(100))

# Usage
class Project(Base, AuditMixin):
    # Has: created_at, updated_at, created_by, updated_by
    pass

# In service
project = Project(
    name="Test",
    created_by=current_user.username
)
```

## SQLAlchemy Column Options

### default vs server_default
```python
# Application-level default (Python)
created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.utcnow  # Called by SQLAlchemy (app)
)

# Database-level default (SQL)
created_at: Mapped[datetime] = mapped_column(
    DateTime,
    server_default=func.now()  # Called by database
)
```

**Our choice**: `default=datetime.utcnow`
- ✅ Works same in SQLite and PostgreSQL
- ✅ Python has full control
- ✅ Easier to test (can mock datetime)

### onupdate
```python
updated_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=datetime.utcnow,
    onupdate=datetime.utcnow  # Auto-update on UPDATE
)
```

**Behavior**:
- При INSERT: использует `default`
- При UPDATE: использует `onupdate`

## Common Patterns

### Filter by Date Range
```python
async def get_tasks_in_date_range(
    self,
    start_date: datetime,
    end_date: datetime
) -> List[Task]:
    result = await self.db.execute(
        select(Task).where(
            Task.created_at >= start_date,
            Task.created_at <= end_date
        )
    )
    return list(result.scalars().all())
```

### Recently Updated Items
```python
async def get_recently_updated(self, hours: int = 24) -> List[Project]:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    result = await self.db.execute(
        select(Project)
        .where(Project.updated_at > cutoff)
        .order_by(Project.updated_at.desc())
    )
    return list(result.scalars().all())
```

### Activity Timeline
```python
# Get all changes in last week
last_week = datetime.utcnow() - timedelta(days=7)

projects = await project_repo.get_updated_since(last_week)
tasks = await task_repo.get_updated_since(last_week)

# Combine and sort by updated_at
all_items = projects + tasks
all_items.sort(key=lambda x: x.updated_at, reverse=True)
```

## Related ADRs
- ADR-0008: SQLAlchemy 2.0 Async - Mixin используется с новым синтаксисом
- ADR-0006: Pydantic Schemas - timestamps включены в response schemas

## Notes
TimestampMixin - простой но мощный паттерн:
- **DRY**: не дублируем код
- **Automatic**: не забываем про timestamps
- **Consistent**: везде одинаковая логика
- **Extensible**: легко расширить (например, добавить created_by/updated_by)

Это стандартный паттерн в Django (auto_now, auto_now_add) и других фреймворках. В SQLAlchemy реализуется через Mixin.
