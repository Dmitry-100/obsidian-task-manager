"""
Обработчики ошибок (Exception Handlers) для API.

Зачем нужны exception handlers?
1. Единый формат ошибок для всего API
2. Перехват ошибок Pydantic (422) и преобразование в наш формат
3. Логирование ошибок
4. Скрытие внутренних деталей от клиента (безопасность)

Как это работает:
1. Где-то в коде возникает исключение (Exception)
2. FastAPI ищет подходящий handler для этого типа исключения
3. Handler преобразует исключение в HTTP ответ
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

from .schemas import ErrorResponse, ErrorBody, ErrorDetail

# Настраиваем логгер для отслеживания ошибок
logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM EXCEPTIONS (Наши собственные исключения)
# =============================================================================

class APIError(Exception):
    """
    Базовый класс для всех API ошибок.

    Использование:
        raise APIError(
            code="NOT_FOUND",
            message="Проект не найден",
            status_code=404
        )
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: list[dict] | None = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(APIError):
    """
    Ресурс не найден (404).

    Использование:
        raise NotFoundError("Project", 123)
        # Сообщение: "Project с id=123 не найден"
    """

    def __init__(self, resource: str, resource_id: int | str):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} с id={resource_id} не найден",
            status_code=status.HTTP_404_NOT_FOUND
        )


class AlreadyExistsError(APIError):
    """
    Ресурс уже существует (400).

    Использование:
        raise AlreadyExistsError("Project", "name", "Вайб-Кодинг")
        # Сообщение: "Project с name='Вайб-Кодинг' уже существует"
    """

    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            code="ALREADY_EXISTS",
            message=f"{resource} с {field}='{value}' уже существует",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=[{"field": field, "message": f"Значение '{value}' уже используется"}]
        )


class ValidationError_(APIError):
    """
    Ошибка валидации бизнес-логики (400).

    Использование:
        raise ValidationError_("Дата окончания не может быть раньше даты начала")
    """

    def __init__(self, message: str, details: list[dict] | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


# =============================================================================
# EXCEPTION HANDLERS (Обработчики исключений)
# =============================================================================

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Обработчик для наших кастомных ошибок (APIError).

    Преобразует APIError в единый формат ErrorResponse.
    """
    # Логируем ошибку
    logger.warning(f"API Error: {exc.code} - {exc.message}")

    # Формируем детали ошибки (если есть)
    details = None
    if exc.details:
        details = [ErrorDetail(field=d["field"], message=d["message"]) for d in exc.details]

    # Создаём ответ в едином формате
    error_response = ErrorResponse(
        error=ErrorBody(
            code=exc.code,
            message=exc.message,
            details=details
        )
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Обработчик для ошибок валидации Pydantic (422).

    Pydantic возвращает ошибки в своём формате:
    {
        "detail": [
            {"type": "string_too_short", "loc": ["body", "name"], "msg": "..."}
        ]
    }

    Мы преобразуем это в наш формат:
    {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Ошибка валидации",
            "details": [{"field": "name", "message": "..."}]
        }
    }
    """
    # Логируем ошибку
    logger.warning(f"Validation Error: {exc.errors()}")

    # Преобразуем ошибки Pydantic в наш формат
    details = []
    for error in exc.errors():
        # loc — это путь к полю, например ["body", "name"] или ["query", "limit"]
        # Берём последний элемент — это имя поля
        field_path = error.get("loc", [])
        field_name = field_path[-1] if field_path else "unknown"

        # Если поле в body, убираем "body" из пути
        if len(field_path) > 1 and field_path[0] == "body":
            field_name = ".".join(str(p) for p in field_path[1:])

        details.append(ErrorDetail(
            field=str(field_name),
            message=error.get("msg", "Ошибка валидации")
        ))

    error_response = ErrorResponse(
        error=ErrorBody(
            code="VALIDATION_ERROR",
            message="Ошибка валидации входных данных",
            details=details
        )
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обработчик для всех остальных ошибок (500).

    ВАЖНО: Не показываем детали внутренних ошибок клиенту!
    Это важно для безопасности — клиент не должен видеть stack trace.
    """
    # Логируем полную ошибку для отладки
    logger.error(f"Internal Error: {type(exc).__name__}: {exc}", exc_info=True)

    error_response = ErrorResponse(
        error=ErrorBody(
            code="INTERNAL_ERROR",
            message="Внутренняя ошибка сервера",
            details=None  # НЕ показываем детали!
        )
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


# =============================================================================
# РЕГИСТРАЦИЯ HANDLERS
# =============================================================================

def register_error_handlers(app):
    """
    Регистрирует все error handlers в приложении FastAPI.

    Вызывается из main.py:
        from src.api.errors import register_error_handlers
        register_error_handlers(app)
    """
    # Наши кастомные ошибки
    app.add_exception_handler(APIError, api_error_handler)

    # Ошибки валидации Pydantic
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # Все остальные ошибки (на всякий случай)
    # ВАЖНО: Раскомментируйте только если хотите скрыть все stack traces
    # app.add_exception_handler(Exception, generic_error_handler)

    logger.info("Error handlers registered")
