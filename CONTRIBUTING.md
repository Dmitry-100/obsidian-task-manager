# Contributing Guide

Руководство по разработке Obsidian Task Manager.

## Quick Start

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Dmitry-100/obsidian-task-manager.git
cd obsidian-task-manager

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Установить pre-commit hooks
pre-commit install

# 5. Запустить проверки
./scripts/check.sh
```

## Development Workflow

### 1. Создание ветки

```bash
git checkout -b feature/my-feature
# или
git checkout -b fix/bug-description
```

### 2. Разработка

Пишите код, следуя стандартам проекта (см. ниже).

### 3. Проверка перед коммитом

```bash
# Запустить все проверки
./scripts/check.sh

# Или по отдельности:
ruff check src/           # Линтер
ruff format src/          # Форматирование
mypy src/                 # Типы
bandit -r src/ -q         # Безопасность
pytest                    # Тесты
```

### 4. Коммит

Pre-commit автоматически проверит код:

```bash
git add .
git commit -m "feat: add new feature"
```

### 5. Pull Request

Создайте PR и заполните чек-лист Definition of Done.

---

## Code Standards

### Type Hints

Все функции должны иметь type hints:

```python
# Правильно
async def create_task(
    self,
    title: str,
    project_id: int,
    priority: TaskPriority = TaskPriority.MEDIUM,
) -> Task:
    ...

# Неправильно
async def create_task(self, title, project_id, priority=None):
    ...
```

### Docstrings

Публичные методы должны иметь docstrings:

```python
async def create_task(self, title: str, project_id: int) -> Task:
    """
    Создать новую задачу.

    Args:
        title: Название задачи
        project_id: ID проекта

    Returns:
        Созданная задача

    Raises:
        ValueError: Если проект не найден
    """
```

### Error Handling

Используйте правильные исключения:

```python
# Service Layer - ValueError
if not project:
    raise ValueError(f"Project with id {project_id} not found")

# API Layer - HTTPException
except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e))
```

### Configuration

Никаких захардкоженных значений:

```python
# Правильно
from src.core.config import settings
database_url = settings.DATABASE_URL

# Неправильно
database_url = "postgresql://localhost/mydb"
```

---

## Definition of Done

Фича считается готовой, когда выполнены ВСЕ пункты:

### Code Quality
- [ ] Ruff linter проходит без ошибок
- [ ] Ruff format применён
- [ ] Mypy проверка типов пройдена
- [ ] Bandit security scan пройден

### Testing
- [ ] Тесты написаны для новой функциональности
- [ ] Все тесты проходят
- [ ] Coverage не упал (минимум 70%)

### Code Standards
- [ ] Type hints добавлены
- [ ] Docstrings написаны
- [ ] Нет захардкоженных значений
- [ ] Ошибки обрабатываются корректно

### Security
- [ ] Нет секретов в коде
- [ ] Пользовательский ввод валидируется
- [ ] SQL инъекции невозможны (ORM)

### Documentation
- [ ] README обновлён (если нужно)
- [ ] API endpoints задокументированы

---

## Project Architecture

```
src/
├── api/           # FastAPI endpoints (тонкий слой)
├── core/          # Конфигурация, база данных
├── models/        # SQLAlchemy модели
├── repositories/  # Работа с БД (CRUD)
└── services/      # Бизнес-логика
```

### Правила архитектуры

1. **API Layer** → вызывает только Service Layer
2. **Service Layer** → вызывает Repository Layer, содержит бизнес-логику
3. **Repository Layer** → работает только с БД

```python
# API → Service → Repository
@router.post("/tasks")
async def create_task(data: TaskCreate, db: AsyncSession):
    service = TaskService(db)              # API → Service
    return await service.create_task(...)  # Service → Repository (внутри)
```

---

## Useful Commands

```bash
# Запуск сервера
uvicorn src.main:app --reload

# Все проверки
./scripts/check.sh

# Только быстрые проверки (без тестов)
./scripts/check.sh --fast

# С автоисправлением
./scripts/check.sh --fix

# Тесты с coverage
pytest --cov=src --cov-report=html

# Pre-commit на всех файлах
pre-commit run --all-files
```

---

## Commit Messages

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add user authentication
fix: resolve task deletion bug
docs: update API documentation
test: add tests for TaskService
refactor: simplify error handling
chore: update dependencies
```
