import type { ReactElement } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { createAppQueryClient } from '@/app/query-client'
import { AuthContext, type AuthContextValue } from '@/features/auth/auth-context'

export const testAuth: AuthContextValue = {
  configured: true,
  configurationMessage: null,
  loading: false,
  session: null,
  user: null,
  sessionExpired: false,
  signIn: async () => undefined,
  signInWithGoogle: async () => undefined,
  signUp: async () => ({ needsEmailConfirmation: false }),
  signOut: async () => undefined,
  requestPasswordReset: async () => undefined,
  updatePassword: async () => undefined,
  clearSessionExpired: () => undefined,
}

export const signedInSession: NonNullable<AuthContextValue['session']> = {
  id: 'user-1',
  email: 'planner@example.com',
  user_metadata: { full_name: 'Aarav Sharma' },
  email_confirmed_at: '2026-01-01T00:00:00.000Z',
  created_at: '2026-01-01T00:00:00.000Z',
  last_sign_in_at: '2026-01-02T00:00:00.000Z',
}

interface ProviderOptions {
  route?: string
  auth?: Partial<AuthContextValue>
  withAuth?: boolean
}

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', auth = {}, withAuth = true }: ProviderOptions = {},
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  const client = createAppQueryClient()
  const value: AuthContextValue = { ...testAuth, ...auth }
  const tree = withAuth ? (
    <AuthContext.Provider value={value}>{ui}</AuthContext.Provider>
  ) : (
    ui
  )

  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[route]}>{tree}</MemoryRouter>
      </QueryClientProvider>,
      options,
    ),
  }
}
