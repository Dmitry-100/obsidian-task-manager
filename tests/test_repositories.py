"""
Тесты для Repository Layer (CRUD операции).

Проверяем базовые CRUD операции:
- Create: создание записи
- Read: чтение по ID и списка
- Update: обновление записи
- Delete: удаление записи
- Relationships: работа со связями (tags, comments, subtasks)
"""

import pytest
from datetime import date, datetime

from src.models import Project, Task, Tag, TaskComment, TaskStatus, TaskPriority
from src.repositories import ProjectRepository, TaskRepository, TagRepository, TaskCommentRepository


# ============================================================================
# PROJECT REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_project_create(test_db):
    """Test: создание проекта."""
    repo = ProjectRepository(test_db)

    project = Project(
        name="Test Project",
        description="Test Description",
        color="#FF0000"
    )

    created = await repo.create(project)
    await test_db.commit()

    assert created.id is not None
    assert created.name == "Test Project"
    assert created.description == "Test Description"
    assert created.color == "#FF0000"
    assert created.is_archived is False
    assert created.created_at is not None
    assert created.updated_at is not None


@pytest.mark.asyncio
async def test_project_get_by_id(test_db):
    """Test: получение проекта по ID."""
    repo = ProjectRepository(test_db)

    # Create project
    project = Project(name="Test Project")
    created = await repo.create(project)
    await test_db.commit()

    # Get by ID
    found = await repo.get_by_id(created.id)

    assert found is not None
    assert found.id == created.id
    assert found.name == "Test Project"


@pytest.mark.asyncio
async def test_project_get_all(test_db):
    """Test: получение списка всех проектов."""
    repo = ProjectRepository(test_db)

    # Create multiple projects
    project1 = Project(name="Project 1")
    project2 = Project(name="Project 2")
    await repo.create(project1)
    await repo.create(project2)
    await test_db.commit()

    # Get all
    projects = await repo.get_all()

    assert len(projects) == 2
    assert projects[0].name == "Project 1"
    assert projects[1].name == "Project 2"


@pytest.mark.asyncio
async def test_project_update(test_db):
    """Test: обновление проекта."""
    repo = ProjectRepository(test_db)

    # Create
    project = Project(name="Old Name")
    created = await repo.create(project)
    await test_db.commit()

    # Update
    created.name = "New Name"
    created.color = "#00FF00"
    await test_db.commit()

    # Verify
    updated = await repo.get_by_id(created.id)
    assert updated.name == "New Name"
    assert updated.color == "#00FF00"
    assert updated.updated_at > updated.created_at


@pytest.mark.asyncio
async def test_project_delete(test_db):
    """Test: удаление проекта."""
    repo = ProjectRepository(test_db)

    # Create
    project = Project(name="To Delete")
    created = await repo.create(project)
    await test_db.commit()

    # Delete
    await repo.delete(created.id)
    await test_db.commit()

    # Verify
    found = await repo.get_by_id(created.id)
    assert found is None


# ============================================================================
# TASK REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_task_create(test_db):
    """Test: создание задачи."""
    project_repo = ProjectRepository(test_db)
    task_repo = TaskRepository(test_db)

    # Create project first
    project = Project(name="Test Project")
    project = await project_repo.create(project)
    await test_db.commit()

    # Create task
    task = Task(
        title="Test Task",
        description="Test Description",
        project_id=project.id,
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH
    )

    created = await task_repo.create(task)
    await test_db.commit()

    assert created.id is not None
    assert created.title == "Test Task"
    assert created.project_id == project.id
    assert created.status == TaskStatus.TODO
    assert created.priority == TaskPriority.HIGH


@pytest.mark.asyncio
async def test_task_get_by_id(test_db):
    """Test: получение задачи по ID."""
    project_repo = ProjectRepository(test_db)
    task_repo = TaskRepository(test_db)

    # Create project and task
    project = await project_repo.create(Project(name="Test Project"))
    task = await task_repo.create(Task(
        title="Test Task",
        project_id=project.id
    ))
    await test_db.commit()

    # Get by ID
    found = await task_repo.get_by_id(task.id)

    assert found is not None
    assert found.id == task.id
    assert found.title == "Test Task"


