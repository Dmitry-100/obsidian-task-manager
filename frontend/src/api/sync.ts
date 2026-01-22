// =============================================================================
// Sync API — Functions for Obsidian synchronization
// =============================================================================
// This module contains all API functions related to sync operations.
//
// Functions correspond to backend endpoints:
//   GET    /sync/status     → getSyncStatus()
//   POST   /sync/import     → importFromObsidian()
//   POST   /sync/export     → exportToObsidian()
//   GET    /sync/conflicts  → getConflicts()
//   POST   /sync/conflicts/:id/resolve → resolveConflict()
//   GET    /sync/history    → getSyncHistory()
//   GET    /sync/config     → getSyncConfig()
//   PUT    /sync/config     → updateSyncConfig()
// =============================================================================

import { api } from './client';
import type {
  SyncStatusInfo,
  SyncResult,
  SyncConflict,
  SyncLog,
  SyncConfig,
  SyncImportRequest,
  SyncExportRequest,
  ConflictResolution,
  SyncConfigUpdate,
} from '@/types';

// =============================================================================
// Sync Status
// =============================================================================

/**
 * Get current sync status.
 *
 * @returns Sync status information
 *
 * @example
 * const status = await getSyncStatus();
 * if (status.is_syncing) {
 *   console.log('Sync in progress...');
 * }
 */
export async function getSyncStatus(): Promise<SyncStatusInfo> {
  return api.get<SyncStatusInfo>('/sync/status');
}

// =============================================================================
// Import / Export
// =============================================================================

/**
 * Import tasks from Obsidian vault.
 *
 * @param request - Optional import request with specific files
 * @returns Sync result with statistics
 *
 * @example
 * // Import from configured sources
 * const result = await importFromObsidian();
 *
 * // Import specific files
 * const result = await importFromObsidian({
 *   source_files: ['/path/to/file.md'],
 * });
 */
export async function importFromObsidian(request?: SyncImportRequest): Promise<SyncResult> {
  return api.post<SyncResult>('/sync/import', request || {});
}

/**
 * Export tasks to Obsidian markdown file.
 *
 * @param request - Optional export request with project ID and output path
 * @returns Sync result with statistics
 *
 * @example
 * // Export all tasks
 * const result = await exportToObsidian();
 *
 * // Export specific project
 * const result = await exportToObsidian({
 *   project_id: 1,
 *   output_path: '/path/to/output.md',
 * });
 */
export async function exportToObsidian(request?: SyncExportRequest): Promise<SyncResult> {
  return api.post<SyncResult>('/sync/export', request || {});
}

// =============================================================================
// Conflicts
// =============================================================================

/**
 * Get list of sync conflicts.
 *
 * @param syncLogId - Optional sync log ID to filter conflicts
 * @returns List of conflicts
 *
 * @example
 * // Get all unresolved conflicts
 * const conflicts = await getConflicts();
 *
 * // Get conflicts for specific sync
 * const conflicts = await getConflicts(123);
 */
export async function getConflicts(syncLogId?: number): Promise<SyncConflict[]> {
  const params = new URLSearchParams();
  if (syncLogId !== undefined) {
    params.append('sync_log_id', String(syncLogId));
  }
  const queryString = params.toString();
  const endpoint = queryString ? `/sync/conflicts?${queryString}` : '/sync/conflicts';
  return api.get<SyncConflict[]>(endpoint);
}

/**
 * Get a specific conflict by ID.
 *
 * @param conflictId - Conflict ID
 * @returns Conflict details
 */
export async function getConflict(conflictId: number): Promise<SyncConflict> {
  return api.get<SyncConflict>(`/sync/conflicts/${conflictId}`);
}

/**
 * Resolve a sync conflict.
 *
 * @param conflictId - Conflict ID
 * @param resolution - Resolution choice
 * @returns Resolved conflict
 *
 * @example
 * // Keep Obsidian version
 * await resolveConflict(1, 'obsidian');
 *
 * // Keep database version
 * await resolveConflict(1, 'database');
 */
export async function resolveConflict(
  conflictId: number,
  resolution: ConflictResolution
): Promise<SyncConflict> {
  return api.post<SyncConflict>(`/sync/conflicts/${conflictId}/resolve`, {
    resolution,
  });
}

/**
 * Resolve all conflicts for a sync log.
 *
 * @param syncLogId - Sync log ID
 * @param resolution - Resolution to apply to all
 * @returns Number of resolved conflicts
 *
 * @example
 * // Keep all Obsidian versions
 * const { resolved_count } = await resolveAllConflicts(123, 'obsidian');
 */
export async function resolveAllConflicts(
  syncLogId: number,
  resolution: ConflictResolution
): Promise<{ resolved_count: number; resolution: string }> {
  return api.post<{ resolved_count: number; resolution: string }>(
    `/sync/conflicts/resolve-all?sync_log_id=${syncLogId}`,
    { resolution }
  );
}

// =============================================================================
// Sync History
// =============================================================================

/**
 * Get sync operation history.
 *
 * @param limit - Maximum number of records (default: 10)
 * @returns List of sync logs
 *
 * @example
 * const history = await getSyncHistory(20);
 */
export async function getSyncHistory(limit: number = 10): Promise<SyncLog[]> {
  return api.get<SyncLog[]>(`/sync/history?limit=${limit}`);
}

// =============================================================================
// Configuration
// =============================================================================

/**
 * Get sync configuration.
 *
 * @returns Current sync configuration
 *
 * @example
 * const config = await getSyncConfig();
 * console.log(config.vault_path);
 */
export async function getSyncConfig(): Promise<SyncConfig> {
  return api.get<SyncConfig>('/sync/config');
}

/**
 * Update sync configuration.
 *
 * @param data - Configuration fields to update
 * @returns Updated configuration
 *
 * @example
 * const config = await updateSyncConfig({
 *   vault_path: '/new/path/to/vault',
 *   default_project: 'Inbox',
 * });
 */
export async function updateSyncConfig(data: SyncConfigUpdate): Promise<SyncConfig> {
  return api.put<SyncConfig>('/sync/config', data);
}
