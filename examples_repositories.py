"""
Примеры использования Repository слоя.

Этот файл демонстрирует, как работать с репозиториями.
Для запуска нужна настроенная БД (см. README.md).
"""

import asyncio
from datetime import date, timedelta

from src.core.database import AsyncSessionLocal
from src.repositories import (
    ProjectRepository,
    TaskRepository,
    TagRepository,
    TaskCommentRepository,
)
from src.models import Project, Task, TaskStatus, TaskPriority, Tag, TaskComment


async def example_1_basic_crud():
    """
    Пример 1: Базовые CRUD операции.

    Демонстрирует:
    - Создание проекта
    - Получение по ID
    - Обновление
    - Удаление
    """
    print("=== Пример 1: Базовые CRUD операции ===\n")

    async with AsyncSessionLocal() as db:
        repo = ProjectRepository(db)

        # CREATE - создание проекта
        print("1. Создаём проект...")
        project = Project(
            name="Вайб-Кодинг",
            description="Учебный проект по программированию",
            obsidian_folder="01_Projects/Вайб-Кодинг",
            color="#3B82F6"
        )
        project = await repo.create(project)
        print(f"✓ Создан проект ID={project.id}: {project.name}\n")

        # READ - получение по ID
        print("2. Получаем проект по ID...")
        found = await repo.get_by_id(project.id)
        print(f"✓ Найден: {found.name}")
        print(f"   Папка Obsidian: {found.obsidian_folder}\n")

        # UPDATE - обновление
        print("3. Обновляем описание...")
        updated = await repo.update(
            project.id,
            description="Обновлённое описание: изучаем FastAPI и SQLAlchemy"
        )
        print(f"✓ Обновлено: {updated.description}\n")

        # DELETE - удаление
        print("4. Удаляем проект...")
        deleted = await repo.delete(project.id)
        print(f"✓ Удалён: {deleted}\n")

        # Коммитим изменения
        await db.commit()


async def example_2_relationships():
    """
    Пример 2: Работа со связями (relationships).

    Демонстрирует:
    - Создание проекта с задачами
    - Eager loading (selectinload)
    - Навигация по связям
    """
    print("=== Пример 2: Работа со связями ===\n")

    async with AsyncSessionLocal() as db:
        project_repo = ProjectRepository(db)
        task_repo = TaskRepository(db)

        # Создаём проект
        print("1. Создаём проект...")
        project = Project(name="API Development")
        project = await project_repo.create(project)
        print(f"✓ Проект создан: {project.name}\n")

        # Создаём задачи для проекта
        print("2. Создаём 3 задачи для проекта...")
        task1 = Task(
            title="Создать модели",
            project_id=project.id,
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH
        )
        task2 = Task(
            title="Создать API endpoints",
            project_id=project.id,
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH
        )
        task3 = Task(
            title="Написать тесты",
            project_id=project.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM
        )

        await task_repo.create(task1)
        await task_repo.create(task2)
        await task_repo.create(task3)
        print("✓ Задачи созданы\n")

        # Получаем проект со всеми задачами (eager loading)
        print("3. Получаем проект с задачами (eager loading)...")
        project_with_tasks = await project_repo.get_by_id_with_tasks(project.id)

        print(f"✓ Проект: {project_with_tasks.name}")
        print(f"   Задач: {len(project_with_tasks.tasks)}")
        for task in project_with_tasks.tasks:
            print(f"   - {task.title} [{task.status.value}]")
        print()

        await db.commit()


