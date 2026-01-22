"""API layer - FastAPI endpoints."""

from .projects import router as projects_router
from .sync import router as sync_router
from .tags import router as tags_router
from .tasks import router as tasks_router

__all__ = [
    "projects_router",
    "tasks_router",
    "tags_router",
    "sync_router",
]
