# Obsidian Task Manager

![CI](https://github.com/Dmitry-100/obsidian-task-manager/actions/workflows/ci.yml/badge.svg)

Task Manager для интеграции с Obsidian Second Brain.

## Возможности

- Управление проектами (CRUD)
- Создание задач и подзадач
- Теги из Obsidian
- Комментарии к задачам
- Связь с файлами Obsidian
- REST API (FastAPI)
- **Web Dashboard (React)**
- **Obsidian Sync Integration** — двусторонняя синхронизация с Tasks Plugin

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  Dashboard │ Projects │ Tasks │ Settings                │
│  React + TypeScript + TailwindCSS + TanStack Query      │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP/REST
┌─────────────────────▼───────────────────────────────────┐
│                    Backend (FastAPI)                     │
│  API Layer → Service Layer → Repository Layer           │
│  FastAPI + SQLAlchemy 2.0 + Pydantic                    │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                    Database                              │
│  PostgreSQL / SQLite                                     │
└─────────────────────────────────────────────────────────┘
```

## Модель данных

```
Projects → Tasks (с подзадачами) → Comments
                ↓
              Tags (M:M)
```

## Obsidian Sync Integration

Двусторонняя синхронизация задач с Obsidian Tasks Plugin.

### Возможности

- **Импорт** — парсинг задач из markdown файлов Obsidian
- **Экспорт** — запись задач обратно в Obsidian формате
- **Conflict Resolution** — UI для разрешения конфликтов
- **Project Mapping** — автоматическое определение проекта по тегам/папкам/секциям

### Поддерживаемый формат Tasks Plugin

```markdown
- [ ] Задача 🔼 📅 2026-01-25 #tag1 #tag2
- [x] Выполненная задача ⏫ 📅 2026-01-20 ✅ 2026-01-22
```

**Приоритеты:** 🔺 critical, ⏫ high, 🔼 medium, 🔽 low

### Конфигурация

Настройте `config/sync_config.yaml`:

```yaml
vault_path: "/path/to/obsidian/vault"

sync_sources:
  - "00_Inbox/TODO*.md"
  - "01_Projects/*/Tasks.md"

tag_mapping:
  health: "Здоровье"
  work: "Работа"

folder_mapping:
  "01_Projects/MyProject": "My Project"
```

### API Endpoints

```
GET  /sync/status              # Статус последней синхронизации
POST /sync/import              # Импорт из Obsidian
POST /sync/export              # Экспорт в Obsidian
GET  /sync/conflicts           # Список конфликтов
POST /sync/conflicts/{id}/resolve  # Разрешить конфликт
```

## Быстрый старт

### 1. Backend

```bash
# Клонировать репозиторий
git clone https://github.com/Dmitry-100/obsidian-task-manager.git
cd obsidian-task-manager

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Установить зависимости
pip install -r requirements.txt

# Настроить .env
cp config/.env.example config/.env

# Применить миграции
alembic upgrade head

# Запустить сервер
uvicorn src.main:app --reload
# Backend работает на http://localhost:8000
```

### 2. Frontend

```bash
# Перейти в директорию frontend
cd frontend

# Установить зависимости
npm install

# Настроить .env
cp .env.example .env.local

# Запустить dev сервер
npm run dev
# Frontend работает на http://localhost:5173
```

### 3. Открыть приложение

- **Web Dashboard:** http://localhost:5173
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc

## Docker (рекомендуется)

Самый простой способ запустить проект — через Docker Compose.

### Быстрый старт с Docker

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Dmitry-100/obsidian-task-manager.git
cd obsidian-task-manager

# 2. Скопировать и настроить .env
cp config/.env.example config/.env

# 3. Запустить всё одной командой
docker-compose up --build
```

После запуска:
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

### Docker команды

```bash
# Запуск в фоне
docker-compose up -d

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f app

# Пересборка после изменений
docker-compose up --build

# Полная очистка (удаляет данные!)
docker-compose down -v
```

### Что запускается

Docker Compose создаёт:
1. **db** — PostgreSQL 16 (данные сохраняются в volume)
2. **migrations** — применяет миграции Alembic (запускается один раз)
3. **app** — FastAPI приложение

### Переменные окружения для Docker

Настраиваются в `config/.env`:

```bash
# PostgreSQL
POSTGRES_USER=obsidian
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=obsidian_tasks

# Application
API_KEY=your-api-key
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Health Check

Docker проверяет здоровье приложения через `/health`:

```json
{
  "status": "ok",
  "checks": {
    "database": "connected",
    "version": "1.0.0",
    "uptime_seconds": 3600
  }
}
```

## Настройка базы данных

```bash
# PostgreSQL
brew install postgresql  # macOS
brew services start postgresql
createdb obsidian_tasks

# Или SQLite (для разработки)
# Просто установите в .env:
# DATABASE_URL=sqlite:///./obsidian_tasks.db
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

## Структура проекта

```
obsidian-task-manager/
├── src/                    # Backend (Python/FastAPI)
│   ├── api/               # API endpoints
│   ├── services/          # Business logic
│   ├── repositories/      # Data access
│   ├── models/            # SQLAlchemy models
│   ├── core/              # Config, database
│   └── integrations/      # External integrations
│       └── obsidian/      # Obsidian sync (parser, writer, resolver)
│
├── frontend/              # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── pages/        # Dashboard, Projects, Tasks, Settings, Sync
│   │   ├── components/   # UI components (shadcn/ui)
│   │   ├── api/          # API client
│   │   ├── hooks/        # React Query hooks
│   │   └── types/        # TypeScript types
│   └── ...
│
├── tests/                 # Backend tests
├── migrations/            # Alembic migrations
├── docs/                  # Documentation
│   └── adr/              # Architecture Decision Records
└── config/               # Configuration files
```

## Технологии

### Backend
- **FastAPI** — современный async веб-фреймворк
- **SQLAlchemy 2.0** — ORM с async поддержкой
- **PostgreSQL / SQLite** — база данных
- **Alembic** — миграции
- **Pydantic** — валидация данных
- **pytest** — тестирование

### Frontend
- **React 18** — UI библиотека
- **TypeScript** — типизация
- **Vite** — сборщик
- **TailwindCSS** — стили
- **shadcn/ui** — UI компоненты
- **TanStack Query** — серверное состояние
- **React Router** — навигация

## Документация

- **[API Examples](api_examples.md)** — примеры curl запросов
- **[Architecture Decisions](docs/adr/)** — ADR документы
- **[Frontend README](frontend/README.md)** — документация frontend
- **[Contributing](CONTRIBUTING.md)** — как контрибьютить
- **[Sync Config Example](config/sync_config.yaml)** — пример конфигурации синхронизации

## Разработка

```bash
# Backend: запуск с hot reload
uvicorn src.main:app --reload

# Frontend: запуск dev сервера
cd frontend && npm run dev

# Backend: запуск тестов
pytest

# Frontend: сборка production
cd frontend && npm run build
```

## Лицензия

MIT
