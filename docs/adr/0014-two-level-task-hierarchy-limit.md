# ADR 0014: Two-Level Task Hierarchy Limit

## Status
Accepted

## Context
В Task Manager нужна возможность создавать подзадачи (subtasks) для разбиения крупных задач.

Вопрос: **сколько уровней вложенности разрешить?**

Варианты:
- 1 level (нет подзадач вообще)
- 2 levels (задача → подзадача)
- 3+ levels (задача → подзадача → под-подзадача → ...)
- Unlimited (любая глубина)

Примеры из других систем:
- **Jira**: unlimited subtasks
- **Todoist**: 4 levels
- **Asana**: 1 level (only subtasks, no sub-subtasks)
- **GitHub Projects**: 1 level

## Decision
Ограничить иерархию до **2 levels максимум**:

```
Project
└── Task (level 1)
    └── Subtask (level 2)
        └── ❌ Sub-subtask (NOT ALLOWED)
```

Бизнес-правило в Service:
```python
async def create_task(self, title: str, parent_task_id: Optional[int], ...):
    if parent_task_id:
        parent_task = await self.task_repo.get_by_id(parent_task_id)

        # Validate: cannot create subtask of subtask
        if parent_task.parent_task_id is not None:
            raise ValueError(
                "Cannot create subtask of subtask. Maximum 2 levels allowed."
            )

    # ... create task
```

## Alternatives Considered

### 1. Unlimited Hierarchy
```python
# No limit - any depth allowed
Task → Subtask → Sub-subtask → Sub-sub-subtask → ...
```
**Отклонено**:
- ❌ Сложность UI (как отображать 5+ levels?)
- ❌ Путаница для пользователей
- ❌ Рекурсивные запросы к БД
- ❌ Over-engineering для Task Manager

### 2. Flat Structure (No Subtasks)
```python
# All tasks independent
Task 1
Task 2
Task 3
```
**Отклонено**:
- ❌ Нельзя разбить крупную задачу
- ❌ Теряется логическая группировка
- ❌ Не хватает flexibility

### 3. Three Levels
```python
Task → Subtask → Sub-subtask (3 levels)
```
**Отклонено**:
- ❌ Более сложный UI
- ❌ Редко нужно на практике
- ❌ Добавляет complexity без реальной пользы

### 4. Tags вместо Hierarchy
```python
# Use tags for grouping instead of subtasks
Task "Setup server" #deployment
Task "Configure nginx" #deployment
Task "Setup SSL" #deployment
```
**Отклонено**:
- ❌ Теряется parent-child relationship
- ❌ Нет dependency tracking
- ❌ Нельзя "завершить все подзадачи = завершить родительскую"

## Consequences

### Positive
- ✅ **Simple to Understand**: интуитивно понятная структура
- ✅ **UI Friendly**: легко отобразить 2 levels
- ✅ **Sufficient**: покрывает 95% use cases
- ✅ **Performance**: не нужны рекурсивные queries
- ✅ **Clear Boundaries**: понятно когда нужно новую task вместо subtask

### Negative
- ❌ **Limited Flexibility**: нельзя создать очень глубокую иерархию
- ❌ **Workarounds Needed**: для сложных задач нужно создавать отдельные tasks

### Neutral
- 🔄 **Validation**: нужна явная проверка в Service
- 🔄 **Database Support**: БД поддерживает unlimited depth, но мы ограничиваем в коде

## Implementation

### Database Model (supports unlimited)
```python
class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=True  # NULL = root task
    )

    # Self-referencing relationship
    parent_task: Mapped[Optional["Task"]] = relationship(
        "Task",
        remote_side=[id],
        back_populates="subtasks"
    )
    subtasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="parent_task"
    )
```

**Note**: БД технически поддерживает любую глубину, но бизнес-логика ограничивает.

### Service Validation
```python
class TaskService:
    async def create_task(
        self,
        title: str,
        project_id: int,
        parent_task_id: Optional[int] = None,
        ...
    ) -> Task:
        # ... other validation

        # Hierarchy validation
        if parent_task_id:
            parent_task = await self.task_repo.get_by_id(parent_task_id)

            if not parent_task:
                raise ValueError(f"Parent task {parent_task_id} not found")

            # KEY VALIDATION: Check hierarchy depth
            if parent_task.parent_task_id is not None:
                raise ValueError(
                    "Cannot create subtask of subtask. "
                    "Maximum 2 levels allowed."
                )

            # Validate same project
            if parent_task.project_id != project_id:
                raise ValueError(
                    f"Parent task is in different project "
                    f"(parent: {parent_task.project_id}, current: {project_id})"
                )

        # Create task
        task = Task(
            title=title,
            project_id=project_id,
            parent_task_id=parent_task_id,
            ...
        )
        return await self.task_repo.create(task)
```

## Use Cases

### Valid Use Case 1: Breaking Down Feature
```
Task: "Implement User Authentication"
├── Subtask: "Create login endpoint"
├── Subtask: "Create registration endpoint"
├── Subtask: "Add password hashing"
└── Subtask: "Write tests"
```

