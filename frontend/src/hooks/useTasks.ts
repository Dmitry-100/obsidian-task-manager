// =============================================================================
// useTasks — React Query хуки для работы с задачами
// =============================================================================
// Хуки для CRUD операций с задачами.
// Автоматически управляют кэшем и состоянием загрузки.
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getTasks,
  getTask,
  createTask,
  updateTask,
  deleteTask,
} from '@/api';
import type { TaskCreate, TaskUpdate, TaskFilters } from '@/types';
import { TaskStatus } from '@/types';

// =============================================================================
// Query Keys
// =============================================================================

export const taskKeys = {
  // Базовый ключ для всех задач
  all: ['tasks'] as const,

  // Списки задач
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (filters?: TaskFilters) => [...taskKeys.lists(), filters] as const,

  // Детали задачи
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: number) => [...taskKeys.details(), id] as const,
};

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Хук для получения списка задач.
 *
 * @param filters - Фильтры (project_id, status, priority, search)
 *
 * @example
 * // Все задачи
 * const { data: tasks } = useTasks();
 *
 * // Задачи проекта
 * const { data: tasks } = useTasks({ project_id: 1 });
 *
 * // Только высокоприоритетные
 * const { data: tasks } = useTasks({ priority: TaskPriority.HIGH });
 */
export function useTasks(filters?: TaskFilters) {
  return useQuery({
    queryKey: taskKeys.list(filters),
    queryFn: () => getTasks(filters),
  });
}

/**
 * Хук для получения одной задачи.
 *
 * @param id - ID задачи
 *
 * @example
 * const { data: task, isLoading } = useTask(taskId);
 */
export function useTask(id: number) {
  return useQuery({
    queryKey: taskKeys.detail(id),
    queryFn: () => getTask(id),
    enabled: !!id,
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Хук для создания задачи.
 *
 * @example
 * const createMutation = useCreateTask();
 *
 * createMutation.mutate({
 *   title: 'Новая задача',
 *   project_id: 1,
 * }, {
 *   onSuccess: (task) => {
 *     toast.success('Задача создана!');
 *   },
 * });
 */
export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TaskCreate) => createTask(data),

    onSuccess: (newTask) => {
      // Инвалидируем списки задач
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });

      // Также инвалидируем статистику проекта (там количество задач)
      queryClient.invalidateQueries({
        queryKey: ['projects', 'detail', newTask.project_id],
      });
    },
  });
}

/**
 * Хук для обновления задачи.
 *
 * @example
 * const updateMutation = useUpdateTask();
 *
 * // Изменить статус
 * updateMutation.mutate({
 *   id: taskId,
 *   data: { status: TaskStatus.DONE },
 * });
 */
export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TaskUpdate }) =>
      updateTask(id, data),

    onSuccess: (updatedTask) => {
      // Обновляем кэш конкретной задачи
      queryClient.setQueryData(
        taskKeys.detail(updatedTask.id),
        updatedTask
      );

      // Инвалидируем списки (статус мог измениться)
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });

      // Инвалидируем статистику проекта
      queryClient.invalidateQueries({
        queryKey: ['projects', 'detail', updatedTask.project_id],
      });
    },
  });
}

/**
 * Хук для удаления задачи.
 *
 * @example
 * const deleteMutation = useDeleteTask();
 * deleteMutation.mutate(taskId);
 */
export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => deleteTask(id),

    onSuccess: (_, deletedId) => {
      // Удаляем из кэша
      queryClient.removeQueries({ queryKey: taskKeys.detail(deletedId) });

      // Инвалидируем списки
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });

      // Инвалидируем статистику всех проектов
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

/**
 * Хук для быстрого переключения статуса задачи.
 *
 * Удобно для checkbox'ов в списке задач.
 *
 * @example
 * const toggleMutation = useToggleTaskComplete();
 *
 * <Checkbox
 *   checked={task.status === 'done'}
 *   onCheckedChange={(checked) => {
 *     toggleMutation.mutate({ id: task.id, completed: checked });
 *   }}
 * />
 */
export function useToggleTaskComplete() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, completed }: { id: number; completed: boolean }) =>
      updateTask(id, { status: completed ? TaskStatus.DONE : TaskStatus.TODO }),

    // Оптимистичное обновление — UI обновляется сразу, до ответа сервера
    onMutate: async () => {
      // Отменяем текущие запросы чтобы они не перезаписали наше обновление
      await queryClient.cancelQueries({ queryKey: taskKeys.lists() });

      // Сохраняем предыдущее состояние для отката в случае ошибки
      const previousTasks = queryClient.getQueryData(taskKeys.lists());

      // Оптимистично обновляем кэш
      // (В реальности это сложнее — нужно обновить конкретный элемент в списке)

      return { previousTasks };
    },

    onError: (_error, _variables, context) => {
      // Откатываем к предыдущему состоянию в случае ошибки
      if (context?.previousTasks) {
        queryClient.setQueryData(taskKeys.lists(), context.previousTasks);
      }
    },

    onSettled: () => {
      // В любом случае инвалидируем кэш чтобы получить актуальные данные
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}
