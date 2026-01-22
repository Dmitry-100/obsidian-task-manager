"""HTTP middleware for request logging and tracing."""

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.logging import generate_request_id, get_logger, request_id_var

logger = get_logger("api.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для логирования HTTP запросов.

    Логирует:
    - Метод и путь запроса
    - Статус код ответа
    - Время выполнения (мс)
    - Request ID для трейсинга

    Пример лога (JSON):
    {
        "timestamp": "2026-01-22T12:00:00Z",
        "level": "INFO",
        "logger": "api.requests",
        "message": "Request completed",
        "request_id": "abc-123",
        "extra": {
            "method": "GET",
            "path": "/api/v1/tasks",
            "status": 200,
            "duration_ms": 45,
            "client_ip": "127.0.0.1"
        }
    }
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and log details."""
        # Generate unique request ID for tracing
        request_id = generate_request_id()
        request_id_var.set(request_id)

        # Record start time
        start_time = time.perf_counter()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error and re-raise
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                "Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        # Calculate duration
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Add request ID to response headers (useful for debugging)
        response.headers["X-Request-ID"] = request_id

        # Log request completion
        # Skip health check and docs to reduce noise
        if request.url.path not in ["/health", "/docs", "/redoc", "/openapi.json"]:
            log_level = "INFO" if response.status_code < 400 else "WARNING"
            getattr(logger, log_level.lower())(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                },
            )

        return response
