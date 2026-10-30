import { describe, expect, it } from 'vitest'

import { ApiError, networkError, parseApiError, timeoutError } from '@/lib/api/errors'

function response(payload: unknown, status: number): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('ApiError', () => {
  it('exposes status helpers, default fields, and field messages', () => {
    const error = new ApiError({
      status: 422,
      code: 'validation_error',
      message: 'Check the highlighted fields.',
      fields: [{ field: 'name', message: 'Name is required.', type: 'value_error' }],
    })

    expect(error.name).toBe('ApiError')
    expect(error.isValidation).toBe(true)
    expect(error.isUnauthorized).toBe(false)
    expect(error.fieldMessage('name')).toBe('Name is required.')
    expect(error.fieldMessage('other')).toBeUndefined()
    expect(new ApiError({ status: 500, code: 'x', message: 'x' }).fields).toEqual([])
  })

  it('reports each HTTP status family', () => {
    expect(new ApiError({ status: 401, code: 'a', message: 'a' }).isUnauthorized).toBe(true)
    expect(new ApiError({ status: 403, code: 'a', message: 'a' }).isForbidden).toBe(true)
    expect(new ApiError({ status: 404, code: 'a', message: 'a' }).isNotFound).toBe(true)
    expect(new ApiError({ status: 409, code: 'a', message: 'a' }).isConflict).toBe(true)
    expect(new ApiError({ status: 0, code: 'a', message: 'a' }).isNetwork).toBe(true)
    expect(new ApiError({ status: 200, code: 'a', message: 'a' }).isValidation).toBe(false)
  })
})

describe('parseApiError', () => {
  it('reads structured error payloads and filters invalid fields', async () => {
    const error = await parseApiError(
      response(
        {
          error: {
            code: 'validation_error',
            message: 'Please fix the budget.',
            fields: [
              { field: 'total_limit', message: 'Must be positive.', type: 'value_error' },
              { field: 'ignored' },
              null,
            ],
          },
        },
        422,
      ),
    )

    expect(error.code).toBe('validation_error')
    expect(error.message).toBe('Please fix the budget.')
    expect(error.fields).toEqual([
      { field: 'total_limit', message: 'Must be positive.', type: 'value_error' },
    ])
  })

  it('falls back to default status messages for empty payloads', async () => {
    const error = await parseApiError(response({}, 404))
    expect(error.code).toBe('http_error')
    expect(error.message).toBe('The requested item could not be found.')
    expect(await parseApiError(response({}, 429))).toMatchObject({
      message: 'Too many requests. Please wait a moment and try again.',
    })
    expect(await parseApiError(response({}, 418))).toMatchObject({
      message: 'The request could not be completed.',
    })
  })

  it('uses a FastAPI detail string or detail object', async () => {
    expect(
      (await parseApiError(response({ detail: 'Event not found.' }, 404))).message,
    ).toBe('Event not found.')

    const nested = await parseApiError(
      response({ detail: { code: 'not_found', message: 'No such event.' } }, 404),
    )
    expect(nested.code).toBe('not_found')
    expect(nested.message).toBe('No such event.')
  })

  it('ignores blank messages and malformed JSON', async () => {
    expect((await parseApiError(response({ detail: '   ' }, 400))).message).toBe(
      'The request is invalid.',
    )
    expect((await parseApiError(response({ error: { message: '  ' } }, 401))).message).toBe(
      'Your session has expired. Please sign in again.',
    )

    const malformed = {
      status: 500,
      json: async () => {
        throw new SyntaxError('invalid json')
      },
    } as unknown as Response
    expect((await parseApiError(malformed)).code).toBe('http_error')
  })

  it('creates offline and timeout errors without an HTTP response', () => {
    expect(networkError()).toMatchObject({ status: 0, code: 'network_error' })
    expect(networkError().isNetwork).toBe(true)
    expect(timeoutError()).toMatchObject({ status: 0, code: 'timeout' })
  })
})
