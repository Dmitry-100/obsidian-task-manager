// =============================================================================
// Утилиты для работы с CSS классами
// =============================================================================
// Этот файл создан shadcn/ui и содержит функцию cn() для объединения классов.
//
// Проблема которую решает cn():
//   В Tailwind CSS часто нужно условно добавлять классы:
//   className={`base-class ${isActive ? 'active-class' : ''}`}
//
//   Но что если base-class и active-class конфликтуют? (например bg-red-500 и bg-blue-500)
//   Tailwind по умолчанию применит тот что последний в CSS файле, а не в строке!
//
// Решение:
//   cn() использует tailwind-merge чтобы правильно объединять классы,
//   где последний класс в списке имеет приоритет.
// =============================================================================

import { clsx, type ClassValue } from 'clsx';
// clsx — библиотека для условного объединения классов
// Поддерживает: строки, объекты, массивы, undefined, null

import { twMerge } from 'tailwind-merge';
// tailwind-merge — умное объединение Tailwind классов
// Понимает конфликты: twMerge('bg-red-500 bg-blue-500') → 'bg-blue-500'

/**
 * cn() — функция для объединения CSS классов
 *
 * @example
 * // Базовое использование
 * cn('px-4 py-2', 'bg-blue-500')
 * // → 'px-4 py-2 bg-blue-500'
 *
 * @example
 * // Условные классы
 * cn('px-4', isActive && 'bg-blue-500', isDisabled && 'opacity-50')
 *
 * @example
 * // Переопределение классов (tailwind-merge в действии)
 * cn('bg-red-500', 'bg-blue-500')
 * // → 'bg-blue-500' (последний выигрывает!)
 *
 * @example
 * // Объект с условиями
 * cn('base', { 'active': isActive, 'disabled': isDisabled })
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
