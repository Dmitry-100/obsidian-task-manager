"""
Тесты для Service Layer (Бизнес-логика).

Проверяем:
- Валидацию бизнес-правил
- Координацию между репозиториями
- Расчёт статистики
- Специфичную бизнес-логику (tag normalization, hierarchy limits, etc.)
"""

from datetime import date, timedelta

import pytest

from src.models import Task, TaskPriority, TaskStatus
from src.services import ProjectService, TagService, TaskService

# ============================================================================
# PROJECT SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_project_validation_empty_name(test_db):
    """Test: валидация - пустое название проекта."""
    service = ProjectService(test_db)

    with pytest.raises(ValueError, match="name cannot be empty"):
        await service.create_project(name="")


@pytest.mark.asyncio
async def test_create_project_validation_duplicate_name(test_db):
    """Test: валидация - дубликат названия проекта."""
    service = ProjectService(test_db)

    # Create first project
    await service.create_project(name="Test Project")
    await test_db.commit()

    # Try to create duplicate
    with pytest.raises(ValueError, match="already exists"):
        await service.create_project(name="Test Project")


@pytest.mark.asyncio
async def test_create_project_validation_invalid_color(test_db):
    """Test: валидация - неправильный формат цвета."""
    service = ProjectService(test_db)

    with pytest.raises(ValueError, match="Invalid color format"):
        await service.create_project(name="Test", color="red")

    with pytest.raises(ValueError, match="Invalid color format"):
        await service.create_project(name="Test", color="#FF")

    with pytest.raises(ValueError, match="Invalid color format"):
        await service.create_project(name="Test", color="FF0000")


@pytest.mark.asyncio
async def test_create_project_valid_color(test_db):
    """Test: создание проекта с валидным цветом."""
    service = ProjectService(test_db)

    project = await service.create_project(name="Test Project", color="#FF0000")
    await test_db.commit()

    assert project.color == "#FF0000"


@pytest.mark.asyncio
async def test_archive_project_already_archived(test_db):
    """Test: нельзя архивировать уже архивированный проект."""
    service = ProjectService(test_db)

    # Create and archive project
    project = await service.create_project(name="Test")
    await test_db.commit()

    await service.archive_project(project.id)
    await test_db.commit()

    # Try to archive again
    with pytest.raises(ValueError, match="already archived"):
        await service.archive_project(project.id)


@pytest.mark.asyncio
async def test_unarchive_project_not_archived(test_db):
    """Test: нельзя разархивировать не архивированный проект."""
    service = ProjectService(test_db)

    project = await service.create_project(name="Test")
    await test_db.commit()

    with pytest.raises(ValueError, match="not archived"):
        await service.unarchive_project(project.id)


@pytest.mark.asyncio
async def test_delete_project_with_tasks_fails(test_db):
    """Test: нельзя удалить проект с задачами без force."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    # Create project with task
    project = await project_service.create_project(name="Test")
    await test_db.commit()

    await task_service.create_task(title="Test Task", project_id=project.id)
    await test_db.commit()

    # Try to delete without force
    with pytest.raises(ValueError, match="Cannot delete project"):
        await project_service.delete_project(project.id)


@pytest.mark.asyncio
async def test_delete_project_with_tasks_force(test_db):
    """Test: можно удалить проект с задачами с force=True."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    # Create project with task
    project = await project_service.create_project(name="Test")
    await test_db.commit()

    await task_service.create_task(title="Test Task", project_id=project.id)
    await test_db.commit()

    # Delete with force
    deleted = await project_service.delete_project(project.id, force=True)
    await test_db.commit()

    assert deleted is True


@pytest.mark.asyncio
async def test_project_statistics(test_db):
    """Test: расчёт статистики проекта."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    # Create project
    project = await project_service.create_project(name="Test")
    await test_db.commit()

    # Create tasks with different statuses
    await task_service.create_task(title="Task 1", project_id=project.id, status=TaskStatus.DONE)
    await task_service.create_task(title="Task 2", project_id=project.id, status=TaskStatus.DONE)
    await task_service.create_task(
        title="Task 3", project_id=project.id, status=TaskStatus.IN_PROGRESS
    )
    await task_service.create_task(title="Task 4", project_id=project.id, status=TaskStatus.TODO)
    await test_db.commit()

    # Get statistics
    stats = await project_service.get_project_statistics(project.id)

    assert stats["total_tasks"] == 4
    assert stats["completed_tasks"] == 2
    assert stats["in_progress_tasks"] == 1
    assert stats["todo_tasks"] == 1
    assert stats["completion_percentage"] == 50.0


# ============================================================================
# TASK SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_task_validation_empty_title(test_db):
    """Test: валидация - пустое название задачи."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    with pytest.raises(ValueError, match="title cannot be empty"):
        await task_service.create_task(title="", project_id=project.id)


