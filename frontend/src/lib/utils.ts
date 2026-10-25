import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function getErrorMessage(
  error: unknown,
  fallback = 'Something went wrong.',
): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  return fallback
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function safeText(value: string | null | undefined): string {
  return value?.trim() ? value : '—'
}
