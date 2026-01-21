"""Task model."""

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TaskStatus(str, enum.Enum):
    """Task status enum."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    """Task priority enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base, TimestampMixin):
    """Task model with support for subtasks."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Foreign Keys
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    parent_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True
    )  # Self-reference for subtasks

    # Task properties
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus, native_enum=False), default=TaskStatus.TODO, nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority, native_enum=False), default=TaskPriority.MEDIUM, nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    obsidian_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    estimated_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")

    # Self-referencing relationships for subtasks
    parent_task: Mapped[Optional["Task"]] = relationship(
        "Task", remote_side=[id], back_populates="subtasks"
    )
    subtasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="parent_task", cascade="all, delete-orphan"
    )

    # Comments relationship
    comments: Mapped[list["TaskComment"]] = relationship(
        "TaskComment", back_populates="task", cascade="all, delete-orphan"
    )

    # Tags relationship (many-to-many)
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary="task_tags", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status={self.status.value})>"
