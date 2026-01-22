// =============================================================================
// useProjects — React Query хуки для работы с проектами
// =============================================================================
// React Query хуки — это обёртки над API функциями которые предоставляют:
//
//   1. Автоматическое управление состоянием (loading, error, data)
//   2. Кэширование — повторные запросы берутся из кэша
//   3. Автоматический рефетч — при возврате на вкладку, при потере фокуса
//   4. Оптимистичные обновления — UI обновляется до ответа сервера
//   5. Инвалидация — автоматически обновляем связанные данные
//
// useQuery — для GET запросов (чтение)
// useMutation — для POST/PUT/DELETE (изменение)
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getProjects,
  getProject,
  getProjectWithStats,
  createProject,
  updateProject,
  deleteProject,
  archiveProject,
} from '@/api';
import type { ProjectCreate, ProjectUpdate, ProjectFilters } from '@/types';

// =============================================================================
// Query Keys
// =============================================================================
// Query keys — это идентификаторы для кэша React Query.
// Структура ключа определяет когда данные нужно инвалидировать.
//
// Пример: ['projects', { include_archived: true }]
//   - 'projects' — базовый ключ
//   - { include_archived: true } — параметры фильтра
//
// При мутации мы инвалидируем все запросы начинающиеся с 'projects'.
// =============================================================================

export const projectKeys = {
  // Все запросы проектов
  all: ['projects'] as const,

  // Список проектов (может быть с разными фильтрами)
  lists: () => [...projectKeys.all, 'list'] as const,
  list: (filters?: ProjectFilters) => [...projectKeys.lists(), filters] as const,

  // Детали проекта (по ID)
  details: () => [...projectKeys.all, 'detail'] as const,
  detail: (id: number) => [...projectKeys.details(), id] as const,

  // Статистика проекта
  stats: (id: number) => [...projectKeys.detail(id), 'stats'] as const,
};

// =============================================================================
// Query Hooks (чтение данных)
// =============================================================================

/**
 * Хук для получения списка проектов.
 *
 * @param filters - Опциональные фильтры
 * @returns Query result с проектами
 *
 * @example
 * function ProjectsList() {
 *   const { data: projects, isLoading, error } = useProjects();
 *
 *   if (isLoading) return <Spinner />;
 *   if (error) return <Error message={error.message} />;
 *
 *   return (
 *     <ul>
 *       {projects.map(p => <li key={p.id}>{p.name}</li>)}
 *     </ul>
 *   );
 * }
 */
export function useProjects(filters?: ProjectFilters) {
  return useQuery({
    // Уникальный ключ для кэширования
    queryKey: projectKeys.list(filters),

    // Функция которая выполняет запрос
    queryFn: () => getProjects(filters),
  });
}

/**
 * Хук для получения одного проекта.
 *
 * @param id - ID проекта
 * @returns Query result с проектом
 *
 * @example
 * function ProjectPage({ id }: { id: number }) {
 *   const { data: project, isLoading } = useProject(id);
 *   // ...
 * }
 */
export function useProject(id: number) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => getProject(id),

    // Не делать запрос если id не задан
    enabled: !!id,
  });
}

/**
 * Хук для получения проекта со статистикой.
 *
 * @param id - ID проекта
 */
export function useProjectWithStats(id: number) {
  return useQuery({
    queryKey: projectKeys.stats(id),
    queryFn: () => getProjectWithStats(id),
    enabled: !!id,
  });
}

// =============================================================================
// Mutation Hooks (изменение данных)
// =============================================================================

/**
 * Хук для создания проекта.
 *
 * @example
 * function CreateProjectForm() {
 *   const createMutation = useCreateProject();
 *
 *   const handleSubmit = (data: ProjectCreate) => {
 *     createMutation.mutate(data, {
 *       onSuccess: (project) => {
 *         toast.success(`Проект "${project.name}" создан!`);
 *       },
 *       onError: (error) => {
 *         toast.error(error.message);
 *       },
 *     });
 *   };
 *
 *   return (
 *     <form onSubmit={handleSubmit}>
 *       <button disabled={createMutation.isPending}>
 *         {createMutation.isPending ? 'Создание...' : 'Создать'}
 *       </button>
 *     </form>
 *   );
 * }
 */
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectCreate) => createProject(data),

    // После успешного создания инвалидируем список проектов
    // чтобы он автоматически обновился
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}

/**
 * Хук для обновления проекта.
 *
 * @example
 * const updateMutation = useUpdateProject();
 * updateMutation.mutate({ id: 1, data: { name: 'Новое имя' } });
 */
export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProjectUpdate }) =>
      updateProject(id, data),

    onSuccess: (updatedProject) => {
      // Обновляем кэш конкретного проекта
      queryClient.setQueryData(
        projectKeys.detail(updatedProject.id),
        updatedProject
      );

      // Инвалидируем списки
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}

/**
 * Хук для удаления проекта.
 *
 * @example
 * const deleteMutation = useDeleteProject();
 * deleteMutation.mutate(projectId);
 */
export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => deleteProject(id),

    onSuccess: (_, deletedId) => {
      // Удаляем из кэша
      queryClient.removeQueries({ queryKey: projectKeys.detail(deletedId) });

      // Инвалидируем списки
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}

/**
 * Хук для архивации проекта.
 */
export function useArchiveProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => archiveProject(id),

    onSuccess: () => {
      // Инвалидируем все данные проектов
      queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}