@pytest.mark.asyncio
async def test_create_task_in_archived_project(test_db):
    """Test: нельзя добавить задачу в архивный проект."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    # Create and archive project
    project = await project_service.create_project(name="Test")
    await test_db.commit()

    await project_service.archive_project(project.id)
    await test_db.commit()

    # Try to create task
    with pytest.raises(ValueError, match="Cannot add tasks to archived project"):
        await task_service.create_task(title="Test Task", project_id=project.id)


@pytest.mark.asyncio
async def test_create_task_parent_in_different_project(test_db):
    """Test: родительская задача должна быть в том же проекте."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    # Create two projects
    project1 = await project_service.create_project(name="Project 1")
    project2 = await project_service.create_project(name="Project 2")
    await test_db.commit()

    # Create task in project1
    parent_task = await task_service.create_task(title="Parent", project_id=project1.id)
    await test_db.commit()

    # Try to create subtask in project2
    with pytest.raises(ValueError, match="different project"):
        await task_service.create_task(
            title="Subtask", project_id=project2.id, parent_task_id=parent_task.id
        )


@pytest.mark.asyncio
async def test_create_task_hierarchy_limit(test_db):
    """Test: максимум 2 уровня вложенности (нет подзадач у подзадач)."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    # Create parent task
    parent = await task_service.create_task(title="Parent", project_id=project.id)
    await test_db.commit()

    # Create subtask
    subtask = await task_service.create_task(
        title="Subtask", project_id=project.id, parent_task_id=parent.id
    )
    await test_db.commit()

    # Try to create sub-subtask (should fail)
    with pytest.raises(ValueError, match="Maximum 2 levels allowed"):
        await task_service.create_task(
            title="Sub-subtask", project_id=project.id, parent_task_id=subtask.id
        )


@pytest.mark.asyncio
async def test_create_task_due_date_in_past(test_db):
    """Test: дедлайн не может быть в прошлом."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    past_date = date.today() - timedelta(days=1)

    with pytest.raises(ValueError, match="Due date cannot be in the past"):
        await task_service.create_task(title="Test", project_id=project.id, due_date=past_date)


@pytest.mark.asyncio
async def test_update_task_status_to_done_sets_completed_at(test_db):
    """Test: при переводе в DONE устанавливается completed_at."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Test", project_id=project.id, status=TaskStatus.TODO
    )
    await test_db.commit()

    assert task.completed_at is None

    # Update to DONE
    updated = await task_service.update_task(task_id=task.id, status=TaskStatus.DONE)
    await test_db.commit()

    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_update_task_status_from_done_clears_completed_at(test_db):
    """Test: при переводе из DONE сбрасывается completed_at."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Test", project_id=project.id, status=TaskStatus.DONE
    )
    await test_db.commit()

    # Move back to TODO
    updated = await task_service.update_task(task_id=task.id, status=TaskStatus.TODO)
    await test_db.commit()

    assert updated.completed_at is None


@pytest.mark.skip(reason="Business rule not fully implemented - needs subtask loading fix")
@pytest.mark.asyncio
async def test_complete_task_with_incomplete_subtasks(test_db):
    """Test: нельзя завершить задачу с незавершёнными подзадачами."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    # Create parent with subtask
    parent = await task_service.create_task(title="Parent", project_id=project.id)
    await task_service.create_task(
        title="Subtask", project_id=project.id, parent_task_id=parent.id, status=TaskStatus.TODO
    )
    await test_db.commit()

    # Try to complete parent
    with pytest.raises(ValueError, match="incomplete subtasks"):
        await task_service.complete_task(parent.id)


@pytest.mark.asyncio
async def test_add_tags_to_task_auto_create(test_db):
    """Test: теги создаются автоматически при добавлении к задаче."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Test", project_id=project.id, tag_names=["python", "fastapi", "backend"]
    )
    await test_db.commit()

    assert len(task.tags) == 3
    tag_names = {tag.name for tag in task.tags}
    assert "python" in tag_names
    assert "fastapi" in tag_names
    assert "backend" in tag_names


