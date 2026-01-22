"""Sync conflict model for tracking conflicts during synchronization."""

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class ConflictResolution(str, enum.Enum):
    """Resolution choice for conflicts."""

    OBSIDIAN = "obsidian"  # Keep Obsidian version
    DATABASE = "database"  # Keep database version
    SKIP = "skip"  # Skip this task (don't sync)
    MANUAL = "manual"  # Manually edited


class SyncConflict(Base, TimestampMixin):
    """Tracks conflicts between Obsidian and database during sync."""

    __tablename__ = "sync_conflicts"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign keys
    sync_log_id: Mapped[int] = mapped_column(ForeignKey("sync_logs.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)

    # Obsidian source location
    obsidian_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    obsidian_line: Mapped[int] = mapped_column(Integer, nullable=False)

    # Data from Obsidian
    obsidian_title: Mapped[str] = mapped_column(String(500), nullable=False)
    obsidian_status: Mapped[str] = mapped_column(String(50), nullable=False)
    obsidian_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    obsidian_priority: Mapped[str] = mapped_column(String(20), nullable=False)
    obsidian_modified: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    obsidian_raw_line: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Data from database
    db_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    db_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    db_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    db_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    db_modified: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Resolution
    resolution: Mapped[ConflictResolution | None] = mapped_column(
        SQLEnum(ConflictResolution, native_enum=False), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "user" | "auto"

    # Relationships
    sync_log: Mapped["SyncLog"] = relationship("SyncLog", back_populates="conflicts")
    task: Mapped["Task | None"] = relationship("Task")

    def __repr__(self) -> str:
        status = "resolved" if self.resolution else "unresolved"
        return f"<SyncConflict(id={self.id}, title='{self.obsidian_title[:30]}...', {status})>"
