"""Sync log model for tracking synchronization operations."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class SyncType(str, enum.Enum):
    """Type of sync operation."""

    IMPORT = "import"
    EXPORT = "export"
    FULL = "full"


class SyncStatus(str, enum.Enum):
    """Status of sync operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncLog(Base, TimestampMixin):
    """Logs sync operations between Obsidian and Task Manager."""

    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    sync_type: Mapped[SyncType] = mapped_column(
        SQLEnum(SyncType, native_enum=False), nullable=False
    )
    status: Mapped[SyncStatus] = mapped_column(
        SQLEnum(SyncStatus, native_enum=False), default=SyncStatus.PENDING, nullable=False
    )

    # Source information
    source_file: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Statistics
    tasks_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conflicts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    conflicts: Mapped[list["SyncConflict"]] = relationship(
        "SyncConflict", back_populates="sync_log", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SyncLog(id={self.id}, type={self.sync_type.value}, status={self.status.value})>"
