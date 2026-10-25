import { env } from '@/lib/env'
import { resolveAccessToken } from '@/lib/api/token'
import { ApiError, networkError, parseApiError, timeoutError } from '@/lib/api/errors'
import { isRecord } from '@/lib/utils'

export const API_PREFIX = '/api/v1'
export const UNAUTHORIZED_EVENT = 'festivo:unauthorized'

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
  timeoutMs?: number
  auth?: boolean
  headers?: Record<string, string>
}

function buildUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${env.apiBaseUrl}${normalized}`
}

async function withTimeout(
  timeoutMs: number,
  signal: AbortSignal | undefined,
): Promise<{ signal: AbortSignal; cleanup: () => void }> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort('timeout'), timeoutMs)
  const abortFromParent = () => controller.abort(signal?.reason)
  signal?.addEventListener('abort', abortFromParent, { once: true })

  return {
    signal: controller.signal,
    cleanup: () => {
      window.clearTimeout(timer)
      signal?.removeEventListener('abort', abortFromParent)
    },
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = 'GET',
    body,
    signal,
    timeoutMs = 30_000,
    auth = true,
    headers: extraHeaders,
  } = options

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...extraHeaders,
  }

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (auth) {
    const token = await resolveAccessToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
  }

  const timeout = await withTimeout(timeoutMs, signal)

  try {
    const response = await fetch(buildUrl(path), {
      method,
      headers,
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: timeout.signal,
    })

    if (!response.ok) {
      if (response.status === 401) {
        window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
      }
      throw await parseApiError(response)
    }

    if (response.status === 204) {
      return undefined as T
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw signal?.aborted ? error : timeoutError()
    }
    throw networkError()
  } finally {
    timeout.cleanup()
  }
}

export interface DownloadedFile {
  blob: Blob
  filename: string
  contentType: string
}

function filenameFromHeader(header: string | null, fallback: string): string {
  if (!header) return fallback
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header)?.[1]
  if (encoded) {
    try {
      return decodeURIComponent(encoded.replace(/["']/g, ''))
    } catch {
      return fallback
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header)?.[1]
  return plain?.replace(/[\\/:*?"<>|]/g, '').trim() || fallback
}

export async function apiDownload(
  path: string,
  fallbackFilename: string,
  options: RequestOptions = {},
): Promise<DownloadedFile> {
  const token = await resolveAccessToken()
  const headers: Record<string, string> = {
    Accept: 'application/pdf, text/csv, application/octet-stream',
    ...options.headers,
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const timeout = await withTimeout(options.timeoutMs ?? 60_000, options.signal)

  try {
    const response = await fetch(buildUrl(path), {
      method: options.method ?? 'GET',
      headers,
      signal: timeout.signal,
    })

    if (!response.ok) {
      if (response.status === 401) {
        window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
      }
      throw await parseApiError(response)
    }

    const blob = await response.blob()
    return {
      blob,
      filename: filenameFromHeader(
        response.headers.get('Content-Disposition'),
        fallbackFilename,
      ),
      contentType: response.headers.get('Content-Type') ?? 'application/octet-stream',
    }
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw options.signal?.aborted ? error : timeoutError()
    }
    throw networkError()
  } finally {
    timeout.cleanup()
  }
}

export function saveDownloadedFile(file: DownloadedFile): void {
  const url = URL.createObjectURL(file.blob)
  try {
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = file.filename
    anchor.rel = 'noopener'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}

export function isApiErrorPayload(value: unknown): value is { error: unknown } {
  return isRecord(value) && 'error' in value
}
