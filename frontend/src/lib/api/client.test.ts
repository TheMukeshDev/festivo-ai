import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiRequest } from '@/lib/api/client'
import { ApiError } from '@/lib/api/errors'
import { setAccessTokenProvider } from '@/lib/api/token'

afterEach(() => {
  setAccessTokenProvider(null)
})

describe('apiRequest', () => {
  it('adds the bearer token and JSON body', async () => {
    setAccessTokenProvider(async () => 'test-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(
      apiRequest<{ ok: boolean }>('/api/v1/events', {
        method: 'POST',
        body: { name: 'Test' },
      }),
    ).resolves.toEqual({ ok: true })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/events'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Test' }),
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
          'Content-Type': 'application/json',
        }),
      }),
    )
  })

  it('parses structured API errors and field messages', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: 'validation_error',
            message: 'Please check the highlighted fields.',
            fields: [{ field: 'name', message: 'Name is required.' }],
          },
        }),
        { status: 422, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    try {
      await apiRequest('/api/v1/events')
      throw new Error('Expected the request to fail.')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      const apiError = error as ApiError
      expect(apiError.status).toBe(422)
      expect(apiError.code).toBe('validation_error')
      expect(apiError.fieldMessage('name')).toBe('Name is required.')
      expect(apiError.isValidation).toBe(true)
    }
  })

  it('returns undefined for a 204 response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }))
    await expect(apiRequest('/api/v1/events/1')).resolves.toBeUndefined()
  })

  it('maps transport failures to a safe network error', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('fetch failed'))

    await expect(apiRequest('/api/v1/events')).rejects.toMatchObject({
      name: 'ApiError',
      status: 0,
      code: 'network_error',
    })
  })
})
