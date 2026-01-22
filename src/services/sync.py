"""Sync service for Obsidian integration."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from ..integrations.obsidian import FileScanner, ObsidianParser, ParsedTask, ProjectResolver
from ..integrations.obsidian.project_resolver import SyncConfig, create_default_config
from ..models import Task, TaskPriority, TaskStatus
from ..models.sync_conflict import ConflictResolution, SyncConflict
from ..models.sync_log import SyncLog, SyncType
from ..repositories import ProjectRepository, TagRepository, TaskRepository
from ..repositories.sync import SyncConflictRepository, SyncLogRepository


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    sync_log_id: int
    tasks_created: int = 0
    tasks_updated: int = 0
    tasks_skipped: int = 0
    conflicts_count: int = 0
    error_message: str | None = None


@dataclass
class SyncStatusInfo:
    """Current sync status information."""

    is_syncing: bool
    last_sync: SyncLog | None
    unresolved_conflicts: int
    total_syncs: int


class SyncService:
    """Service for syncing tasks between Obsidian and database."""

    def __init__(self, db: AsyncSession, config: SyncConfig | None = None):
        """Initialize sync service.

        Args:
            db: Async database session
            config: Sync configuration (uses default if not provided)
        """
        self.db = db
        self.config = config or create_default_config()

        # Repositories
        self.sync_log_repo = SyncLogRepository(db)
        self.conflict_repo = SyncConflictRepository(db)
        self.task_repo = TaskRepository(db)
        self.project_repo = ProjectRepository(db)
        self.tag_repo = TagRepository(db)

        # Obsidian integration
        self.parser = ObsidianParser()
        self.resolver = ProjectResolver(self.config)

    async def get_status(self) -> SyncStatusInfo:
        """Get current sync status.

        Returns:
            SyncStatusInfo with current state
        """
        in_progress = await self.sync_log_repo.get_in_progress()
        last_sync = await self.sync_log_repo.get_latest()
        unresolved = await self.conflict_repo.count_unresolved()
        total = await self.sync_log_repo.count()

        return SyncStatusInfo(
            is_syncing=in_progress is not None,
            last_sync=last_sync,
            unresolved_conflicts=unresolved,
            total_syncs=total,
        )

    async def import_from_obsidian(self, source_files: list[str] | None = None) -> SyncResult:
        """Import tasks from Obsidian files.

        Args:
            source_files: List of file paths to import (uses config sources if not provided)

        Returns:
            SyncResult with operation details
        """
        # Check if sync is already in progress
        in_progress = await self.sync_log_repo.get_in_progress()
        if in_progress:
            return SyncResult(
                success=False,
                sync_log_id=in_progress.id,
                error_message="Sync already in progress",
            )

        # Start sync log
        sync_log = await self.sync_log_repo.start_sync(
            sync_type=SyncType.IMPORT,
            source_file=",".join(source_files) if source_files else None,
        )
        await self.db.flush()

        try:
            # Get files to scan
            if source_files:
                files_to_scan = source_files
            else:
                files_to_scan = await self._get_source_files()

            tasks_created = 0
            tasks_updated = 0
            tasks_skipped = 0
            conflicts = []

            # Process each file
            for file_path in files_to_scan:
                path = Path(file_path)
                if not path.exists():
                    continue

                # Parse tasks from file
                parsed_tasks = self.parser.parse_file(file_path)

                # Process each task
                for parsed in parsed_tasks:
                    result = await self._process_parsed_task(parsed, sync_log.id)
                    if result == "created":
                        tasks_created += 1
                    elif result == "updated":
                        tasks_updated += 1
                    elif result == "skipped":
                        tasks_skipped += 1
                    elif result == "conflict":
                        conflicts.append(parsed)

            # Complete sync
            await self.sync_log_repo.complete_sync(
                sync_log.id,
                tasks_created=tasks_created,
                tasks_updated=tasks_updated,
                tasks_skipped=tasks_skipped,
                conflicts_count=len(conflicts),
            )
            await self.db.flush()

            return SyncResult(
                success=True,
                sync_log_id=sync_log.id,
                tasks_created=tasks_created,
                tasks_updated=tasks_updated,
                tasks_skipped=tasks_skipped,
                conflicts_count=len(conflicts),
            )

        except Exception as e:
            # Mark sync as failed
            await self.sync_log_repo.fail_sync(sync_log.id, str(e))
            await self.db.flush()

            return SyncResult(
                success=False,
                sync_log_id=sync_log.id,
                error_message=str(e),
            )

    async def export_to_obsidian(
        self, project_id: int | None = None, output_path: str | None = None
    ) -> SyncResult:
        """Export tasks to Obsidian markdown file.

        Args:
            project_id: Project to export (exports all if not specified)
            output_path: Output file path (uses default if not specified)

        Returns:
            SyncResult with operation details
        """
        # Check if sync is already in progress
        in_progress = await self.sync_log_repo.get_in_progress()
        if in_progress:
            return SyncResult(
                success=False,
                sync_log_id=in_progress.id,
                error_message="Sync already in progress",
            )

        # Start sync log
        sync_log = await self.sync_log_repo.start_sync(
            sync_type=SyncType.EXPORT,
            source_file=output_path,
        )
        await self.db.flush()

        try:
            # Get tasks to export
            if project_id:
                tasks = await self.task_repo.get_by_project(project_id, include_completed=True)
            else:
                tasks = await self.task_repo.get_all(limit=1000)

            # Generate markdown
            lines = ["# Exported Tasks", "", f"*Exported at: {datetime.now().isoformat()}*", ""]

            current_project = None
            for task in tasks:
                # Add project header if changed
                if task.project_id != current_project:
                    project = await self.project_repo.get_by_id(task.project_id)
                    if project:
                        lines.append(f"## {project.name}")
                        lines.append("")
                    current_project = task.project_id

                # Convert task to markdown
                parsed = self._task_to_parsed(task)
                md_line = self.parser.task_to_markdown(parsed)
                lines.append(md_line)

            # Determine output path
            if not output_path:
                vault_path = Path(self.config.vault_path)
                output_path = str(vault_path / "00_Inbox" / "Exported_Tasks.md")

            # Write file
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("\n".join(lines), encoding="utf-8")

            # Complete sync
            await self.sync_log_repo.complete_sync(
                sync_log.id,
                tasks_created=0,
                tasks_updated=len(tasks),
                tasks_skipped=0,
                conflicts_count=0,
            )
            await self.db.flush()

            return SyncResult(
                success=True,
                sync_log_id=sync_log.id,
                tasks_updated=len(tasks),
            )

        except Exception as e:
            await self.sync_log_repo.fail_sync(sync_log.id, str(e))
            await self.db.flush()

            return SyncResult(
                success=False,
                sync_log_id=sync_log.id,
                error_message=str(e),
            )

    async def get_conflicts(self, sync_log_id: int | None = None) -> list[SyncConflict]:
        """Get sync conflicts.

        Args:
            sync_log_id: Get conflicts for specific sync (all unresolved if not specified)

        Returns:
            List of conflicts
        """
        if sync_log_id:
            return await self.conflict_repo.get_by_sync_log(sync_log_id)
        return await self.conflict_repo.get_unresolved()

    async def resolve_conflict(
        self,
        conflict_id: int,
        resolution: ConflictResolution,
    ) -> SyncConflict:
        """Resolve a sync conflict.

        Args:
            conflict_id: ID of conflict to resolve
            resolution: Resolution choice

        Returns:
            Resolved conflict

        Raises:
            ValueError: If conflict not found
        """
        conflict = await self.conflict_repo.get_by_id(conflict_id)
        if not conflict:
            raise ValueError(f"Conflict with id {conflict_id} not found")

        if conflict.resolution:
            raise ValueError(f"Conflict {conflict_id} is already resolved")

        # Apply resolution
        if resolution == ConflictResolution.OBSIDIAN:
            await self._apply_obsidian_version(conflict)
        elif resolution == ConflictResolution.DATABASE:
            await self._apply_database_version(conflict)
        # SKIP does nothing

        # Mark as resolved
        resolved = await self.conflict_repo.resolve(conflict_id, resolution, "user")
        await self.db.flush()

        return resolved

    async def resolve_all_conflicts(
        self,
        sync_log_id: int,
        resolution: ConflictResolution,
    ) -> int:
        """Resolve all conflicts for a sync with same resolution.

        Args:
            sync_log_id: Sync log ID
            resolution: Resolution to apply

        Returns:
            Number of conflicts resolved
        """
        conflicts = await self.conflict_repo.get_unresolved_by_sync_log(sync_log_id)

        for conflict in conflicts:
            if resolution == ConflictResolution.OBSIDIAN:
                await self._apply_obsidian_version(conflict)
            elif resolution == ConflictResolution.DATABASE:
                await self._apply_database_version(conflict)

        count = await self.conflict_repo.resolve_all_for_sync(sync_log_id, resolution, "auto")
        await self.db.flush()

        return count

    async def get_sync_history(self, limit: int = 10) -> list[SyncLog]:
        """Get recent sync history.

        Args:
            limit: Maximum number of records

        Returns:
            List of sync logs
        """
        return await self.sync_log_repo.get_recent(limit)

    # Private helper methods

    async def _get_source_files(self) -> list[str]:
        """Get list of files to scan from config."""
        if not self.config.vault_path:
            return []

        scanner = FileScanner(self.config.vault_path)
        scanned = scanner.scan(self.config.sync_sources)
        return [f.path for f in scanned]

    async def _process_parsed_task(self, parsed: ParsedTask, sync_log_id: int) -> str:
        """Process a parsed task from Obsidian.

        Returns:
            "created", "updated", "skipped", or "conflict"
        """
        # Resolve project
        project_name = self.resolver.resolve(parsed)
        project = await self._get_or_create_project(project_name)

        # Check if task already exists
        existing = await self._find_existing_task(parsed, project.id)

        if existing:
            # Check for conflicts
            if self._has_conflict(parsed, existing):
                await self._create_conflict(parsed, existing, sync_log_id)
                return "conflict"

            # Update if Obsidian is newer
            if (
                parsed.file_modified
                and existing.updated_at
                and parsed.file_modified > existing.updated_at
            ):
                await self._update_task_from_parsed(existing, parsed)
                return "updated"

            return "skipped"

        # Create new task
        await self._create_task_from_parsed(parsed, project.id)
        return "created"

    async def _get_or_create_project(self, name: str):
        """Get or create project by name."""
        # Search for existing project
        projects = await self.project_repo.search_by_name(name)
        if projects:
            return projects[0]

        # Create new project
        from ..models import Project

        project = Project(name=name)
        project = await self.project_repo.create(project)
        await self.db.flush()
        return project

    async def _find_existing_task(self, parsed: ParsedTask, project_id: int) -> Task | None:
        """Find existing task that matches parsed task."""
        # Search by title in the same project
        tasks = await self.task_repo.search_by_title(parsed.title)
        for task in tasks:
            if task.project_id == project_id:
                return task

        # Search by obsidian_path if available
        if parsed.source_file:
            all_tasks = await self.task_repo.get_by_project(project_id, include_completed=True)
            for task in all_tasks:
                if (
                    task.obsidian_path == parsed.source_file
                    and task.title.lower() == parsed.title.lower()
                ):
                    return task

        return None

    def _has_conflict(self, parsed: ParsedTask, existing: Task) -> bool:
        """Check if there's a conflict between parsed and existing task."""
        # Conflict if both have been modified and differ
        if not parsed.file_modified or not existing.updated_at:
            return False

        # Compare key fields
        status_differs = self._map_status(parsed.status) != existing.status
        due_differs = parsed.due_date != existing.due_date
        priority_differs = self._map_priority(parsed.priority) != existing.priority

        return status_differs or due_differs or priority_differs

    async def _create_conflict(
        self, parsed: ParsedTask, existing: Task, sync_log_id: int
    ) -> SyncConflict:
        """Create a conflict record."""
        conflict = SyncConflict(
            sync_log_id=sync_log_id,
            task_id=existing.id,
            obsidian_path=parsed.source_file,
            obsidian_line=parsed.source_line,
            obsidian_title=parsed.title,
            obsidian_status=parsed.status,
            obsidian_due_date=parsed.due_date,
            obsidian_priority=parsed.priority,
            obsidian_modified=parsed.file_modified or datetime.now(UTC),
            obsidian_raw_line=parsed.raw_line,
            db_title=existing.title,
            db_status=existing.status.value,
            db_due_date=existing.due_date,
            db_priority=existing.priority.value,
            db_modified=existing.updated_at,
        )
        conflict = await self.conflict_repo.create(conflict)
        await self.db.flush()
        return conflict

    async def _create_task_from_parsed(self, parsed: ParsedTask, project_id: int) -> Task:
        """Create a new task from parsed data."""
        task = Task(
            title=parsed.title,
            project_id=project_id,
            status=self._map_status(parsed.status),
            priority=self._map_priority(parsed.priority),
            due_date=parsed.due_date,
            obsidian_path=parsed.source_file,
            completed_at=datetime.combine(parsed.completed_at, datetime.min.time())
            if parsed.completed_at
            else None,
        )
        task = await self.task_repo.create(task)

        # Add tags
        if parsed.tags:
            tags = await self.tag_repo.bulk_get_or_create(parsed.tags)
            for tag in tags:
                await self.task_repo.add_tag(task.id, tag)

        await self.db.flush()
        return task

    async def _update_task_from_parsed(self, task: Task, parsed: ParsedTask) -> Task:
        """Update existing task from parsed data."""
        updates = {
            "title": parsed.title,
            "status": self._map_status(parsed.status),
            "priority": self._map_priority(parsed.priority),
            "due_date": parsed.due_date,
        }

        if parsed.completed_at:
            updates["completed_at"] = datetime.combine(parsed.completed_at, datetime.min.time())

        task = await self.task_repo.update(task.id, **updates)
        await self.db.flush()
        return task

    async def _apply_obsidian_version(self, conflict: SyncConflict) -> None:
        """Apply Obsidian version to database."""
        if not conflict.task_id:
            return

        await self.task_repo.update(
            conflict.task_id,
            title=conflict.obsidian_title,
            status=self._map_status(conflict.obsidian_status),
            priority=self._map_priority(conflict.obsidian_priority),
            due_date=conflict.obsidian_due_date,
        )
        await self.db.flush()

    async def _apply_database_version(self, conflict: SyncConflict) -> None:
        """Apply database version to Obsidian file."""
        # Read the file
        if not conflict.obsidian_path:
            return

        path = Path(conflict.obsidian_path)
        if not path.exists():
            return

        content = path.read_text(encoding="utf-8")

        # Find and update the task line
        task = await self.task_repo.get_by_id(conflict.task_id) if conflict.task_id else None
        if not task:
            return

        # Convert task to parsed format
        parsed = self._task_to_parsed(task)

        # Update line in content
        new_content = self.parser.update_task_in_content(content, conflict.obsidian_line, parsed)

        # Write back
        path.write_text(new_content, encoding="utf-8")

    def _task_to_parsed(self, task: Task) -> ParsedTask:
        """Convert Task to ParsedTask for markdown generation."""
        return ParsedTask(
            title=task.title,
            status="done" if task.status == TaskStatus.DONE else "todo",
            priority=task.priority.value,
            due_date=task.due_date,
            completed_at=task.completed_at.date() if task.completed_at else None,
            tags=[],  # Tags would need to be loaded
        )

    def _map_status(self, status: str) -> TaskStatus:
        """Map Obsidian status to TaskStatus enum."""
        if status.lower() == "done":
            return TaskStatus.DONE
        return TaskStatus.TODO

    def _map_priority(self, priority: str) -> TaskPriority:
        """Map Obsidian priority to TaskPriority enum."""
        priority_map = {
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
        }
        return priority_map.get(priority.lower(), TaskPriority.MEDIUM)
