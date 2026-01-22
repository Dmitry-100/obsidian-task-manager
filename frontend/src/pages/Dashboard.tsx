// =============================================================================
// Dashboard Page — Главная страница со статистикой
// =============================================================================
// Эта страница показывает общую картину:
//   - Сколько всего задач и проектов
//   - Сколько задач просрочено
//   - Список просроченных задач
//   - Быстрые действия
//
// Роут: / (корневой)
// =============================================================================

import { useMemo } from 'react';
import { Link } from 'react-router-dom';

// -----------------------------------------------------------------------------
// Импорты компонентов shadcn/ui
// -----------------------------------------------------------------------------
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';

// -----------------------------------------------------------------------------
// Импорты хуков и типов
// -----------------------------------------------------------------------------
import { useTasks, useProjects, useToggleTaskComplete } from '@/hooks';
import { TaskStatus, TaskPriority } from '@/types';
import type { Task } from '@/types';

// =============================================================================
// Компонент StatCard — карточка статистики
// =============================================================================
// Вынесен отдельно для переиспользования и чистоты кода
// =============================================================================

interface StatCardProps {
  title: string;
  value: number | string;
  description: string;
  // Цвет значения: text-green-600, text-blue-600, text-red-600
  valueClassName?: string;
  isLoading?: boolean;
}

