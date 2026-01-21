# Неделя 6: Качество и Безопасность

**Дата:** 22 января 2026
**Тема:** Quality Assurance, Security, CI/CD

---

## Цели недели

Настроить инструменты контроля качества кода и автоматизировать проверки.

---

## Что сделано

### 1. Test Coverage (pytest-cov)

**Что это:** Измерение того, какой процент кода выполняется при запуске тестов.

```bash
pytest --cov=src --cov-report=term-missing
```

**Результат:**
| Метрика | Значение |
|---------|----------|
| Общее покрытие | 78% |
| services/task.py | 98% (было 58%) |
| Добавлено тестов | +26 |

**Ключевые тесты добавлены для:**
- Валидации в create_task/update_task
- complete_task с подзадачами
- Управление тегами (add/remove)
- Комментарии
- Статистика и иерархия задач

---

### 2. Ruff (Linter + Formatter)

**Что это:** Быстрый линтер на Rust, заменяет flake8, isort, black.

```bash
ruff check src/      # Проверка
ruff check src/ --fix  # Автоисправление
ruff format src/     # Форматирование
```

**Конфигурация:** `pyproject.toml`
```toml
[tool.ruff.lint]
select = ["E", "F", "I", "W", "UP", "B", "SIM"]
ignore = ["E501", "B008", "B904", "E712"]

[tool.ruff.lint.per-file-ignores]
"src/models/*.py" = ["F821"]  # Forward references
```

**Результат:** 202 ошибки автоисправлено, 0 оставшихся.

---

### 3. Mypy (Type Checker)

**Что это:** Статический анализатор типов Python.

```bash
mypy src/
```

**Конфигурация:** `pyproject.toml`
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = ["src.repositories.*", "src.models.*"]
ignore_errors = true  # Сложные generics
```

**Результат:** 0 ошибок типов.

---

### 4. Bandit (Security Scanner)

**Что это:** Сканер безопасности, ищет уязвимости в коде.

```bash
bandit -r src/ -q
```

**Что проверяет:**
- SQL инъекции
- Захардкоженные пароли
- Небезопасные функции (eval, exec)
- Слабые алгоритмы шифрования

**Результат:** 0 уязвимостей найдено.

---

### 5. Pre-commit Hooks

**Что это:** Git hooks, запускающие проверки перед каждым коммитом.

```bash
pre-commit install  # Установка
pre-commit run --all-files  # Ручной запуск
```

**Конфигурация:** `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Результат:** Автоматические проверки при каждом коммите.

---

### 6. Definition of Done

**Что это:** Чек-лист критериев готовности фичи.

**Создано:**

1. **PR Template** (`.github/pull_request_template.md`)
   - Чек-лист появляется при создании PR
   - Code Quality, Testing, Security, Documentation

2. **CONTRIBUTING.md**
   - Гайд для разработчика
   - Code Standards с примерами
   - Development Workflow

3. **Обновлённый check.sh**
   - Выводит DoD summary
   - Показывает статус всех проверок

---

### 7. GitHub Actions CI

**Что это:** Автоматические проверки на GitHub при push/PR.

**Конфигурация:** `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - Ruff Linter
      - Ruff Format Check
      - Mypy Type Checker
      - Bandit Security Check
      - Pytest with Coverage
```

**Результат:** CI бейдж в README.

---

## Архитектура качества

```
Developer Workflow:

  Код → pre-commit → Коммит → Push → GitHub Actions
         │                            │
         ├─ trailing-whitespace       ├─ ruff check
         ├─ end-of-file-fixer         ├─ ruff format --check
         ├─ check-yaml                ├─ mypy
         ├─ ruff --fix                ├─ bandit
         └─ ruff-format               └─ pytest --cov
```

---

## Команды

```bash
# Все проверки локально
./scripts/check.sh

# Быстрые проверки (без тестов)
./scripts/check.sh --fast

# С автоисправлением
./scripts/check.sh --fix

# Отдельные инструменты
ruff check src/
ruff format src/
mypy src/
bandit -r src/ -q
pytest --cov=src
```

---

## Файлы проекта

```
obsidian-task-manager/
├── .pre-commit-config.yaml    # Pre-commit hooks
├── pyproject.toml             # Ruff, Mypy, Pytest config
├── CONTRIBUTING.md            # Developer guide
├── .github/
│   ├── pull_request_template.md  # PR checklist
│   └── workflows/
│       └── ci.yml             # GitHub Actions
└── scripts/
    └── check.sh               # Quality check script
```

---

## Метрики

| Инструмент | Статус | Результат |
|------------|--------|-----------|
| pytest-cov | ✅ | 78% coverage |
| ruff | ✅ | 0 errors |
| mypy | ✅ | 0 type errors |
| bandit | ✅ | 0 vulnerabilities |
| pre-commit | ✅ | Installed |
| GitHub Actions | ✅ | Passing |

---

## Изученные концепции

1. **SQL Injection** — атака через пользовательский ввод в SQL. SQLAlchemy ORM защищает через параметризованные запросы.

2. **Static Analysis** — анализ кода без выполнения (ruff, mypy).

3. **Pre-commit Hooks** — автоматизация проверок в Git workflow.

4. **CI/CD** — Continuous Integration автоматизирует сборку и тесты.

5. **Definition of Done** — стандарт качества для каждой фичи.

---

## Итог недели 6

**До:**
- Только pytest
- Нет проверок стиля
- Нет автоматизации

**После:**
- 78% test coverage
- Ruff + Mypy + Bandit
- Pre-commit на каждый коммит
- GitHub Actions CI
- Definition of Done процесс

---

## Следующие шаги

- [ ] Увеличить coverage до 85%+
- [ ] Исправить eager loading подзадач (5 skipped тестов)
- [ ] Добавить E2E тесты
- [ ] Настроить Codecov для отслеживания coverage