### Valid Use Case 2: Project Milestones
```
Task: "Launch MVP"
├── Subtask: "Design UI mockups"
├── Subtask: "Implement backend API"
├── Subtask: "Connect frontend to API"
└── Subtask: "Deploy to production"
```

### Invalid Use Case: Too Deep Hierarchy
```
Task: "Build Website"
└── Subtask: "Create Header"
    └── ❌ Sub-subtask: "Add Logo"  // NOT ALLOWED
        └── ❌ "Upload image"        // NOT ALLOWED
```

**Solution**: Create separate task
```
Task: "Build Website"
├── Subtask: "Create Header"
└── Subtask: "Add Logo to Header"  // Flattened
```

## API Behavior

### Creating Root Task (Level 1)
```bash
POST /tasks
{
    "title": "Implement Authentication",
    "project_id": 1,
    "parent_task_id": null  # Root task
}

# Success ✅
```

### Creating Subtask (Level 2)
```bash
POST /tasks
{
    "title": "Create login endpoint",
    "project_id": 1,
    "parent_task_id": 1  # Parent is root task
}

# Success ✅
```

### Creating Sub-subtask (Level 3) - REJECTED
```bash
POST /tasks
{
    "title": "Add validation",
    "project_id": 1,
    "parent_task_id": 2  # Parent is already a subtask!
}

# Error 400 ❌
{
    "detail": "Cannot create subtask of subtask. Maximum 2 levels allowed."
}
```

## UI Representation

### List View
```
📁 Project: Website Development
    ☐ Implement Authentication
        ☐ Create login endpoint
        ☐ Create registration endpoint
        ☑ Add password hashing
        ☐ Write tests
    ☐ Design Landing Page
        ☐ Create hero section
        ☐ Add call-to-action
```

### Tree View
```
Project
│
├─ Task 1
│  ├─ Subtask 1.1
│  ├─ Subtask 1.2
│  └─ Subtask 1.3
│
└─ Task 2
   ├─ Subtask 2.1
   └─ Subtask 2.2
```

**Max depth = 2**, легко визуализировать без сложных tree components.

## Statistics and Progress

### Parent Task Progress
```python
# Calculate completion percentage
task = await task_repo.get_by_id_full(1)

total_subtasks = len(task.subtasks)
completed_subtasks = sum(1 for st in task.subtasks if st.status == TaskStatus.DONE)

progress = (completed_subtasks / total_subtasks * 100) if total_subtasks > 0 else 0

# Example: 2 of 4 subtasks done = 50%
```

### Auto-complete Parent
```python
# Optional: Auto-complete parent when all subtasks done
async def complete_task(self, task_id: int):
    task = await self.task_repo.get_by_id_full(task_id)

    # Mark task as complete
    task.status = TaskStatus.DONE
    task.completed_at = datetime.utcnow()

    # If this is a subtask, check if parent should auto-complete
    if task.parent_task_id:
        parent = await self.task_repo.get_by_id_full(task.parent_task_id)
        all_subtasks_done = all(st.status == TaskStatus.DONE for st in parent.subtasks)

        if all_subtasks_done:
            parent.status = TaskStatus.DONE
            parent.completed_at = datetime.utcnow()

    await self.db.flush()
    return task
```

## Querying Tasks

### Get All Root Tasks
```python
async def get_root_tasks(self, project_id: int) -> List[Task]:
    result = await self.db.execute(
        select(Task)
        .where(
            Task.project_id == project_id,
            Task.parent_task_id.is_(None)  # Only root tasks
        )
    )
    return list(result.scalars().all())
```

### Get Task with Subtasks
```python
async def get_task_with_subtasks(self, task_id: int) -> Task:
    result = await self.db.execute(
        select(Task)
        .options(selectinload(Task.subtasks))  # Load subtasks
        .where(Task.id == task_id)
    )
    return result.scalar_one_or_none()
```

## Future Considerations

If 2 levels становится недостаточно:

### Option 1: Increase to 3 Levels
- Minimal code change (update validation)
- More complex UI

### Option 2: Move to Tags
- Use tags for detailed categorization
- Keep tasks flat

### Option 3: Task Dependencies
- Instead of hierarchy, use "depends on" relationships
- More flexible but more complex

## Real-World Examples

### Asana (2 levels)
- Task
  - Subtask (no further nesting)

**Works well** for most project management needs.

### Notion (unlimited but discouraged)
- Technically allows unlimited
- Best practices recommend 2-3 levels max
- UI becomes cluttered beyond 3 levels

### GitHub Projects (1 level)
- Issue
  - Task list items (not real subtasks)

**Too restrictive** for complex projects.

## Related ADRs
- ADR-0003: Service Layer - validation в Service
- ADR-0010: Validation in Service Layer

## Notes
2 levels - практичный компромисс между flexibility и simplicity:
- Достаточно для большинства use cases
- Простой UI
- Хорошая производительность
- Ясная ментальная модель

Unlimited hierarchy кажется более "мощным", но на практике создаёт complexity без реальной пользы.
