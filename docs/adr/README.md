# Architecture Decision Records (ADR)

Этот каталог содержит все архитектурные решения проекта Obsidian Task Manager.

## Что такое ADR?

Architecture Decision Record (ADR) - это документ, который фиксирует важное архитектурное решение вместе с его контекстом и последствиями.

## Формат ADR

Каждый ADR содержит:
- **Status**: Accepted / Proposed / Deprecated
- **Context**: Почему это решение было важно
- **Decision**: Что было решено
- **Alternatives Considered**: Какие варианты рассматривались
- **Consequences**: Положительные и отрицательные последствия
- **Examples**: Примеры кода и использования

## Список всех ADR

### Архитектурные паттерны

1. **[ADR-0001: Three-Layer Architecture](0001-three-layer-architecture.md)**
   - Разделение на API → Service → Repository слои
   - Основа всей архитектуры проекта

2. **[ADR-0002: Repository Pattern with Generics](0002-repository-pattern-with-generics.md)**
   - Generic BaseRepository для всех моделей
   - Type safety через TypeVar

3. **[ADR-0003: Service Layer for Business Logic](0003-service-layer-for-business-logic.md)**
   - Бизнес-логика в Service слое
   - Координация между несколькими репозиториями

4. **[ADR-0004: Dependency Injection Pattern](0004-dependency-injection-pattern.md)**
   - DI через FastAPI Depends()
   - Автоматическое управление lifecycle

### Технологический стек

5. **[ADR-0005: FastAPI Framework](0005-fastapi-framework.md)**
   - Выбор FastAPI как веб-фреймворка
   - Async, auto validation, auto documentation

6. **[ADR-0006: Pydantic Schemas (DTO Pattern)](0006-pydantic-schemas-dto-pattern.md)**
   - Отдельные Pydantic schemas для API
   - Разделение ORM models и DTOs

7. **[ADR-0008: SQLAlchemy 2.0 Async ORM](0008-sqlalchemy-2-0-async-orm.md)**
   - Async SQLAlchemy 2.0 с новым синтаксисом
   - Mapped[] type annotations

8. **[ADR-0011: Database Support - PostgreSQL and SQLite](0011-database-support-postgresql-sqlite.md)**
   - Поддержка обеих БД
   - Разные pool strategies

### Frontend

17. **[ADR-0017: Frontend Framework Selection](0017-frontend-framework-selection.md)**
    - Выбор React + TypeScript + Vite
    - TailwindCSS, shadcn/ui, TanStack Query

### Работа с данными

7. **[ADR-0007: Transaction Management (flush vs commit)](0007-transaction-management-flush-vs-commit.md)**
   - flush() в Repository/Service
   - commit() только в Dependency
   - Решение проблемы expired relationships

9. **[ADR-0009: Eager Loading Strategy (selectinload)](0009-eager-loading-strategy.md)**
   - selectinload() для избежания N+1 проблемы
   - Два метода: get_by_id() vs get_by_id_full()

10. **[ADR-0010: Validation in Service Layer](0010-validation-in-service-layer.md)**
    - Техническая валидация в Pydantic
    - Бизнес-валидация в Service
    - Repository без валидации

### Бизнес-логика

13. **[ADR-0013: Tag Normalization for Obsidian](0013-tag-normalization-for-obsidian.md)**
    - Автоматическая нормализация тегов
    - Совместимость с Obsidian формат

14. **[ADR-0014: Two-Level Task Hierarchy Limit](0014-two-level-task-hierarchy-limit.md)**
    - Максимум 2 уровня вложенности задач
    - Task → Subtask (без sub-subtasks)

### Модели данных

15. **[ADR-0015: Explicit Junction Table for Many-to-Many](0015-explicit-junction-table-for-many-to-many.md)**
    - Явная junction table для Task-Tag relationship
    - Поле created_at для аудита

