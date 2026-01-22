// =============================================================================
// API Module — Точка входа для всех API функций
// =============================================================================
// Этот файл реэкспортирует все API функции для удобного импорта.
//
// Использование:
//   import { getProjects, getTasks, ApiError } from '@/api';
//
// Вместо:
//   import { getProjects } from '@/api/projects';
//   import { getTasks } from '@/api/tasks';
//   import { ApiError } from '@/api/client';
// =============================================================================

// Клиент и ошибки
export { api, apiClient, ApiError, NetworkError } from './client';

// Projects API
export {
  getProjects,
  getProject,
  getProjectWithStats,
  createProject,
  updateProject,
  deleteProject,
  archiveProject,
  unarchiveProject,
} from './projects';

// Tasks API
export {
  getTasks,
  getTask,
  createTask,
  updateTask,
  deleteTask,
  getProjectTasks,
  toggleTaskComplete,
  addTagToTask,
  removeTagFromTask,
} from './tasks';

// Tags API
export {
  getTags,
  getPopularTags,
  createTag,
  deleteTag,
} from './tags';
