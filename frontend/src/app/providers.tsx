import { useEffect, useState, type ReactNode, lazy, Suspense } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'

import { createAppQueryClient } from '@/app/query-client'
import { AuthContext, type AuthContextValue } from '@/features/auth/auth-context'
import type { QueryClient } from '@tanstack/react-query'

const Toaster = lazy(() => import('sonner').then((m) => ({ default: m.Toaster })))
const AuthProvider = lazy(() =>
  import('@/features/auth/auth-provider').then((m) => ({ default: m.AuthProvider })),
)

const authLoadingValue: AuthContextValue = {
  configured: true,
  configurationMessage: null,
  loading: true,
  session: null,
  user: null,
  sessionExpired: false,
  signIn: async () => {
    throw new Error('Authentication is still loading.')
  },
  signInWithGoogle: async () => {
    throw new Error('Authentication is still loading.')
  },
  signUp: async () => {
    throw new Error('Authentication is still loading.')
  },
  signOut: async () => {
    throw new Error('Authentication is still loading.')
  },
  requestPasswordReset: async () => {
    throw new Error('Authentication is still loading.')
  },
  updatePassword: async () => {
    throw new Error('Authentication is still loading.')
  },
  clearSessionExpired: () => undefined,
}

function needsAuthOnInitialLoad(): boolean {
  const path = window.location.pathname
  return (
    path.startsWith('/app') ||
    path === '/sign-in' ||
    path === '/sign-up' ||
    path === '/forgot-password' ||
    path === '/reset-password' ||
    path === '/auth/callback'
  )
}

function AuthBoundary({ children }: { children: ReactNode }) {
  const [authRequested, setAuthRequested] = useState(needsAuthOnInitialLoad)

  useEffect(() => {
    if (authRequested) return

    const requestAuth = () => setAuthRequested(true)
    window.addEventListener('pointerdown', requestAuth, { once: true, passive: true })
    window.addEventListener('keydown', requestAuth, { once: true })
    return () => {
      window.removeEventListener('pointerdown', requestAuth)
      window.removeEventListener('keydown', requestAuth)
    }
  }, [authRequested])

  if (!authRequested) {
    return <AuthContext.Provider value={authLoadingValue}>{children}</AuthContext.Provider>
  }

  return (
    <Suspense
      fallback={
        <AuthContext.Provider value={authLoadingValue}>{children}</AuthContext.Provider>
      }
    >
      <AuthProvider>{children}</AuthProvider>
    </Suspense>
  )
}

export function AppProviders({
  children,
  client,
}: {
  children: ReactNode
  client?: QueryClient
}) {
  const [queryClient] = useState(() => client ?? createAppQueryClient())

  return (
    <QueryClientProvider client={queryClient}>
      <AuthBoundary>{children}</AuthBoundary>
      <Suspense fallback={null}>
        <Toaster position="top-right" closeButton richColors />
      </Suspense>
    </QueryClientProvider>
  )
}
