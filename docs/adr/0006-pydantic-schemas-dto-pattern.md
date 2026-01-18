# ADR 0006: Pydantic Schemas (DTO Pattern)

## Status
Accepted

## Context
Необходимо было решить, как представлять данные в API:
- Как валидировать входящие данные от клиента?
- Как сериализовать SQLAlchemy модели в JSON?
- Как скрыть внутренние поля (например, created_at при создании)?
- Как обеспечить разные представления для разных операций (Create vs Response)?

Проблема использования SQLAlchemy моделей напрямую:
```python
# ❌ Плохо
@router.post("/projects")
async def create_project(project: Project):  # SQLAlchemy model
    # Клиент может установить любые поля, включая id, created_at
    # Нет валидации
    # Сложная сериализация
```

## Decision
Использовать **Pydantic Schemas как DTO (Data Transfer Objects)**, полностью отдельно от SQLAlchemy моделей:

```python
# SQLAlchemy Model (Database)
class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    ...

# Pydantic Schemas (API)
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    color: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    color: Optional[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

## Alternatives Considered

### 1. Использовать SQLAlchemy модели напрямую
```python
@router.post("/projects")
async def create_project(project: Project):
    ...
```
**Отклонено**:
- ❌ Клиент может установить id, created_at
- ❌ Нет валидации полей
- ❌ Exposure внутренних деталей БД
- ❌ Сложно сериализовать relationship

### 2. Marshmallow Schemas
```python
class ProjectSchema(Schema):
    name = fields.Str(required=True, validate=Length(min=1))
    color = fields.Str()
```
**Отклонено**:
- ❌ Отдельная библиотека (не интегрирована с FastAPI)
- ❌ Нет type hints support
- ❌ Хуже работает с IDE

### 3. Dataclasses
```python
@dataclass
class ProjectCreate:
    name: str
    color: Optional[str] = None
```
**Отклонено**:
- ❌ Нет автоматической валидации
- ❌ Нет JSON сериализации из коробки
- ❌ Нет Field validators

### 4. Одна Pydantic Schema для всего
```python
class Project(BaseModel):
    id: Optional[int] = None  # Present только в response
    name: str
    created_at: Optional[datetime] = None  # Present только в response
```
**Отклонено**:
- ❌ Путаница: какие поля для Create, какие для Response
- ❌ Клиент может попытаться установить id
- ❌ Нет чёткого контракта

## Consequences

### Positive
- ✅ **Separation of Concerns**: API representation отделена от DB models
- ✅ **Automatic Validation**: Pydantic валидирует данные автоматически
- ✅ **Type Safety**: полная поддержка type hints
- ✅ **Clear API Contract**: разные schemas для Create/Update/Response
- ✅ **Field Validation**: можно задать min/max длину, regex паттерны
- ✅ **JSON Serialization**: автоматическая сериализация/десериализация
- ✅ **IDE Support**: автодополнение работает идеально
- ✅ **Documentation**: schemas автоматически документируются в Swagger
- ✅ **Security**: клиент не может установить internal поля

### Negative
- ❌ **Duplication**: некоторые поля дублируются в Model и Schema
- ❌ **Boilerplate**: нужно писать несколько schemas для одной entity
- ❌ **Sync Issues**: изменение Model требует изменения Schema
- ❌ **Conversion Overhead**: нужно конвертировать Model ↔ Schema

### Neutral
- 🔄 **Manual Conversion**: `model_validate()` для конвертации Model → Schema
- 🔄 **Nested Schemas**: для relationships нужны вложенные schemas

## Schema Types Pattern

Для каждой entity создаём несколько schemas:

### 1. Base Schema (общие поля)
```python
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
```

### 2. Create Schema (input для POST)
```python
class ProjectCreate(ProjectBase):
    # Только поля, которые клиент может установить при создании
    obsidian_folder: Optional[str] = None
```

### 3. Update Schema (input для PUT/PATCH)
```python
class ProjectUpdate(BaseModel):
    # Все поля Optional (partial update)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    color: Optional[str] = None
```

### 4. Response Schema (output)
```python
class ProjectResponse(ProjectBase):
    # Включаем server-generated поля
    id: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)  # Для конвертации из ORM
```

### 5. Detailed Response (with relationships)
```python
class ProjectDetailResponse(ProjectResponse):
    tasks: List[TaskResponse] = []  # Nested schema
```

## Examples

### API Endpoint with Schemas
```python
@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,  # Input validation
    service: ProjectService = Depends(get_project_service)
):
    # data уже провалидирована Pydantic
    project = await service.create_project(
        name=data.name,
        color=data.color,
        obsidian_folder=data.obsidian_folder
    )

    # Конвертация ORM Model → Pydantic Schema
    return ProjectResponse.model_validate(project)
```

### Field Validation
```python
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300, description="Task title")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, gt=0, description="Must be positive")

    @field_validator('due_date')
    def due_date_not_in_past(cls, v):
        if v and v < date.today():
            raise ValueError('Due date cannot be in the past')
        return v
```

### Nested Schemas
```python
class TagResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

class TaskDetailResponse(BaseModel):
    id: int
    title: str
    tags: List[TagResponse] = []  # Nested
    comments: List[CommentResponse] = []  # Nested

    model_config = ConfigDict(from_attributes=True)
```

### Conversion: ORM → Pydantic
```python
# ORM model
task = await task_repo.get_by_id_full(1)  # Returns Task (SQLAlchemy)

# Convert to Pydantic
response = TaskDetailResponse.model_validate(task)

# Now can return as JSON
return response  # FastAPI автоматически сериализует
```

## Validation Flow

```
Client sends JSON
    ↓
FastAPI receives request
    ↓
Pydantic validates against ProjectCreate schema
    ↓
If invalid: automatic 422 error
If valid: pass to endpoint
    ↓
Service processes business logic
    ↓
Repository returns ORM model
    ↓
Convert ORM → Pydantic (model_validate)
    ↓
FastAPI serializes to JSON
    ↓
Client receives response
```

## Error Handling

### Automatic Validation Errors (422)
```python
# Client sends
POST /projects
{
    "name": "",  # Too short
    "color": "red"  # Invalid format
}

# FastAPI automatically returns
{
    "detail": [
        {
            "type": "string_too_short",
            "loc": ["body", "name"],
            "msg": "String should have at least 1 character"
        },
        {
            "type": "string_pattern_mismatch",
            "loc": ["body", "color"],
            "msg": "String should match pattern '^#[0-9A-Fa-f]{6}$'"
        }
    ]
}
```

## Documentation Benefits

Pydantic schemas автоматически документируются в Swagger:
- Request body schema с примерами
- Response schema
- Validation rules (min/max, pattern)
- Field descriptions
- Required/Optional поля

## Related ADRs
- ADR-0005: FastAPI Framework - интеграция с Pydantic
- ADR-0008: SQLAlchemy 2.0 Async - разделение ORM models и DTO

## Notes
Разделение ORM Models и Pydantic Schemas - один из ключевых паттернов для чистой архитектуры. Да, это создаёт некоторое дублирование, но зато:
- API контракт независим от БД
- Безопасность (клиент не может установить internal поля)
- Ясность (понятно, что можно передать в API)