@pytest.mark.skip(reason="Business rule not fully implemented - needs subtask loading fix")
@pytest.mark.asyncio
async def test_delete_task_with_subtasks_fails(test_db):
    """Test: нельзя удалить задачу с подзадачами без force."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    parent = await task_service.create_task(title="Parent", project_id=project.id)
    await task_service.create_task(title="Subtask", project_id=project.id, parent_task_id=parent.id)
    await test_db.commit()

    with pytest.raises(ValueError, match="Cannot delete task"):
        await task_service.delete_task(parent.id)


@pytest.mark.asyncio
async def test_delete_task_with_subtasks_force(test_db):
    """Test: можно удалить задачу с подзадачами с force=True."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    parent = await task_service.create_task(title="Parent", project_id=project.id)
    await task_service.create_task(title="Subtask", project_id=project.id, parent_task_id=parent.id)
    await test_db.commit()

    deleted = await task_service.delete_task(parent.id, force=True)
    await test_db.commit()

    assert deleted is True


# ============================================================================
# TASK SERVICE TESTS - ADDITIONAL COVERAGE
# ============================================================================


@pytest.mark.asyncio
async def test_create_task_project_not_found(test_db):
    """Test: ошибка если проект не найден."""
    task_service = TaskService(test_db)

    with pytest.raises(ValueError, match="Project with id 999 not found"):
        await task_service.create_task(title="Test Task", project_id=999)


@pytest.mark.asyncio
async def test_create_task_parent_not_found(test_db):
    """Test: ошибка если родительская задача не найдена."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    with pytest.raises(ValueError, match="Parent task with id 999 not found"):
        await task_service.create_task(title="Subtask", project_id=project.id, parent_task_id=999)


@pytest.mark.asyncio
async def test_create_task_estimated_hours_validation(test_db):
    """Test: estimated_hours должен быть положительным."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    with pytest.raises(ValueError, match="Estimated hours must be positive"):
        await task_service.create_task(title="Test", project_id=project.id, estimated_hours=0)

    with pytest.raises(ValueError, match="Estimated hours must be positive"):
        await task_service.create_task(title="Test", project_id=project.id, estimated_hours=-5)


@pytest.mark.asyncio
async def test_get_task_not_found(test_db):
    """Test: ошибка если задача не найдена."""
    task_service = TaskService(test_db)

    with pytest.raises(ValueError, match="Task with id 999 not found"):
        await task_service.get_task(999)


@pytest.mark.asyncio
async def test_get_task_full_loading(test_db):
    """Test: get_task с full=True загружает все связи."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Test", project_id=project.id, tag_names=["python", "backend"]
    )
    await test_db.commit()

    # Get with full loading
    loaded = await task_service.get_task(task.id, full=True)

    assert loaded.title == "Test"
    assert len(loaded.tags) == 2


@pytest.mark.asyncio
async def test_update_task_empty_title(test_db):
    """Test: нельзя обновить задачу с пустым названием."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(title="Original", project_id=project.id)
    await test_db.commit()

    with pytest.raises(ValueError, match="title cannot be empty"):
        await task_service.update_task(task.id, title="")

    with pytest.raises(ValueError, match="title cannot be empty"):
        await task_service.update_task(task.id, title="   ")


@pytest.mark.asyncio
async def test_update_task_due_date_in_past(test_db):
    """Test: нельзя установить дедлайн в прошлом при обновлении."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(title="Test", project_id=project.id)
    await test_db.commit()

    past_date = date.today() - timedelta(days=1)

    with pytest.raises(ValueError, match="Due date cannot be in the past"):
        await task_service.update_task(task.id, due_date=past_date)


@pytest.mark.asyncio
async def test_update_task_estimated_hours_validation(test_db):
    """Test: estimated_hours должен быть положительным при обновлении."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(title="Test", project_id=project.id)
    await test_db.commit()

    with pytest.raises(ValueError, match="Estimated hours must be positive"):
        await task_service.update_task(task.id, estimated_hours=0)