16. **[ADR-0016: TimestampMixin for Audit Trail](0016-timestamp-mixin-for-audit.md)**
    - Mixin для created_at/updated_at
    - DRY principle для всех моделей

### Интеграции

18. **[ADR-0018: Obsidian Sync Integration](0018-obsidian-sync-integration.md)**
    - Двусторонняя синхронизация с Obsidian Tasks Plugin
    - Parser, Writer, Project Resolver
    - Conflict Resolution UI

### Инфраструктура

12. **[ADR-0012: Fully Async Architecture](0012-async-architecture.md)**
    - Async/await на всех слоях
    - FastAPI + SQLAlchemy async + asyncpg/aiosqlite

## Категории решений

### По уровням архитектуры

**API Layer:**
- ADR-0005: FastAPI Framework
- ADR-0006: Pydantic Schemas
- ADR-0004: Dependency Injection

**Service Layer:**
- ADR-0003: Service Layer for Business Logic
- ADR-0010: Validation in Service Layer
- ADR-0013: Tag Normalization
- ADR-0014: Task Hierarchy Limit

**Repository Layer:**
- ADR-0002: Repository Pattern
- ADR-0009: Eager Loading Strategy

**Database:**
- ADR-0008: SQLAlchemy 2.0 Async
- ADR-0011: PostgreSQL and SQLite Support
- ADR-0015: Junction Table
- ADR-0016: TimestampMixin

**Cross-cutting:**
- ADR-0001: Three-Layer Architecture
- ADR-0007: Transaction Management
- ADR-0012: Async Architecture

### По проблемам

**Performance:**
- ADR-0009: Eager Loading (решает N+1)
- ADR-0012: Async Architecture (высокий throughput)

**Data Integrity:**
- ADR-0007: Transaction Management
- ADR-0010: Validation
- ADR-0015: Junction Table

**Code Quality:**
- ADR-0002: Repository Pattern (DRY, type safety)
- ADR-0016: TimestampMixin (DRY)

**Business Requirements:**
- ADR-0013: Tag Normalization (Obsidian integration)
- ADR-0014: Task Hierarchy (UX simplicity)

## Связи между ADR

### Фундаментальные решения (влияют на всё)
1. **ADR-0001: Three-Layer Architecture** - основа проекта
2. **ADR-0012: Async Architecture** - async на всех слоях

### Зависимости

```
ADR-0001 (3-Layer)
├── ADR-0002 (Repository Pattern)
├── ADR-0003 (Service Layer)
└── ADR-0004 (Dependency Injection)

ADR-0012 (Async)
├── ADR-0005 (FastAPI)
├── ADR-0008 (SQLAlchemy Async)
└── ADR-0009 (Eager Loading)

ADR-0008 (SQLAlchemy)
├── ADR-0007 (Transaction Management)
├── ADR-0009 (Eager Loading)
├── ADR-0011 (Database Support)
├── ADR-0015 (Junction Table)
└── ADR-0016 (TimestampMixin)
```

## Хронология решений

Порядок принятия решений в проекте:

