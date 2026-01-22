// =============================================================================
// Dashboard Page — Главная страница со статистикой
// =============================================================================
// Эта страница показывает общую картину:
//   - Сколько всего задач и проектов
//   - Сколько задач просрочено
//   - Последние активности
//   - Быстрые действия
//
// Роут: / (корневой)
// =============================================================================

// -----------------------------------------------------------------------------
// Импорты компонентов shadcn/ui
// -----------------------------------------------------------------------------
// Card — контейнер для группировки контента с тенью и скруглением
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

// -----------------------------------------------------------------------------
// Компонент Dashboard
// -----------------------------------------------------------------------------
// Пока это placeholder — потом добавим реальные данные из API
// -----------------------------------------------------------------------------
export function Dashboard() {
  return (
    <div className="space-y-6">
      {/* -----------------------------------------------------------------------
       * Заголовок страницы
       * ----------------------------------------------------------------------- */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Обзор ваших задач и проектов
        </p>
      </div>

      {/* -----------------------------------------------------------------------
       * Карточки статистики
       * grid — CSS Grid layout
       * grid-cols-1 — 1 колонка на мобильных
       * md:grid-cols-2 — 2 колонки на планшетах (≥768px)
       * lg:grid-cols-4 — 4 колонки на десктопах (≥1024px)
       * ----------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Карточка: Всего задач */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Всего задач</CardDescription>
            <CardTitle className="text-4xl">--</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Загрузка...
            </p>
          </CardContent>
        </Card>

        {/* Карточка: Выполнено */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Выполнено</CardDescription>
            <CardTitle className="text-4xl text-green-600">--</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Загрузка...
            </p>
          </CardContent>
        </Card>

        {/* Карточка: В работе */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>В работе</CardDescription>
            <CardTitle className="text-4xl text-blue-600">--</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Загрузка...
            </p>
          </CardContent>
        </Card>

        {/* Карточка: Просрочено */}
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Просрочено</CardDescription>
            <CardTitle className="text-4xl text-red-600">--</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Загрузка...
            </p>
          </CardContent>
        </Card>
      </div>

      {/* -----------------------------------------------------------------------
       * Секция: Просроченные задачи
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Просроченные задачи</CardTitle>
          <CardDescription>
            Задачи которые нужно выполнить в первую очередь
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            Данные загружаются...
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Экспорт по умолчанию
// -----------------------------------------------------------------------------
// В React принято экспортировать компоненты как named export (export function X)
// и как default export для удобства импорта в роутере
// -----------------------------------------------------------------------------
export default Dashboard;
