"""Sync repository for sync logs and conflicts."""

from datetime import datetime

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.sync_conflict import ConflictResolution, SyncConflict
from ..models.sync_log import SyncLog, SyncStatus, SyncType
from .base import BaseRepository


class SyncLogRepository(BaseRepository[SyncLog]):
    """Repository for sync log operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(SyncLog, db)

    async def get_latest(self) -> SyncLog | None:
        """Get the most recent sync log."""
        result = await self.db.execute(
            select(SyncLog)
            .options(selectinload(SyncLog.conflicts))
            .order_by(desc(SyncLog.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_by_type(self, sync_type: SyncType) -> SyncLog | None:
        """Get the most recent sync log of a specific type."""
        result = await self.db.execute(
            select(SyncLog)
            .where(SyncLog.sync_type == sync_type)
            .order_by(desc(SyncLog.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_status(self, status: SyncStatus) -> list[SyncLog]:
        """Get all sync logs with a specific status."""
        result = await self.db.execute(
            select(SyncLog).where(SyncLog.status == status).order_by(desc(SyncLog.created_at))
        )
        return list(result.scalars().all())

    async def get_in_progress(self) -> SyncLog | None:
        """Get currently running sync operation (if any)."""
        result = await self.db.execute(
            select(SyncLog).where(SyncLog.status == SyncStatus.IN_PROGRESS)
        )
        return result.scalar_one_or_none()

    async def get_recent(self, limit: int = 10) -> list[SyncLog]:
        """Get recent sync logs with conflicts."""
        result = await self.db.execute(
            select(SyncLog)
            .options(selectinload(SyncLog.conflicts))
            .order_by(desc(SyncLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def start_sync(self, sync_type: SyncType, source_file: str | None = None) -> SyncLog:
        """Create a new sync log and mark it as in progress."""
        sync_log = SyncLog(
            sync_type=sync_type,
            status=SyncStatus.IN_PROGRESS,
            source_file=source_file,
            started_at=datetime.utcnow(),
        )
        return await self.create(sync_log)

    async def complete_sync(
        self,
        sync_log_id: int,
        tasks_created: int = 0,
        tasks_updated: int = 0,
        tasks_skipped: int = 0,
        conflicts_count: int = 0,
    ) -> SyncLog | None:
        """Mark sync as completed with statistics."""
        return await self.update(
            sync_log_id,
            status=SyncStatus.COMPLETED,
            tasks_created=tasks_created,
            tasks_updated=tasks_updated,
            tasks_skipped=tasks_skipped,
            conflicts_count=conflicts_count,
            completed_at=datetime.utcnow(),
        )

    async def fail_sync(self, sync_log_id: int, error_message: str) -> SyncLog | None:
        """Mark sync as failed with error message."""
        return await self.update(
            sync_log_id,
            status=SyncStatus.FAILED,
            error_message=error_message,
            completed_at=datetime.utcnow(),
        )


class SyncConflictRepository(BaseRepository[SyncConflict]):
    """Repository for sync conflict operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(SyncConflict, db)

    async def get_by_sync_log(self, sync_log_id: int) -> list[SyncConflict]:
        """Get all conflicts for a specific sync log."""
        result = await self.db.execute(
            select(SyncConflict)
            .where(SyncConflict.sync_log_id == sync_log_id)
            .order_by(SyncConflict.id)
        )
        return list(result.scalars().all())

    async def get_unresolved(self) -> list[SyncConflict]:
        """Get all unresolved conflicts."""
        result = await self.db.execute(
            select(SyncConflict)
            .where(SyncConflict.resolution.is_(None))
            .order_by(desc(SyncConflict.created_at))
        )
        return list(result.scalars().all())

    async def get_unresolved_by_sync_log(self, sync_log_id: int) -> list[SyncConflict]:
        """Get unresolved conflicts for a specific sync log."""
        result = await self.db.execute(
            select(SyncConflict).where(
                and_(
                    SyncConflict.sync_log_id == sync_log_id,
                    SyncConflict.resolution.is_(None),
                )
            )
        )
        return list(result.scalars().all())

    async def resolve(
        self,
        conflict_id: int,
        resolution: ConflictResolution,
        resolved_by: str = "user",
    ) -> SyncConflict | None:
        """Resolve a conflict with the specified resolution."""
        return await self.update(
            conflict_id,
            resolution=resolution,
            resolved_at=datetime.utcnow(),
            resolved_by=resolved_by,
        )

    async def resolve_all_for_sync(
        self,
        sync_log_id: int,
        resolution: ConflictResolution,
        resolved_by: str = "auto",
    ) -> int:
        """Resolve all conflicts for a sync log with the same resolution."""
        conflicts = await self.get_unresolved_by_sync_log(sync_log_id)
        count = 0
        for conflict in conflicts:
            await self.resolve(conflict.id, resolution, resolved_by)
            count += 1
        return count

    async def count_unresolved(self) -> int:
        """Count all unresolved conflicts."""
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count()).select_from(SyncConflict).where(SyncConflict.resolution.is_(None))
        )
        return result.scalar_one()

    async def find_by_task(self, task_id: int) -> list[SyncConflict]:
        """Find all conflicts related to a specific task."""
        result = await self.db.execute(
            select(SyncConflict)
            .where(SyncConflict.task_id == task_id)
            .order_by(desc(SyncConflict.created_at))
        )
        return list(result.scalars().all())

    async def find_by_obsidian_path(self, obsidian_path: str) -> list[SyncConflict]:
        """Find all conflicts from a specific Obsidian file."""
        result = await self.db.execute(
            select(SyncConflict)
            .where(SyncConflict.obsidian_path == obsidian_path)
            .order_by(desc(SyncConflict.created_at))
        )
        return list(result.scalars().all())
