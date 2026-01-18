# ADR 0010: Validation in Service Layer (not Repository)

## Status
Accepted

## Context
В приложении существуют два типа валидации:
1. **Техническая валидация**: проверка формата данных (email format, число > 0)
2. **Бизнес-валидация**: проверка бизнес-правил (проект не архивирован, уникальность названия)

Нужно решить, где размещать валидацию:
- В API Layer (Pydantic)?
- В Service Layer?
- В Repository Layer?
- В Database (constraints)?

## Decision
Принято решение о **разделении валидации по слоям**:

1. **Pydantic (API Layer)**: техническая валидация входных данных
2. **Service Layer**: бизнес-правила и бизнес-валидация
3. **Repository Layer**: НЕТ валидации, только data access
4. **Database**: constraints для integrity

```python
# Pydantic (API)
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)  # Format validation
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')  # Format

# Service (Business Logic)
async def create_project(self, name: str, color: str):
    # Business validation
    if not name.strip():
        raise ValueError("Name cannot be empty")

    # Business rule: uniqueness
    existing = await self.project_repo.search_by_name(name)
    if existing:
        raise ValueError(f"Project '{name}' already exists")

    # Business rule: color format
    if color and not self._is_valid_hex_color(color):
        raise ValueError(f"Invalid color: {color}")

    # No validation in Repository!
    return await self.project_repo.create(Project(name=name, color=color))

# Repository (NO validation)
async def create(self, obj: Project) -> Project:
    self.db.add(obj)  # Just save, no checks
    await self.db.flush()
    return obj
```

## Alternatives Considered

### 1. Validation в Repository
```python
class ProjectRepository:
    async def create(self, project: Project) -> Project:
        # ❌ Business validation в Repository
        if not project.name.strip():
            raise ValueError("Name cannot be empty")

        existing = await self.get_by_name(project.name)
        if existing:
            raise ValueError("Already exists")

        self.db.add(project)
        return project
```
**Отклонено**:
- ❌ Repository становится зависимым от бизнес-правил
- ❌ Сложно тестировать Repository (нужны mock для других методов)
- ❌ Нарушает Single Responsibility (data access + validation)
- ❌ Нельзя переиспользовать Repository с другими правилами

### 2. Вся валидация в Pydantic
```python
class ProjectCreate(BaseModel):
    name: str

    @field_validator('name')
    def check_uniqueness(cls, v):
        # ❌ Нужен доступ к БД в Pydantic!
        # Как получить db session в validator?
        ...
```
**Отклонено**:
- ❌ Pydantic validators не имеют доступа к БД
- ❌ Смешивание concerns (DTO + business logic)
- ❌ Сложно тестировать

### 3. Validation в моделях (Active Record style)
```python
class Project(Base):
    def validate(self):
        if not self.name.strip():
            raise ValueError("Invalid")
```
**Отклонено**:
- ❌ "Fat models" anti-pattern
- ❌ Модель знает о бизнес-правилах
- ❌ Сложно тестировать

### 4. Отдельный Validator класс
```python
class ProjectValidator:
    def validate_create(self, data: dict):
        ...
```
**Отклонено**:
- ❌ Лишняя абстракция для небольшого проекта
- ❌ Service и так может делать валидацию

## Consequences

### Positive
- ✅ **Separation of Concerns**: техническая vs бизнес-валидация
- ✅ **Reusable Repository**: Repository не зависит от бизнес-правил
- ✅ **Testability**: можно тестировать Service с mock Repository
- ✅ **Clear Responsibility**: Service знает правила бизнеса
- ✅ **Flexibility**: разные Service могут иметь разные правила для одного Repository

### Negative
- ❌ **Duplication**: похожая валидация в Pydantic и Service
- ❌ **Late Validation**: бизнес-ошибки обнаруживаются позже (после Pydantic)

### Neutral
- 🔄 **Error Handling**: Service бросает ValueError, API конвертирует в HTTP 400

## Validation Layers

### Layer 1: Pydantic (API) - Format Validation
```python
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, gt=0)

    @field_validator('due_date')
    def due_date_format(cls, v):
        # Format check (не бизнес-правило!)
        if v and not isinstance(v, date):
            raise ValueError('Must be a date')
        return v
```

**Что проверяет:**
- ✅ Типы данных (str, int, date)
- ✅ Форматы (email, URL, regex pattern)
- ✅ Длина строк (min/max length)
- ✅ Числовые границы (gt, lt, ge, le)
- ✅ Required vs Optional поля

**Что НЕ проверяет:**
- ❌ Бизнес-правила (uniqueness, relationships)
- ❌ Проверки требующие БД
- ❌ Сложная логика

