// =============================================================================
// Projects Page — Страница управления проектами
// =============================================================================
// Эта страница показывает список проектов и позволяет:
//   - Просматривать проекты в виде карточек
//   - Создавать новые проекты
//   - Редактировать существующие
//   - Архивировать/удалять
//
// Используемые хуки:
//   useProjects() — получение списка проектов
//   useCreateProject() — создание нового проекта
//
// Роут: /projects
// =============================================================================

import { useState } from 'react';
import { Link } from 'react-router-dom';

// UI компоненты
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
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

// Хуки для работы с данными
import { useProjects, useCreateProject, useUpdateProject, useDeleteProject } from '@/hooks';

// Типы
import type { Project, ProjectCreate, ProjectUpdate } from '@/types';

// =============================================================================
// Компонент Projects
// =============================================================================
export function Projects() {
  // ---------------------------------------------------------------------------
  // State (локальное состояние)
  // ---------------------------------------------------------------------------
  // Состояние для модалки создания проекта
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  // Данные формы создания
  const [newProject, setNewProject] = useState<ProjectCreate>({
    name: '',
    description: '',
    color: '#3B82F6', // Синий по умолчанию
  });

  // Состояние для редактирования
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [editForm, setEditForm] = useState<ProjectUpdate>({});

  // Состояние для удаления
  const [deletingProject, setDeletingProject] = useState<Project | null>(null);

  // ---------------------------------------------------------------------------
  // Hooks (React Query)
  // ---------------------------------------------------------------------------
  // useProjects() возвращает объект с:
  //   - data: Project[] — данные (undefined пока загружается)
  //   - isLoading: boolean — идёт загрузка
  //   - error: Error | null — ошибка если есть
  //   - refetch: () => void — функция для повторного запроса
  const { data: projects, isLoading, error } = useProjects();

  // useCreateProject() возвращает mutation объект с:
  //   - mutate: (data) => void — функция для выполнения мутации
  //   - isPending: boolean — мутация выполняется
  //   - error: Error | null — ошибка
  const createMutation = useCreateProject();
  const updateMutation = useUpdateProject();
  const deleteMutation = useDeleteProject();

  // ---------------------------------------------------------------------------
  // Handlers (обработчики событий)
  // ---------------------------------------------------------------------------
  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault(); // Предотвращаем стандартную отправку формы

    // Выполняем мутацию
    createMutation.mutate(newProject, {
      onSuccess: () => {
        // Успех — закрываем модалку и сбрасываем форму
        setIsCreateDialogOpen(false);
        setNewProject({ name: '', description: '', color: '#3B82F6' });
      },
      // onError обрабатывается автоматически через React Query
    });
  };

  // Открытие диалога редактирования
  const handleEditClick = (project: Project, e: React.MouseEvent) => {
    e.preventDefault(); // Предотвращаем переход по ссылке
    e.stopPropagation();
    setEditingProject(project);
    setEditForm({
      name: project.name,
      description: project.description || '',
      color: project.color || '#3B82F6',
    });
  };

  // Сохранение изменений
  const handleUpdateProject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProject) return;

    updateMutation.mutate(
      { id: editingProject.id, data: editForm },
      {
        onSuccess: () => {
          setEditingProject(null);
          setEditForm({});
        },
      }
    );
  };

  // Открытие диалога удаления
  const handleDeleteClick = (project: Project, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDeletingProject(project);
  };

  // Подтверждение удаления
  const handleConfirmDelete = () => {
    if (!deletingProject) return;

    deleteMutation.mutate(deletingProject.id, {
      onSuccess: () => {
        setDeletingProject(null);
      },
    });
  };

  // ---------------------------------------------------------------------------
  // Render: Loading state
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Проекты</h1>
          <p className="text-gray-500 mt-1">Загрузка...</p>
        </div>

        {/* Skeleton карточки */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-6 bg-gray-200 rounded w-3/4" />
                <div className="h-4 bg-gray-200 rounded w-1/2 mt-2" />
              </CardHeader>
              <CardContent>
                <div className="h-4 bg-gray-200 rounded w-1/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: Error state
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Проекты</h1>
          <p className="text-red-500 mt-1">Ошибка загрузки: {error.message}</p>
        </div>

        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-800">Не удалось загрузить проекты</CardTitle>
            <CardDescription className="text-red-600">
              Убедитесь что backend запущен на http://localhost:8000
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: Success state
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* -----------------------------------------------------------------------
       * Заголовок с кнопкой создания
       * ----------------------------------------------------------------------- */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Проекты</h1>
          <p className="text-gray-500 mt-1">
            {projects?.length || 0} проектов
          </p>
        </div>

        {/* Кнопка открытия модалки создания */}
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>+ Новый проект</Button>
          </DialogTrigger>

          <DialogContent>
            <DialogHeader>
              <DialogTitle>Создать проект</DialogTitle>
              <DialogDescription>
                Проект — это контейнер для группировки связанных задач.
              </DialogDescription>
            </DialogHeader>

            {/* Форма создания проекта */}
            <form onSubmit={handleCreateProject} className="space-y-4">
              {/* Название */}
              <div className="space-y-2">
                <Label htmlFor="name">Название *</Label>
                <Input
                  id="name"
                  value={newProject.name}
                  onChange={(e) =>
                    setNewProject({ ...newProject, name: e.target.value })
                  }
                  placeholder="Мой проект"
                  required
                />
              </div>

              {/* Описание */}
              <div className="space-y-2">
                <Label htmlFor="description">Описание</Label>
                <Input
                  id="description"
                  value={newProject.description || ''}
                  onChange={(e) =>
                    setNewProject({ ...newProject, description: e.target.value })
                  }
                  placeholder="Краткое описание проекта"
                />
              </div>

              {/* Цвет */}
              <div className="space-y-2">
                <Label htmlFor="color">Цвет</Label>
                <div className="flex gap-2">
                  <Input
                    id="color"
                    type="color"
                    value={newProject.color || '#3B82F6'}
                    onChange={(e) =>
                      setNewProject({ ...newProject, color: e.target.value })
                    }
                    className="w-16 h-10 p-1"
                  />
                  <Input
                    value={newProject.color || '#3B82F6'}
                    onChange={(e) =>
                      setNewProject({ ...newProject, color: e.target.value })
                    }
                    placeholder="#3B82F6"
                    className="flex-1"
                  />
                </div>
              </div>

              {/* Кнопка отправки */}
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Отмена
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Создание...' : 'Создать'}
                </Button>
              </div>

              {/* Ошибка мутации */}
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
       * Диалог редактирования проекта
       * ----------------------------------------------------------------------- */}
      <Dialog open={!!editingProject} onOpenChange={(open) => !open && setEditingProject(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Редактировать проект</DialogTitle>
            <DialogDescription>
              Измените данные проекта
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleUpdateProject} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Название *</Label>
              <Input
                id="edit-name"
                value={editForm.name || ''}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-description">Описание</Label>
              <Input
                id="edit-description"
                value={editForm.description || ''}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-color">Цвет</Label>
              <div className="flex gap-2">
                <Input
                  id="edit-color"
                  type="color"
                  value={editForm.color || '#3B82F6'}
                  onChange={(e) => setEditForm({ ...editForm, color: e.target.value })}
                  className="w-16 h-10 p-1"
                />
                <Input
                  value={editForm.color || '#3B82F6'}
                  onChange={(e) => setEditForm({ ...editForm, color: e.target.value })}
                  className="flex-1"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setEditingProject(null)}>
                Отмена
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? 'Сохранение...' : 'Сохранить'}
              </Button>
            </div>

            {updateMutation.error && (
              <p className="text-red-500 text-sm">Ошибка: {updateMutation.error.message}</p>
            )}
          </form>
        </DialogContent>
      </Dialog>

      {/* -----------------------------------------------------------------------
       * Диалог подтверждения удаления
       * ----------------------------------------------------------------------- */}
      <Dialog open={!!deletingProject} onOpenChange={(open) => !open && setDeletingProject(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить проект?</DialogTitle>
            <DialogDescription>
              Вы уверены что хотите удалить проект "{deletingProject?.name}"?
              Это действие нельзя отменить. Все задачи проекта также будут удалены.
            </DialogDescription>
          </DialogHeader>

          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setDeletingProject(null)}>
              Отмена
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Удаление...' : 'Удалить'}
            </Button>
          </div>

          {deleteMutation.error && (
            <p className="text-red-500 text-sm mt-2">Ошибка: {deleteMutation.error.message}</p>
          )}
        </DialogContent>
      </Dialog>

      {/* -----------------------------------------------------------------------
       * Сетка проектов
       * ----------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Карточки существующих проектов */}
        {projects?.map((project: Project) => (
          <ProjectCard
            key={project.id}
            project={project}
            onEdit={handleEditClick}
            onDelete={handleDeleteClick}
          />
        ))}

        {/* Карточка "Создать проект" — всегда последняя */}
        <Card
          className="border-dashed hover:border-primary/50 hover:bg-primary/5 transition-colors cursor-pointer"
          onClick={() => setIsCreateDialogOpen(true)}
        >
          <CardHeader className="text-center py-12">
            <CardTitle className="text-muted-foreground text-lg">
              + Создать проект
            </CardTitle>
            <CardDescription>
              Нажмите чтобы добавить новый проект
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    </div>
  );
}

