"""
Скрипт для инициализации базы данных.

Создаёт все таблицы напрямую через SQLAlchemy.
Используется для тестирования вместо Alembic миграций.
"""

import asyncio
from src.core.database import init_db


async def main():
    """Создать все таблицы."""
    print("Создание таблиц...")
    await init_db()
    print("✓ Таблицы созданы успешно!")


if __name__ == "__main__":
    asyncio.run(main())
