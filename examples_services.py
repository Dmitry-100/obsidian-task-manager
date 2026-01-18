"""
Примеры использования Service слоя.

Демонстрирует разницу между Repository и Service подходами,
а также показывает бизнес-логику в действии.
"""

import asyncio
from datetime import date, timedelta

from src.core.database import AsyncSessionLocal
from src.services import ProjectService, TaskService, TagService
from src.models import TaskStatus, TaskPriority


async def example_1_basic_service():
    """
    Пример 1: Базовое использование Service.

    Демонстрирует:
    - Создание проекта через сервис
    - Валидация на уровне Service
    - Обработка ошибок
    """
    print("=== Пример 1: Базовое использование Service ===\n")

    async with AsyncSessionLocal() as db:
        service = ProjectService(db)

        # УСПЕХ: Создание проекта с валидными данными
        print("1. Создаём проект с валидными данными...")
        try:
            project = await service.create_project(
                name="Вайб-Кодинг Week 4",
                description="Изучение баз данных",
                color="#3B82F6"
            )
            print(f"✓ Проект создан: {project.name}")
            print(f"  ID: {project.id}")
            print(f"  Цвет: {project.color}\n")
        except ValueError as e:
            print(f"❌ Ошибка: {e}\n")

        # ОШИБКА: Попытка создать дубликат
        print("2. Пытаемся создать проект с тем же названием...")
        try:
            duplicate = await service.create_project(
                name="Вайб-Кодинг Week 4",  # дубликат!
                description="Другое описание"
            )
            print(f"✓ Проект создан: {duplicate.name}\n")
        except ValueError as e:
            print(f"✓ Валидация сработала!")
            print(f"  Ошибка: {e}\n")

        # ОШИБКА: Некорректный цвет
        print("3. Пытаемся создать проект с некорректным цветом...")
        try:
            project = await service.create_project(
                name="Тестовый проект",
                color="red"  # неправильный формат!
            )
            print(f"✓ Проект создан: {project.name}\n")
        except ValueError as e:
            print(f"✓ Валидация сработала!")
            print(f"  Ошибка: {e}\n")

        # ОШИБКА: Пустое название
        print("4. Пытаемся создать проект с пустым названием...")
        try:
            project = await service.create_project(
                name="   ",  # только пробелы!
                description="Описание"
            )
            print(f"✓ Проект создан: {project.name}\n")
        except ValueError as e:
            print(f"✓ Валидация сработала!")
            print(f"  Ошибка: {e}\n")


async def example_2_service_coordination():
    """
    Пример 2: Координация между сервисами.

    Демонстрирует:
    - Создание задачи с автоматическим созданием тегов
    - Координация TaskService + TagService
    - Транзакции (всё или ничего)
    """
    print("=== Пример 2: Координация сервисов ===\n")

    async with AsyncSessionLocal() as db:
        project_service = ProjectService(db)
        task_service = TaskService(db)

        # Создаём проект
        print("1. Создаём проект...")
        project = await project_service.create_project(
            name="Backend Development"
        )
        print(f"✓ Проект: {project.name}\n")

        # Создаём задачу с тегами
        print("2. Создаём задачу с тегами...")
        print("   Теги: python, fastapi, database")
        print("   (теги будут созданы автоматически!)\n")

        task = await task_service.create_task(
            title="Создать REST API",
            project_id=project.id,
            description="Реализовать CRUD endpoints",
            priority=TaskPriority.HIGH,
            due_date=date.today() + timedelta(days=7),
            tag_names=["python", "fastapi", "database"]  # ← автосоздание!
        )

        print(f"✓ Задача создана: {task.title}")
        print(f"  Теги: {', '.join(t.name for t in task.tags)}")
        print(f"  Дедлайн: {task.due_date}\n")

        # Добавляем ещё теги
        print("3. Добавляем ещё теги к задаче...")
        task = await task_service.add_tags_to_task(
            task.id,
            ["backend", "api", "postgresql"]
        )
        print(f"✓ Теги обновлены: {', '.join(t.name for t in task.tags)}\n")


