// =============================================================================
// API Client — Клиент для работы с Backend API
// =============================================================================
// Этот модуль предоставляет типизированную обёртку над fetch() для работы
// с нашим FastAPI backend.
//
// Функции:
//   1. Автоматическое добавление заголовков (Content-Type, API Key)
//   2. Обработка ошибок и преобразование в понятные исключения
//   3. Типизация запросов и ответов
//   4. Централизованная конфигурация (URL, таймауты)
//
// Использование:
//   import { apiClient } from '@/api/client';
//
//   const projects = await apiClient<Project[]>('/projects');
//   const task = await apiClient<Task>('/tasks/1');
// =============================================================================

import type { ErrorResponse } from '@/types';

// =============================================================================
// Конфигурация
// =============================================================================

/**
 * Базовый URL для API запросов.
 *
 * import.meta.env — это способ Vite предоставить переменные окружения.
 * Переменные с префиксом VITE_ доступны в клиентском коде.
 *
 * Приоритет:
 *   1. VITE_API_URL из .env.local (для разработки)
 *   2. Дефолтное значение http://localhost:8000
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * API ключ для авторизации.
 *
 * Backend ожидает заголовок X-API-Key с этим значением.
 * В реальном приложении это должно быть защищено!
 */
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-api-key-change-in-production';

// =============================================================================
// Кастомные ошибки
// =============================================================================

/**
 * Ошибка API — выбрасывается когда сервер вернул ошибку.
 *
 * Содержит:
 *   - status: HTTP статус код (400, 404, 500, etc.)
 *   - code: Код ошибки из API (VALIDATION_ERROR, NOT_FOUND, etc.)
 *   - message: Человекочитаемое сообщение
 *   - details: Детали ошибки (для валидации — список полей с ошибками)
 *
 * @example
 * try {
 *   await apiClient('/projects/999');
 * } catch (error) {
 *   if (error instanceof ApiError && error.status === 404) {
 *     console.log('Проект не найден');
 *   }
 * }
 */
export class ApiError extends Error {
  status: number;
  code: string;
  details: { field: string; message: string }[] | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: { field: string; message: string }[] | null = null
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/**
 * Ошибка сети — выбрасывается когда запрос не удалось выполнить.
 *
 * Причины:
 *   - Нет интернета
 *   - Сервер не отвечает
 *   - CORS ошибка
 *   - Таймаут
 */
export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

// =============================================================================
// Основной клиент
// =============================================================================

/**
 * Типизированный API клиент.
 *
 * Выполняет HTTP запрос к backend API с автоматическим:
 *   - Добавлением базового URL
 *   - Добавлением заголовков авторизации
 *   - Сериализацией body в JSON
 *   - Парсингом ответа
 *   - Обработкой ошибок
 *
 * @template T - Ожидаемый тип ответа
 * @param endpoint - Путь API (например: '/projects', '/tasks/1')
 * @param options - Опции fetch() (method, body, headers, etc.)
 * @returns Promise с типизированным ответом
 * @throws {ApiError} Когда сервер вернул ошибку (4xx, 5xx)
 * @throws {NetworkError} Когда запрос не удалось выполнить
 *
 * @example
 * // GET запрос
 * const projects = await apiClient<Project[]>('/projects');
 *
 * @example
 * // POST запрос с телом
 * const newProject = await apiClient<Project>('/projects', {
 *   method: 'POST',
 *   body: JSON.stringify({ name: 'Новый проект' }),
 * });
 *
 * @example
 * // DELETE запрос
 * await apiClient<void>('/projects/1', { method: 'DELETE' });
 */
export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  // -------------------------------------------------------------------------
  // Формируем URL
  // -------------------------------------------------------------------------
  // Backend использует корневой путь без /api/v1 префикса
  const url = `${API_BASE_URL}${endpoint}`;

  // -------------------------------------------------------------------------
  // Подготавливаем заголовки
  // -------------------------------------------------------------------------
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
    ...options.headers,
  };

  // -------------------------------------------------------------------------
  // Выполняем запрос
  // -------------------------------------------------------------------------
  let response: Response;

  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (error) {
    // fetch() выбрасывает ошибку только при проблемах с сетью
    // (не при 4xx/5xx статусах!)
    throw new NetworkError(
      error instanceof Error
        ? `Ошибка сети: ${error.message}`
        : 'Не удалось подключиться к серверу'
    );
  }

  // -------------------------------------------------------------------------
  // Обрабатываем ответ
  // -------------------------------------------------------------------------

  // Успешный ответ (2xx)
  if (response.ok) {
    // 204 No Content — возвращаем undefined
    if (response.status === 204) {
      return undefined as T;
    }

    // Парсим JSON
    try {
      return await response.json();
    } catch {
      // Если ответ не JSON, возвращаем пустой объект
      return {} as T;
    }
  }

  // -------------------------------------------------------------------------
  // Обрабатываем ошибку (4xx, 5xx)
  // -------------------------------------------------------------------------
  let errorBody: ErrorResponse | null = null;

  try {
    errorBody = await response.json();
  } catch {
    // Если ответ не JSON, создаём дефолтную ошибку
  }

  // Если сервер вернул структурированную ошибку
  if (errorBody?.error) {
    throw new ApiError(
      response.status,
      errorBody.error.code,
      errorBody.error.message,
      errorBody.error.details
    );
  }

  // Если ошибка в другом формате (например { detail: "..." })
  const detail = (errorBody as { detail?: string } | null)?.detail;
  if (detail) {
    throw new ApiError(response.status, 'UNKNOWN_ERROR', detail);
  }

  // Дефолтная ошибка
  throw new ApiError(
    response.status,
    'UNKNOWN_ERROR',
    `HTTP ${response.status}: ${response.statusText}`
  );
}

// =============================================================================
// Хелперы для HTTP методов
// =============================================================================
// Эти функции — синтаксический сахар для удобства.
// Вместо: apiClient('/projects', { method: 'POST', body: JSON.stringify(data) })
// Пишем: api.post('/projects', data)
// =============================================================================

export const api = {
  /**
   * GET запрос.
   *
   * @example
   * const projects = await api.get<Project[]>('/projects');
   */
  get: <T>(endpoint: string, options?: RequestInit) =>
    apiClient<T>(endpoint, { ...options, method: 'GET' }),

  /**
   * POST запрос.
   *
   * @example
   * const project = await api.post<Project>('/projects', { name: 'Новый' });
   */
  post: <T>(endpoint: string, data?: unknown, options?: RequestInit) =>
    apiClient<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  /**
   * PUT запрос (полное обновление).
   *
   * @example
   * const project = await api.put<Project>('/projects/1', { name: 'Обновлённый' });
   */
  put: <T>(endpoint: string, data?: unknown, options?: RequestInit) =>
    apiClient<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  /**
   * PATCH запрос (частичное обновление).
   *
   * @example
   * const project = await api.patch<Project>('/projects/1', { name: 'Новое имя' });
   */
  patch: <T>(endpoint: string, data?: unknown, options?: RequestInit) =>
    apiClient<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }),

  /**
   * DELETE запрос.
   *
   * @example
   * await api.delete('/projects/1');
   */
  delete: <T = void>(endpoint: string, options?: RequestInit) =>
    apiClient<T>(endpoint, { ...options, method: 'DELETE' }),
};
