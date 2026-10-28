import { useState, type ReactNode, lazy, Suspense } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'

import { createAppQueryClient } from '@/app/query-client'
import { AuthContext, type AuthContextValue } from '@/features/auth/auth-context'
import type { QueryClient } from '@tanstack/react-query'

const Toaster = lazy(() => import('sonner').then(m => ({ default: m.Toaster })))
const AuthProvider = lazy(() =>
  import('@/features/auth/auth-provider').then(m => ({ default: m.AuthProvider })),
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
      <Suspense
        fallback={
          <AuthContext.Provider value={authLoadingValue}>
            {children}
          </AuthContext.Provider>
        }
      >
        <AuthProvider>{children}</AuthProvider>
      </Suspense>
      <Suspense fallback={null}>
        <Toaster position="top-right" closeButton richColors />
      </Suspense>
    </QueryClientProvider>
  )
}