async def example_3_business_logic_validation():
    """
    Пример 3: Валидация бизнес-правил.

    Демонстрирует:
    - Нельзя добавить задачу в архивный проект
    - Нельзя завершить задачу с незавершёнными подзадачами
    - Нельзя создать циклические зависимости
    """
    print("=== Пример 3: Валидация бизнес-правил ===\n")

    async with AsyncSessionLocal() as db:
        project_service = ProjectService(db)
        task_service = TaskService(db)

        # Создаём и архивируем проект
        print("1. Создаём и архивируем проект...")
        project = await project_service.create_project(name="Старый проект")
        await project_service.archive_project(project.id)
        print(f"✓ Проект '{project.name}' архивирован\n")

        # Пытаемся добавить задачу в архивный проект
        print("2. Пытаемся добавить задачу в архивный проект...")
        try:
            task = await task_service.create_task(
                title="Новая задача",
                project_id=project.id  # архивный проект!
            )
            print(f"✓ Задача создана: {task.title}\n")
        except ValueError as e:
            print(f"✓ Валидация сработала!")
            print(f"  Ошибка: {e}\n")

        # Создаём активный проект
        print("3. Создаём активный проект для тестов...")
        active_project = await project_service.create_project(name="Активный проект")

        # Создаём родительскую задачу с подзадачей
        print("4. Создаём задачу с подзадачей...")
        parent = await task_service.create_task(
            title="Разработать фичу",
            project_id=active_project.id
        )

        subtask = await task_service.create_task(
            title="Написать тесты",
            project_id=active_project.id,
            parent_task_id=parent.id,
            status=TaskStatus.TODO
        )
        print(f"✓ Родитель: {parent.title}")
        print(f"  Подзадача: {subtask.title}\n")

        # Пытаемся завершить родителя с незавершённой подзадачей
        print("5. Пытаемся завершить задачу с незавершённой подзадачей...")
        try:
            await task_service.complete_task(parent.id)
            print("✓ Задача завершена\n")
        except ValueError as e:
            print(f"✓ Валидация сработала!")
            print(f"  Ошибка: {e}\n")

        # Сначала завершаем подзадачу
        print("6. Завершаем сначала подзадачу...")
        await task_service.update_task(subtask.id, status=TaskStatus.DONE)
        print("✓ Подзадача завершена\n")

        # Теперь можем завершить родителя
        print("7. Теперь завершаем родительскую задачу...")
        parent = await task_service.complete_task(parent.id)
        print(f"✓ Задача завершена: {parent.title}")
        print(f"  Статус: {parent.status.value}")
        print(f"  Завершена: {parent.completed_at}\n")


async def example_4_complex_operations():
    """
    Пример 4: Сложные операции.

    Демонстрирует:
    - Получение статистики
    - Работу с иерархией задач
    - Слияние тегов
    """
    print("=== Пример 4: Сложные операции ===\n")

    async with AsyncSessionLocal() as db:
        project_service = ProjectService(db)
        task_service = TaskService(db)
        tag_service = TagService(db)

        # Создаём проект с задачами
        print("1. Создаём проект с несколькими задачами...")
        project = await project_service.create_project(name="Учебный проект")

        for i in range(1, 6):
            status = TaskStatus.DONE if i <= 3 else TaskStatus.TODO
            await task_service.create_task(
                title=f"Задача {i}",
                project_id=project.id,
                status=status
            )
        print("✓ Создано 5 задач (3 завершённые)\n")

        # Получаем статистику проекта
        print("2. Получаем статистику проекта...")
        stats = await project_service.get_project_statistics(project.id)
        print(f"✓ Проект: {stats['project_name']}")
        print(f"  Всего задач: {stats['total_tasks']}")
        print(f"  Завершено: {stats['completed_tasks']}")
        print(f"  В работе: {stats['in_progress_tasks']}")
        print(f"  К выполнению: {stats['todo_tasks']}")
        print(f"  Прогресс: {stats['completion_percentage']}%\n")

        # Создаём теги
        print("3. Создаём теги...")
        tag1 = await tag_service.get_or_create_tag("python3")
        tag2 = await tag_service.get_or_create_tag("python")
        print(f"✓ Теги созданы: {tag1.name}, {tag2.name}\n")

        # Объединяем теги
        print("4. Объединяем теги 'python3' → 'python'...")
        merged = await tag_service.merge_tags(
            source_tag_id=tag1.id,
            target_tag_id=tag2.id
        )
        print(f"✓ Теги объединены в: {merged.name}")
        print(f"  Тег 'python3' удалён\n")


