"""
Pytest fixtures для тестов.

Предоставляет:
- test_db: изолированная SQLite in-memory БД для каждого теста
- test_client: HTTP клиент для тестирования API endpoints
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from src.models import Base
from src.api.dependencies import get_db  # ВАЖНО: используем get_db из dependencies, не из database!
from src.main import app


# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """
    Создаёт async engine для тестовой БД (SQLite in-memory).

    StaticPool обеспечивает что используется одно и то же соединение,
    что критично для in-memory БД (иначе данные теряются).

    ВАЖНО: Таблицы пересоздаются для каждого теста, обеспечивая полную изоляцию.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Отключаем логи SQL в тестах
        poolclass=StaticPool,  # Для SQLite in-memory
        connect_args={"check_same_thread": False}
    )

    # Удаляем все таблицы (если остались от предыдущего теста)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Создаём все таблицы заново
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Удаляем все таблицы после теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine):
    """
    Предоставляет async session для работы с тестовой БД.

    Каждый тест получает чистую БД.
    Транзакция откатывается после теста.
    """
    # Создаём session maker
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with TestSessionLocal() as session:
        yield session
        # Откатываем все изменения после теста
        await session.rollback()


@pytest_asyncio.fixture
async def test_client(test_engine):
    """
    Предоставляет HTTP клиент для тестирования API endpoints.

    Использует тестовую БД вместо production БД.
    """
    # Override get_db dependency
    async def override_get_db():
        TestSessionLocal = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Создаём async HTTP клиент
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

    # Очищаем overrides после теста
    app.dependency_overrides.clear()


# Pytest configuration
@pytest.fixture(scope="session")
def anyio_backend():
    """Используем asyncio для всех async тестов."""
    return "asyncio"