@pytest.mark.asyncio
async def test_task_with_tags(test_db):
    """Test: задача с тегами (Many-to-Many relationship)."""
    project_repo = ProjectRepository(test_db)
    task_repo = TaskRepository(test_db)
    tag_repo = TagRepository(test_db)

    # Create project
    project = await project_repo.create(Project(name="Test Project"))
    await test_db.commit()

    # Create task
    task = await task_repo.create(Task(
        title="Test Task",
        project_id=project.id
    ))
    await test_db.commit()

    # Create tags
    tag1 = await tag_repo.create(Tag(name="python"))
    tag2 = await tag_repo.create(Tag(name="testing"))
    await test_db.commit()

    # Add tags to task
    await task_repo.add_tag(task.id, tag1)
    await task_repo.add_tag(task.id, tag2)
    await test_db.commit()

    # Verify
    task_with_tags = await task_repo.get_by_id_full(task.id)
    assert len(task_with_tags.tags) == 2
    tag_names = {tag.name for tag in task_with_tags.tags}
    assert "python" in tag_names
    assert "testing" in tag_names


@pytest.mark.asyncio
async def test_task_hierarchy_parent_child(test_db):
    """Test: иерархия задач (parent-child relationship)."""
    project_repo = ProjectRepository(test_db)
    task_repo = TaskRepository(test_db)

    # Create project
    project = await project_repo.create(Project(name="Test Project"))
    await test_db.commit()

    # Create parent task
    parent = await task_repo.create(Task(
        title="Parent Task",
        project_id=project.id
    ))
    await test_db.commit()

    # Create subtask
    subtask = await task_repo.create(Task(
        title="Subtask",
        project_id=project.id,
        parent_task_id=parent.id
    ))
    await test_db.commit()

    # Verify parent has subtask
    parent_full = await task_repo.get_by_id_full(parent.id)
    assert len(parent_full.subtasks) == 1
    assert parent_full.subtasks[0].title == "Subtask"

    # Verify subtask has parent
    subtask_full = await task_repo.get_by_id_full(subtask.id)
    assert subtask_full.parent_task_id == parent.id


# ============================================================================
# TAG REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tag_create(test_db):
    """Test: создание тега."""
    repo = TagRepository(test_db)

    tag = Tag(name="python")
    created = await repo.create(tag)
    await test_db.commit()

    assert created.id is not None
    assert created.name == "python"
    assert created.created_at is not None


@pytest.mark.asyncio
async def test_tag_get_by_name(test_db):
    """Test: получение тега по имени."""
    repo = TagRepository(test_db)

    # Create tag
    tag = await repo.create(Tag(name="fastapi"))
    await test_db.commit()

    # Get by name
    found = await repo.get_by_name("fastapi")

    assert found is not None
    assert found.name == "fastapi"


@pytest.mark.asyncio
async def test_tag_bulk_get_or_create(test_db):
    """Test: массовое получение/создание тегов."""
    repo = TagRepository(test_db)

    # Create one tag
    existing_tag = await repo.create(Tag(name="python"))
    await test_db.commit()

    # Bulk get or create (one exists, two new)
    tag_names = ["python", "fastapi", "sqlalchemy"]
    tags = await repo.bulk_get_or_create(tag_names)
    await test_db.commit()

    assert len(tags) == 3
    tag_names_result = {tag.name for tag in tags}
    assert tag_names_result == {"python", "fastapi", "sqlalchemy"}


# ============================================================================
# COMMENT REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_comment_create(test_db):
    """Test: создание комментария."""
    project_repo = ProjectRepository(test_db)
    task_repo = TaskRepository(test_db)
    comment_repo = TaskCommentRepository(test_db)

    # Create project and task
    project = await project_repo.create(Project(name="Test Project"))
    task = await task_repo.create(Task(
        title="Test Task",
        project_id=project.id
    ))
    await test_db.commit()

    # Create comment
    comment = TaskComment(
        task_id=task.id,
        content="Test comment"
    )
    created = await comment_repo.create(comment)
    await test_db.commit()

    assert created.id is not None
    assert created.task_id == task.id
    assert created.content == "Test comment"


@pytest.mark.asyncio
async def test_comment_get_by_task(test_db):
    """Test: получение комментариев для задачи."""
    project_repo = ProjectRepository(test_db)
    task_repo = TaskRepository(test_db)
    comment_repo = TaskCommentRepository(test_db)

    # Create project and task
    project = await project_repo.create(Project(name="Test Project"))
    task = await task_repo.create(Task(
        title="Test Task",
        project_id=project.id
    ))
    await test_db.commit()

    # Create multiple comments
    comment1 = await comment_repo.create(TaskComment(
        task_id=task.id,
        content="Comment 1"
    ))
    comment2 = await comment_repo.create(TaskComment(
        task_id=task.id,
        content="Comment 2"
    ))
    await test_db.commit()

    # Get comments for task
    comments = await comment_repo.get_by_task(task.id)

    assert len(comments) == 2
    contents = {c.content for c in comments}
    assert "Comment 1" in contents
    assert "Comment 2" in contents