async def example_5_repository_vs_service():
    """
    Пример 5: Разница между Repository и Service.

    Демонстрирует:
    - Repository: простые операции с БД
    - Service: бизнес-логика и валидация
    """
    print("=== Пример 5: Repository vs Service ===\n")

    async with AsyncSessionLocal() as db:
        from src.repositories import ProjectRepository

        project_repo = ProjectRepository(db)
        project_service = ProjectService(db)

        print("--- ЧЕРЕЗ REPOSITORY (без валидации) ---\n")

        # Repository не валидирует
        from src.models import Project

        print("1. Создаём проект через Repository...")
        print("   (название пустое - Repository не проверяет!)\n")

        project = Project(name="")  # пустое название!
        created = await project_repo.create(project)
        await db.commit()

        print(f"✓ Создано через Repository:")
        print(f"  ID: {created.id}")
        print(f"  Название: '{created.name}' (пустое!)\n")

        print("--- ЧЕРЕЗ SERVICE (с валидацией) ---\n")

        print("2. Пытаемся создать проект через Service...")
        print("   (название пустое - Service проверяет!)\n")

        try:
            project = await project_service.create_project(name="")
            print(f"✓ Создано через Service: {project.name}\n")
        except ValueError as e:
            print(f"✓ Service отклонил некорректные данные:")
            print(f"  Ошибка: {e}\n")

        print("ВЫВОД:")
        print("  • Repository - простое сохранение в БД")
        print("  • Service - проверка бизнес-правил\n")


async def example_6_error_handling():
    """
    Пример 6: Обработка ошибок и транзакции.

    Демонстрирует:
    - Откат транзакций при ошибке
    - Целостность данных
    """
    print("=== Пример 6: Обработка ошибок ===\n")

    async with AsyncSessionLocal() as db:
        task_service = TaskService(db)

        print("1. Пытаемся создать задачу с несуществующим проектом...")
        try:
            task = await task_service.create_task(
                title="Задача без проекта",
                project_id=9999  # не существует!
            )
            print(f"✓ Задача создана: {task.title}\n")
        except ValueError as e:
            print(f"✓ Ошибка поймана!")
            print(f"  {e}")
            print(f"  Транзакция откачена, БД не изменена\n")


async def example_7_tag_normalization():
    """
    Пример 7: Нормализация тегов для Obsidian.

    Демонстрирует:
    - Автоматическое приведение к формату Obsidian
    - Lowercase, замена пробелов, удаление спецсимволов
    """
    print("=== Пример 7: Нормализация тегов ===\n")

    async with AsyncSessionLocal() as db:
        tag_service = TagService(db)

        test_names = [
            "Python Programming",
            "Web  Dev",
            "C++",
            "Test_Tag",
            "UPPERCASE",
        ]

        print("Создаём теги с разными форматами...\n")

        for name in test_names:
            tag = await tag_service.get_or_create_tag(name)
            print(f"  '{name}' → '{tag.name}'")

        print()


async def main():
    """Запуск всех примеров."""
    print("\n" + "="*60)
    print("  ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ SERVICE СЛОЯ")
    print("="*60 + "\n")

    try:
        await example_1_basic_service()
        await example_2_service_coordination()
        await example_3_business_logic_validation()
        await example_4_complex_operations()
        await example_5_repository_vs_service()
        await example_6_error_handling()
        await example_7_tag_normalization()

        print("="*60)
        print("  ВСЕ ПРИМЕРЫ ВЫПОЛНЕНЫ УСПЕШНО!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