// =============================================================================
// ProjectCard — Компонент карточки проекта
// =============================================================================
interface ProjectCardProps {
  project: Project;
  onEdit: (project: Project, e: React.MouseEvent) => void;
  onDelete: (project: Project, e: React.MouseEvent) => void;
}

function ProjectCard({ project, onEdit, onDelete }: ProjectCardProps) {
  return (
    <Link to={`/tasks?project=${project.id}`}>
      <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full group">
        <CardHeader>
          <div className="flex justify-between items-start">
            {/* Цветовой индикатор */}
            {project.color && (
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: project.color }}
              />
            )}

            {/* Кнопки действий (видны при наведении) */}
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={(e) => onEdit(project, e)}
              >
                ✏️
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 hover:bg-red-100"
                onClick={(e) => onDelete(project, e)}
              >
                🗑️
              </Button>
            </div>
          </div>

          <CardTitle className="line-clamp-1">{project.name}</CardTitle>

          {project.description && (
            <CardDescription className="line-clamp-2">
              {project.description}
            </CardDescription>
          )}
        </CardHeader>

        <CardContent>
          <div className="text-sm text-muted-foreground">
            Создан: {new Date(project.created_at).toLocaleDateString('ru-RU')}
          </div>

          {project.is_archived && (
            <span className="inline-block mt-2 px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
              Архив
            </span>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

export default Projects;
