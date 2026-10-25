import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CircleAlert, LoaderCircle } from 'lucide-react'

import { AuthCallbackGate } from '@/features/auth/auth-guard'
import { useAuth } from '@/features/auth/use-auth'
import { Button } from '@/components/ui/button'

function CallbackContent() {
  const auth = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (auth.session) {
      navigate('/app', { replace: true })
    }
  }, [auth.session, navigate])

  if (auth.session) {
    return (
      <div className="flex items-center gap-3 text-sm text-ink-soft">
        <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
        Taking you to your workspace…
      </div>
    )
  }

  return (
    <div className="w-full max-w-md rounded-lg border border-line bg-surface p-6 text-center shadow-soft">
      <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-warning-soft text-warning">
        <CircleAlert className="size-5" aria-hidden="true" />
      </span>
      <h1 className="mt-4 font-display text-2xl text-ink">This link did not work</h1>
      <p className="mt-2 text-sm leading-6 text-muted">
        The confirmation link may have expired or already been used. Try signing in, or
        request a new link.
      </p>
      <div className="mt-6 grid gap-2">
        <Button asChild>
          <Link to="/sign-in">Go to sign in</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/forgot-password">Request a new link</Link>
        </Button>
      </div>
    </div>
  )
}

export function AuthCallbackPage() {
  return (
    <main
      id="main-content"
      className="flex min-h-screen flex-col items-center justify-center gap-6 bg-canvas p-6"
    >
      <AuthCallbackGate>
        <CallbackContent />
      </AuthCallbackGate>
    </main>
  )
}
