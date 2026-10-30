import { afterEach, describe, expect, it, vi } from 'vitest'

import { resolveAccessToken, setAccessTokenProvider } from '@/lib/api/token'

describe('access token provider', () => {
  afterEach(() => setAccessTokenProvider(null))

  it('returns null when no provider is registered', async () => {
    await expect(resolveAccessToken()).resolves.toBeNull()
  })

  it('delegates to the registered provider and can be cleared', async () => {
    const provider = vi.fn().mockResolvedValue('token-123')
    setAccessTokenProvider(provider)
    await expect(resolveAccessToken()).resolves.toBe('token-123')
    expect(provider).toHaveBeenCalledTimes(1)

    setAccessTokenProvider(null)
    await expect(resolveAccessToken()).resolves.toBeNull()
    expect(provider).toHaveBeenCalledTimes(1)
  })
})