async def example_3_subtasks():
    """
    Пример 3: Работа с подзадачами (иерархия).

    Демонстрирует:
    - Self-referencing foreign key
    - Создание дерева задач
    - Навигацию по иерархии
    """
    print("=== Пример 3: Иерархия задач (подзадачи) ===\n")

    async with AsyncSessionLocal() as db:
        project_repo = ProjectRepository(db)
        task_repo = TaskRepository(db)

        # Создаём проект
        project = await project_repo.create(Project(name="Сайт"))

        # Создаём родительскую задачу
        print("1. Создаём родительскую задачу...")
        parent_task = Task(
            title="Разработать бэкенд",
            project_id=project.id,
            priority=TaskPriority.HIGH
        )
        parent_task = await task_repo.create(parent_task)
        print(f"✓ Родительская задача: {parent_task.title}\n")

        # Создаём подзадачи
        print("2. Создаём 3 подзадачи...")
        subtasks = [
            Task(
                title="Настроить базу данных",
                project_id=project.id,
                parent_task_id=parent_task.id,  # ← связь с родителем!
                priority=TaskPriority.HIGH
            ),
            Task(
                title="Создать API endpoints",
                project_id=project.id,
                parent_task_id=parent_task.id,
                priority=TaskPriority.MEDIUM
            ),
            Task(
                title="Написать документацию",
                project_id=project.id,
                parent_task_id=parent_task.id,
                priority=TaskPriority.LOW
            ),
        ]

        for subtask in subtasks:
            await task_repo.create(subtask)
        print("✓ Подзадачи созданы\n")

        # Получаем подзадачи
        print("3. Получаем все подзадачи...")
        found_subtasks = await task_repo.get_subtasks(parent_task.id)
        print(f"✓ Найдено подзадач: {len(found_subtasks)}")
        for st in found_subtasks:
            print(f"   - {st.title}")
        print()

        # Получаем корневые задачи (без родителя)
        print("4. Получаем корневые задачи проекта...")
        root_tasks = await task_repo.get_root_tasks(project.id)
        print(f"✓ Корневых задач: {len(root_tasks)}")
        for rt in root_tasks:
            print(f"   - {rt.title}")
        print()

        await db.commit()


async def example_4_tags():
    """
    Пример 4: Работа с тегами (Many-to-Many).

    Демонстрирует:
    - Создание тегов
    - get_or_create паттерн
    - Привязка тегов к задачам
    - Поиск задач по тегу
    """
    print("=== Пример 4: Теги (Many-to-Many) ===\n")

    async with AsyncSessionLocal() as db:
        project_repo = ProjectRepository(db)
        task_repo = TaskRepository(db)
        tag_repo = TagRepository(db)

        # Создаём проект и задачу
        project = await project_repo.create(Project(name="Учёба"))
        task = await task_repo.create(Task(
            title="Изучить SQLAlchemy",
            project_id=project.id
        ))

        # Создаём/получаем теги
        print("1. Создаём теги через get_or_create...")
        tag1 = await tag_repo.get_or_create("python")
        tag2 = await tag_repo.get_or_create("database")
        tag3 = await tag_repo.get_or_create("backend")
        print(f"✓ Теги: {tag1.name}, {tag2.name}, {tag3.name}\n")

        # Пытаемся создать тег "python" ещё раз - вернётся существующий
        print("2. Пытаемся создать 'python' ещё раз...")
        duplicate = await tag_repo.get_or_create("python")
        print(f"✓ Вернулся существующий тег ID={duplicate.id} (не создан дубликат)\n")

        # Привязываем теги к задаче
        print("3. Привязываем теги к задаче...")
        await task_repo.add_tag(task.id, tag1)
        await task_repo.add_tag(task.id, tag2)
        await task_repo.add_tag(task.id, tag3)
        print("✓ Теги привязаны\n")

        # Получаем задачу с тегами
        print("4. Получаем задачу с тегами...")
        task_full = await task_repo.get_by_id_full(task.id)
        print(f"✓ Задача: {task_full.title}")
        print(f"   Теги: {', '.join(t.name for t in task_full.tags)}\n")

        # Ищем задачи по тегу
        print("5. Ищем все задачи с тегом 'python'...")
        python_tasks = await task_repo.get_tasks_by_tag(tag1.id)
        print(f"✓ Найдено задач: {len(python_tasks)}")
        for t in python_tasks:
            print(f"   - {t.title}")
        print()

        await db.commit()