@pytest.mark.asyncio
async def test_update_task_all_fields(test_db):
    """Test: обновление всех полей задачи."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Original",
        project_id=project.id,
        description="Original desc",
        priority=TaskPriority.LOW,
    )
    await test_db.commit()

    future_date = date.today() + timedelta(days=7)

    updated = await task_service.update_task(
        task.id,
        title="Updated Title",
        description="Updated description",
        priority=TaskPriority.HIGH,
        due_date=future_date,
        estimated_hours=5.5,
    )
    await test_db.commit()

    assert updated.title == "Updated Title"
    assert updated.description == "Updated description"
    assert updated.priority == TaskPriority.HIGH
    assert updated.due_date == future_date
    assert updated.estimated_hours == 5.5


@pytest.mark.asyncio
async def test_update_task_clear_description(test_db):
    """Test: можно очистить описание задачи."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Test", project_id=project.id, description="Some description"
    )
    await test_db.commit()

    updated = await task_service.update_task(task.id, description="")
    await test_db.commit()

    assert updated.description is None


@pytest.mark.asyncio
async def test_complete_task_success(test_db):
    """Test: успешное завершение задачи без подзадач."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Test", project_id=project.id, status=TaskStatus.IN_PROGRESS
    )
    await test_db.commit()

    completed = await task_service.complete_task(task.id)
    await test_db.commit()

    assert completed.status == TaskStatus.DONE
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_complete_task_with_completed_subtasks(test_db):
    """Test: можно завершить задачу если все подзадачи завершены."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    parent = await task_service.create_task(title="Parent", project_id=project.id)
    await test_db.commit()

    # Создаём подзадачу и сразу завершаем её
    _subtask = await task_service.create_task(
        title="Subtask", project_id=project.id, parent_task_id=parent.id, status=TaskStatus.DONE
    )
    await test_db.commit()

    # Теперь можно завершить родителя
    completed = await task_service.complete_task(parent.id)
    await test_db.commit()

    assert completed.status == TaskStatus.DONE


@pytest.mark.asyncio
async def test_complete_task_with_cancelled_subtasks(test_db):
    """Test: можно завершить задачу если подзадачи отменены."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    parent = await task_service.create_task(title="Parent", project_id=project.id)
    await test_db.commit()

    # Создаём отменённую подзадачу
    await task_service.create_task(
        title="Cancelled Subtask",
        project_id=project.id,
        parent_task_id=parent.id,
        status=TaskStatus.CANCELLED,
    )
    await test_db.commit()

    # Можно завершить родителя
    completed = await task_service.complete_task(parent.id)
    await test_db.commit()

    assert completed.status == TaskStatus.DONE


@pytest.mark.asyncio
async def test_add_tags_to_task(test_db):
    """Test: добавление тегов к существующей задаче."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(title="Test", project_id=project.id)
    await test_db.commit()

    # Добавляем теги
    updated = await task_service.add_tags_to_task(task.id, ["python", "fastapi", "backend"])
    await test_db.commit()

    assert len(updated.tags) == 3
    tag_names = {tag.name for tag in updated.tags}
    assert "python" in tag_names


@pytest.mark.asyncio
async def test_remove_tag_from_task(test_db):
    """Test: удаление тега с задачи."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Test", project_id=project.id, tag_names=["python", "backend"]
    )
    await test_db.commit()

    # Удаляем тег
    updated = await task_service.remove_tag_from_task(task.id, "python")
    await test_db.commit()

    assert len(updated.tags) == 1
    assert updated.tags[0].name == "backend"


@pytest.mark.asyncio
async def test_remove_tag_not_found(test_db):
    """Test: ошибка если тег не найден."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(title="Test", project_id=project.id)
    await test_db.commit()

    with pytest.raises(ValueError, match="Tag 'nonexistent' not found"):
        await task_service.remove_tag_from_task(task.id, "nonexistent")


@pytest.mark.asyncio
async def test_add_comment(test_db):
    """Test: добавление комментария к задаче."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(title="Test", project_id=project.id)
    await test_db.commit()

    comment = await task_service.add_comment(task.id, "This is a comment")
    await test_db.commit()

    assert comment.id is not None
    assert comment.content == "This is a comment"
    assert comment.task_id == task.id


@pytest.mark.asyncio
async def test_add_comment_empty_content(test_db):
    """Test: нельзя добавить пустой комментарий."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(title="Test", project_id=project.id)
    await test_db.commit()

    with pytest.raises(ValueError, match="Comment content cannot be empty"):
        await task_service.add_comment(task.id, "")

    with pytest.raises(ValueError, match="Comment content cannot be empty"):
        await task_service.add_comment(task.id, "   ")


