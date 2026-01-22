# =============================================================================
# Stage 1: Builder
# =============================================================================
# Устанавливаем зависимости в отдельном слое для кэширования
FROM python:3.13-slim AS builder

WORKDIR /build

# Установка системных зависимостей для сборки (psycopg2, asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt для использования кэша слоёв
COPY requirements.txt .

# Устанавливаем Python зависимости в --user директорию
# --no-cache-dir уменьшает размер образа
RUN pip install --user --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Runtime
# =============================================================================
# Минимальный образ для запуска
FROM python:3.13-slim

WORKDIR /app

# Метаданные образа
LABEL maintainer="Dmitry Sotnikov"
LABEL version="1.0.0"
LABEL description="Obsidian Task Manager API"

# Установка runtime зависимостей (только libpq для psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаём non-root пользователя для безопасности
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Копируем установленные пакеты из builder
COPY --from=builder /root/.local /home/appuser/.local

# Копируем код приложения
COPY --chown=appuser:appuser ./src ./src
COPY --chown=appuser:appuser ./alembic.ini .
COPY --chown=appuser:appuser ./migrations ./migrations
COPY --chown=appuser:appuser ./config ./config

# Переключаемся на non-root пользователя
USER appuser

# Добавляем .local/bin в PATH для доступа к установленным пакетам
ENV PATH=/home/appuser/.local/bin:$PATH

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose порт
EXPOSE 8000

# Healthcheck - проверяем /health endpoint каждые 30 секунд
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения через uvicorn
# --host 0.0.0.0 - слушать на всех интерфейсах (необходимо для Docker)
# --port 8000 - порт приложения
# --workers 1 - один воркер (для development; в production увеличить)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
