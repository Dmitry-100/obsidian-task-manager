// =============================================================================
// Tasks API — Функции для работы с задачами
// =============================================================================
// Этот модуль содержит все API функции связанные с задачами.
//
// Функции соответствуют эндпойнтам backend:
//   GET    /tasks         → getTasks()
//   POST   /tasks         → createTask()
//   GET    /tasks/:id     → getTask()
//   PUT    /tasks/:id     → updateTask()
//   DELETE /tasks/:id     → deleteTask()
//
// Дополнительно:
//   - Фильтрация по статусу, приоритету, проекту
//   - Поиск по тексту
//   - Пагинация
// =============================================================================

import { api } from './client';
import type {
  Task,
  TaskCreate,
  TaskUpdate,
  TaskFilters,
} from '@/types';
import { TaskStatus } from '@/types';

// =============================================================================
// CRUD Operations
// =============================================================================

/**
 * Получить список задач с фильтрацией и пагинацией.
 *
 * @param filters - Опциональные фильтры
 * @returns Массив задач
 *
 * @example
 * // Все задачи
 * const tasks = await getTasks();
 *
 * // Задачи конкретного проекта
 * const projectTasks = await getTasks({ project_id: 1 });
 *
 * // Только выполненные задачи
 * const doneTasks = await getTasks({ status: TaskStatus.DONE });
 *
 * // Поиск
 * const searchResults = await getTasks({ search: 'API' });
 */
export async function getTasks(filters?: TaskFilters): Promise<Task[]> {
  // Формируем query параметры
  const params = new URLSearchParams();

  if (filters?.project_id !== undefined) {
    params.append('project_id', String(filters.project_id));
  }
  if (filters?.status) {
    params.append('status', filters.status);
  }
  if (filters?.priority) {
    params.append('priority', filters.priority);
  }
  if (filters?.search) {
    params.append('search', filters.search);
  }
  if (filters?.skip !== undefined) {
    params.append('skip', String(filters.skip));
  }
  if (filters?.limit !== undefined) {
    params.append('limit', String(filters.limit));
  }

  const queryString = params.toString();
  const endpoint = queryString ? `/tasks?${queryString}` : '/tasks';

  return api.get<Task[]>(endpoint);
}

/**
 * Получить задачу по ID.
 *
 * @param id - ID задачи
 * @returns Задача со всеми связями (теги, проект)
 * @throws {ApiError} Если задача не найдена (404)
 *
 * @example
 * const task = await getTask(1);
 * console.log(task.tags); // Теги задачи
 */
export async function getTask(id: number): Promise<Task> {
  return api.get<Task>(`/tasks/${id}`);
}

/**
 * Создать новую задачу.
 *
 * @param data - Данные для создания
 * @returns Созданная задача
 *
 * @example
 * const task = await createTask({
 *   title: 'Написать тесты',
 *   project_id: 1,
 *   priority: TaskPriority.HIGH,
 *   due_date: '2026-01-25',
 *   tag_names: ['testing', 'backend'],
 * });
 */
export async function createTask(data: TaskCreate): Promise<Task> {
  return api.post<Task>('/tasks', data);
}

/**
 * Обновить задачу.
 *
 * @param id - ID задачи
 * @param data - Данные для обновления (только изменённые поля)
 * @returns Обновлённая задача
 *
 * @example
 * // Изменить статус
 * const task = await updateTask(1, {
 *   status: TaskStatus.IN_PROGRESS,
 * });
 *
 * // Отметить выполненной
 * const doneTask = await updateTask(1, {
 *   status: TaskStatus.DONE,
 * });
 */
export async function updateTask(id: number, data: TaskUpdate): Promise<Task> {
  return api.put<Task>(`/tasks/${id}`, data);
}

/**
 * Удалить задачу.
 *
 * ВАЖНО: Удаление каскадное — все подзадачи тоже будут удалены!
 *
 * @param id - ID задачи
 *
 * @example
 * await deleteTask(1);
 */
export async function deleteTask(id: number): Promise<void> {
  return api.delete(`/tasks/${id}`);
}

// =============================================================================
// Дополнительные операции
// =============================================================================

/**
 * Получить задачи проекта.
 *
 * Удобный хелпер для получения задач конкретного проекта.
 *
 * @param projectId - ID проекта
 * @param filters - Дополнительные фильтры
 * @returns Массив задач
 *
 * @example
 * const tasks = await getProjectTasks(1);
 */
export async function getProjectTasks(
  projectId: number,
  filters?: Omit<TaskFilters, 'project_id'>
): Promise<Task[]> {
  return getTasks({ ...filters, project_id: projectId });
}

/**
 * Быстро переключить статус задачи на "Выполнено".
 *
 * Удобный хелпер для checkbox'ов.
 *
 * @param id - ID задачи
 * @param completed - Выполнена или нет
 * @returns Обновлённая задача
 *
 * @example
 * // Отметить выполненной
 * await toggleTaskComplete(1, true);
 *
 * // Вернуть в работу
 * await toggleTaskComplete(1, false);
 */
export async function toggleTaskComplete(id: number, completed: boolean): Promise<Task> {
  return updateTask(id, {
    status: completed ? TaskStatus.DONE : TaskStatus.TODO,
  });
}

// =============================================================================
// Теги задачи
// =============================================================================

/**
 * Добавить тег к задаче.
 *
 * @param taskId - ID задачи
 * @param tagName - Название тега
 * @returns Обновлённая задача
 */
export async function addTagToTask(taskId: number, tagName: string): Promise<Task> {
  return api.post<Task>(`/tasks/${taskId}/tags`, { name: tagName });
}

/**
 * Удалить тег с задачи.
 *
 * @param taskId - ID задачи
 * @param tagId - ID тега
 */
export async function removeTagFromTask(taskId: number, tagId: number): Promise<void> {
  return api.delete(`/tasks/${taskId}/tags/${tagId}`);
}
