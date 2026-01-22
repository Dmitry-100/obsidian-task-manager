// =============================================================================
// useSync — React Query hooks for Obsidian synchronization
// =============================================================================
// These hooks provide:
//   1. Automatic state management (loading, error, data)
//   2. Caching of sync status and conflicts
//   3. Automatic refetch on focus
//   4. Optimistic updates for conflict resolution
//   5. Cache invalidation after sync operations
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSyncStatus,
  importFromObsidian,
  exportToObsidian,
  getConflicts,
  resolveConflict,
  resolveAllConflicts,
  getSyncHistory,
  getSyncConfig,
  updateSyncConfig,
} from '@/api';
import type {
  SyncImportRequest,
  SyncExportRequest,
  ConflictResolution,
  SyncConfigUpdate,
} from '@/types';

// =============================================================================
// Query Keys
// =============================================================================

export const syncKeys = {
  // All sync-related queries
  all: ['sync'] as const,

  // Sync status
  status: () => [...syncKeys.all, 'status'] as const,

  // Conflicts
  conflicts: () => [...syncKeys.all, 'conflicts'] as const,
  conflictsByLog: (syncLogId: number) => [...syncKeys.conflicts(), syncLogId] as const,

  // History
  history: () => [...syncKeys.all, 'history'] as const,
  historyWithLimit: (limit: number) => [...syncKeys.history(), limit] as const,

  // Config
  config: () => [...syncKeys.all, 'config'] as const,
};

// =============================================================================
// Query Hooks (reading data)
// =============================================================================

/**
 * Hook for getting sync status.
 *
 * @example
 * function SyncStatusCard() {
 *   const { data: status, isLoading } = useSyncStatus();
 *
 *   if (isLoading) return <Spinner />;
 *
 *   return (
 *     <div>
 *       <p>Syncing: {status.is_syncing ? 'Yes' : 'No'}</p>
 *       <p>Conflicts: {status.unresolved_conflicts}</p>
 *     </div>
 *   );
 * }
 */
export function useSyncStatus() {
  return useQuery({
    queryKey: syncKeys.status(),
    queryFn: getSyncStatus,
    // Refetch every 5 seconds while syncing
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.is_syncing ? 5000 : false;
    },
  });
}

/**
 * Hook for getting sync conflicts.
 *
 * @param syncLogId - Optional sync log ID to filter conflicts
 */
export function useSyncConflicts(syncLogId?: number) {
  return useQuery({
    queryKey: syncLogId ? syncKeys.conflictsByLog(syncLogId) : syncKeys.conflicts(),
    queryFn: () => getConflicts(syncLogId),
  });
}

/**
 * Hook for getting sync history.
 *
 * @param limit - Maximum number of records
 */
export function useSyncHistory(limit: number = 10) {
  return useQuery({
    queryKey: syncKeys.historyWithLimit(limit),
    queryFn: () => getSyncHistory(limit),
  });
}

/**
 * Hook for getting sync configuration.
 */
export function useSyncConfig() {
  return useQuery({
    queryKey: syncKeys.config(),
    queryFn: getSyncConfig,
  });
}

// =============================================================================
// Mutation Hooks (modifying data)
// =============================================================================

/**
 * Hook for importing from Obsidian.
 *
 * @example
 * function ImportButton() {
 *   const importMutation = useImportFromObsidian();
 *
 *   return (
 *     <button
 *       onClick={() => importMutation.mutate({})}
 *       disabled={importMutation.isPending}
 *     >
 *       {importMutation.isPending ? 'Importing...' : 'Import'}
 *     </button>
 *   );
 * }
 */
export function useImportFromObsidian() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request?: SyncImportRequest) => importFromObsidian(request),

    onSuccess: () => {
      // Invalidate all sync-related queries
      queryClient.invalidateQueries({ queryKey: syncKeys.all });
      // Also invalidate tasks and projects as they may have changed
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

/**
 * Hook for exporting to Obsidian.
 */
export function useExportToObsidian() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request?: SyncExportRequest) => exportToObsidian(request),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: syncKeys.status() });
      queryClient.invalidateQueries({ queryKey: syncKeys.history() });
    },
  });
}

/**
 * Hook for resolving a single conflict.
 *
 * @example
 * const resolveMutation = useResolveConflict();
 * resolveMutation.mutate({
 *   conflictId: 1,
 *   resolution: 'obsidian',
 * });
 */
export function useResolveConflict() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      conflictId,
      resolution,
    }: {
      conflictId: number;
      resolution: ConflictResolution;
    }) => resolveConflict(conflictId, resolution),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: syncKeys.conflicts() });
      queryClient.invalidateQueries({ queryKey: syncKeys.status() });
      // Also invalidate tasks as they may have changed
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

/**
 * Hook for resolving all conflicts.
 */
export function useResolveAllConflicts() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      syncLogId,
      resolution,
    }: {
      syncLogId: number;
      resolution: ConflictResolution;
    }) => resolveAllConflicts(syncLogId, resolution),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: syncKeys.conflicts() });
      queryClient.invalidateQueries({ queryKey: syncKeys.status() });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

/**
 * Hook for updating sync configuration.
 */
export function useUpdateSyncConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SyncConfigUpdate) => updateSyncConfig(data),

    onSuccess: (updatedConfig) => {
      // Update config cache
      queryClient.setQueryData(syncKeys.config(), updatedConfig);
    },
  });
}
