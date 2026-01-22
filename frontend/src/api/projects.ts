// =============================================================================
// Projects API — Функции для работы с проектами
// =============================================================================
// Этот модуль содержит все API функции связанные с проектами.
//
// Функции соответствуют эндпойнтам backend:
//   GET    /projects         → getProjects()
//   POST   /projects         → createProject()
//   GET    /projects/:id     → getProject()
//   PUT    /projects/:id     → updateProject()
//   DELETE /projects/:id     → deleteProject()
//   POST   /projects/:id/archive → archiveProject()
// =============================================================================

import { api } from './client';
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectWithStats,
  ProjectFilters,
  SuccessResponse,
} from '@/types';

// =============================================================================
// CRUD Operations
// =============================================================================

/**
 * Получить список всех проектов.
 *
 * @param filters - Опциональные фильтры
 * @returns Массив проектов
 *
 * @example
 * // Все активные проекты
 * const projects = await getProjects();
 *
 * // Включая архивные
 * const allProjects = await getProjects({ include_archived: true });
 */
export async function getProjects(filters?: ProjectFilters): Promise<Project[]> {
  // Формируем query параметры
  const params = new URLSearchParams();

  if (filters?.include_archived) {
    params.append('include_archived', 'true');
  }
  if (filters?.skip !== undefined) {
    params.append('skip', String(filters.skip));
  }
  if (filters?.limit !== undefined) {
    params.append('limit', String(filters.limit));
  }

  const queryString = params.toString();
  const endpoint = queryString ? `/projects?${queryString}` : '/projects';

  return api.get<Project[]>(endpoint);
}

/**
 * Получить проект по ID.
 *
 * @param id - ID проекта
 * @returns Проект
 * @throws {ApiError} Если проект не найден (404)
 *
 * @example
 * const project = await getProject(1);
 */
export async function getProject(id: number): Promise<Project> {
  return api.get<Project>(`/projects/${id}`);
}

/**
 * Получить проект со статистикой.
 *
 * @param id - ID проекта
 * @returns Проект с подсчётом задач
 *
 * @example
 * const project = await getProjectWithStats(1);
 * console.log(`Выполнено: ${project.completion_percentage}%`);
 */
export async function getProjectWithStats(id: number): Promise<ProjectWithStats> {
  return api.get<ProjectWithStats>(`/projects/${id}/stats`);
}

/**
 * Создать новый проект.
 *
 * @param data - Данные для создания
 * @returns Созданный проект
 *
 * @example
 * const project = await createProject({
 *   name: 'Мой проект',
 *   description: 'Описание проекта',
 *   color: '#3B82F6',
 * });
 */
export async function createProject(data: ProjectCreate): Promise<Project> {
  return api.post<Project>('/projects', data);
}

/**
 * Обновить проект.
 *
 * @param id - ID проекта
 * @param data - Данные для обновления (только изменённые поля)
 * @returns Обновлённый проект
 *
 * @example
 * const project = await updateProject(1, {
 *   name: 'Новое название',
 * });
 */
export async function updateProject(id: number, data: ProjectUpdate): Promise<Project> {
  return api.put<Project>(`/projects/${id}`, data);
}

/**
 * Удалить проект.
 *
 * ВАЖНО: Удаление каскадное — все задачи проекта тоже будут удалены!
 *
 * @param id - ID проекта
 *
 * @example
 * await deleteProject(1);
 */
export async function deleteProject(id: number): Promise<void> {
  return api.delete(`/projects/${id}`);
}

/**
 * Архивировать проект.
 *
 * Архивированные проекты скрыты по умолчанию, но могут быть восстановлены.
 *
 * @param id - ID проекта
 * @returns Сообщение об успехе
 *
 * @example
 * await archiveProject(1);
 */
export async function archiveProject(id: number): Promise<SuccessResponse> {
  return api.post<SuccessResponse>(`/projects/${id}/archive`);
}

/**
 * Разархивировать проект.
 *
 * @param id - ID проекта
 * @returns Сообщение об успехе
 */
export async function unarchiveProject(id: number): Promise<SuccessResponse> {
  return api.post<SuccessResponse>(`/projects/${id}/unarchive`);
}
