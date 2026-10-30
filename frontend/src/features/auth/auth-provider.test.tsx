import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { useAuth } from '@/features/auth/use-auth'

vi.mock('@/lib/firebase/client', () => ({
  auth: { name: 'test-auth' },
  firebaseConfigurationError: null,
  firebaseReady: true,
}))

vi.mock('firebase/auth', () => ({
  onIdTokenChanged: vi.fn(() => () => undefined),
  getRedirectResult: vi.fn(() => Promise.resolve(null)),
  signInWithEmailAndPassword: vi.fn(),
  signInWithPopup: vi.fn(),
  signInWithRedirect: vi.fn(),
  createUserWithEmailAndPassword: vi.fn(),
  updateProfile: vi.fn(),
  signOut: vi.fn(),
  sendPasswordResetEmail: vi.fn(),
  confirmPasswordReset: vi.fn(),
  updatePassword: vi.fn(),
  GoogleAuthProvider: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('@/lib/api/token', () => ({
  setAccessTokenProvider: vi.fn(),
}))

import { AuthProvider } from '@/features/auth/auth-provider'

function TestConsumer() {
  const auth = useAuth()
  return <div data-testid="loading">{auth.loading ? 'loading' : 'ready'}</div>
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('starts in loading state when firebase is ready', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )
    expect(screen.getByTestId('loading')).toHaveTextContent('loading')
  })
})
