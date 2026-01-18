# ADR 0002: Repository Pattern with Generic Base Class

## Status
Accepted

## Context
Необходимо было организовать слой доступа к данным для работы с несколькими моделями (Project, Task, Tag, TaskComment). Требовалось:
- Избежать дублирования CRUD кода для каждой модели
- Обеспечить type safety при работе с разными моделями
- Сохранить возможность добавлять специфичные методы для каждой модели
- Упростить тестирование через mock repositories

## Decision
Использовать **Repository Pattern** с **Generic Base Class**:

```python
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def create(self, obj: ModelType) -> ModelType:
        # Generic CRUD implementation
        ...
```

Каждая конкретная модель имеет свой репозиторий:
```python
class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: AsyncSession):
        super().__init__(Project, db)

    # Специфичные методы
    async def get_active_projects(self) -> List[Project]:
        ...
```

## Alternatives Considered

1. **Active Record Pattern**: Отклонено, так как бизнес-логика смешивается с моделями
2. **Data Mapper без Generic**: Отклонено из-за дублирования кода
3. **SQLAlchemy напрямую в Service**: Отклонено - нарушает разделение ответственности
4. **Один универсальный Repository**: Отклонено - теряется type safety и специфичные методы

## Consequences

### Positive
- ✅ **DRY**: базовые CRUD методы написаны один раз
- ✅ **Type Safety**: TypeVar обеспечивает корректные типы при компиляции
- ✅ **Расширяемость**: легко добавить специфичные методы для модели
- ✅ **Тестируемость**: Repository легко мокируется в тестах Service
- ✅ **Инкапсуляция**: вся работа с SQLAlchemy скрыта от Service
- ✅ **Переиспользование**: один BaseRepository для всех моделей

### Negative
- ❌ **Complexity**: нужно понимать Generic типы Python
- ❌ **Boilerplate**: для каждой модели нужен класс репозитория
- ❌ **Ограничения Generic**: TypeVar не поддерживает все возможности Python typing

### Neutral
- 🔄 **flush() vs commit()**: Repository использует flush(), оставляя commit() для Service
- 🔄 **Error Handling**: Repository пробрасывает исключения SQLAlchemy вверх

## Examples

### Base Repository
```python
class BaseRepository(Generic[ModelType]):
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj
```

### Specific Repository
```python
class TaskRepository(BaseRepository[Task]):
    async def get_by_project(self, project_id: int) -> List[Task]:
        result = await self.db.execute(
            select(Task).where(Task.project_id == project_id)
        )
        return list(result.scalars().all())
```

## Impact on Testing
```python
# Mock repository для тестов
class MockProjectRepository(BaseRepository[Project]):
    def __init__(self):
        self.projects = []

    async def create(self, project: Project) -> Project:
        self.projects.append(project)
        return project
```

## Related ADRs
- ADR-0001: Three-Layer Architecture - Repository является частью Data Access Layer
- ADR-0007: flush() в Repository, commit() в Dependency

## Notes
Этот паттерн делает код более предсказуемым и безопасным. IDE (PyCharm, VSCode) корректно подсказывает типы благодаря Generic.
