import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { AppProviders } from '@/app/providers'
import { createAppQueryClient } from '@/app/query-client'
import { routes } from '@/app/router'

const authValue = vi.hoisted(() => ({
  configured: false,
  configurationMessage: 'Authentication is not configured.',
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
}))

vi.mock('@/features/auth/auth-provider', () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => children,
}))

vi.mock('@/features/auth/use-auth', () => ({
  useAuth: () => authValue,
}))

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <AppProviders client={createAppQueryClient()}>
      <RouterProvider router={router} />
    </AppProviders>,
  )
  return router
}

describe('application routes', () => {
  it('renders the public not-found page for an unknown address', async () => {
    renderAt('/not-a-real-page')
    expect(
      await screen.findByRole('heading', {
        name: 'This page is not part of the plan',
      }),
    ).toBeInTheDocument()
  })

  it('renders the sign-in page for anonymous visitors', async () => {
    renderAt('/sign-in')
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
  })

  it('protects the workspace when authentication is not configured', async () => {
    renderAt('/app')
    expect(await screen.findByText('Authentication is not configured')).toBeInTheDocument()
  })
})
