# Примеры использования API

Этот файл содержит примеры запросов к API для тестирования.

## Запуск сервера

```bash
cd /Users/Sotnikov/Google\ Drive\ 100/10\ -\ coding\ project/obsidian-task-manager
source venv/bin/activate
uvicorn src.main:app --reload
```

Сервер запустится на `http://localhost:8000`

## Интерактивная документация

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Projects API

### 1. Создать проект

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Вайб-Кодинг Week 4",
    "description": "Изучение баз данных и SQLAlchemy",
    "color": "#3B82F6"
  }'
```

### 2. Получить все проекты

```bash
curl http://localhost:8000/projects
```

### 3. Получить проект по ID

```bash
curl http://localhost:8000/projects/1
```

### 4. Обновить проект

```bash
curl -X PUT http://localhost:8000/projects/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Обновлённое название",
    "color": "#FF0000"
  }'
```

### 5. Архивировать проект

```bash
curl -X POST http://localhost:8000/projects/1/archive
```

### 6. Восстановить проект

```bash
curl -X POST http://localhost:8000/projects/1/unarchive
```

### 7. Получить статистику проекта

```bash
curl http://localhost:8000/projects/1/stats
```

### 8. Удалить проект

```bash
# Без задач
curl -X DELETE http://localhost:8000/projects/1

# С задачами (принудительно)
curl -X DELETE "http://localhost:8000/projects/1?force=true"
```

---

## Tasks API

### 1. Создать задачу

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Создать REST API",
    "description": "Реализовать CRUD endpoints для всех сущностей",
    "project_id": 1,
    "priority": "high",
    "due_date": "2026-01-25",
    "estimated_hours": 8,
    "tag_names": ["python", "fastapi", "backend", "api"]
  }'
```

### 2. Создать подзадачу

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Написать тесты для API",
    "project_id": 1,
    "parent_task_id": 1,
    "priority": "medium",
    "tag_names": ["testing", "pytest"]
  }'
```

### 3. Получить задачу по ID

```bash
curl http://localhost:8000/tasks/1
```

### 4. Обновить задачу

```bash
curl -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress",
    "priority": "high"
  }'
```

### 5. Завершить задачу

```bash
curl -X POST http://localhost:8000/tasks/1/complete
```

### 6. Получить задачи проекта

```bash
# Все задачи
curl http://localhost:8000/tasks/by-project/1

# Только активные
curl "http://localhost:8000/tasks/by-project/1?include_completed=false"

# Только корневые задачи
curl "http://localhost:8000/tasks/by-project/1?root_only=true"
```

### 7. Получить просроченные задачи

```bash
curl http://localhost:8000/tasks/overdue
```

### 8. Добавить теги к задаче

```bash
curl -X POST http://localhost:8000/tasks/1/tags \
  -H "Content-Type: application/json" \
  -d '["urgent", "bug", "production"]'
```

### 9. Удалить тег у задачи

```bash
curl -X DELETE http://localhost:8000/tasks/1/tags/urgent
```

### 10. Добавить комментарий

```bash
curl -X POST http://localhost:8000/tasks/1/comments \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Нашёл **баг** в авторизации. Нужно срочно исправить!\n\n```python\nif user.password == \"\":\n    return True  # BUG!\n```"
  }'
```

### 11. Получить иерархию задачи

```bash
curl http://localhost:8000/tasks/1/hierarchy
```

### 12. Получить статистику задачи

```bash
curl http://localhost:8000/tasks/1/stats
```

### 13. Удалить задачу

```bash
# Без подзадач
curl -X DELETE http://localhost:8000/tasks/1

# С подзадачами
curl -X DELETE "http://localhost:8000/tasks/1?force=true"
```

---

## Tags API

### 1. Создать тег

```bash
curl -X POST http://localhost:8000/tags \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python Programming"
  }'

