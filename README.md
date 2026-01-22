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
│   └── core/              # Config, database
│
├── frontend/              # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── pages/        # Dashboard, Projects, Tasks, Settings
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
