import { useState, type ReactNode, lazy, Suspense } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'

import { createAppQueryClient } from '@/app/query-client'
import { AuthProvider } from '@/features/auth/auth-provider'
import type { QueryClient } from '@tanstack/react-query'

const Toaster = lazy(() => import('sonner').then(m => ({ default: m.Toaster })))

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
      <AuthProvider>
        {children}
        <Suspense fallback={null}>
          <Toaster position="top-right" closeButton richColors />
        </Suspense>
      </AuthProvider>
    </QueryClientProvider>
  )
}
