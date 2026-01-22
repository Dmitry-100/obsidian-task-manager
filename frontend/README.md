# Obsidian Task Manager — Frontend

Web Dashboard для управления задачами, построенный на React + TypeScript.

## Технологии

| Технология | Назначение |
|------------|------------|
| **React 18** | UI библиотека |
| **TypeScript** | Статическая типизация |
| **Vite** | Сборщик (dev server + production build) |
| **TailwindCSS** | Utility-first CSS фреймворк |
| **shadcn/ui** | Библиотека UI компонентов |
| **TanStack Query** | Управление серверным состоянием |
| **React Router** | Клиентская навигация |

## Быстрый старт

```bash
# Установить зависимости
npm install

# Настроить переменные окружения
cp .env.example .env.local
# Отредактировать .env.local

# Запустить dev сервер
npm run dev

# Открыть в браузере
open http://localhost:5173
```

## Переменные окружения

```bash
# .env.local
VITE_API_URL=http://localhost:8000   # URL backend сервера
VITE_API_KEY=dev-api-key-change-in-production  # API ключ
```

## Страницы

| Страница | URL | Описание |
|----------|-----|----------|
| **Dashboard** | `/` | Статистика, просроченные задачи, активные проекты |
| **Projects** | `/projects` | Список проектов, создание/редактирование/удаление |
| **Tasks** | `/tasks` | Список задач с фильтрами, CRUD операции |
| **Settings** | `/settings` | Настройки API подключения |

## Структура проекта

```
frontend/
├── src/
│   ├── api/                 # API клиент и функции
│   │   ├── client.ts       # Базовый fetch wrapper
│   │   ├── projects.ts     # CRUD проектов
│   │   ├── tasks.ts        # CRUD задач
│   │   └── tags.ts         # CRUD тегов
│   │
│   ├── components/
│   │   ├── ui/             # shadcn/ui компоненты
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── ...
│   │   └── layout/
│   │       └── Layout.tsx  # Общий layout с навигацией
│   │
│   ├── hooks/              # React Query хуки
│   │   ├── useProjects.ts
│   │   ├── useTasks.ts
│   │   └── index.ts
│   │
│   ├── pages/              # Страницы приложения
│   │   ├── Dashboard.tsx   # Главная со статистикой
│   │   ├── Projects.tsx    # Управление проектами
│   │   ├── Tasks.tsx       # Управление задачами
│   │   └── Settings.tsx    # Настройки
│   │
│   ├── types/              # TypeScript типы
│   │   └── index.ts        # Все типы (Task, Project, Tag, etc.)
│   │
│   ├── lib/
│   │   └── utils.ts        # Утилиты (cn для классов)
│   │
│   ├── App.tsx             # Корневой компонент + Router
│   ├── main.tsx            # Точка входа
│   └── index.css           # Tailwind директивы
│
├── index.html              # HTML template
├── vite.config.ts          # Vite конфигурация
├── tailwind.config.js      # Tailwind конфигурация
├── tsconfig.json           # TypeScript конфигурация
└── package.json            # Зависимости
```

## Команды

```bash
npm run dev      # Запуск dev сервера с hot reload
npm run build    # Production сборка в dist/
npm run preview  # Предпросмотр production сборки
npm run lint     # Проверка ESLint
```

## Функциональность

### Dashboard
- 5 карточек статистики (всего, выполнено, в работе, ожидают, просрочено)
- Список просроченных задач с возможностью отметить выполненной
- Активные проекты с прогресс-барами

### Projects
- Список проектов в виде карточек
- Создание нового проекта (диалог)
- Редактирование проекта (диалог)
- Удаление проекта (подтверждение)
- Цветовой индикатор проекта

### Tasks
- Список задач с фильтрами:
  - По проекту (Select)
  - По статусу (todo, in_progress, done)
  - Поиск по названию
- URL-based фильтрация (`/tasks?project=1&status=done`)
- Создание задачи (диалог)
- Редактирование задачи (диалог)
- Удаление задачи (подтверждение)
- Toggle статуса (checkbox)
- Отображение просроченных задач

### Settings
- Настройки API (URL, ключ)
- Проверка подключения
- Информация о приложении

## API Integration

### React Query хуки

```typescript
// Получение списка
const { data: tasks, isLoading, error } = useTasks();
const { data: projects } = useProjects();

// Мутации
const createMutation = useCreateTask();
createMutation.mutate({ title: 'New Task', project_id: 1 });

const updateMutation = useUpdateTask();
updateMutation.mutate({ id: 1, data: { status: 'done' } });

const deleteMutation = useDeleteTask();
deleteMutation.mutate(taskId);
```

### API клиент

```typescript
import { api } from '@/api';

// GET /projects
const projects = await api.get<Project[]>('/projects');

// POST /tasks
const task = await api.post<Task>('/tasks', { title: 'New', project_id: 1 });

// PUT /tasks/1
const updated = await api.put<Task>('/tasks/1', { status: 'done' });

// DELETE /tasks/1
await api.delete('/tasks/1');
```

## Стилизация

### TailwindCSS классы

```tsx
// Responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

// Условные стили
<div className={cn(
  'p-4 rounded-lg',
  isActive && 'bg-blue-100',
  isError && 'border-red-500'
)}>

// Hover эффекты
<div className="opacity-0 group-hover:opacity-100 transition-opacity">
```

### shadcn/ui компоненты

```tsx
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Dialog, DialogTrigger, DialogContent } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectContent, SelectItem } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
```

## Production Build

```bash
# Сборка
npm run build

# Результат в dist/
dist/
├── index.html
└── assets/
    ├── index-xxx.css   # ~27 KB (gzip: ~6 KB)
    └── index-xxx.js    # ~428 KB (gzip: ~136 KB)
```

## Требования

- Node.js 18+
- npm 9+
- Backend сервер на http://localhost:8000
