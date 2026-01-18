# ADR 0011: Database Support - PostgreSQL and SQLite

## Status
Accepted

## Context
Проект должен поддерживать разные сценарии использования:
- **Development**: быстрый старт без установки PostgreSQL
- **Testing**: лёгкая БД для юнит-тестов и CI/CD
- **Production**: надёжная БД с ACID гарантиями

Также нужно учесть:
- Асинхронная работа с БД
- Connection pooling strategy
- Разные драйверы для async (asyncpg vs aiosqlite)

## Decision
Поддерживать **оба варианта** - PostgreSQL и SQLite:

```python
# Configuration
if "sqlite" in settings.DATABASE_URL:
    # SQLite: StaticPool для async
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL: NullPool
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        poolclass=NullPool
    )
```

**Connection Strings:**
```bash
# PostgreSQL (production)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/obsidian_tasks

# SQLite (development/testing)
DATABASE_URL=sqlite+aiosqlite:///./obsidian_tasks.db
```

## Alternatives Considered

### 1. Только PostgreSQL
**Отклонено**:
- ❌ Требует установки PostgreSQL для разработки
- ❌ Сложнее запустить проект новичкам
- ❌ Оверкилл для тестирования
- ❌ Нужен Docker для CI/CD

### 2. Только SQLite
**Отклонено**:
- ❌ Не подходит для production (конкурентный доступ)
- ❌ Ограничения по features (некоторые SQL функции)
- ❌ Нет настоящего concurrent access

### 3. MySQL вместо PostgreSQL
**Отклонено**:
- ❌ Меньше features чем PostgreSQL
- ❌ Хуже async support в Python

### 4. Только in-memory SQLite
```python
DATABASE_URL=sqlite+aiosqlite:///:memory:
```
**Отклонено для development**:
- ❌ Данные теряются при перезапуске
- ⚠️ Полезно для unit tests

## Consequences

### Positive
- ✅ **Easy Start**: новички могут начать без PostgreSQL
- ✅ **Fast Testing**: SQLite in-memory быстро для тестов
- ✅ **Production Ready**: PostgreSQL для production
- ✅ **CI/CD Friendly**: SQLite не требует setup в CI
- ✅ **Same Code**: SQLAlchemy обеспечивает одинаковый код
- ✅ **Flexibility**: можно переключаться через .env

### Negative
- ❌ **Different Behavior**: некоторые различия в SQL диалектах
- ❌ **Pool Configuration**: разные pooling strategies
- ❌ **Testing Gap**: тесты на SQLite могут пропустить PostgreSQL issues
- ❌ **Feature Differences**: не все PostgreSQL features в SQLite

### Neutral
- 🔄 **Async Drivers**: asyncpg vs aiosqlite (разные библиотеки)
- 🔄 **Performance**: PostgreSQL быстрее для concurrent access

## Database Comparison

| Feature | PostgreSQL | SQLite |
|---------|-----------|--------|
| **Concurrent Writes** | ✅ Excellent | ⚠️ Limited (file locking) |
| **ACID** | ✅ Full support | ✅ Full support |
| **Async Support** | ✅ asyncpg | ✅ aiosqlite |
| **JSON Types** | ✅ JSONB | ⚠️ TEXT |
| **Full Text Search** | ✅ Built-in | ⚠️ FTS extension |
| **Setup Required** | ❌ Yes (server) | ✅ No (file-based) |
| **Size Limit** | ✅ Unlimited | ⚠️ ~140TB (practical limit lower) |
| **Use Case** | Production | Development/Testing |

## Pool Strategy Differences

### Why Different Pools?

#### SQLite: StaticPool
```python
if "sqlite" in settings.DATABASE_URL:
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=StaticPool,  # Single connection
        connect_args={"check_same_thread": False}
    )
```

**Reason:**
- SQLite file-based БД плохо работает с connection pooling
- Async SQLite требует StaticPool для избежания greenlet errors
- `check_same_thread=False` позволяет использовать в async

#### PostgreSQL: NullPool
```python
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool  # No pooling
    )
```

**Reason:**
- NullPool создаёт новое соединение для каждой транзакции
- Проще для development (нет connection pool issues)
- В production можно использовать QueuePool

