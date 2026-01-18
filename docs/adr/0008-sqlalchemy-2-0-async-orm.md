# ADR 0008: SQLAlchemy 2.0 Async ORM

## Status
Accepted

## Context
Необходимо было выбрать ORM для работы с базой данных. Требования:
- Асинхронная работа (совместимость с FastAPI async)
- Поддержка сложных relationships (Many-to-Many, иерархия)
- Type hints support
- Миграции БД
- Поддержка PostgreSQL и SQLite
- Production-ready и battle-tested

## Decision
Использовать **SQLAlchemy 2.0 с async engine**:

```python
# Async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO
)

# Async session
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Models с новым синтаксисом
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    tags: Mapped[List["Tag"]] = relationship(secondary=task_tags, back_populates="tasks")
```

## Alternatives Considered

### 1. SQLAlchemy 1.4 (sync)
```python
# Sync engine
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Sync operations
def get_task(db: Session, task_id: int):
    return db.query(Task).filter(Task.id == task_id).first()
```
**Отклонено**:
- ❌ Блокирует event loop в async приложении
- ❌ Плохая производительность с FastAPI async
- ❌ Устаревший синтаксис (query API deprecated)

### 2. Tortoise ORM
```python
class Task(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=300)
    tags = fields.ManyToManyField("models.Tag")
```
**Отклонено**:
- ❌ Меньше features чем SQLAlchemy
- ❌ Меньше community support
- ❌ Хуже документация
- ❌ Ограниченная поддержка сложных queries

### 3. SQLModel (by Tiangolo)
```python
class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
```
**Отклонено**:
- ❌ Ещё очень молодой (не production-ready)
- ❌ Ограниченная функциональность
- ❌ Плохо работает со сложными relationships
- ❌ Смешивает Pydantic и SQLAlchemy (противоречит DTO паттерну)

### 4. Django ORM
**Отклонено**:
- ❌ Требует Django фреймворк (слишком тяжеловесно)
- ❌ Хуже async support

### 5. Raw SQL (asyncpg)
```python
async with pool.acquire() as conn:
    result = await conn.fetch("SELECT * FROM tasks WHERE id = $1", task_id)
```
**Отклонено**:
- ❌ Нет ORM абстракции
- ❌ SQL injection риски
- ❌ Сложность работы с relationships
- ❌ Больше boilerplate кода

## Consequences

### Positive
- ✅ **Full Async Support**: native async/await, не блокирует event loop
- ✅ **Production Ready**: battle-tested, используется в крупных проектах
- ✅ **Type Hints**: новый синтаксис с `Mapped[]` обеспечивает type safety
- ✅ **Powerful Relationships**: сложные relationships из коробки
- ✅ **Flexible Queries**: мощный query API
- ✅ **Database Agnostic**: PostgreSQL, SQLite, MySQL одинаковый код
- ✅ **Migration Support**: Alembic интеграция
- ✅ **Lazy/Eager Loading**: контроль над загрузкой relationships
- ✅ **Large Community**: много примеров, Stack Overflow ответов

### Negative
- ❌ **Complexity**: крутая learning curve
- ❌ **Verbose**: больше кода чем в Django ORM
- ❌ **Greenlet Issues**: async требует понимания greenlet
- ❌ **N+1 Problem**: нужно явно использовать eager loading

### Neutral
- 🔄 **Breaking Changes**: SQLAlchemy 2.0 сильно отличается от 1.4
- 🔄 **Pool Configuration**: разные pool для SQLite и PostgreSQL

## SQLAlchemy 2.0 New Features

### Mapped Type Annotations
```python
# Old style (1.4)
title = Column(String(300), nullable=False)

# New style (2.0) - with type hints!
title: Mapped[str] = mapped_column(String(300))
# IDE знает что title это str
```

### Declarative Base
```python
# Old
Base = declarative_base()

# New
class Base(DeclarativeBase):
    pass
```

### Select API (instead of Query)
```python
# Old (deprecated)
db.query(Task).filter(Task.id == 1).first()

# New
result = await db.execute(select(Task).where(Task.id == 1))
task = result.scalar_one_or_none()
```

## Async Pattern

### Repository Pattern
```python
class TaskRepository(BaseRepository[Task]):
    async def get_by_id(self, id: int) -> Optional[Task]:
        result = await self.db.execute(
            select(Task).where(Task.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_project(self, project_id: int) -> List[Task]:
        result = await self.db.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.created_at.desc())
        )
        return list(result.scalars().all())
```

### Eager Loading (solve N+1)
```python
# Without eager loading - N+1 problem
task = await db.get(Task, 1)
for tag in task.tags:  # ❌ Separate query for EACH tag
    print(tag.name)

# With eager loading - 2 queries total
result = await db.execute(
    select(Task)
    .options(selectinload(Task.tags))  # ✅ Load tags in advance
    .where(Task.id == 1)
)
task = result.scalar_one()
for tag in task.tags:  # ✅ No additional queries
    print(tag.name)
```

## Database Configuration

### PostgreSQL vs SQLite
```python
if "sqlite" in settings.DATABASE_URL:
    # SQLite requires StaticPool for async
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL uses NullPool
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool
    )
```

### Connection String Examples
```python
# PostgreSQL
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/dbname"

# SQLite
DATABASE_URL = "sqlite+aiosqlite:///./database.db"
```

## Relationships Examples

### Many-to-Many
```python
# Junction table
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

# Models
class Task(Base):
    tags: Mapped[List["Tag"]] = relationship(secondary=task_tags, back_populates="tasks")

class Tag(Base):
    tasks: Mapped[List["Task"]] = relationship(secondary=task_tags, back_populates="tags")
```

### Self-Referencing (Hierarchy)
```python
class Task(Base):
    parent_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"))

    parent_task: Mapped[Optional["Task"]] = relationship(
        "Task",
        remote_side=[id],
        back_populates="subtasks"
    )
    subtasks: Mapped[List["Task"]] = relationship("Task", back_populates="parent_task")
```

### One-to-Many
```python
class Project(Base):
    tasks: Mapped[List["Task"]] = relationship(back_populates="project")

class Task(Base):
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    project: Mapped["Project"] = relationship(back_populates="tasks")
```

## Migration with Alembic

```python
# Auto-generate migration
alembic revision --autogenerate -m "Create tables"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Performance Considerations

### Good Practices
```python
# ✅ Batch operations
tasks = [Task(title=f"Task {i}") for i in range(100)]
db.add_all(tasks)
await db.flush()

# ✅ Eager loading
result = await db.execute(
    select(Task).options(selectinload(Task.tags), selectinload(Task.comments))
)

# ✅ Limit queries
result = await db.execute(
    select(Task).limit(10).offset(0)
)
```

### Bad Practices
```python
# ❌ N+1 problem
tasks = await db.execute(select(Task))
for task in tasks.scalars():
    print(task.tags)  # Separate query for EACH task

# ❌ Loading all data
tasks = await db.execute(select(Task))  # Loads ALL tasks from DB

# ❌ Accessing expired relationships
await db.commit()
print(task.tags)  # Error: relationship expired
```

## Related ADRs
- ADR-0007: Transaction Management - flush() vs commit()
- ADR-0009: Eager Loading - selectinload()
- ADR-0012: Async Architecture

## Notes
SQLAlchemy 2.0 - это мощный, но сложный инструмент. Новый синтаксис с type hints делает его безопаснее, но требует понимания async patterns.

Для учебного проекта это хороший выбор, так как:
- Учит работе с "настоящим" production ORM
- Type hints помогают избежать ошибок
- Можно использовать как с PostgreSQL, так и с SQLite
