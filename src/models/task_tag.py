"""Task-Tag junction table."""

from datetime import datetime
from sqlalchemy import Table, Column, Integer, ForeignKey, DateTime

from .base import Base


# Many-to-many junction table for tasks and tags
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False)
)
