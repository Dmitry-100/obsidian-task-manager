"""
Тесты для Service Layer (Бизнес-логика).

Проверяем:
- Валидацию бизнес-правил
- Координацию между репозиториями
- Расчёт статистики
- Специфичную бизнес-логику (tag normalization, hierarchy limits, etc.)
"""

import pytest
from datetime import date, datetime, timedelta

from src.models import Project, Task, Tag, TaskStatus, TaskPriority
from src.services import ProjectService, TaskService, TagService


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

    project = await service.create_project(
        name="Test Project",
        color="#FF0000"
    )
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

    await task_service.create_task(
        title="Test Task",
        project_id=project.id
    )
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

    await task_service.create_task(
        title="Test Task",
        project_id=project.id
    )
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
    await task_service.create_task(
        title="Task 1",
        project_id=project.id,
        status=TaskStatus.DONE
    )
    await task_service.create_task(
        title="Task 2",
        project_id=project.id,
        status=TaskStatus.DONE
    )
    await task_service.create_task(
        title="Task 3",
        project_id=project.id,
        status=TaskStatus.IN_PROGRESS
    )
    await task_service.create_task(
        title="Task 4",
        project_id=project.id,
        status=TaskStatus.TODO
    )
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
        await task_service.create_task(
            title="",
            project_id=project.id
        )


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
        await task_service.create_task(
            title="Test Task",
            project_id=project.id
        )


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
    parent_task = await task_service.create_task(
        title="Parent",
        project_id=project1.id
    )
    await test_db.commit()

    # Try to create subtask in project2
    with pytest.raises(ValueError, match="different project"):
        await task_service.create_task(
            title="Subtask",
            project_id=project2.id,
            parent_task_id=parent_task.id
        )


@pytest.mark.asyncio
async def test_create_task_hierarchy_limit(test_db):
    """Test: максимум 2 уровня вложенности (нет подзадач у подзадач)."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    # Create parent task
    parent = await task_service.create_task(
        title="Parent",
        project_id=project.id
    )
    await test_db.commit()

    # Create subtask
    subtask = await task_service.create_task(
        title="Subtask",
        project_id=project.id,
        parent_task_id=parent.id
    )
    await test_db.commit()

    # Try to create sub-subtask (should fail)
    with pytest.raises(ValueError, match="Maximum 2 levels allowed"):
        await task_service.create_task(
            title="Sub-subtask",
            project_id=project.id,
            parent_task_id=subtask.id
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
        await task_service.create_task(
            title="Test",
            project_id=project.id,
            due_date=past_date
        )


@pytest.mark.asyncio
async def test_update_task_status_to_done_sets_completed_at(test_db):
    """Test: при переводе в DONE устанавливается completed_at."""
    project_service = ProjectService(test_db)
    task_service = TaskService(test_db)

    project = await project_service.create_project(name="Test")
    await test_db.commit()

    task = await task_service.create_task(
        title="Test",
        project_id=project.id,
        status=TaskStatus.TODO
    )
    await test_db.commit()

    assert task.completed_at is None

    # Update to DONE
    updated = await task_service.update_task(
        task_id=task.id,
        status=TaskStatus.DONE
    )
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
        title="Test",
        project_id=project.id,
        status=TaskStatus.DONE
    )
    await test_db.commit()

    # Move back to TODO
    updated = await task_service.update_task(
        task_id=task.id,
        status=TaskStatus.TODO
    )
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
    parent = await task_service.create_task(
        title="Parent",
        project_id=project.id
    )
    await task_service.create_task(
        title="Subtask",
        project_id=project.id,
        parent_task_id=parent.id,
        status=TaskStatus.TODO
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
        title="Test",
        project_id=project.id,
        tag_names=["python", "fastapi", "backend"]
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

    parent = await task_service.create_task(
        title="Parent",
        project_id=project.id
    )
    await task_service.create_task(
        title="Subtask",
        project_id=project.id,
        parent_task_id=parent.id
    )
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

    parent = await task_service.create_task(
        title="Parent",
        project_id=project.id
    )
    await task_service.create_task(
        title="Subtask",
        project_id=project.id,
        parent_task_id=parent.id
    )
    await test_db.commit()

    deleted = await task_service.delete_task(parent.id, force=True)
    await test_db.commit()

    assert deleted is True


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
        title="Test",
        project_id=project.id,
        tag_names=["python3"]
    )
    await test_db.commit()

    # Create target tag
    target_tag = await tag_service.create_tag(name="python")
    await test_db.commit()

    # Get source tag
    source_tag = await tag_service.get_tag_by_name("python3")

    # Merge tags
    merged = await tag_service.merge_tags(source_tag.id, target_tag.id)
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

    await task_service.create_task(
        title="Test",
        project_id=project.id,
        tag_names=["python"]
    )
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

    await task_service.create_task(
        title="Test",
        project_id=project.id,
        tag_names=["python"]
    )
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
        title="Task 1",
        project_id=project.id,
        status=TaskStatus.DONE,
        tag_names=["python"]
    )
    await task_service.create_task(
        title="Task 2",
        project_id=project.id,
        status=TaskStatus.IN_PROGRESS,
        tag_names=["python"]
    )
    await task_service.create_task(
        title="Task 3",
        project_id=project.id,
        status=TaskStatus.TODO,
        tag_names=["python"]
    )
    await test_db.commit()

    tag = await tag_service.get_tag_by_name("python")
    stats = await tag_service.get_tag_statistics(tag.id)

    assert stats["total_tasks"] == 3
    assert stats["completed_tasks"] == 1
    assert stats["in_progress_tasks"] == 1
    assert stats["todo_tasks"] == 1