1. **ADR-0001**: Three-Layer Architecture (фундамент)
2. **ADR-0012**: Async Architecture (технический выбор)
3. **ADR-0005**: FastAPI (фреймворк)
4. **ADR-0008**: SQLAlchemy 2.0 Async (ORM)
5. **ADR-0011**: PostgreSQL/SQLite Support (БД)
6. **ADR-0002**: Repository Pattern (data layer)
7. **ADR-0003**: Service Layer (business layer)
8. **ADR-0004**: Dependency Injection (связывание слоёв)
9. **ADR-0006**: Pydantic Schemas (API contracts)
10. **ADR-0007**: Transaction Management (исправление bug'а)
11. **ADR-0009**: Eager Loading (исправление N+1 и greenlet errors)
12. **ADR-0010**: Validation in Service (разделение ответственности)
13. **ADR-0016**: TimestampMixin (DRY для моделей)
14. **ADR-0015**: Junction Table (M:M relationship)
15. **ADR-0013**: Tag Normalization (бизнес-требование Obsidian)
16. **ADR-0014**: Task Hierarchy Limit (бизнес-требование UX)

## Статистика

- **Всего ADR**: 18
- **Architectural Patterns**: 4 (ADR-0001 to ADR-0004)
- **Tech Stack Backend**: 4 (ADR-0005, ADR-0006, ADR-0008, ADR-0011)
- **Tech Stack Frontend**: 1 (ADR-0017)
- **Data Management**: 4 (ADR-0007, ADR-0009, ADR-0010, ADR-0015)
- **Business Logic**: 2 (ADR-0013, ADR-0014)
- **Infrastructure**: 2 (ADR-0012, ADR-0016)
- **Integrations**: 1 (ADR-0018)

## Ключевые принципы проекта

Из ADR можно выделить ключевые принципы:

1. **Separation of Concerns** (ADR-0001, ADR-0010)
   - API ≠ Service ≠ Repository
   - Technical ≠ Business logic

2. **DRY (Don't Repeat Yourself)** (ADR-0002, ADR-0016)
   - Generic Repository
   - TimestampMixin

3. **Explicit over Implicit** (ADR-0009, ADR-0015)
   - Явный eager loading
   - Явная junction table

4. **Type Safety** (ADR-0002, ADR-0006, ADR-0008)
   - Generic types в Repository
   - Pydantic schemas
   - SQLAlchemy Mapped[]

5. **Async First** (ADR-0012)
   - Async на всех слоях

6. **Database Agnostic** (ADR-0011)
   - Работает с PostgreSQL и SQLite

## Как читать ADR

### Для новичков в проекте
Рекомендуемый порядок чтения:
1. ADR-0001: Three-Layer Architecture - общая структура
2. ADR-0012: Async Architecture - async концепция
3. ADR-0005: FastAPI Framework - веб-фреймворк
4. ADR-0008: SQLAlchemy 2.0 - ORM
5. Остальные по мере необходимости

### Для понимания конкретной области

**Хочу понять API Layer:**
- ADR-0005: FastAPI
- ADR-0006: Pydantic Schemas
- ADR-0004: Dependency Injection

**Хочу понять работу с БД:**
- ADR-0008: SQLAlchemy
- ADR-0007: Transaction Management
- ADR-0009: Eager Loading
- ADR-0011: Database Support

**Хочу понять бизнес-логику:**
- ADR-0003: Service Layer
- ADR-0010: Validation
- ADR-0013: Tag Normalization
- ADR-0014: Task Hierarchy

## Как добавить новый ADR

1. Создайте файл `XXXX-short-title.md`
2. Используйте следующий template:

```markdown
# ADR XXXX: Title

## Status
Proposed / Accepted / Deprecated

## Context
Описание проблемы и почему нужно решение

## Decision
Что решили делать

## Alternatives Considered
Какие варианты рассматривались и почему отклонены

## Consequences
### Positive
- ✅ Плюсы

### Negative
- ❌ Минусы

### Neutral
- 🔄 Нейтральные моменты

## Examples
Примеры кода

## Related ADRs
Ссылки на связанные ADR

## Notes
Дополнительные заметки
```

3. Добавьте ссылку в этот README
4. Commit: `docs: add ADR-XXXX for [decision name]`

## Обновление ADR

ADR **не изменяются** после принятия. Если решение меняется:
1. Создайте новый ADR
2. Отметьте старый как "Deprecated"
3. В новом ADR укажите ссылку на устаревший

Пример:
- ADR-0007: Transaction Management (Accepted)
- ADR-0XXX: Transaction Management v2 (Accepted) - supersedes ADR-0007
- ADR-0007: Transaction Management (Deprecated by ADR-0XXX)

## Полезные ресурсы

- [ADR GitHub Organization](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [Architecture Decision Records in Action](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records)
