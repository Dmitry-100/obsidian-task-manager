"""Task-Tag junction table."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table

from .base import Base, utc_now

# Many-to-many junction table for tasks and tags
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    Column("created_at", DateTime, default=utc_now, nullable=False),
)
