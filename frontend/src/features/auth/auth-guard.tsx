import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { KeyRound, Settings2 } from 'lucide-react'

import { useAuth } from '@/features/auth/use-auth'
import { Button } from '@/components/ui/button'
import { FullPageLoader } from '@/components/ui/full-page-loader'
import { EmptyState } from '@/components/ui/empty-state'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const auth = useAuth()
  const location = useLocation()

  if (auth.loading) {
    return <FullPageLoader label="Restoring your session" />
  }

  if (!auth.configured) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-xl">
          <EmptyState
            icon={Settings2}
            title="Authentication is not configured"
            description={
              auth.configurationMessage ??
              'Add the public Firebase web config (VITE_FIREBASE_* variables) to the frontend environment.'
            }
            action={
              <Button asChild variant="outline">
                <a href="/">Back to the landing page</a>
              </Button>
            }
          />
        </div>
      </main>
    )
  }

  if (!auth.session) {
    return (
      <Navigate
        to="/sign-in"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    )
  }

  return <>{children}</>
}

export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const auth = useAuth()

  if (auth.loading) {
    return <FullPageLoader label="Checking your session" />
  }

  if (auth.session) {
    return <Navigate to="/app" replace />
  }

  return <>{children}</>
}

export function AuthCallbackGate({ children }: { children: ReactNode }) {
  const auth = useAuth()

  if (auth.loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-ink-soft">
          <KeyRound className="size-4" aria-hidden="true" />
          Completing sign in…
        </div>
      </div>
    )
  }

  return <>{children}</>
}
