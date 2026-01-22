// =============================================================================
// Sync Page — Страница синхронизации с Obsidian
// =============================================================================
// Позволяет:
//   - Импортировать задачи из Obsidian vault
//   - Экспортировать задачи в Obsidian
//   - Просматривать и разрешать конфликты
//   - Настраивать конфигурацию синхронизации
//
// Роут: /sync
// =============================================================================

import { useState } from 'react';

// UI компоненты
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// Хуки
import {
  useSyncStatus,
  useSyncConflicts,
  useSyncHistory,
  useSyncConfig,
  useImportFromObsidian,
  useExportToObsidian,
  useResolveConflict,
  useResolveAllConflicts,
} from '@/hooks';

// Типы
import type { SyncConflict, ConflictResolution } from '@/types';

// =============================================================================
// Компонент Sync
// =============================================================================
export function Sync() {
  // ---------------------------------------------------------------------------
  // Состояние
  // ---------------------------------------------------------------------------
  const [selectedConflict, setSelectedConflict] = useState<SyncConflict | null>(null);
  const [conflictDialogOpen, setConflictDialogOpen] = useState(false);

  // ---------------------------------------------------------------------------
  // Данные
  // ---------------------------------------------------------------------------
  const { data: status, isLoading: statusLoading } = useSyncStatus();
  const { data: conflicts = [], isLoading: conflictsLoading } = useSyncConflicts();
  const { data: history = [], isLoading: historyLoading } = useSyncHistory(5);
  const { data: config } = useSyncConfig();

  // ---------------------------------------------------------------------------
  // Мутации
  // ---------------------------------------------------------------------------
  const importMutation = useImportFromObsidian();
  const exportMutation = useExportToObsidian();
  const resolveMutation = useResolveConflict();
  const resolveAllMutation = useResolveAllConflicts();

  // ---------------------------------------------------------------------------
  // Обработчики
  // ---------------------------------------------------------------------------
  const handleImport = () => {
    importMutation.mutate({});
  };

  const handleExport = () => {
    exportMutation.mutate({});
  };

  const handleResolveConflict = (resolution: ConflictResolution) => {
    if (!selectedConflict) return;

    resolveMutation.mutate(
      { conflictId: selectedConflict.id, resolution },
      {
        onSuccess: () => {
          setConflictDialogOpen(false);
          setSelectedConflict(null);
        },
      }
    );
  };

  const handleResolveAll = (resolution: ConflictResolution) => {
    if (!status?.last_sync) return;

    resolveAllMutation.mutate({
      syncLogId: status.last_sync.id,
      resolution,
    });
  };

  const openConflictDialog = (conflict: SyncConflict) => {
    setSelectedConflict(conflict);
    setConflictDialogOpen(true);
  };

  // ---------------------------------------------------------------------------
  // Форматирование
  // ---------------------------------------------------------------------------
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('ru-RU');
  };

  const getStatusBadge = (statusStr: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      completed: 'default',
      in_progress: 'secondary',
      failed: 'destructive',
      pending: 'outline',
    };
    return <Badge variant={variants[statusStr] || 'outline'}>{statusStr}</Badge>;
  };

  // ---------------------------------------------------------------------------
  // Рендер
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Синхронизация</h1>
        <p className="text-gray-500 mt-1">
          Синхронизация задач с Obsidian vault
        </p>
      </div>

      {/* -----------------------------------------------------------------------
       * Статус синхронизации
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Статус</CardTitle>
          <CardDescription>
            Текущее состояние синхронизации
          </CardDescription>
        </CardHeader>
        <CardContent>
          {statusLoading ? (
            <p className="text-muted-foreground">Загрузка...</p>
          ) : status ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Синхронизация</p>
                <p className="font-medium">
                  {status.is_syncing ? (
                    <Badge variant="secondary">В процессе</Badge>
                  ) : (
                    <Badge variant="outline">Остановлена</Badge>
                  )}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Неразрешённых конфликтов</p>
                <p className="font-medium">
                  {status.unresolved_conflicts > 0 ? (
                    <Badge variant="destructive">{status.unresolved_conflicts}</Badge>
                  ) : (
                    <span className="text-green-600">0</span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Всего синхронизаций</p>
                <p className="font-medium">{status.total_syncs}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Последняя синхронизация</p>
                <p className="font-medium text-sm">
                  {status.last_sync ? formatDate(status.last_sync.completed_at) : 'Никогда'}
                </p>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * Кнопки действий
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Действия</CardTitle>
          <CardDescription>
            Запустить синхронизацию
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <Button
              onClick={handleImport}
              disabled={importMutation.isPending || status?.is_syncing}
            >
              {importMutation.isPending ? 'Импорт...' : 'Импорт из Obsidian'}
            </Button>
            <Button
              variant="outline"
              onClick={handleExport}
              disabled={exportMutation.isPending || status?.is_syncing}
            >
              {exportMutation.isPending ? 'Экспорт...' : 'Экспорт в Obsidian'}
            </Button>
          </div>

          {/* Результат последнего импорта */}
          {importMutation.data && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="font-medium mb-2">Результат импорта:</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                <div>Создано: <span className="font-medium text-green-600">{importMutation.data.tasks_created}</span></div>
                <div>Обновлено: <span className="font-medium text-blue-600">{importMutation.data.tasks_updated}</span></div>
                <div>Пропущено: <span className="font-medium text-gray-600">{importMutation.data.tasks_skipped}</span></div>
                <div>Конфликтов: <span className="font-medium text-orange-600">{importMutation.data.conflicts_count}</span></div>
              </div>
            </div>
          )}

          {importMutation.error && (
            <p className="text-red-600 text-sm">
              Ошибка: {(importMutation.error as Error).message}
            </p>
          )}
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * Конфликты
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Конфликты</CardTitle>
            <CardDescription>
              Задачи с различиями между Obsidian и базой данных
            </CardDescription>
          </div>
          {conflicts.length > 0 && (
            <div className="flex gap-2">
              <Select onValueChange={(v) => handleResolveAll(v as ConflictResolution)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Разрешить все" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="obsidian">Оставить Obsidian</SelectItem>
                  <SelectItem value="database">Оставить базу</SelectItem>
                  <SelectItem value="skip">Пропустить все</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {conflictsLoading ? (
            <p className="text-muted-foreground">Загрузка...</p>
          ) : conflicts.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">
              Нет неразрешённых конфликтов
            </p>
          ) : (
            <div className="space-y-2">
              {conflicts.map((conflict) => (
                <div
                  key={conflict.id}
                  className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer"
                  onClick={() => openConflictDialog(conflict)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{conflict.obsidian_title}</p>
                      <p className="text-sm text-muted-foreground">
                        {conflict.obsidian_path}:{conflict.obsidian_line}
                      </p>
                    </div>
                    <Badge variant="outline">
                      {conflict.resolution || 'Не разрешён'}
                    </Badge>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Obsidian:</span>{' '}
                      {conflict.obsidian_status} / {conflict.obsidian_priority}
                    </div>
                    <div>
                      <span className="text-muted-foreground">База:</span>{' '}
                      {conflict.db_status || '-'} / {conflict.db_priority || '-'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * История синхронизаций
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>История</CardTitle>
          <CardDescription>
            Последние операции синхронизации
          </CardDescription>
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <p className="text-muted-foreground">Загрузка...</p>
          ) : history.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">
              История пуста
            </p>
          ) : (
            <div className="space-y-2">
              {history.map((log) => (
                <div
                  key={log.id}
                  className="p-4 border rounded-lg"
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{log.sync_type}</Badge>
                      {getStatusBadge(log.status)}
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {formatDate(log.completed_at || log.started_at)}
                    </span>
                  </div>
                  <div className="mt-2 grid grid-cols-4 gap-2 text-sm">
                    <div>Создано: {log.tasks_created}</div>
                    <div>Обновлено: {log.tasks_updated}</div>
                    <div>Пропущено: {log.tasks_skipped}</div>
                    <div>Конфликтов: {log.conflicts_count}</div>
                  </div>
                  {log.error_message && (
                    <p className="mt-2 text-sm text-red-600">{log.error_message}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * Конфигурация (краткая информация)
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Конфигурация</CardTitle>
          <CardDescription>
            Настройки синхронизации
          </CardDescription>
        </CardHeader>
        <CardContent>
          {config ? (
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Путь к vault</p>
                <p className="font-mono text-sm">{config.vault_path || 'Не указан'}</p>
              </div>
              <hr className="my-4" />
              <div>
                <p className="text-sm text-muted-foreground mb-2">Источники для синхронизации</p>
                <div className="flex flex-wrap gap-2">
                  {config.sync_sources.map((source, i) => (
                    <Badge key={i} variant="outline">{source}</Badge>
                  ))}
                </div>
              </div>
              <hr className="my-4" />
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Проект по умолчанию</p>
                  <p className="font-medium">{config.default_project}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Разрешение конфликтов</p>
                  <p className="font-medium">{config.default_conflict_resolution}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">Загрузка...</p>
          )}
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * Диалог разрешения конфликта
       * ----------------------------------------------------------------------- */}
      <Dialog open={conflictDialogOpen} onOpenChange={setConflictDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Разрешение конфликта</DialogTitle>
            <DialogDescription>
              {selectedConflict?.obsidian_title}
            </DialogDescription>
          </DialogHeader>

          {selectedConflict && (
            <div className="grid grid-cols-2 gap-4 py-4">
              {/* Obsidian версия */}
              <div className="p-4 border rounded-lg bg-blue-50">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <span>Obsidian</span>
                  <Badge variant="outline" className="text-xs">Файл</Badge>
                </h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Статус:</span>{' '}
                    {selectedConflict.obsidian_status}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Приоритет:</span>{' '}
                    {selectedConflict.obsidian_priority}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Дедлайн:</span>{' '}
                    {selectedConflict.obsidian_due_date || '-'}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Изменено:</span>{' '}
                    {formatDate(selectedConflict.obsidian_modified)}
                  </div>
                </div>
              </div>

              {/* Database версия */}
              <div className="p-4 border rounded-lg bg-green-50">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <span>База данных</span>
                  <Badge variant="outline" className="text-xs">DB</Badge>
                </h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Статус:</span>{' '}
                    {selectedConflict.db_status || '-'}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Приоритет:</span>{' '}
                    {selectedConflict.db_priority || '-'}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Дедлайн:</span>{' '}
                    {selectedConflict.db_due_date || '-'}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Изменено:</span>{' '}
                    {formatDate(selectedConflict.db_modified)}
                  </div>
                </div>
              </div>
            </div>
          )}

          <DialogFooter className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => handleResolveConflict('skip')}
              disabled={resolveMutation.isPending}
            >
              Пропустить
            </Button>
            <Button
              variant="outline"
              onClick={() => handleResolveConflict('database')}
              disabled={resolveMutation.isPending}
            >
              Оставить базу
            </Button>
            <Button
              onClick={() => handleResolveConflict('obsidian')}
              disabled={resolveMutation.isPending}
            >
              Оставить Obsidian
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default Sync;
