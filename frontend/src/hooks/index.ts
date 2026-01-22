// =============================================================================
// Hooks Module — Точка входа для всех хуков
// =============================================================================
// Реэкспорт всех React Query хуков для удобного импорта.
//
// Использование:
//   import { useProjects, useTasks, useCreateTask } from '@/hooks';
// =============================================================================

// Projects hooks
export {
  projectKeys,
  useProjects,
  useProject,
  useProjectWithStats,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
  useArchiveProject,
} from './useProjects';

// Tasks hooks
export {
  taskKeys,
  useTasks,
  useTask,
  useCreateTask,
  useUpdateTask,
  useDeleteTask,
  useToggleTaskComplete,
} from './useTasks';
