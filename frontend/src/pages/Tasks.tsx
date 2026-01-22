// =============================================================================
// Tasks Page — Страница списка задач
// =============================================================================
// Эта страница показывает:
//   - Все задачи (или задачи конкретного проекта)
//   - Фильтры по статусу, приоритету, проекту
//   - Возможность создать/редактировать/удалить задачу
//   - Быстрое переключение статуса (чекбокс)
//
// Роуты:
//   /tasks — все задачи
//   /projects/:projectId/tasks — задачи проекта (будет позже)
// =============================================================================

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';

// -----------------------------------------------------------------------------
// Компонент Tasks
// -----------------------------------------------------------------------------
export function Tasks() {
  return (
    <div className="space-y-6">
      {/* -----------------------------------------------------------------------
       * Заголовок с кнопкой создания
       * ----------------------------------------------------------------------- */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Задачи</h1>
          <p className="text-gray-500 mt-1">
            Управление задачами
          </p>
        </div>

        <Button>
          + Новая задача
        </Button>
      </div>

      {/* -----------------------------------------------------------------------
       * Фильтры и поиск
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            {/* Поиск */}
            <Input
              placeholder="Поиск задач..."
              className="max-w-sm"
            />

            {/* Фильтры — потом добавим Select компоненты */}
            <div className="flex gap-2">
              <Badge variant="outline" className="cursor-pointer hover:bg-primary/10">
                Все
              </Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-primary/10">
                Активные
              </Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-primary/10">
                Выполненные
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * Список задач
       * Каждая задача — строка с чекбоксом, названием, тегами, датой
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Список задач</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Placeholder задачи — потом заменим на реальные данные */}
          <div className="space-y-2">
            {/* Пример задачи */}
            <div className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted/50 transition-colors">
              <Checkbox />
              <div className="flex-1">
                <p className="font-medium">Загрузка задач...</p>
                <p className="text-sm text-muted-foreground">
                  Данные загружаются из API
                </p>
              </div>
              <Badge>Загрузка</Badge>
            </div>

            {/* Пустое состояние */}
            <div className="text-center py-8 text-muted-foreground">
              <p>Нет задач для отображения</p>
              <p className="text-sm">Создайте первую задачу нажав кнопку выше</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default Tasks;