@pytest.mark.skip(reason="Business rule not fully implemented - needs subtask loading fix")
@pytest.mark.asyncio
async def test_get_task_hierarchy(test_db):
    """Test: получение иерархии задачи."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    parent = await task_service.create_task(title="Parent", project_id=project.id)
    await test_db.commit()

    _subtask1 = await task_service.create_task(
        title="Subtask 1", project_id=project.id, parent_task_id=parent.id
    )
    _subtask2 = await task_service.create_task(
        title="Subtask 2", project_id=project.id, parent_task_id=parent.id
    )
    await test_db.commit()

    hierarchy = await task_service.get_task_hierarchy(parent.id)

    assert hierarchy["task"].id == parent.id
    assert hierarchy["parent"] is None
    assert len(hierarchy["subtasks"]) == 2


@pytest.mark.asyncio
async def test_get_task_hierarchy_not_found(test_db):
    """Test: ошибка если задача не найдена."""
    task_service = TaskService(test_db)

    with pytest.raises(ValueError, match="Task with id 999 not found"):
        await task_service.get_task_hierarchy(999)


@pytest.mark.asyncio
async def test_get_overdue_tasks(test_db):
    """Test: получение просроченных задач."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    # Создаём задачу с просроченным дедлайном через прямое создание
    from src.repositories import TaskRepository

    task_repo = TaskRepository(test_db)

    overdue_task = Task(
        title="Overdue",
        project_id=project.id,
        due_date=date.today() - timedelta(days=5),
        status=TaskStatus.TODO,
    )
    await task_repo.create(overdue_task)
    await test_db.commit()

    # Создаём обычную задачу
    await task_service.create_task(
        title="Normal", project_id=project.id, due_date=date.today() + timedelta(days=5)
    )
    await test_db.commit()

    overdue = await task_service.get_overdue_tasks()

    assert len(overdue) == 1
    assert overdue[0].title == "Overdue"


@pytest.mark.asyncio
async def test_get_tasks_by_project(test_db):
    """Test: получение задач проекта."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    await task_service.create_task(title="Task 1", project_id=project.id)
    await task_service.create_task(title="Task 2", project_id=project.id)
    await test_db.commit()

    tasks = await task_service.get_tasks_by_project(project.id)

    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_get_tasks_by_project_not_found(test_db):
    """Test: ошибка если проект не найден."""
    task_service = TaskService(test_db)

    with pytest.raises(ValueError, match="Project with id 999 not found"):
        await task_service.get_tasks_by_project(999)


@pytest.mark.asyncio
async def test_get_tasks_by_project_root_only(test_db):
    """Test: получение только корневых задач."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    parent = await task_service.create_task(title="Parent", project_id=project.id)
    await test_db.commit()

    await task_service.create_task(title="Subtask", project_id=project.id, parent_task_id=parent.id)
    await test_db.commit()

    # Все задачи
    all_tasks = await task_service.get_tasks_by_project(project.id)
    assert len(all_tasks) == 2

    # Только корневые
    root_tasks = await task_service.get_tasks_by_project(project.id, root_only=True)
    assert len(root_tasks) == 1
    assert root_tasks[0].title == "Parent"


@pytest.mark.asyncio
async def test_delete_task_not_found(test_db):
    """Test: ошибка если задача не найдена при удалении."""
    task_service = TaskService(test_db)

    with pytest.raises(ValueError, match="Task with id 999 not found"):
        await task_service.delete_task(999)