# Название будет нормализовано в: "python-programming"
```

### 2. Получить все теги

```bash
curl http://localhost:8000/tags
```

### 3. Получить популярные теги

```bash
curl "http://localhost:8000/tags/popular?limit=5"
```

### 4. Получить неиспользуемые теги

```bash
curl http://localhost:8000/tags/unused
```

### 5. Получить тег по ID

```bash
curl http://localhost:8000/tags/1
```

### 6. Переименовать тег

```bash
curl -X PUT http://localhost:8000/tags/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new-name"
  }'
```

### 7. Объединить теги

```bash
# Объединить "python3" (id=1) в "python" (id=2)
curl -X POST http://localhost:8000/tags/1/merge/2
```

### 8. Удалить тег

```bash
# Без задач
curl -X DELETE http://localhost:8000/tags/1

# С задачами (отвязать от всех задач)
curl -X DELETE "http://localhost:8000/tags/1?force=true"
```

### 9. Очистить неиспользуемые теги

```bash
curl -X POST http://localhost:8000/tags/cleanup
```

### 10. Получить статистику тега

```bash
curl http://localhost:8000/tags/1/stats
```

---

## Полный workflow: от проекта до задачи

```bash
# 1. Создать проект
PROJECT_ID=$(curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Новый проект", "color": "#00FF00"}' \
  | jq -r '.id')

echo "Создан проект ID: $PROJECT_ID"

# 2. Создать задачу
TASK_ID=$(curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Главная задача\",
    \"project_id\": $PROJECT_ID,
    \"priority\": \"high\",
    \"tag_names\": [\"important\", \"urgent\"]
  }" \
  | jq -r '.id')

echo "Создана задача ID: $TASK_ID"

# 3. Создать подзадачу
SUBTASK_ID=$(curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Подзадача\",
    \"project_id\": $PROJECT_ID,
    \"parent_task_id\": $TASK_ID
  }" \
  | jq -r '.id')

echo "Создана подзадача ID: $SUBTASK_ID"

# 4. Добавить комментарий
curl -X POST "http://localhost:8000/tasks/$TASK_ID/comments" \
  -H "Content-Type: application/json" \
  -d '{"content": "Начал работу над задачей"}'

# 5. Завершить подзадачу
curl -X POST "http://localhost:8000/tasks/$SUBTASK_ID/complete"

# 6. Завершить главную задачу
curl -X POST "http://localhost:8000/tasks/$TASK_ID/complete"

# 7. Получить статистику проекта
curl "http://localhost:8000/projects/$PROJECT_ID/stats" | jq
```

---

## Тестирование с помощью HTTPie (альтернатива curl)

Установка:
```bash
pip install httpie
```

Примеры:

```bash
# POST запрос
http POST localhost:8000/projects name="Проект" color="#FF0000"

# GET запрос
http GET localhost:8000/projects/1

# PUT запрос
http PUT localhost:8000/tasks/1 status=done

# DELETE запрос
http DELETE localhost:8000/tasks/1 force==true
```

---

## Использование в Python (httpx)

```python
import asyncio
import httpx

async def test_api():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Создать проект
        response = await client.post("/projects", json={
            "name": "Python проект",
            "color": "#3B82F6"
        })
        project = response.json()
        print(f"Создан проект: {project['name']}")

        # Создать задачу
        response = await client.post("/tasks", json={
            "title": "Моя задача",
            "project_id": project["id"],
            "tag_names": ["python", "backend"]
        })
        task = response.json()
        print(f"Создана задача: {task['title']}")

        # Получить задачи проекта
        response = await client.get(f"/tasks/by-project/{project['id']}")
        tasks = response.json()
        print(f"Задач в проекте: {len(tasks)}")

if __name__ == "__main__":
    asyncio.run(test_api())
```

---

## Примечания

1. Для работы API нужна настроенная БД (PostgreSQL)
2. Примените миграции перед тестированием: `alembic upgrade head`
3. Все примеры предполагают, что сервер запущен на `localhost:8000`
4. Для красивого вывода JSON используйте `| jq` или HTTPie
5. ID в примерах могут отличаться - используйте реальные ID из ответов
