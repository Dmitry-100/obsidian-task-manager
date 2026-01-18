"""
Демонстрация разницы между flush() и commit().

Показывает, что произойдёт при ошибке после flush().
"""

import asyncio
from src.core.database import AsyncSessionLocal
from src.models import Project


async def demo_flush_without_commit():
    """
    Демонстрация 1: flush() БЕЗ commit() = данные НЕ сохранятся.
    """
    print("=== Демонстрация 1: flush() БЕЗ commit() ===\n")

    async with AsyncSessionLocal() as db:
        # Создаём проект
        project = Project(name="Тестовый проект")
        db.add(project)

        # flush() - отправить в БД
        await db.flush()

        print(f"После flush():")
        print(f"  project.id = {project.id}")  # ID получен из БД!
        print(f"  Данные отправлены в PostgreSQL")
        print(f"  Но транзакция НЕ закоммичена\n")

        # НЕ делаем commit()!
        # Транзакция откатится автоматически при выходе из контекста

    print("Вышли из контекста (session закрыта)")
    print("Транзакция откатилась автоматически\n")

    # Проверяем: есть ли проект в БД?
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Project))
        projects = list(result.scalars().all())

        print(f"Проектов в БД: {len(projects)}")
        print("Вывод: flush() БЕЗ commit() НЕ сохраняет данные\n")


async def demo_error_after_flush():
    """
    Демонстрация 2: Ошибка после flush() = автоматический rollback.
    """
    print("=== Демонстрация 2: Ошибка после flush() ===\n")

    try:
        async with AsyncSessionLocal() as db:
            # ШАГ 1: Создаём проект
            project = Project(name="Проект для теста")
            db.add(project)
            await db.flush()

            print(f"ШАГ 1: После flush()")
            print(f"  project.id = {project.id}")
            print(f"  Данные в БД (в транзакции)\n")

            # ШАГ 2: Имитируем ошибку
            print("ШАГ 2: Проверяем бизнес-правило...")
            if project.name.startswith("Проект"):
                print("  ❌ ОШИБКА! Название не должно начинаться с 'Проект'\n")
                raise ValueError("Invalid project name")

            # ШАГ 3: Этот код НЕ выполнится
            await db.commit()
            print("ШАГ 3: commit() выполнен\n")

    except ValueError as e:
        print(f"Исключение поймано: {e}")
        print("Транзакция откатилась автоматически\n")

    # Проверяем: есть ли проект в БД?
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Project))
        projects = list(result.scalars().all())

        print(f"Проектов в БД: {len(projects)}")
        print("Вывод: Ошибка после flush() откатывает транзакцию\n")


async def demo_successful_commit():
    """
    Демонстрация 3: flush() + commit() = данные сохранены.
    """
    print("=== Демонстрация 3: flush() + commit() (успех) ===\n")

    async with AsyncSessionLocal() as db:
        # Создаём проект
        project = Project(name="Успешный проект")
        db.add(project)

        # flush()
        await db.flush()
        print(f"После flush(): project.id = {project.id}")

        # Проверки прошли успешно
        print("Все проверки прошли ✓\n")

        # commit()
        await db.commit()
        print("После commit(): данные сохранены навсегда\n")

    # Проверяем: есть ли проект в БД?
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Project))
        projects = list(result.scalars().all())

        print(f"Проектов в БД: {len(projects)}")
        for p in projects:
            print(f"  - {p.name}")
        print("\nВывод: flush() + commit() сохраняет данные\n")


async def demo_multiple_flush_before_commit():
    """
    Демонстрация 4: Несколько flush() в одной транзакции.
    """
    print("=== Демонстрация 4: Множественные flush() ===\n")

    try:
        async with AsyncSessionLocal() as db:
            # flush() #1
            project1 = Project(name="Проект 1")
            db.add(project1)
            await db.flush()
            print(f"flush() #1: project1.id = {project1.id}")

            # flush() #2
            project2 = Project(name="Проект 2")
            db.add(project2)
            await db.flush()
            print(f"flush() #2: project2.id = {project2.id}")

            # flush() #3
            project3 = Project(name="Проект 3")
            db.add(project3)
            await db.flush()
            print(f"flush() #3: project3.id = {project3.id}\n")

            # Имитируем ошибку ПОСЛЕ 3 flush()
            print("Проверяем условие...")
            if len("Проект 3") > 5:
                print("❌ ОШИБКА!\n")
                raise ValueError("Name too long")

            await db.commit()

    except ValueError as e:
        print(f"Исключение: {e}")
        print("Все 3 flush() откатились!\n")

    # Проверяем БД
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Project))
        projects = list(result.scalars().all())

        print(f"Проектов в БД: {len(projects)}")
        print("Вывод: ВСЕ flush() откатились, несмотря на успешное выполнение\n")


async def cleanup():
    """Очистить БД после демонстраций."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete
        await db.execute(delete(Project))
        await db.commit()


async def main():
    """Запуск всех демонстраций."""
    print("\n" + "="*60)
    print("  ДЕМОНСТРАЦИЯ: flush() vs commit()")
    print("="*60 + "\n")

    await cleanup()  # Очистить БД перед демонстрациями

    await demo_flush_without_commit()
    await demo_error_after_flush()
    await demo_successful_commit()
    await demo_multiple_flush_before_commit()

    await cleanup()  # Очистить после демонстраций

    print("="*60)
    print("  ИТОГО:")
    print("  • flush() - отправляет в БД, но НЕ сохраняет")
    print("  • commit() - сохраняет навсегда")
    print("  • Ошибка после flush() = автоматический rollback")
    print("  • Все flush() внутри транзакции откатятся вместе")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
