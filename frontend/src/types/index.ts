// =============================================================================
// TypeScript Types — Типы для API
// =============================================================================
// Эти типы соответствуют Pydantic схемам из backend (src/api/schemas.py).
//
// Зачем дублировать типы?
//   TypeScript и Python — разные языки, каждый со своей системой типов.
//   Мы создаём TypeScript версию чтобы получить:
//   1. Автодополнение в IDE
//   2. Проверку типов при компиляции
//   3. Документацию прямо в коде
//
// Соответствие Backend схемам:
//   ProjectResponse → Project
//   TaskResponse → Task
//   TagResponse → Tag
// =============================================================================

// =============================================================================
// ENUMS (Перечисления)
// =============================================================================
// В TypeScript enum компилируется в JavaScript объект.
// Используем string enum чтобы значения читались в JSON.
// =============================================================================

/**
 * Статус задачи.
 *
 * Используем const object вместо enum для совместимости с erasableSyntaxOnly.
 *
 * @example
 * if (task.status === TaskStatus.DONE) {
 *   // Задача выполнена
 * }
 */
export const TaskStatus = {
  TODO: 'todo',
  IN_PROGRESS: 'in_progress',
  DONE: 'done',
  CANCELLED: 'cancelled',
} as const;

export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus];

/**
 * Приоритет задачи.
 */
export const TaskPriority = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
} as const;

export type TaskPriority = (typeof TaskPriority)[keyof typeof TaskPriority];

// =============================================================================
// PROJECT TYPES
// =============================================================================

/**
 * Проект — контейнер для группировки связанных задач.
 *
 * Соответствует: backend/src/api/schemas.py -> ProjectResponse
 */
export interface Project {
  id: number;
  name: string;
  description: string | null;
  obsidian_folder: string | null;
  color: string | null; // Формат: #RRGGBB
  is_archived: boolean;
  created_at: string; // ISO datetime string
  updated_at: string;
}

/**
 * Проект со статистикой.
 *
 * Соответствует: backend/src/api/schemas.py -> ProjectWithStats
 */
export interface ProjectWithStats extends Project {
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  todo_tasks: number;
  completion_percentage: number;
}

/**
 * Данные для создания проекта.
 *
 * Соответствует: backend/src/api/schemas.py -> ProjectCreate
 */
export interface ProjectCreate {
  name: string;
  description?: string | null;
  obsidian_folder?: string | null;
  color?: string | null;
}

/**
 * Данные для обновления проекта (все поля опциональные).
 *
 * Соответствует: backend/src/api/schemas.py -> ProjectUpdate
 */
export interface ProjectUpdate {
  name?: string;
  description?: string | null;
  obsidian_folder?: string | null;
  color?: string | null;
}

// =============================================================================
// TAG TYPES
// =============================================================================

/**
 * Тег для категоризации задач.
 *
 * Соответствует: backend/src/api/schemas.py -> TagResponse
 */
export interface Tag {
  id: number;
  name: string;
  created_at: string;
}

/**
 * Тег с количеством использований.
 *
 * Соответствует: backend/src/api/schemas.py -> TagWithUsage
 */
export interface TagWithUsage extends Tag {
  usage_count: number;
}

/**
 * Данные для создания тега.
 */
export interface TagCreate {
  name: string;
}

// =============================================================================
// TASK TYPES
// =============================================================================

/**
 * Задача — основная сущность приложения.
 *
 * Соответствует: backend/src/api/schemas.py -> TaskResponse
 */
export interface Task {
  id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null; // ISO date string (YYYY-MM-DD)
  obsidian_path: string | null;
  estimated_hours: number | null;
  project_id: number;
  parent_task_id: number | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  tags: Tag[];
}

/**
 * Данные для создания задачи.
 *
 * Соответствует: backend/src/api/schemas.py -> TaskCreate
 */
export interface TaskCreate {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string | null;
  obsidian_path?: string | null;
  estimated_hours?: number | null;
  project_id: number;
  parent_task_id?: number | null;
  tag_names?: string[];
}

/**
 * Данные для обновления задачи (все поля опциональные).
 *
 * Соответствует: backend/src/api/schemas.py -> TaskUpdate
 */
export interface TaskUpdate {
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: string | null;
  estimated_hours?: number | null;
}

// =============================================================================
// COMMENT TYPES
// =============================================================================

/**
 * Комментарий к задаче.
 *
 * Соответствует: backend/src/api/schemas.py -> CommentResponse
 */
export interface Comment {
  id: number;
  task_id: number;
  content: string;
  created_at: string;
}

/**
 * Данные для создания комментария.
 */
export interface CommentCreate {
  content: string;
}

// =============================================================================
// API RESPONSE TYPES
// =============================================================================

/**
 * Пагинированный ответ API.
 *
 * @template T - Тип элементов в списке
 *
 * @example
 * const response: PaginatedResponse<Task> = await api.getTasks();
 * console.log(response.items); // Task[]
 * console.log(response.total); // Всего задач
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * Детали ошибки для конкретного поля.
 */
export interface ErrorDetail {
  field: string;
  message: string;
}

/**
 * Тело ошибки API.
 */
export interface ErrorBody {
  code: string;
  message: string;
  details: ErrorDetail[] | null;
}

/**
 * Ответ API с ошибкой.
 */
export interface ErrorResponse {
  error: ErrorBody;
}

/**
 * Успешный ответ без данных.
 */
export interface SuccessResponse {
  message: string;
}

// =============================================================================
// FILTER TYPES
// =============================================================================

/**
 * Фильтры для запроса списка задач.
 *
 * Все поля опциональные — можно передать любую комбинацию.
 *
 * @example
 * // Получить все высокоприоритетные задачи проекта 1
 * const filters: TaskFilters = {
 *   project_id: 1,
 *   priority: TaskPriority.HIGH,
 * };
 */
export interface TaskFilters {
  project_id?: number;
  status?: TaskStatus;
  priority?: TaskPriority;
  search?: string;
  skip?: number;
  limit?: number;
}

/**
 * Фильтры для запроса списка проектов.
 */
export interface ProjectFilters {
  include_archived?: boolean;
  skip?: number;
  limit?: number;
}
