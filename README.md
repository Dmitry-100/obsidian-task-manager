# Obsidian Task Manager

Task Manager для интеграции с Obsidian Second Brain.

## Возможности

- Управление проектами
- Создание задач и подзадач
- Теги из Obsidian
- Комментарии к задачам
- Связь с файлами Obsidian
- REST API (FastAPI)

## Модель данных

```
Projects → Tasks (с подзадачами) → Comments
                ↓
              Tags (M:M)
```

## Установка

```bash
# Создать виртуальное окружение
python3 -m venv venv

# Активировать
source venv/bin/activate  # macOS/Linux

# Установить зависимости
pip install -r requirements.txt

# Настроить .env
cp config/.env.example config/.env
```

## Настройка базы данных

```bash
# 1. Установить PostgreSQL (если ещё нет)
brew install postgresql  # macOS

# 2. Запустить PostgreSQL
brew services start postgresql

# 3. Создать базу данных
createdb obsidian_tasks

# 4. Настроить .env файл
cp config/.env.example config/.env
# Отредактировать config/.env с корректными данными БД

# 5. Применить миграции
alembic upgrade head
```

## Запуск

```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Запустить сервер в режиме разработки
uvicorn src.main:app --reload

# Открыть документацию API
open http://localhost:8000/docs  # Swagger UI
open http://localhost:8000/redoc # ReDoc
```

## Примеры использования API

См. файл [api_examples.md](api_examples.md) для примеров запросов.

## Структура

```
src/
├── models/          # SQLAlchemy модели
├── repositories/    # Data Layer
├── services/        # Business Layer
├── api/            # API Layer
└── core/           # Database, config
```

## Технологии

- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- Alembic (миграции)
- Pydantic