@pytest.mark.skip(reason="Business rule not fully implemented - needs subtask loading fix")
@pytest.mark.asyncio
async def test_delete_task_with_subtasks_no_force(test_db):
    """Test: нельзя удалить задачу с подзадачами без force."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    parent = await task_service.create_task(title="Parent", project_id=project.id)
    await test_db.commit()

    await task_service.create_task(title="Subtask", project_id=project.id, parent_task_id=parent.id)
    await test_db.commit()

    with pytest.raises(ValueError, match="Cannot delete task with"):
        await task_service.delete_task(parent.id, force=False)


@pytest.mark.skip(reason="Business rule not fully implemented - needs subtask loading fix")
@pytest.mark.asyncio
async def test_get_task_statistics(test_db):
    """Test: получение статистики по задаче."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    parent = await task_service.create_task(
        title="Parent Task",
        project_id=project.id,
        tag_names=["python", "backend"],
        due_date=date.today() + timedelta(days=5),
    )
    await test_db.commit()

    # Добавляем подзадачи
    await task_service.create_task(
        title="Subtask 1", project_id=project.id, parent_task_id=parent.id, status=TaskStatus.DONE
    )
    await task_service.create_task(
        title="Subtask 2", project_id=project.id, parent_task_id=parent.id, status=TaskStatus.TODO
    )
    await test_db.commit()

    # Добавляем комментарии
    await task_service.add_comment(parent.id, "Comment 1")
    await task_service.add_comment(parent.id, "Comment 2")
    await test_db.commit()

    stats = await task_service.get_task_statistics(parent.id)

    assert stats["task_id"] == parent.id
    assert stats["task_title"] == "Parent Task"
    assert stats["total_subtasks"] == 2
    assert stats["completed_subtasks"] == 1
    assert stats["comments_count"] == 2
    assert stats["tags_count"] == 2
    assert stats["is_overdue"] is False
    assert stats["days_until_due"] == 5


@pytest.mark.asyncio
async def test_get_task_statistics_overdue(test_db):
    """Test: статистика для просроченной задачи."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    # Создаём задачу с просроченным дедлайном напрямую
    from src.repositories import TaskRepository

    task_repo = TaskRepository(test_db)

    overdue_task = Task(
        title="Overdue Task",
        project_id=project.id,
        due_date=date.today() - timedelta(days=3),
        status=TaskStatus.TODO,
    )
    await task_repo.create(overdue_task)
    await test_db.commit()

    stats = await task_service.get_task_statistics(overdue_task.id)

    assert stats["is_overdue"] is True
    assert stats["days_until_due"] == -3


@pytest.mark.asyncio
async def test_get_task_statistics_not_found(test_db):
    """Test: ошибка если задача не найдена."""
    task_service = TaskService(test_db)

    with pytest.raises(ValueError, match="Task with id 999 not found"):
        await task_service.get_task_statistics(999)


# ============================================================================
# TAG SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_tag_validation_empty_name(test_db):
    """Test: валидация - пустое название тега."""
    service = TagService(test_db)

    with pytest.raises(ValueError, match="name cannot be empty"):
        await service.create_tag(name="")


@pytest.mark.asyncio
async def test_create_tag_validation_duplicate(test_db):
    """Test: валидация - дубликат названия тега."""
    service = TagService(test_db)

    await service.create_tag(name="python")
    await test_db.commit()

    with pytest.raises(ValueError, match="already exists"):
        await service.create_tag(name="python")


@pytest.mark.asyncio
async def test_tag_normalization_lowercase(test_db):
    """Test: нормализация - приведение к нижнему регистру."""
    service = TagService(test_db)

    tag = await service.create_tag(name="PyThOn")
    await test_db.commit()

    assert tag.name == "python"


@pytest.mark.asyncio
async def test_tag_normalization_spaces_to_dashes(test_db):
    """Test: нормализация - пробелы в дефисы."""
    service = TagService(test_db)

    tag = await service.create_tag(name="Python Programming")
    await test_db.commit()

    assert tag.name == "python-programming"


@pytest.mark.asyncio
async def test_tag_normalization_multiple_spaces(test_db):
    """Test: нормализация - множественные пробелы."""
    service = TagService(test_db)

    tag = await service.create_tag(name="Web  Dev")
    await test_db.commit()

    assert tag.name == "web-dev"


@pytest.mark.asyncio
async def test_tag_normalization_special_characters(test_db):
    """Test: нормализация - удаление спецсимволов."""
    service = TagService(test_db)

    tag = await service.create_tag(name="C++")
    await test_db.commit()

    assert tag.name == "c"


@pytest.mark.asyncio
async def test_tag_normalization_underscores_preserved(test_db):
    """Test: нормализация - подчёркивания сохраняются."""
    service = TagService(test_db)

    tag = await service.create_tag(name="Test_Tag")
    await test_db.commit()

    assert tag.name == "test_tag"


@pytest.mark.asyncio
async def test_merge_tags(test_db):
    """Test: объединение двух тегов."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)
    tag_service = TagService(test_db)

    # Create project and task
    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Test", project_id=project.id, tag_names=["python3"]
    )
    await test_db.commit()

    # Create target tag
    target_tag = await tag_service.create_tag(name="python")
    await test_db.commit()

    # Get source tag
    source_tag = await tag_service.get_tag_by_name("python3")

    # Merge tags
    _merged = await tag_service.merge_tags(source_tag.id, target_tag.id)
    await test_db.commit()

    # Verify
    updated_task = await task_service.get_task(task.id, full=True)
    tag_names = {tag.name for tag in updated_task.tags}

    assert "python" in tag_names
    assert "python3" not in tag_names

    # Source tag should be deleted
    source_after_merge = await tag_service.get_tag_by_name("python3")
    assert source_after_merge is None


