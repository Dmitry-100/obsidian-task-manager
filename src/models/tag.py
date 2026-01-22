"""Tag model."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utc_now


class Tag(Base):
    """Tag model for categorizing tasks (integrates with Obsidian tags)."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    tasks: Mapped[list["Task"]] = relationship("Task", secondary="task_tags", back_populates="tags")

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}')>"
