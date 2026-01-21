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

## Авторизация

API защищён с помощью API Key. Передавайте ключ в заголовке `X-API-Key`:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/projects
```

Ключ настраивается в `config/.env`:

```bash
API_KEY=your-secret-key-here
```

По умолчанию (для разработки): `dev-api-key-change-in-production`

**Публичные endpoints (без авторизации):**
- `GET /` - информация об API
- `GET /health` - health check

## Примеры использования API

- **curl примеры:** [api_examples.md](api_examples.md)
- **Postman коллекция:** [postman_collection.json](postman_collection.json) - импортируйте в Postman

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