### Production PostgreSQL Pool
```python
# For production - use QueuePool
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,  # Max 5 connections
    max_overflow=10,  # Max 15 total (5 + 10)
    pool_pre_ping=True  # Check connection alive
)
```

## Configuration Examples

### Development (.env)
```bash
# SQLite for quick start
DATABASE_URL=sqlite+aiosqlite:///./obsidian_tasks.db
DATABASE_ECHO=True  # Log SQL queries
```

### Production (.env)
```bash
# PostgreSQL for production
DATABASE_URL=postgresql+asyncpg://user:password@db.example.com:5432/obsidian_tasks
DATABASE_ECHO=False  # Don't log in production
```

### Testing (.env.test)
```bash
# In-memory SQLite for fast tests
DATABASE_URL=sqlite+aiosqlite:///:memory:
DATABASE_ECHO=False
```

## Migration Compatibility

Most SQLAlchemy features work the same:
```python
# Works in both PostgreSQL and SQLite
class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### PostgreSQL-specific features (avoided)
```python
# ❌ Don't use PostgreSQL-specific types
from sqlalchemy.dialects.postgresql import JSONB
data: Mapped[dict] = mapped_column(JSONB)  # Won't work in SQLite

# ✅ Use generic types
data: Mapped[str] = mapped_column(Text)  # Works in both
```

## Async Drivers

### asyncpg (PostgreSQL)
```bash
pip install asyncpg
```
- Fast (written in C)
- PostgreSQL-specific optimizations
- Battle-tested

### aiosqlite (SQLite)
```bash
pip install aiosqlite
```
- Wrapper around sqlite3
- Slower than asyncpg
- Good enough for development

## Database Setup

### SQLite
```bash
# No setup needed!
# Just run the app
python init_db.py
uvicorn src.main:app
```

### PostgreSQL
```bash
# Install PostgreSQL
brew install postgresql  # macOS
sudo apt install postgresql  # Ubuntu

# Start server
brew services start postgresql

# Create database
createdb obsidian_tasks

# Create user (optional)
createuser -P taskmanager  # Set password

# Grant permissions
psql -c "GRANT ALL PRIVILEGES ON DATABASE obsidian_tasks TO taskmanager;"

# Run migrations
alembic upgrade head
```

## Testing Strategy

### Unit Tests - SQLite in-memory
```python
# Fast, isolated tests
@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

    await engine.dispose()
```

### Integration Tests - PostgreSQL
```python
# Test against real PostgreSQL
@pytest.fixture
async def db():
    engine = create_async_engine(
        "postgresql+asyncpg://test:test@localhost:5432/test_db"
    )
    # ... setup test database
```

## Switching Between Databases

Just change `.env`:
```bash
# Switch to SQLite
DATABASE_URL=sqlite+aiosqlite:///./obsidian_tasks.db

# Switch to PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/obsidian_tasks
```

No code changes needed!

## Common Issues

### Issue 1: Greenlet errors with SQLite
**Problem:**
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
```

**Solution:**
```python
# Use StaticPool for SQLite
poolclass=StaticPool
```

### Issue 2: "database is locked" (SQLite)
**Problem:** Multiple processes writing to SQLite

**Solution:**
- Use PostgreSQL for multi-process
- Or add connection pooling timeout

### Issue 3: Different SQL syntax
**Problem:** PostgreSQL `RETURNING *` vs SQLite

**Solution:**
- Use SQLAlchemy ORM (handles differences)
- Avoid raw SQL when possible

## Performance Considerations

### SQLite
- ✅ Fast reads
- ⚠️ Slow concurrent writes
- ✅ Low memory footprint
- ✅ No server overhead

### PostgreSQL
- ✅ Fast concurrent access
- ✅ Scales horizontally
- ❌ Higher memory usage
- ❌ Server maintenance required

## Migration Path

1. **Start**: SQLite for development
2. **Testing**: SQLite in-memory for unit tests
3. **Staging**: PostgreSQL to catch production issues
4. **Production**: PostgreSQL with proper pooling

## Related ADRs
- ADR-0008: SQLAlchemy 2.0 Async
- ADR-0007: Transaction Management

## Notes
Поддержка двух БД - практичное решение:
- SQLite для быстрого старта и обучения
- PostgreSQL для production

Код остаётся одинаковым благодаря SQLAlchemy абстракции.
