# ADR 0005: FastAPI Framework

## Status
Accepted

## Context
Необходимо было выбрать веб-фреймворк для REST API. Требования:
- Асинхронная работа (async/await)
- Автоматическая валидация данных
- Автоматическая генерация документации (OpenAPI/Swagger)
- Type hints и IDE support
- Высокая производительность
- Простота обучения для учебного проекта

## Decision
Использовать **FastAPI** как основной веб-фреймворк.

## Alternatives Considered

### 1. Flask
```python
@app.route('/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    # Manual validation
    if not data.get('name'):
        return {'error': 'Name required'}, 400
    # ...
```
**Отклонено**:
- ❌ Нет встроенной async поддержки (нужен Flask-Async)
- ❌ Ручная валидация данных
- ❌ Нет автоматической документации
- ❌ Нет type hints support

### 2. Django + Django REST Framework
```python
class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
```
**Отклонено**:
- ❌ Слишком тяжеловесный для API-only проекта
- ❌ ORM тесно интегрирован (хотели использовать SQLAlchemy)
- ❌ Сложнее настроить async
- ❌ Больше boilerplate

### 3. Sanic
```python
@app.post('/projects')
async def create_project(request):
    # Manual validation
    data = request.json
    # ...
```
**Отклонено**:
- ❌ Меньше ecosystem
- ❌ Нет автоматической документации
- ❌ Нет Pydantic integration

### 4. Starlette (базовый фреймворк FastAPI)
**Отклонено**:
- ❌ Слишком низкоуровневый
- ❌ Нужно писать много boilerplate
- ❌ Нет автоматической валидации

## Consequences

### Positive
- ✅ **Async by Default**: полная поддержка async/await
- ✅ **Pydantic Integration**: автоматическая валидация через Pydantic schemas
- ✅ **Auto Documentation**: Swagger UI и ReDoc из коробки
- ✅ **Type Hints**: полная поддержка Python type hints, отличная работа с IDE
- ✅ **Dependency Injection**: встроенная система DI через Depends()
- ✅ **Performance**: один из самых быстрых Python фреймворков
- ✅ **Modern Python**: использует современные возможности Python 3.7+
- ✅ **OpenAPI Standard**: генерация OpenAPI 3.0 спецификации
- ✅ **Learning Curve**: простой и понятный для обучения

### Negative
- ❌ **Young Framework**: меньше legacy code examples в интернете
- ❌ **FastAPI-specific patterns**: код зависит от фреймворка
- ❌ **Breaking Changes**: фреймворк ещё развивается, возможны breaking changes

### Neutral
- 🔄 **Starlette + Pydantic**: FastAPI построен на них, нужно знать оба
- 🔄 **ASGI**: требует ASGI сервер (Uvicorn, Hypercorn)

## Examples

### Automatic Validation
```python
# Pydantic schema
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')

# Endpoint - валидация автоматическая!
@router.post("/projects", response_model=ProjectResponse)
async def create_project(data: ProjectCreate):
    # data уже провалидирована Pydantic
    # если невалидно - FastAPI автоматически вернёт 422 error
    ...
```

### Automatic Documentation
```python
@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new project",
    description="Create a new project with name and optional color"
)
async def create_project(data: ProjectCreate):
    """
    Create a new project.

    - **name**: Project name (required)
    - **color**: Hex color code (optional)
    """
    ...
```
Это автоматически генерирует:
- Swagger UI на `/docs`
- ReDoc на `/redoc`
- OpenAPI JSON на `/openapi.json`

### Dependency Injection
```python
@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,  # Automatic path param validation
    service: ProjectService = Depends(get_project_service)  # DI
):
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

### Error Handling
```python
# Automatic HTTP error handling
try:
    project = await service.create_project(name=data.name)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

## Comparison with Flask

| Feature | FastAPI | Flask |
|---------|---------|-------|
| Async Support | ✅ Native | ⚠️ Flask-Async extension |
| Validation | ✅ Automatic (Pydantic) | ❌ Manual |
| Documentation | ✅ Auto (Swagger/ReDoc) | ❌ Flask-RESTX extension |
| Type Hints | ✅ Full support | ⚠️ Partial |
| Performance | ✅ Very fast | ⚠️ Slower |
| DI | ✅ Built-in | ❌ Manual |
| Learning Curve | ✅ Easy | ✅ Easy |
| Maturity | ⚠️ Young | ✅ Mature |

## Performance
FastAPI - один из самых быстрых Python фреймворков:
- Comparable to Node.js and Go
- Построен на Starlette (ASGI)
- Async I/O позволяет обрабатывать тысячи запросов параллельно

## Developer Experience

### Auto-completion в IDE
```python
@router.post("/projects")
async def create_project(
    data: ProjectCreate,  # IDE знает все поля ProjectCreate
    service: ProjectService = Depends(...)  # IDE знает методы ProjectService
):
    project = await service.create_project(
        name=data.name,  # IDE автодополнение работает!
        color=data.color
    )
    return project  # IDE знает тип возврата
```

### Interactive Documentation
- **Swagger UI**: `/docs` - можно тестировать API прямо в браузере
- **ReDoc**: `/redoc` - красивая читаемая документация
- Автоматически обновляется при изменении кода

## Related ADRs
- ADR-0004: Dependency Injection - использует встроенную DI FastAPI
- ADR-0006: Pydantic Schemas - FastAPI интегрирован с Pydantic
- ADR-0012: Async Architecture - FastAPI поддерживает async

## Migration Path
Если потребуется мигрировать на другой фреймворк:
- Business logic в Service Layer не зависит от FastAPI
- Repository Layer не зависит от FastAPI
- Нужно переписать только API Layer

## Notes
FastAPI был выбран как идеальный баланс между:
- Простотой (для учебного проекта)
- Современностью (async, type hints)
- Функциональностью (auto docs, validation)
- Производительностью

Для учебного проекта автоматическая документация и валидация особенно ценны.
