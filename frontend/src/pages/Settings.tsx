// =============================================================================
// Settings Page — Страница настроек
// =============================================================================
// Позволяет управлять настройками приложения:
//   - Подключение к API (URL, ключ)
//   - Информация о приложении
//   - Будущее: тема, уведомления
//
// Роут: /settings
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';

// =============================================================================
// Компонент Settings
// =============================================================================
export function Settings() {
  // ---------------------------------------------------------------------------
  // Состояние настроек
  // ---------------------------------------------------------------------------
  // В реальном приложении эти значения брались бы из localStorage или контекста
  const [apiUrl, setApiUrl] = useState(
    import.meta.env.VITE_API_URL || 'http://localhost:8000'
  );
  const [apiKey, setApiKey] = useState(
    import.meta.env.VITE_API_KEY || ''
  );
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Обработчик сохранения
  // ---------------------------------------------------------------------------
  const handleSave = async () => {
    setIsSaving(true);
    setSaveMessage(null);

    // Имитация сохранения (в реальности сохраняли бы в localStorage)
    await new Promise((resolve) => setTimeout(resolve, 500));

    // Сохраняем в localStorage для использования в следующих сессиях
    localStorage.setItem('api_url', apiUrl);
    localStorage.setItem('api_key', apiKey);

    setSaveMessage('Настройки сохранены! Перезагрузите страницу для применения.');
    setIsSaving(false);
  };

  // ---------------------------------------------------------------------------
  // Проверка подключения к API
  // ---------------------------------------------------------------------------
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'checking' | 'success' | 'error'>('idle');

  const handleTestConnection = async () => {
    setConnectionStatus('checking');

    try {
      const response = await fetch(apiUrl, {
        headers: {
          'X-API-Key': apiKey,
        },
      });

      if (response.ok) {
        setConnectionStatus('success');
      } else {
        setConnectionStatus('error');
      }
    } catch {
      setConnectionStatus('error');
    }

    // Сбросить статус через 3 секунды
    setTimeout(() => setConnectionStatus('idle'), 3000);
  };

  // ---------------------------------------------------------------------------
  // Рендер
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Настройки</h1>
        <p className="text-gray-500 mt-1">
          Управление конфигурацией приложения
        </p>
      </div>

      {/* -----------------------------------------------------------------------
       * Настройки API
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>Подключение к API</CardTitle>
          <CardDescription>
            Настройки подключения к backend серверу
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* API URL */}
          <div className="space-y-2">
            <Label htmlFor="api-url">URL сервера</Label>
            <Input
              id="api-url"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="http://localhost:8000"
            />
            <p className="text-xs text-muted-foreground">
              Адрес FastAPI backend сервера
            </p>
          </div>

          {/* API Key */}
          <div className="space-y-2">
            <Label htmlFor="api-key">API ключ</Label>
            <Input
              id="api-key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Введите API ключ"
            />
            <p className="text-xs text-muted-foreground">
              Ключ для авторизации запросов (X-API-Key)
            </p>
          </div>

          {/* Кнопки */}
          <div className="flex gap-2 pt-4">
            <Button onClick={handleTestConnection} variant="outline" disabled={connectionStatus === 'checking'}>
              {connectionStatus === 'checking' ? 'Проверка...' : 'Проверить подключение'}
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? 'Сохранение...' : 'Сохранить'}
            </Button>
          </div>

          {/* Статус подключения */}
          {connectionStatus === 'success' && (
            <p className="text-green-600 text-sm">Подключение успешно!</p>
          )}
          {connectionStatus === 'error' && (
            <p className="text-red-600 text-sm">Ошибка подключения. Проверьте URL и API ключ.</p>
          )}

          {/* Сообщение о сохранении */}
          {saveMessage && (
            <p className="text-blue-600 text-sm">{saveMessage}</p>
          )}
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * Информация о приложении
       * ----------------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle>О приложении</CardTitle>
          <CardDescription>
            Obsidian Task Manager — веб-интерфейс для управления задачами
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Версия</p>
              <p className="font-medium">1.0.0</p>
            </div>
            <div>
              <p className="text-muted-foreground">Frontend</p>
              <p className="font-medium">React + TypeScript + Vite</p>
            </div>
            <div>
              <p className="text-muted-foreground">Backend</p>
              <p className="font-medium">FastAPI + SQLAlchemy</p>
            </div>
            <div>
              <p className="text-muted-foreground">UI</p>
              <p className="font-medium">TailwindCSS + shadcn/ui</p>
            </div>
          </div>

          {/* Технологии */}
          <div className="pt-4">
            <p className="text-sm text-muted-foreground mb-2">Стек технологий</p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">React 18</Badge>
              <Badge variant="outline">TypeScript</Badge>
              <Badge variant="outline">TailwindCSS</Badge>
              <Badge variant="outline">TanStack Query</Badge>
              <Badge variant="outline">React Router</Badge>
              <Badge variant="outline">Vite</Badge>
              <Badge variant="outline">FastAPI</Badge>
              <Badge variant="outline">SQLAlchemy</Badge>
              <Badge variant="outline">PostgreSQL</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* -----------------------------------------------------------------------
       * Будущие настройки (пока заглушка)
       * ----------------------------------------------------------------------- */}
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-muted-foreground">Скоро</CardTitle>
          <CardDescription>
            Дополнительные настройки появятся в следующих версиях
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="text-sm text-muted-foreground space-y-2">
            <li>Тёмная тема</li>
            <li>Настройки уведомлений</li>
            <li>Интеграция с Obsidian</li>
            <li>Экспорт/импорт данных</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

export default Settings;
