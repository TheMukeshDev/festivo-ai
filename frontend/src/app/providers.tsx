import { useState, type ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'

import { createAppQueryClient } from '@/app/query-client'
import { AuthProvider } from '@/features/auth/auth-provider'
import type { QueryClient } from '@tanstack/react-query'

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
        <Toaster position="top-right" closeButton richColors />
      </AuthProvider>
    </QueryClientProvider>
  )
}
