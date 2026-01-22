// =============================================================================
// Tasks Page — Страница списка задач
// =============================================================================
// Главная рабочая страница приложения. Показывает все задачи с возможностью:
//   - Фильтрации по статусу, приоритету, проекту
//   - Поиска по названию
//   - Создания новых задач
//   - Отметки задач как выполненных (чекбокс)
//   - Просмотра деталей задачи
//
// URL параметры:
//   /tasks              — все задачи
//   /tasks?project=1    — задачи проекта с id=1
//   /tasks?status=done  — только выполненные
// =============================================================================

import { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

// UI компоненты
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';

// Хуки
import { useTasks, useCreateTask, useUpdateTask } from '@/hooks';
import { useProjects } from '@/hooks';

// Типы
import type { Task, TaskCreate } from '@/types';
import { TaskStatus, TaskPriority } from '@/types';

// =============================================================================
// Вспомогательные функции
// =============================================================================

/**
 * Получить цвет бейджа для приоритета.
 */
function getPriorityColor(priority: TaskPriority): string {
  switch (priority) {
    case TaskPriority.HIGH:
      return 'bg-red-100 text-red-800 border-red-200';
    case TaskPriority.MEDIUM:
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case TaskPriority.LOW:
      return 'bg-green-100 text-green-800 border-green-200';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

/**
 * Получить текст для приоритета.
 */
function getPriorityLabel(priority: TaskPriority): string {
  switch (priority) {
    case TaskPriority.HIGH:
      return 'Высокий';
    case TaskPriority.MEDIUM:
      return 'Средний';
    case TaskPriority.LOW:
      return 'Низкий';
    default:
      return priority;
  }
}

/**
 * Получить текст для статуса.
 */
function getStatusLabel(status: TaskStatus): string {
  switch (status) {
    case TaskStatus.TODO:
      return 'К выполнению';
    case TaskStatus.IN_PROGRESS:
      return 'В работе';
    case TaskStatus.DONE:
      return 'Выполнено';
    case TaskStatus.CANCELLED:
      return 'Отменено';
    default:
      return status;
  }
}

/**
 * Проверить, просрочена ли задача.
 */
function isOverdue(task: Task): boolean {
  if (!task.due_date || task.status === TaskStatus.DONE) {
    return false;
  }
  return new Date(task.due_date) < new Date();
}

// =============================================================================
// Компонент Tasks
// =============================================================================
export function Tasks() {
  // ---------------------------------------------------------------------------
  // URL параметры
  // ---------------------------------------------------------------------------
  // useSearchParams позволяет читать и изменять query параметры URL
  // Например: /tasks?project=1&status=todo
  const [searchParams, setSearchParams] = useSearchParams();

  // Читаем фильтры из URL
  const projectFilter = searchParams.get('project');
  const statusFilter = searchParams.get('status') as TaskStatus | null;

  // ---------------------------------------------------------------------------
  // Локальное состояние
  // ---------------------------------------------------------------------------
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newTask, setNewTask] = useState<Partial<TaskCreate>>({
    title: '',
    description: '',
    priority: TaskPriority.MEDIUM,
    project_id: projectFilter ? parseInt(projectFilter) : undefined,
  });

  // ---------------------------------------------------------------------------
  // React Query хуки
  // ---------------------------------------------------------------------------
  // Загружаем задачи с учётом фильтра по проекту
  const { data: tasks, isLoading, error } = useTasks(
    projectFilter ? { project_id: parseInt(projectFilter) } : undefined
  );

  // Загружаем проекты для селекта
  const { data: projects } = useProjects();

  // Мутации
  const createMutation = useCreateTask();
  const updateMutation = useUpdateTask();

  // ---------------------------------------------------------------------------
  // Фильтрация и сортировка (на клиенте)
  // ---------------------------------------------------------------------------
  // useMemo кэширует результат вычисления и пересчитывает только при
  // изменении зависимостей (tasks, statusFilter, searchQuery)
  const filteredTasks = useMemo(() => {
    if (!tasks) return [];

    let result = [...tasks];

    // Фильтр по статусу
    if (statusFilter) {
      result = result.filter((t) => t.status === statusFilter);
    }

    // Поиск по названию
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.title.toLowerCase().includes(query) ||
          t.description?.toLowerCase().includes(query)
      );
    }

    // Сортировка: сначала не выполненные, потом по приоритету, потом по дате
    result.sort((a, b) => {
      // Выполненные в конец
      if (a.status === TaskStatus.DONE && b.status !== TaskStatus.DONE) return 1;
      if (a.status !== TaskStatus.DONE && b.status === TaskStatus.DONE) return -1;

      // По приоритету (high > medium > low)
      const priorityOrder = { high: 0, medium: 1, low: 2 };
      const priorityDiff =
        priorityOrder[a.priority as keyof typeof priorityOrder] -
        priorityOrder[b.priority as keyof typeof priorityOrder];
      if (priorityDiff !== 0) return priorityDiff;

      // По дате создания (новые сначала)
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

    return result;
  }, [tasks, statusFilter, searchQuery]);

  // ---------------------------------------------------------------------------
  // Обработчики
  // ---------------------------------------------------------------------------

  /**
   * Изменить фильтр статуса.
   */
  const handleStatusFilter = (status: string) => {
    if (status === 'all') {
      searchParams.delete('status');
    } else {
      searchParams.set('status', status);
    }
    setSearchParams(searchParams);
  };

  /**
   * Изменить фильтр проекта.
   */
  const handleProjectFilter = (projectId: string) => {
    if (projectId === 'all') {
      searchParams.delete('project');
    } else {
      searchParams.set('project', projectId);
    }
    setSearchParams(searchParams);

    // Обновляем project_id в форме создания
    setNewTask((prev) => ({
      ...prev,
      project_id: projectId === 'all' ? undefined : parseInt(projectId),
    }));
  };

  /**
   * Переключить статус задачи (чекбокс).
   */
  const handleToggleComplete = (task: Task) => {
    const newStatus =
      task.status === TaskStatus.DONE ? TaskStatus.TODO : TaskStatus.DONE;

    updateMutation.mutate({
      id: task.id,
      data: { status: newStatus },
    });
  };

  /**
   * Создать новую задачу.
   */
  const handleCreateTask = (e: React.FormEvent) => {
    e.preventDefault();

    if (!newTask.title || !newTask.project_id) {
      return;
    }

    createMutation.mutate(
      {
        title: newTask.title,
        description: newTask.description || undefined,
        priority: newTask.priority,
        project_id: newTask.project_id,
        due_date: newTask.due_date || undefined,
      } as TaskCreate,
      {
        onSuccess: () => {
          setIsCreateDialogOpen(false);
          setNewTask({
            title: '',
            description: '',
            priority: TaskPriority.MEDIUM,
            project_id: projectFilter ? parseInt(projectFilter) : undefined,
          });
        },
      }
    );
  };

  // ---------------------------------------------------------------------------
  // Render: Loading
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Задачи</h1>
          <p className="text-gray-500 mt-1">Загрузка...</p>
        </div>
        <Card>
          <CardContent className="py-8">
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-4 animate-pulse">
                  <div className="w-5 h-5 bg-gray-200 rounded" />
                  <div className="flex-1">
                    <div className="h-5 bg-gray-200 rounded w-3/4" />
                    <div className="h-4 bg-gray-200 rounded w-1/2 mt-2" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: Error
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Задачи</h1>
          <p className="text-red-500 mt-1">Ошибка: {error.message}</p>
        </div>
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-800">
              Не удалось загрузить задачи
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-600">
              Убедитесь что backend запущен на http://localhost:8000
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: Success
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* -----------------------------------------------------------------------
       * Заголовок
       * ----------------------------------------------------------------------- */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Задачи</h1>
          <p className="text-gray-500 mt-1">
            {filteredTasks.length} из {tasks?.length || 0} задач
          </p>
        </div>

        {/* Кнопка создания задачи */}
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>+ Новая задача</Button>
          </DialogTrigger>

          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Создать задачу</DialogTitle>
              <DialogDescription>
                Заполните информацию о новой задаче
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleCreateTask} className="space-y-4">
              {/* Название */}
              <div className="space-y-2">
                <Label htmlFor="title">Название *</Label>
                <Input
                  id="title"
                  value={newTask.title || ''}
                  onChange={(e) =>
                    setNewTask({ ...newTask, title: e.target.value })
                  }
                  placeholder="Что нужно сделать?"
                  required
                />
              </div>

              {/* Описание */}
              <div className="space-y-2">
                <Label htmlFor="description">Описание</Label>
                <Input
                  id="description"
                  value={newTask.description || ''}
                  onChange={(e) =>
                    setNewTask({ ...newTask, description: e.target.value })
                  }
                  placeholder="Дополнительные детали..."
                />
              </div>

              {/* Проект и Приоритет в одной строке */}
              <div className="grid grid-cols-2 gap-4">
                {/* Проект */}
                <div className="space-y-2">
                  <Label>Проект *</Label>
                  <Select
                    value={newTask.project_id?.toString() || ''}
                    onValueChange={(v) =>
                      setNewTask({ ...newTask, project_id: parseInt(v) })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите проект" />
                    </SelectTrigger>
                    <SelectContent>
                      {projects?.map((p) => (
                        <SelectItem key={p.id} value={p.id.toString()}>
                          {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Приоритет */}
                <div className="space-y-2">
                  <Label>Приоритет</Label>
                  <Select
                    value={newTask.priority || TaskPriority.MEDIUM}
                    onValueChange={(v) =>
                      setNewTask({ ...newTask, priority: v as TaskPriority })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={TaskPriority.HIGH}>Высокий</SelectItem>
                      <SelectItem value={TaskPriority.MEDIUM}>Средний</SelectItem>
                      <SelectItem value={TaskPriority.LOW}>Низкий</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Дедлайн */}
              <div className="space-y-2">
                <Label htmlFor="due_date">Дедлайн</Label>
                <Input
                  id="due_date"
                  type="date"
                  value={newTask.due_date || ''}
                  onChange={(e) =>
                    setNewTask({ ...newTask, due_date: e.target.value })
                  }
                />
              </div>

              {/* Кнопки */}
              <div className="flex justify-end gap-2 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Отмена
                </Button>
                <Button
                  type="submit"
                  disabled={createMutation.isPending || !newTask.project_id}
                >
                  {createMutation.isPending ? 'Создание...' : 'Создать'}
                </Button>
              </div>

              {createMutation.error && (
                <p className="text-red-500 text-sm">
                  Ошибка: {createMutation.error.message}
                </p>
              )}
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* -----------------------------------------------------------------------
       * Фильтры
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            {/* Поиск */}
            <Input
              placeholder="Поиск задач..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="max-w-xs"
            />

            {/* Фильтр по проекту */}
            <Select
              value={projectFilter || 'all'}
              onValueChange={handleProjectFilter}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Все проекты" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все проекты</SelectItem>
                {projects?.map((p) => (
                  <SelectItem key={p.id} value={p.id.toString()}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Фильтр по статусу */}
            <Select
              value={statusFilter || 'all'}
              onValueChange={handleStatusFilter}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Все статусы" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все статусы</SelectItem>
                <SelectItem value={TaskStatus.TODO}>К выполнению</SelectItem>
                <SelectItem value={TaskStatus.IN_PROGRESS}>В работе</SelectItem>
                <SelectItem value={TaskStatus.DONE}>Выполнено</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * Список задач
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>
            {projectFilter && projects
              ? `Задачи: ${projects.find((p) => p.id === parseInt(projectFilter))?.name}`
              : 'Все задачи'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredTasks.length === 0 ? (
            // Пустое состояние
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-lg">Нет задач</p>
              <p className="text-sm mt-1">
                {searchQuery || statusFilter
                  ? 'Попробуйте изменить фильтры'
                  : 'Создайте первую задачу нажав кнопку выше'}
              </p>
            </div>
          ) : (
            // Список задач
            <div className="space-y-2">
              {filteredTasks.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  projects={projects || []}
                  onToggleComplete={() => handleToggleComplete(task)}
                  isUpdating={updateMutation.isPending}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// TaskRow — Строка задачи
// =============================================================================
interface TaskRowProps {
  task: Task;
  projects: { id: number; name: string; color: string | null }[];
  onToggleComplete: () => void;
  isUpdating: boolean;
}

function TaskRow({ task, projects, onToggleComplete, isUpdating }: TaskRowProps) {
  const isDone = task.status === TaskStatus.DONE;
  const overdue = isOverdue(task);
  const project = projects.find((p) => p.id === task.project_id);

  return (
    <div
      className={`
        flex items-center gap-4 p-4 rounded-lg border transition-colors
        ${isDone ? 'bg-muted/30 opacity-60' : 'hover:bg-muted/50'}
        ${overdue ? 'border-red-200 bg-red-50/50' : ''}
      `}
    >
      {/* Чекбокс */}
      <Checkbox
        checked={isDone}
        onCheckedChange={onToggleComplete}
        disabled={isUpdating}
        className="h-5 w-5"
      />

      {/* Основной контент */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {/* Название */}
          <p
            className={`font-medium truncate ${isDone ? 'line-through text-muted-foreground' : ''}`}
          >
            {task.title}
          </p>

          {/* Просрочено */}
          {overdue && (
            <Badge variant="destructive" className="text-xs">
              Просрочено
            </Badge>
          )}
        </div>

        {/* Мета информация */}
        <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
          {/* Проект */}
          {project && (
            <span className="flex items-center gap-1">
              {project.color && (
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: project.color }}
                />
              )}
              {project.name}
            </span>
          )}

          {/* Дедлайн */}
          {task.due_date && (
            <span className={overdue ? 'text-red-600' : ''}>
              Срок: {new Date(task.due_date).toLocaleDateString('ru-RU')}
            </span>
          )}

          {/* Теги */}
          {task.tags.length > 0 && (
            <div className="flex gap-1">
              {task.tags.slice(0, 3).map((tag) => (
                <Badge key={tag.id} variant="outline" className="text-xs">
                  {tag.name}
                </Badge>
              ))}
              {task.tags.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{task.tags.length - 3}
                </Badge>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Приоритет */}
      <Badge className={`${getPriorityColor(task.priority)} border`}>
        {getPriorityLabel(task.priority)}
      </Badge>

      {/* Статус (если не done) */}
      {!isDone && task.status !== TaskStatus.TODO && (
        <Badge variant="secondary">{getStatusLabel(task.status)}</Badge>
      )}
    </div>
  );
}

export default Tasks;
