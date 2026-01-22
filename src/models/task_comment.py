"""Task comment model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utc_now


class TaskComment(Base):
    """Comment model for tasks (supports Markdown)."""

    __tablename__ = "task_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="comments")

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<TaskComment(id={self.id}, task_id={self.task_id}, content='{preview}')>"
