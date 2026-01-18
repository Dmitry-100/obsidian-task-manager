# ADR 0003: Service Layer for Business Logic

## Status
Accepted

## Context
В проекте существуют сложные бизнес-правила:
- Нельзя добавлять задачи в архивированный проект
- Нельзя создать подзадачу для подзадачи (максимум 2 уровня)
- Теги должны нормализоваться для совместимости с Obsidian
- При создании задачи нужно координировать работу нескольких репозиториев (Task, Tag, TaskTag)

Нужно решить, где размещать эту логику:
- В API endpoints?
- В Repository?
- В отдельном Service слое?

## Decision
Создать **Service Layer** между API и Repository для размещения всей бизнес-логики:

```python
class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.project_repo = ProjectRepository(db)
        self.tag_repo = TagRepository(db)

    async def create_task(self, title: str, project_id: int, ...):
        # Business validation
        if not title.strip():
            raise ValueError("Title cannot be empty")

        # Business rules
        project = await self.project_repo.get_by_id(project_id)
        if project.is_archived:
            raise ValueError("Cannot add tasks to archived project")

        # Coordination
        task = await self.task_repo.create(Task(...))
        tags = await self.tag_repo.bulk_get_or_create(tag_names)
        for tag in tags:
            await self.task_repo.add_tag(task.id, tag)

        await self.db.flush()
        return task
```

## Alternatives Considered

1. **Business Logic в API Layer**:
   - Отклонено: API становится толстым, сложно тестировать, нельзя переиспользовать

2. **Business Logic в Repository**:
   - Отклонено: смешиваются технические и бизнес-задачи, репозиторий становится зависимым от других репозиториев

3. **Business Logic в Models (Active Record)**:
   - Отклонено: модели становятся "fat models", сложно тестировать

4. **Domain Services + Application Services**:
   - Отклонено: избыточная сложность для учебного проекта

## Consequences

### Positive
- ✅ **Separation of Concerns**: бизнес-логика отделена от технической
- ✅ **Testability**: Service легко тестировать с mock repositories
- ✅ **Reusability**: Service может использоваться из API, CLI, background jobs
- ✅ **Single Responsibility**: Repository = data access, Service = business rules
- ✅ **Coordination**: Service координирует работу нескольких репозиториев
- ✅ **Transaction Management**: Service управляет границами транзакций (flush)

### Negative
- ❌ **Extra Layer**: дополнительная прослойка в коде
- ❌ **Boilerplate**: простые CRUD проходят через Service без реальной логики
- ❌ **Learning Curve**: нужно понимать разницу между Service и Repository

### Neutral
- 🔄 **Error Handling**: Service преобразует технические ошибки в бизнесовые
- 🔄 **Validation**: и Pydantic (в API), и Service (бизнес-правила) делают валидацию

## Examples

### Business Validation in Service
```python
async def create_project(self, name: str, color: str) -> Project:
    # VALIDATION: Business rule
    if not name or not name.strip():
        raise ValueError("Project name cannot be empty")

    # VALIDATION: Uniqueness (business constraint)
    existing = await self.project_repo.search_by_name(name.strip())
    if existing:
        raise ValueError(f"Project '{name}' already exists")

    # VALIDATION: Format (business rule)
    if color and not self._is_valid_hex_color(color):
        raise ValueError(f"Invalid color format: {color}")

    # Data operation
    project = await self.project_repo.create(Project(name=name, color=color))
    await self.db.flush()
    return project
```

### Coordination Between Repositories
```python
async def create_task(self, title: str, tag_names: List[str], ...):
    # Create task
    task = await self.task_repo.create(Task(title=title, ...))

    # Get or create tags
    tags = await self.tag_repo.bulk_get_or_create(tag_names)

    # Link task and tags
    for tag in tags:
        await self.task_repo.add_tag(task.id, tag)

    await self.db.flush()
    return await self.task_repo.get_by_id_full(task.id)
```

## What Goes into Service vs Repository?

### Service (Business Logic)
- ✅ Бизнес-правила ("cannot add task to archived project")
- ✅ Валидация бизнес-ограничений (uniqueness, formats)
- ✅ Координация между несколькими репозиториями
- ✅ Workflow orchestration
- ✅ flush() для сохранения изменений

### Repository (Technical Logic)
- ✅ CRUD операции
- ✅ SQL queries
- ✅ ORM взаимодействие
- ✅ Eager/Lazy loading
- ✅ Фильтрация, сортировка, пагинация

## Related ADRs
- ADR-0001: Three-Layer Architecture
- ADR-0002: Repository Pattern
- ADR-0007: flush() в Repository/Service, commit() в Dependency
- ADR-0010: Validation в Service, не в Repository

## Notes
Service Layer - это "сердце" бизнес-логики приложения. API - это просто транспорт, Repository - просто data access, но Service знает правила игры.
