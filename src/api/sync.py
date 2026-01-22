"""
API endpoints for Obsidian sync operations.

REST API structure:
- GET    /sync/status             - Get sync status
- POST   /sync/import             - Import from Obsidian
- POST   /sync/export             - Export to Obsidian
- GET    /sync/conflicts          - Get unresolved conflicts
- GET    /sync/conflicts/{id}     - Get specific conflict
- POST   /sync/conflicts/{id}/resolve  - Resolve a conflict
- POST   /sync/conflicts/resolve-all   - Resolve all conflicts
- GET    /sync/history            - Get sync history
- GET    /sync/config             - Get sync configuration
- PUT    /sync/config             - Update sync configuration
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.sync_conflict import ConflictResolution
from ..services import SyncService
from .dependencies import get_sync_service
from .schemas import (
    ConflictResolutionRequest,
    ErrorResponse,
    ResolveAllConflictsRequest,
    SyncConfigResponse,
    SyncConfigUpdate,
    SyncConflictResponse,
    SyncExportRequest,
    SyncImportRequest,
    SyncLogResponse,
    SyncResultResponse,
    SyncStatusResponse,
)

router = APIRouter(prefix="/sync", tags=["sync"])


# ============================================================================
# SYNC STATUS
# ============================================================================


@router.get(
    "/status",
    response_model=SyncStatusResponse,
    summary="Get sync status",
    description="Get current synchronization status including last sync and unresolved conflicts.",
)
async def get_sync_status(
    service: SyncService = Depends(get_sync_service),
) -> SyncStatusResponse:
    """Get current sync status."""
    status_info = await service.get_status()

    last_sync_response = None
    if status_info.last_sync:
        last_sync_response = SyncLogResponse.model_validate(status_info.last_sync)

    return SyncStatusResponse(
        is_syncing=status_info.is_syncing,
        last_sync=last_sync_response,
        unresolved_conflicts=status_info.unresolved_conflicts,
        total_syncs=status_info.total_syncs,
    )


# ============================================================================
# IMPORT FROM OBSIDIAN
# ============================================================================


@router.post(
    "/import",
    response_model=SyncResultResponse,
    summary="Import from Obsidian",
    description="""
    Import tasks from Obsidian vault files.

    If no source_files specified, uses patterns from sync configuration.
    """,
    responses={
        200: {"description": "Import completed"},
        400: {"model": ErrorResponse, "description": "Import failed"},
    },
)
async def import_from_obsidian(
    data: SyncImportRequest = None,
    service: SyncService = Depends(get_sync_service),
) -> SyncResultResponse:
    """Import tasks from Obsidian files."""
    source_files = data.source_files if data else None

    result = await service.import_from_obsidian(source_files)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message or "Import failed",
        )

    return SyncResultResponse(
        success=result.success,
        sync_log_id=result.sync_log_id,
        tasks_created=result.tasks_created,
        tasks_updated=result.tasks_updated,
        tasks_skipped=result.tasks_skipped,
        conflicts_count=result.conflicts_count,
        error_message=result.error_message,
    )


# ============================================================================
# EXPORT TO OBSIDIAN
# ============================================================================


@router.post(
    "/export",
    response_model=SyncResultResponse,
    summary="Export to Obsidian",
    description="""
    Export tasks to Obsidian markdown file.

    If project_id specified, exports only that project.
    If output_path not specified, exports to default location.
    """,
    responses={
        200: {"description": "Export completed"},
        400: {"model": ErrorResponse, "description": "Export failed"},
    },
)
async def export_to_obsidian(
    data: SyncExportRequest = None,
    service: SyncService = Depends(get_sync_service),
) -> SyncResultResponse:
    """Export tasks to Obsidian file."""
    project_id = data.project_id if data else None
    output_path = data.output_path if data else None

    result = await service.export_to_obsidian(project_id, output_path)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message or "Export failed",
        )

    return SyncResultResponse(
        success=result.success,
        sync_log_id=result.sync_log_id,
        tasks_created=result.tasks_created,
        tasks_updated=result.tasks_updated,
        tasks_skipped=result.tasks_skipped,
        conflicts_count=result.conflicts_count,
        error_message=result.error_message,
    )


# ============================================================================
# CONFLICTS
# ============================================================================


@router.get(
    "/conflicts",
    response_model=list[SyncConflictResponse],
    summary="Get sync conflicts",
    description="Get list of unresolved sync conflicts.",
)
async def get_conflicts(
    sync_log_id: int | None = Query(None, description="Filter by sync log ID"),
    service: SyncService = Depends(get_sync_service),
) -> list[SyncConflictResponse]:
    """Get unresolved conflicts."""
    conflicts = await service.get_conflicts(sync_log_id)
    return [SyncConflictResponse.model_validate(c) for c in conflicts]


@router.get(
    "/conflicts/{conflict_id}",
    response_model=SyncConflictResponse,
    summary="Get specific conflict",
    responses={
        200: {"description": "Conflict found"},
        404: {"model": ErrorResponse, "description": "Conflict not found"},
    },
)
async def get_conflict(
    conflict_id: int,
    service: SyncService = Depends(get_sync_service),
) -> SyncConflictResponse:
    """Get a specific conflict by ID."""
    conflicts = await service.get_conflicts()
    for conflict in conflicts:
        if conflict.id == conflict_id:
            return SyncConflictResponse.model_validate(conflict)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Conflict with id {conflict_id} not found",
    )


@router.post(
    "/conflicts/{conflict_id}/resolve",
    response_model=SyncConflictResponse,
    summary="Resolve a conflict",
    description="""
    Resolve a sync conflict with specified resolution.

    Resolution options:
    - **obsidian**: Keep Obsidian version, update database
    - **database**: Keep database version, update Obsidian file
    - **skip**: Skip this task (don't sync)
    - **manual**: Mark as manually handled
    """,
    responses={
        200: {"description": "Conflict resolved"},
        400: {"model": ErrorResponse, "description": "Resolution failed"},
        404: {"model": ErrorResponse, "description": "Conflict not found"},
    },
)
async def resolve_conflict(
    conflict_id: int,
    data: ConflictResolutionRequest,
    service: SyncService = Depends(get_sync_service),
) -> SyncConflictResponse:
    """Resolve a sync conflict."""
    try:
        resolution = ConflictResolution(data.resolution.lower())
        conflict = await service.resolve_conflict(conflict_id, resolution)
        return SyncConflictResponse.model_validate(conflict)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/conflicts/resolve-all",
    summary="Resolve all conflicts",
    description="Resolve all unresolved conflicts with the same resolution.",
    responses={
        200: {"description": "Conflicts resolved"},
        400: {"model": ErrorResponse, "description": "Resolution failed"},
    },
)
async def resolve_all_conflicts(
    sync_log_id: int = Query(..., description="Sync log ID"),
    data: ResolveAllConflictsRequest = ...,
    service: SyncService = Depends(get_sync_service),
) -> dict:
    """Resolve all conflicts for a sync log."""
    try:
        resolution = ConflictResolution(data.resolution.lower())
        count = await service.resolve_all_conflicts(sync_log_id, resolution)
        return {"resolved_count": count, "resolution": data.resolution}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# SYNC HISTORY
# ============================================================================


@router.get(
    "/history",
    response_model=list[SyncLogResponse],
    summary="Get sync history",
    description="Get recent sync operations history.",
)
async def get_sync_history(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records"),
    service: SyncService = Depends(get_sync_service),
) -> list[SyncLogResponse]:
    """Get sync history."""
    history = await service.get_sync_history(limit)
    return [SyncLogResponse.model_validate(log) for log in history]


# ============================================================================
# SYNC CONFIGURATION
# ============================================================================


@router.get(
    "/config",
    response_model=SyncConfigResponse,
    summary="Get sync configuration",
    description="Get current sync configuration including vault path and mappings.",
)
async def get_sync_config(
    service: SyncService = Depends(get_sync_service),
) -> SyncConfigResponse:
    """Get sync configuration."""
    config = service.config
    return SyncConfigResponse(
        vault_path=config.vault_path,
        sync_sources=config.sync_sources,
        folder_mapping=config.folder_mapping,
        tag_mapping=config.tag_mapping,
        section_mapping=config.section_mapping,
        default_project=config.default_project,
        default_conflict_resolution=config.default_conflict_resolution,
    )


@router.put(
    "/config",
    response_model=SyncConfigResponse,
    summary="Update sync configuration",
    description="Update sync configuration. Only specified fields will be updated.",
    responses={
        200: {"description": "Configuration updated"},
        400: {"model": ErrorResponse, "description": "Invalid configuration"},
    },
)
async def update_sync_config(
    data: SyncConfigUpdate,
    service: SyncService = Depends(get_sync_service),
) -> SyncConfigResponse:
    """Update sync configuration."""
    # Update only provided fields
    config = service.config

    if data.vault_path is not None:
        config.vault_path = data.vault_path
    if data.sync_sources is not None:
        config.sync_sources = data.sync_sources
    if data.folder_mapping is not None:
        config.folder_mapping = data.folder_mapping
    if data.tag_mapping is not None:
        config.tag_mapping = data.tag_mapping
    if data.section_mapping is not None:
        config.section_mapping = data.section_mapping
    if data.default_project is not None:
        config.default_project = data.default_project
    if data.default_conflict_resolution is not None:
        config.default_conflict_resolution = data.default_conflict_resolution

    # Note: In a production system, you would persist this config to a file
    # For now, it's only updated in memory

    return SyncConfigResponse(
        vault_path=config.vault_path,
        sync_sources=config.sync_sources,
        folder_mapping=config.folder_mapping,
        tag_mapping=config.tag_mapping,
        section_mapping=config.section_mapping,
        default_project=config.default_project,
        default_conflict_resolution=config.default_conflict_resolution,
    )