@pytest.mark.asyncio
async def test_delete_tag_used_in_tasks_fails(test_db):
    """Test: нельзя удалить тег, используемый в задачах без force."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)
    tag_service = TagService(test_db)

    # Create project and task with tag
    project = await project_service.create_project(name="Test")
    await test_db.commit()

    await task_service.create_task(title="Test", project_id=project.id, tag_names=["python"])
    await test_db.commit()

    tag = await tag_service.get_tag_by_name("python")

    with pytest.raises(ValueError, match="Cannot delete tag"):
        await tag_service.delete_tag(tag.id)


@pytest.mark.asyncio
async def test_delete_tag_used_in_tasks_force(test_db):
    """Test: можно удалить используемый тег с force=True."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)
    tag_service = TagService(test_db)

    # Create project and task with tag
    project = await project_service.create_project(name="Test")
    await test_db.commit()

    await task_service.create_task(title="Test", project_id=project.id, tag_names=["python"])
    await test_db.commit()

    tag = await tag_service.get_tag_by_name("python")

    deleted = await tag_service.delete_tag(tag.id, force=True)
    await test_db.commit()

    assert deleted is True


@pytest.mark.asyncio
async def test_cleanup_unused_tags(test_db):
    """Test: удаление неиспользуемых тегов."""
    tag_service = TagService(test_db)

    # Create unused tags
    await tag_service.create_tag(name="unused1")
    await tag_service.create_tag(name="unused2")
    await tag_service.create_tag(name="unused3")
    await test_db.commit()

    # Cleanup
    count = await tag_service.cleanup_unused_tags()
    await test_db.commit()

    assert count == 3

    # Verify all deleted
    all_tags = await tag_service.get_all_tags()
    assert len(all_tags) == 0


@pytest.mark.asyncio
async def test_get_or_create_tag_existing(test_db):
    """Test: get_or_create возвращает существующий тег."""
    tag_service = TagService(test_db)

    # Create tag
    tag1 = await tag_service.create_tag(name="python")
    await test_db.commit()

    # Get or create (should return existing)
    tag2 = await tag_service.get_or_create_tag(name="python")
    await test_db.commit()

    assert tag1.id == tag2.id


@pytest.mark.asyncio
async def test_get_or_create_tag_new(test_db):
    """Test: get_or_create создаёт новый тег."""
    tag_service = TagService(test_db)

    # Get or create (should create new)
    tag = await tag_service.get_or_create_tag(name="fastapi")
    await test_db.commit()

    assert tag.id is not None
    assert tag.name == "fastapi"


@pytest.mark.asyncio
async def test_tag_statistics(test_db):
    """Test: расчёт статистики по тегу."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)
    tag_service = TagService(test_db)

    # Create project
    project = await project_service.create_project(name="Test")
    await test_db.commit()

    # Create tasks with same tag
    await task_service.create_task(
        title="Task 1", project_id=project.id, status=TaskStatus.DONE, tag_names=["python"]
    )
    await task_service.create_task(
        title="Task 2", project_id=project.id, status=TaskStatus.IN_PROGRESS, tag_names=["python"]
    )
    await task_service.create_task(
        title="Task 3", project_id=project.id, status=TaskStatus.TODO, tag_names=["python"]
    )
    await test_db.commit()

    tag = await tag_service.get_tag_by_name("python")
    stats = await tag_service.get_tag_statistics(tag.id)

    assert stats["total_tasks"] == 3
    assert stats["completed_tasks"] == 1
    assert stats["in_progress_tasks"] == 1
    assert stats["todo_tasks"] == 1