### Layer 2: Service - Business Validation
```python
async def create_task(self, title: str, project_id: int, parent_task_id: Optional[int]):
    # Business Rule 1: Empty title
    if not title.strip():
        raise ValueError("Title cannot be empty")

    # Business Rule 2: Project exists and active
    project = await self.project_repo.get_by_id(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")
    if project.is_archived:
        raise ValueError("Cannot add tasks to archived project")

    # Business Rule 3: Parent task validation
    if parent_task_id:
        parent = await self.task_repo.get_by_id(parent_task_id)
        if not parent:
            raise ValueError(f"Parent task {parent_task_id} not found")

        # Business Rule 4: Hierarchy depth limit
        if parent.parent_task_id is not None:
            raise ValueError("Cannot create subtask of subtask")

        # Business Rule 5: Same project
        if parent.project_id != project_id:
            raise ValueError("Parent task in different project")

    # All validations passed - create task
    return await self.task_repo.create(Task(...))
```

**Что проверяет:**
- ✅ Бизнес-правила (архивированный проект, глубина иерархии)
- ✅ Существование связанных объектов
- ✅ Uniqueness constraints
- ✅ Сложные проверки с несколькими объектами

### Layer 3: Database - Integrity Constraints
```sql
-- Uniqueness
ALTER TABLE tags ADD CONSTRAINT unique_tag_name UNIQUE (name);

-- Foreign Keys
ALTER TABLE tasks ADD CONSTRAINT fk_project
    FOREIGN KEY (project_id) REFERENCES projects(id);

-- Check Constraints
ALTER TABLE projects ADD CONSTRAINT check_color_format
    CHECK (color ~ '^#[0-9A-Fa-f]{6}$');
```

**Что проверяет:**
- ✅ Referential integrity (foreign keys)
- ✅ Uniqueness (UNIQUE constraints)
- ✅ NOT NULL constraints
- ✅ CHECK constraints

## Examples

### Example 1: Creating Project

```python
# 1. API receives JSON
{
    "name": "My Project",
    "color": "#FF0000"
}

# 2. Pydantic validates format
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)  # ✅ Has at least 1 char
    color: str = Field(pattern=r'^#[0-9A-Fa-f]{6}$')  # ✅ Valid hex

# 3. Service validates business rules
async def create_project(self, name: str, color: str):
    # Check uniqueness (business rule)
    existing = await self.project_repo.search_by_name(name)
    if existing:
        raise ValueError("Project already exists")  # ❌ Business rule violated

    # If all OK - create
    return await self.project_repo.create(Project(name=name, color=color))

# 4. Repository just saves (no validation)
async def create(self, project: Project):
    self.db.add(project)
    await self.db.flush()
    return project
```

### Example 2: Creating Task with Parent

```python
# API
@router.post("/tasks")
async def create_task(data: TaskCreate, service: TaskService = Depends(...)):
    try:
        # Pydantic already validated format
        task = await service.create_task(
            title=data.title,
            project_id=data.project_id,
            parent_task_id=data.parent_task_id
        )
        return TaskResponse.model_validate(task)
    except ValueError as e:
        # Business validation failed
        raise HTTPException(status_code=400, detail=str(e))

# Service
async def create_task(self, title, project_id, parent_task_id):
    # Business validation #1
    project = await self.project_repo.get_by_id(project_id)
    if project.is_archived:
        raise ValueError("Cannot add to archived project")

    # Business validation #2
    if parent_task_id:
        parent = await self.task_repo.get_by_id(parent_task_id)
        if parent.parent_task_id is not None:
            raise ValueError("Max 2 levels hierarchy")

    # Repository - no validation
    return await self.task_repo.create(Task(...))
```

## Why Not Repository?

### Problem: Repository становится coupled с бизнес-логикой
```python
# ❌ Bad: Repository знает бизнес-правила
class TaskRepository:
    async def create(self, task: Task):
        # Repository проверяет archived project?
        project = await self.project_repo.get_by_id(task.project_id)
        if project.is_archived:
            raise ValueError("...")

        # Repository проверяет hierarchy?
        if task.parent_task_id:
            parent = await self.get_by_id(task.parent_task_id)
            if parent.parent_task_id:
                raise ValueError("...")

        self.db.add(task)
        await self.db.flush()
```

**Проблемы:**
- Repository зависит от ProjectRepository
- Repository знает про "archived" и "hierarchy limit"
- Сложно переиспользовать (что если нужен другой limit?)
- Сложно тестировать (нужны моки для других repos)

### Solution: Service координирует
```python
# ✅ Good: Service координирует, Repository просто сохраняет
class TaskService:
    async def create_task(self, ...):
        # Service знает бизнес-правила
        project = await self.project_repo.get_by_id(project_id)
        if project.is_archived:
            raise ValueError("...")

        # Service использует Repository для data access
        return await self.task_repo.create(Task(...))

class TaskRepository:
    async def create(self, task: Task):
        # Repository просто сохраняет
        self.db.add(task)
        await self.db.flush()
        return task
```

## Related ADRs
- ADR-0001: Three-Layer Architecture
- ADR-0003: Service Layer for Business Logic
- ADR-0006: Pydantic Schemas (DTO)

## Notes
Разделение валидации по слоям делает код чище:
- **Pydantic** защищает от плохих данных (формат)
- **Service** защищает бизнес-правила
- **Repository** просто работает с данными
- **Database** - последняя линия защиты (constraints)

Это создаёт "defence in depth" - несколько уровней защиты.
