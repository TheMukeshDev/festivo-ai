import type { ApiFieldError } from '@/types/api'
import { isRecord } from '@/lib/utils'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: ApiFieldError[]

  constructor(options: {
    status: number
    code: string
    message: string
    fields?: ApiFieldError[]
  }) {
    super(options.message)
    this.name = 'ApiError'
    this.status = options.status
    this.code = options.code
    this.fields = options.fields ?? []
  }

  get isUnauthorized(): boolean {
    return this.status === 401
  }

  get isForbidden(): boolean {
    return this.status === 403
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  get isConflict(): boolean {
    return this.status === 409
  }

  get isValidation(): boolean {
    return this.status === 422
  }

  get isNetwork(): boolean {
    return this.status === 0
  }

  fieldMessage(field: string): string | undefined {
    return this.fields.find((item) => item.field === field)?.message
  }
}

const DEFAULT_MESSAGES: Record<number, string> = {
  400: 'The request is invalid.',
  401: 'Your session has expired. Please sign in again.',
  403: 'You are not authorized to perform this action.',
  404: 'The requested item could not be found.',
  409: 'This item changed while you were editing. Refresh and try again.',
  422: 'Please check the highlighted fields.',
  429: 'Too many requests. Please wait a moment and try again.',
  500: 'The server encountered an error. Please try again.',
  502: 'The service is temporarily unavailable.',
  503: 'The service is temporarily unavailable.',
  504: 'The request timed out. Please try again.',
}

function parseFields(value: unknown): ApiFieldError[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    if (!isRecord(item)) return []
    const field = typeof item.field === 'string' ? item.field : null
    const message = typeof item.message === 'string' ? item.message : null
    if (!field || !message) return []
    return [
      { field, message, type: typeof item.type === 'string' ? item.type : 'value_error' },
    ]
  })
}

export async function parseApiError(response: Response): Promise<ApiError> {
  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  let code = response.status === 401 ? 'unauthorized' : 'http_error'
  let message = DEFAULT_MESSAGES[response.status] ?? 'The request could not be completed.'
  let fields: ApiFieldError[] = []

  if (isRecord(payload)) {
    if (isRecord(payload.error)) {
      if (typeof payload.error.code === 'string') code = payload.error.code
      if (typeof payload.error.message === 'string' && payload.error.message.trim()) {
        message = payload.error.message
      }
      fields = parseFields(payload.error.fields)
    } else if (typeof payload.detail === 'string' && payload.detail.trim()) {
      message = payload.detail
    } else if (isRecord(payload.detail)) {
      if (typeof payload.detail.code === 'string') code = payload.detail.code
      if (typeof payload.detail.message === 'string') message = payload.detail.message
    }
  }

  return new ApiError({ status: response.status, code, message, fields })
}

export function networkError(): ApiError {
  return new ApiError({
    status: 0,
    code: 'network_error',
    message:
      'Festivo could not reach the planning service. Check your connection and that the API is running.',
  })
}

export function timeoutError(): ApiError {
  return new ApiError({
    status: 0,
    code: 'timeout',
    message: 'The request took too long. Please try again.',
  })
}