function StatCard({ title, value, description, valueClassName = '', isLoading = false }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className={`text-4xl ${valueClassName}`}>
          {isLoading ? '--' : value}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">
          {isLoading ? 'Загрузка...' : description}
        </p>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Компонент OverdueTaskRow — строка просроченной задачи
// =============================================================================
// Показывает задачу с возможностью отметить выполненной
// =============================================================================

interface OverdueTaskRowProps {
  task: Task;
  projectName: string;
  onToggleComplete: (id: number, completed: boolean) => void;
}

function OverdueTaskRow({ task, projectName, onToggleComplete }: OverdueTaskRowProps) {
  // Вычисляем сколько дней просрочено
  const daysOverdue = useMemo(() => {
    if (!task.due_date) return 0;
    const due = new Date(task.due_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    due.setHours(0, 0, 0, 0);
    return Math.floor((today.getTime() - due.getTime()) / (1000 * 60 * 60 * 24));
  }, [task.due_date]);

  // Цвет приоритета
  const priorityColors: Record<string, string> = {
    [TaskPriority.HIGH]: 'bg-red-100 text-red-800 border-red-200',
    [TaskPriority.MEDIUM]: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    [TaskPriority.LOW]: 'bg-green-100 text-green-800 border-green-200',
  };

  return (
    <div className="flex items-center gap-3 p-3 border-b last:border-b-0 hover:bg-gray-50">
      {/* Checkbox для отметки выполнения */}
      <Checkbox
        checked={task.status === TaskStatus.DONE}
        onCheckedChange={(checked) => onToggleComplete(task.id, checked as boolean)}
      />

      {/* Информация о задаче */}
      <div className="flex-1 min-w-0">
        {/* Заголовок задачи */}
        <Link
          to={`/tasks?project=${task.project_id}`}
          className="font-medium text-gray-900 hover:text-blue-600 truncate block"
        >
          {task.title}
        </Link>

        {/* Метаданные: проект, дата */}
        <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
          <span>{projectName}</span>
          <span>•</span>
          <span className="text-red-600 font-medium">
            Просрочено на {daysOverdue} {daysOverdue === 1 ? 'день' : daysOverdue < 5 ? 'дня' : 'дней'}
          </span>
        </div>
      </div>

      {/* Приоритет */}
      <Badge
        variant="outline"
        className={priorityColors[task.priority] || 'bg-gray-100 text-gray-800 border-gray-200'}
      >
        {task.priority}
      </Badge>
    </div>
  );
}

// =============================================================================
// Главный компонент Dashboard
// =============================================================================

export function Dashboard() {
  // ---------------------------------------------------------------------------
  // Загрузка данных
  // ---------------------------------------------------------------------------
  // useTasks() — загружает все задачи
  // useProjects() — загружает все проекты (для отображения имён)
  // ---------------------------------------------------------------------------
  const { data: tasks = [], isLoading: tasksLoading, error: tasksError } = useTasks();
  const { data: projects = [], isLoading: projectsLoading } = useProjects();
  const toggleComplete = useToggleTaskComplete();

  // Общий статус загрузки
  const isLoading = tasksLoading || projectsLoading;

  // ---------------------------------------------------------------------------
  // Вычисление статистики
  // ---------------------------------------------------------------------------
  // useMemo — кэширует результат вычислений пока tasks не изменятся
  // ---------------------------------------------------------------------------
  const stats = useMemo(() => {
    const total = tasks.length;

    // Выполненные задачи
    const completed = tasks.filter((t) => t.status === TaskStatus.DONE).length;

    // Задачи в работе
    const inProgress = tasks.filter((t) => t.status === TaskStatus.IN_PROGRESS).length;

    // Просроченные задачи (due_date < today И статус не done/cancelled)
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const overdueTasks = tasks.filter((t) => {
      if (!t.due_date) return false;
      if (t.status === TaskStatus.DONE || t.status === TaskStatus.CANCELLED) return false;
      const dueDate = new Date(t.due_date);
      dueDate.setHours(0, 0, 0, 0);
      return dueDate < today;
    });

    // Ожидающие задачи (todo)
    const todo = tasks.filter((t) => t.status === TaskStatus.TODO).length;

    return {
      total,
      completed,
      inProgress,
      todo,
      overdue: overdueTasks.length,
      overdueTasks,
    };
  }, [tasks]);

  // ---------------------------------------------------------------------------
  // Создаём map проектов для быстрого поиска имени по ID
  // ---------------------------------------------------------------------------
  const projectsMap = useMemo(() => {
    const map = new Map<number, string>();
    projects.forEach((p) => map.set(p.id, p.name));
    return map;
  }, [projects]);

  // ---------------------------------------------------------------------------
  // Обработчик переключения статуса задачи
  // ---------------------------------------------------------------------------
  const handleToggleComplete = (id: number, completed: boolean) => {
    toggleComplete.mutate({ id, completed });
  };

  // ---------------------------------------------------------------------------
  // Обработка ошибок
  // ---------------------------------------------------------------------------
  if (tasksError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        </div>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-600">
              Ошибка загрузки данных: {tasksError.message}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Убедитесь что backend сервер запущен на http://localhost:8000
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Рендер
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Заголовок страницы */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">
            Обзор ваших задач и проектов
          </p>
        </div>

        {/* Быстрые действия */}
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/projects">Все проекты</Link>
          </Button>
          <Button asChild>
            <Link to="/tasks">Все задачи</Link>
          </Button>
        </div>
      </div>

      {/* -----------------------------------------------------------------------
       * Карточки статистики
       * grid — CSS Grid layout
       * grid-cols-1 — 1 колонка на мобильных
       * md:grid-cols-2 — 2 колонки на планшетах (≥768px)
       * lg:grid-cols-5 — 5 колонок на десктопах (≥1024px)
       * ----------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Всего задач */}
        <StatCard
          title="Всего задач"
          value={stats.total}
          description={`${projects.length} проектов`}
          isLoading={isLoading}
        />

        {/* Выполнено */}
        <StatCard
          title="Выполнено"
          value={stats.completed}
          description={stats.total > 0 ? `${Math.round((stats.completed / stats.total) * 100)}% от всех` : '—'}
          valueClassName="text-green-600"
          isLoading={isLoading}
        />

        {/* В работе */}
        <StatCard
          title="В работе"
          value={stats.inProgress}
          description="Активные задачи"
          valueClassName="text-blue-600"
          isLoading={isLoading}
        />

        {/* Ожидают */}
        <StatCard
          title="Ожидают"
          value={stats.todo}
          description="Нужно начать"
          valueClassName="text-gray-600"
          isLoading={isLoading}
        />

        {/* Просрочено */}
        <StatCard
          title="Просрочено"
          value={stats.overdue}
          description={stats.overdue > 0 ? 'Требуют внимания!' : 'Всё в порядке'}
          valueClassName={stats.overdue > 0 ? 'text-red-600' : 'text-green-600'}
          isLoading={isLoading}
        />
      </div>

      {/* -----------------------------------------------------------------------
       * Секция: Просроченные задачи
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Просроченные задачи
            {stats.overdue > 0 && (
              <Badge variant="destructive">{stats.overdue}</Badge>
            )}
          </CardTitle>
          <CardDescription>
            Задачи которые нужно выполнить в первую очередь
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            // Скелетон загрузки
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          ) : stats.overdueTasks.length === 0 ? (
            // Нет просроченных задач
            <div className="text-center py-8">
              <p className="text-2xl mb-2">🎉</p>
              <p className="text-muted-foreground">
                Нет просроченных задач — отличная работа!
              </p>
            </div>
          ) : (
            // Список просроченных задач
            <div className="divide-y">
              {stats.overdueTasks
                .sort((a, b) => {
                  // Сортируем по дате (самые старые сверху)
                  const dateA = a.due_date ? new Date(a.due_date).getTime() : 0;
                  const dateB = b.due_date ? new Date(b.due_date).getTime() : 0;
                  return dateA - dateB;
                })
                .map((task) => (
                  <OverdueTaskRow
                    key={task.id}
                    task={task}
                    projectName={projectsMap.get(task.project_id) || 'Неизвестный проект'}
                    onToggleComplete={handleToggleComplete}
                  />
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * Секция: Недавние проекты
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Активные проекты</CardTitle>
          <CardDescription>
            Проекты над которыми вы работаете
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-24 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          ) : projects.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">
                У вас пока нет проектов
              </p>
              <Button asChild>
                <Link to="/projects">Создать первый проект</Link>
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects
                .filter((p) => !p.is_archived)
                .slice(0, 6) // Показываем максимум 6 проектов
                .map((project) => {
                  // Считаем статистику по задачам проекта
                  const projectTasks = tasks.filter((t) => t.project_id === project.id);
                  const completedTasks = projectTasks.filter((t) => t.status === TaskStatus.DONE).length;
                  const totalTasks = projectTasks.length;
                  const progress = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

                  return (
                    <Link
                      key={project.id}
                      to={`/tasks?project=${project.id}`}
                      className="block p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <h3 className="font-medium text-gray-900 truncate">
                        {project.name}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {completedTasks} / {totalTasks} задач выполнено
                      </p>
                      {/* Прогресс-бар */}
                      <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600 transition-all"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    </Link>
                  );
                })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Экспорт по умолчанию
// -----------------------------------------------------------------------------
export default Dashboard;
