import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AuthContext, type AuthContextValue } from '@/features/auth/auth-context'
import { ProtectedRoute, PublicOnlyRoute } from '@/features/auth/auth-guard'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

const baseAuth: AuthContextValue = {
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

function renderWithAuth(ui: React.ReactElement, auth: Partial<AuthContextValue> = {}) {
  const value: AuthContextValue = { ...baseAuth, ...auth }
  return render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={['/test']}>
        <Routes>
          <Route path="/test" element={ui} />
          <Route path="/sign-in" element={<div>Sign in page</div>} />
          <Route path="/app" element={<div>App page</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

describe('auth guards', () => {
  it('redirects unauthenticated users from protected route to sign-in', () => {
    renderWithAuth(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>,
      { session: null },
    )
    expect(screen.getByText('Sign in page')).toBeInTheDocument()
  })

  it('allows authenticated users to access protected route', () => {
    renderWithAuth(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>,
      {
        session: {
          id: '1',
          email: 'test@example.com',
          user_metadata: { full_name: 'Test' },
          email_confirmed_at: null,
          created_at: new Date().toISOString(),
          last_sign_in_at: null,
        },
      },
    )
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('redirects authenticated users away from public-only routes', () => {
    renderWithAuth(
      <PublicOnlyRoute>
        <div>Sign in form</div>
      </PublicOnlyRoute>,
      {
        session: {
          id: '1',
          email: 'test@example.com',
          user_metadata: { full_name: 'Test' },
          email_confirmed_at: null,
          created_at: new Date().toISOString(),
          last_sign_in_at: null,
        },
      },
    )
    expect(screen.getByText('App page')).toBeInTheDocument()
  })

  it('shows loading state for protected route while auth loads', () => {
    renderWithAuth(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>,
      { loading: true },
    )
    expect(screen.getByText(/Restoring your session/i)).toBeInTheDocument()
  })
})