async def example_5_filters():
    """
    Пример 5: Фильтрация и поиск.

    Демонстрирует:
    - Фильтрацию по статусу/приоритету
    - Поиск просроченных задач
    - Полнотекстовый поиск
    """
    print("=== Пример 5: Фильтрация и поиск ===\n")

    async with AsyncSessionLocal() as db:
        project_repo = ProjectRepository(db)
        task_repo = TaskRepository(db)

        project = await project_repo.create(Project(name="Тестовый проект"))

        # Создаём задачи с разными статусами
        print("1. Создаём задачи с разными статусами...")
        await task_repo.create(Task(
            title="Срочная задача",
            project_id=project.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            due_date=date.today() - timedelta(days=2)  # просрочена!
        ))
        await task_repo.create(Task(
            title="В работе",
            project_id=project.id,
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM
        ))
        await task_repo.create(Task(
            title="Готово",
            project_id=project.id,
            status=TaskStatus.DONE,
            priority=TaskPriority.LOW
        ))
        print("✓ Задачи созданы\n")

        # Фильтр по статусу
        print("2. Получаем задачи в работе...")
        in_progress = await task_repo.get_by_status(TaskStatus.IN_PROGRESS)
        print(f"✓ В работе: {len(in_progress)} задач")
        for t in in_progress:
            print(f"   - {t.title}")
        print()

        # Фильтр по приоритету
        print("3. Получаем высокоприоритетные задачи...")
        high_priority = await task_repo.get_by_priority(TaskPriority.HIGH)
        print(f"✓ Высокий приоритет: {len(high_priority)} задач")
        for t in high_priority:
            print(f"   - {t.title}")
        print()

        # Просроченные задачи
        print("4. Получаем просроченные задачи...")
        overdue = await task_repo.get_overdue_tasks()
        print(f"✓ Просрочено: {len(overdue)} задач")
        for t in overdue:
            print(f"   - {t.title} (срок: {t.due_date})")
        print()

        # Поиск по названию
        print("5. Ищем задачи со словом 'задача'...")
        found = await task_repo.search_by_title("задача")
        print(f"✓ Найдено: {len(found)} задач")
        for t in found:
            print(f"   - {t.title}")
        print()

        await db.commit()


async def example_6_comments():
    """
    Пример 6: Работа с комментариями.

    Демонстрирует:
    - Добавление комментариев
    - Поиск по содержимому
    - Подсчёт комментариев
    """
    print("=== Пример 6: Комментарии к задачам ===\n")

    async with AsyncSessionLocal() as db:
        project_repo = ProjectRepository(db)
        task_repo = TaskRepository(db)
        comment_repo = TaskCommentRepository(db)

        # Создаём проект и задачу
        project = await project_repo.create(Project(name="Проект с багом"))
        task = await task_repo.create(Task(
            title="Исправить баг в авторизации",
            project_id=project.id
        ))

        # Добавляем комментарии
        print("1. Добавляем комментарии к задаче...")
        await comment_repo.create(TaskComment(
            task_id=task.id,
            content="Нашёл баг: пользователь может войти с пустым паролем"
        ))
        await comment_repo.create(TaskComment(
            task_id=task.id,
            content="Исправил валидацию, теперь требуется минимум 8 символов"
        ))
        await comment_repo.create(TaskComment(
            task_id=task.id,
            content="Добавил тесты для проверки валидации"
        ))
        print("✓ Комментарии добавлены\n")

        # Получаем комментарии задачи
        print("2. Получаем все комментарии задачи...")
        comments = await comment_repo.get_by_task(task.id)
        print(f"✓ Комментариев: {len(comments)}")
        for c in comments:
            preview = c.content[:50] + "..." if len(c.content) > 50 else c.content
            print(f"   - {preview}")
        print()

        # Поиск по содержимому
        print("3. Ищем комментарии со словом 'валидация'...")
        found = await comment_repo.search_comments("валидация")
        print(f"✓ Найдено: {len(found)} комментариев")
        for c in found:
            print(f"   - {c.content}")
        print()

        # Подсчёт комментариев
        print("4. Подсчитываем комментарии...")
        count = await comment_repo.count_by_task(task.id)
        print(f"✓ Всего комментариев: {count}\n")

        await db.commit()


async def main():
    """Запуск всех примеров."""
    print("\n" + "="*60)
    print("  ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ REPOSITORY СЛОЯ")
    print("="*60 + "\n")

    try:
        await example_1_basic_crud()
        await example_2_relationships()
        await example_3_subtasks()
        await example_4_tags()
        await example_5_filters()
        await example_6_comments()

        print("="*60)
        print("  ВСЕ ПРИМЕРЫ ВЫПОЛНЕНЫ УСПЕШНО!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\nУбедитесь, что:")
        print("1. PostgreSQL запущен")
        print("2. База данных создана (createdb obsidian_tasks)")
        print("3. .env файл настроен")
        print("4. Миграции применены (alembic upgrade head)")


if __name__ == "__main__":
    asyncio.run(main())
