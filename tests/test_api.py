"""
Тесты для API Layer (REST endpoints).

Проверяем:
- HTTP статус-коды
- Форматы запросов/ответов (JSON)
- Обработку ошибок (400, 404, 500)
- Интеграцию всех слоёв (API → Service → Repository → DB)
"""

import pytest
from httpx import AsyncClient


# ============================================================================
# PROJECT API TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_project(test_client: AsyncClient):
    """Test: POST /projects - создание проекта."""
    response = await test_client.post(
        "/projects",
        json={
            "name": "Test Project",
            "description": "Test Description",
            "color": "#FF0000"
        }
    )

    if response.status_code != 201:
        print(f"Error response: {response.json()}")

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "Test Description"
    assert data["color"] == "#FF0000"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_project_validation_error(test_client: AsyncClient):
    """Test: POST /projects - ошибка валидации (пустое название)."""
    response = await test_client.post(
        "/projects",
        json={
            "name": "",
            "description": "Test"
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_get_projects_list(test_client: AsyncClient):
    """Test: GET /projects - получение списка проектов."""
    # Create projects
    await test_client.post("/projects", json={"name": "Project 1"})
    await test_client.post("/projects", json={"name": "Project 2"})

    # Get list
    response = await test_client.get("/projects")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Project 1"
    assert data[1]["name"] == "Project 2"


@pytest.mark.asyncio
async def test_get_project_by_id(test_client: AsyncClient):
    """Test: GET /projects/{id} - получение проекта по ID."""
    # Create project
    create_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = create_response.json()["id"]

    # Get by ID
    response = await test_client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Test Project"


@pytest.mark.asyncio
async def test_get_project_not_found(test_client: AsyncClient):
    """Test: GET /projects/{id} - проект не найден."""
    response = await test_client.get("/projects/999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project(test_client: AsyncClient):
    """Test: PUT /projects/{id} - обновление проекта."""
    # Create project
    create_response = await test_client.post(
        "/projects",
        json={"name": "Old Name"}
    )
    project_id = create_response.json()["id"]

    # Update
    response = await test_client.put(
        f"/projects/{project_id}",
        json={"name": "New Name", "color": "#00FF00"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["color"] == "#00FF00"


@pytest.mark.asyncio
async def test_archive_project(test_client: AsyncClient):
    """Test: POST /projects/{id}/archive - архивирование проекта."""
    # Create project
    create_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = create_response.json()["id"]

    # Archive
    response = await test_client.post(f"/projects/{project_id}/archive")

    assert response.status_code == 200
    data = response.json()
    assert data["is_archived"] is True


@pytest.mark.asyncio
async def test_unarchive_project(test_client: AsyncClient):
    """Test: POST /projects/{id}/unarchive - восстановление проекта."""
    # Create and archive project
    create_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = create_response.json()["id"]
    await test_client.post(f"/projects/{project_id}/archive")

    # Unarchive
    response = await test_client.post(f"/projects/{project_id}/unarchive")

    assert response.status_code == 200
    data = response.json()
    assert data["is_archived"] is False


@pytest.mark.asyncio
async def test_delete_project(test_client: AsyncClient):
    """Test: DELETE /projects/{id} - удаление проекта."""
    # Create project
    create_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = create_response.json()["id"]

    # Delete
    response = await test_client.delete(f"/projects/{project_id}")

    assert response.status_code == 200

    # Verify deleted
    get_response = await test_client.get(f"/projects/{project_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_project_statistics(test_client: AsyncClient):
    """Test: GET /projects/{id}/stats - статистика проекта."""
    # Create project
    create_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = create_response.json()["id"]

    # Create tasks
    await test_client.post(
        "/tasks",
        json={
            "title": "Task 1",
            "project_id": project_id,
            "status": "done"
        }
    )
    await test_client.post(
        "/tasks",
        json={
            "title": "Task 2",
            "project_id": project_id,
            "status": "todo"
        }
    )

    # Get statistics
    response = await test_client.get(f"/projects/{project_id}/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 2
    assert data["completed_tasks"] == 1
    assert "completion_percentage" in data


# ============================================================================
# TASK API TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_task(test_client: AsyncClient):
    """Test: POST /tasks - создание задачи."""
    # Create project first
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Create task
    response = await test_client.post(
        "/tasks",
        json={
            "title": "Test Task",
            "project_id": project_id,
            "description": "Test Description",
            "priority": "high",
            "tag_names": ["python", "testing"]
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "Test Description"
    assert data["priority"] == "high"
    assert data["project_id"] == project_id
    assert len(data["tags"]) == 2


@pytest.mark.asyncio
async def test_create_task_validation_error(test_client: AsyncClient):
    """Test: POST /tasks - ошибка валидации."""
    # Create project
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Try to create task with empty title
    response = await test_client.post(
        "/tasks",
        json={
            "title": "",
            "project_id": project_id
        }
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_task_by_id(test_client: AsyncClient):
    """Test: GET /tasks/{id} - получение задачи по ID."""
    # Create project and task
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    create_response = await test_client.post(
        "/tasks",
        json={"title": "Test Task", "project_id": project_id}
    )
    task_id = create_response.json()["id"]

    # Get task
    response = await test_client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == "Test Task"


@pytest.mark.asyncio
async def test_update_task(test_client: AsyncClient):
    """Test: PUT /tasks/{id} - обновление задачи."""
    # Create project and task
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    create_response = await test_client.post(
        "/tasks",
        json={"title": "Old Title", "project_id": project_id}
    )
    task_id = create_response.json()["id"]

    # Update task
    response = await test_client.put(
        f"/tasks/{task_id}",
        json={
            "title": "New Title",
            "status": "in_progress",
            "priority": "high"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"


@pytest.mark.asyncio
async def test_complete_task(test_client: AsyncClient):
    """Test: POST /tasks/{id}/complete - завершение задачи."""
    # Create project and task
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    create_response = await test_client.post(
        "/tasks",
        json={"title": "Test Task", "project_id": project_id}
    )
    task_id = create_response.json()["id"]

    # Complete task
    response = await test_client.post(f"/tasks/{task_id}/complete")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_delete_task(test_client: AsyncClient):
    """Test: DELETE /tasks/{id} - удаление задачи."""
    # Create project and task
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    create_response = await test_client.post(
        "/tasks",
        json={"title": "Test Task", "project_id": project_id}
    )
    task_id = create_response.json()["id"]

    # Delete task
    response = await test_client.delete(f"/tasks/{task_id}")

    assert response.status_code == 200

    # Verify deleted
    get_response = await test_client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_add_tags_to_task(test_client: AsyncClient):
    """Test: POST /tasks/{id}/tags - добавление тегов к задаче."""
    # Create project and task
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    create_response = await test_client.post(
        "/tasks",
        json={"title": "Test Task", "project_id": project_id}
    )
    task_id = create_response.json()["id"]

    # Add tags
    response = await test_client.post(
        f"/tasks/{task_id}/tags",
        json={"tag_names": ["python", "backend"]}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 2


@pytest.mark.asyncio
async def test_remove_tag_from_task(test_client: AsyncClient):
    """Test: DELETE /tasks/{id}/tags/{tag_name} - удаление тега у задачи."""
    # Create project and task with tags
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    create_response = await test_client.post(
        "/tasks",
        json={
            "title": "Test Task",
            "project_id": project_id,
            "tag_names": ["python", "backend"]
        }
    )
    task_id = create_response.json()["id"]

    # Remove tag
    response = await test_client.delete(f"/tasks/{task_id}/tags/python")

    assert response.status_code == 200
    data = response.json()
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "backend"


@pytest.mark.asyncio
async def test_add_comment_to_task(test_client: AsyncClient):
    """Test: POST /tasks/{id}/comments - добавление комментария."""
    # Create project and task
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    create_response = await test_client.post(
        "/tasks",
        json={"title": "Test Task", "project_id": project_id}
    )
    task_id = create_response.json()["id"]

    # Add comment
    response = await test_client.post(
        f"/tasks/{task_id}/comments",
        json={"content": "This is a test comment"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "This is a test comment"
    assert data["task_id"] == task_id


@pytest.mark.asyncio
async def test_create_task_hierarchy(test_client: AsyncClient):
    """Test: создание иерархии задач (parent + subtask)."""
    # Create project
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Create parent task
    parent_response = await test_client.post(
        "/tasks",
        json={"title": "Parent Task", "project_id": project_id}
    )
    parent_id = parent_response.json()["id"]

    # Create subtask
    subtask_response = await test_client.post(
        "/tasks",
        json={
            "title": "Subtask",
            "project_id": project_id,
            "parent_task_id": parent_id
        }
    )

    assert subtask_response.status_code == 201
    subtask_data = subtask_response.json()
    assert subtask_data["parent_task_id"] == parent_id


@pytest.mark.asyncio
async def test_get_tasks_by_project(test_client: AsyncClient):
    """Test: GET /projects/{id}/tasks - получение задач проекта."""
    # Create project
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Create tasks
    await test_client.post(
        "/tasks",
        json={"title": "Task 1", "project_id": project_id}
    )
    await test_client.post(
        "/tasks",
        json={"title": "Task 2", "project_id": project_id}
    )

    # Get tasks
    response = await test_client.get(f"/projects/{project_id}/tasks")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


# ============================================================================
# TAG API TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_tag(test_client: AsyncClient):
    """Test: POST /tags - создание тега."""
    response = await test_client.post(
        "/tags",
        json={"name": "python"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "python"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_tag_normalization(test_client: AsyncClient):
    """Test: POST /tags - нормализация названия тега."""
    response = await test_client.post(
        "/tags",
        json={"name": "Python Programming"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "python-programming"


@pytest.mark.asyncio
async def test_get_tags_list(test_client: AsyncClient):
    """Test: GET /tags - получение списка тегов."""
    # Create tags
    await test_client.post("/tags", json={"name": "python"})
    await test_client.post("/tags", json={"name": "fastapi"})

    # Get list
    response = await test_client.get("/tags")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_tag_by_id(test_client: AsyncClient):
    """Test: GET /tags/{id} - получение тега по ID."""
    # Create tag
    create_response = await test_client.post(
        "/tags",
        json={"name": "python"}
    )
    tag_id = create_response.json()["id"]

    # Get tag
    response = await test_client.get(f"/tags/{tag_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tag_id
    assert data["name"] == "python"


@pytest.mark.asyncio
async def test_rename_tag(test_client: AsyncClient):
    """Test: PUT /tags/{id} - переименование тега."""
    # Create tag
    create_response = await test_client.post(
        "/tags",
        json={"name": "oldname"}
    )
    tag_id = create_response.json()["id"]

    # Rename
    response = await test_client.put(
        f"/tags/{tag_id}",
        json={"name": "newname"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "newname"


@pytest.mark.asyncio
async def test_delete_tag(test_client: AsyncClient):
    """Test: DELETE /tags/{id} - удаление тега."""
    # Create tag
    create_response = await test_client.post(
        "/tags",
        json={"name": "test"}
    )
    tag_id = create_response.json()["id"]

    # Delete
    response = await test_client.delete(f"/tags/{tag_id}")

    assert response.status_code == 200

    # Verify deleted
    get_response = await test_client.get(f"/tags/{tag_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_tag_statistics(test_client: AsyncClient):
    """Test: GET /tags/{id}/stats - статистика по тегу."""
    # Create project
    project_response = await test_client.post(
        "/projects",
        json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Create tasks with tag
    await test_client.post(
        "/tasks",
        json={
            "title": "Task 1",
            "project_id": project_id,
            "status": "done",
            "tag_names": ["python"]
        }
    )
    await test_client.post(
        "/tasks",
        json={
            "title": "Task 2",
            "project_id": project_id,
            "status": "todo",
            "tag_names": ["python"]
        }
    )

    # Get tag
    tags_response = await test_client.get("/tags")
    tag_id = tags_response.json()[0]["id"]

    # Get statistics
    response = await test_client.get(f"/tags/{tag_id}/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 2
    assert data["completed_tasks"] == 1
    assert data["todo_tasks"] == 1


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_workflow_create_project_with_tasks(test_client: AsyncClient):
    """
    Test: полный workflow создания проекта с задачами и тегами.

    Это интеграционный тест, проверяющий работу всех слоёв вместе.
    """
    # 1. Create project
    project_response = await test_client.post(
        "/projects",
        json={
            "name": "My Project",
            "description": "Test project",
            "color": "#3B82F6"
        }
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    # 2. Create parent task with tags
    parent_response = await test_client.post(
        "/tasks",
        json={
            "title": "Parent Task",
            "project_id": project_id,
            "priority": "high",
            "tag_names": ["python", "backend"]
        }
    )
    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]

    # 3. Create subtask
    subtask_response = await test_client.post(
        "/tasks",
        json={
            "title": "Subtask",
            "project_id": project_id,
            "parent_task_id": parent_id,
            "tag_names": ["testing"]
        }
    )
    assert subtask_response.status_code == 201

    # 4. Add comment to parent task
    comment_response = await test_client.post(
        f"/tasks/{parent_id}/comments",
        json={"content": "This is a comment"}
    )
    assert comment_response.status_code == 201

    # 5. Complete subtask
    complete_response = await test_client.post(f"/tasks/{subtask_response.json()['id']}/complete")
    assert complete_response.status_code == 200

    # 6. Get project statistics
    stats_response = await test_client.get(f"/projects/{project_id}/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_tasks"] == 2
    assert stats["completed_tasks"] == 1

    # 7. Get all tags
    tags_response = await test_client.get("/tags")
    assert tags_response.status_code == 200
    assert len(tags_response.json()) == 3  # python, backend, testing
