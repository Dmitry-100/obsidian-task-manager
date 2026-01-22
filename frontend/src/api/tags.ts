// =============================================================================
// Tags API — Функции для работы с тегами
// =============================================================================
// Теги используются для категоризации задач.
// Один тег может быть на нескольких задачах, одна задача может иметь много тегов.
//
// Эндпойнты:
//   GET    /tags         → getTags()
//   POST   /tags         → createTag()
//   DELETE /tags/:id     → deleteTag()
// =============================================================================

import { api } from './client';
import type { Tag, TagCreate, TagWithUsage } from '@/types';

// =============================================================================
// CRUD Operations
// =============================================================================

/**
 * Получить список всех тегов.
 *
 * @returns Массив тегов
 *
 * @example
 * const tags = await getTags();
 */
export async function getTags(): Promise<Tag[]> {
  return api.get<Tag[]>('/tags');
}

/**
 * Получить популярные теги с количеством использований.
 *
 * @returns Массив тегов с usage_count
 *
 * @example
 * const popularTags = await getPopularTags();
 * // [{ id: 1, name: 'python', usage_count: 15 }, ...]
 */
export async function getPopularTags(): Promise<TagWithUsage[]> {
  return api.get<TagWithUsage[]>('/tags/popular');
}

/**
 * Создать новый тег.
 *
 * Название будет нормализовано (lowercase, дефисы вместо пробелов).
 *
 * @param data - Данные для создания
 * @returns Созданный тег
 *
 * @example
 * const tag = await createTag({ name: 'My New Tag' });
 * // tag.name === 'my-new-tag'
 */
export async function createTag(data: TagCreate): Promise<Tag> {
  return api.post<Tag>('/tags', data);
}

/**
 * Удалить тег.
 *
 * Тег будет удалён со всех задач.
 *
 * @param id - ID тега
 *
 * @example
 * await deleteTag(1);
 */
export async function deleteTag(id: number): Promise<void> {
  return api.delete(`/tags/${id}`);
}
