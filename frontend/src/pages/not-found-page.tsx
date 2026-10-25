import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, CalendarDays, Home } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/use-auth'

export function NotFoundPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const signedIn = Boolean(auth.session)

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center px-4 py-16 text-center">
      <p className="font-display text-7xl leading-none text-primary/30 sm:text-8xl">404</p>
      <p className="eyebrow mt-6">Page not found</p>
      <h1 className="mt-2 font-display text-3xl tracking-[-0.02em] text-ink sm:text-4xl">
        This page is not part of the plan
      </h1>
      <p className="mt-3 max-w-md text-sm leading-6 text-muted">
        The address may be mistyped, or the page may have moved. Your saved events and
        planning data are unaffected.
      </p>
      <div className="mt-7 flex flex-col gap-2 sm:flex-row">
        <Button type="button" variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft aria-hidden="true" />
          Go back
        </Button>
        {signedIn ? (
          <>
            <Button asChild>
              <Link to="/app">
                <Home aria-hidden="true" />
                Dashboard
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/app/events">
                <CalendarDays aria-hidden="true" />
                Events
              </Link>
            </Button>
          </>
        ) : (
          <Button asChild>
            <Link to="/">
              <Home aria-hidden="true" />
              Back to Festivo
            </Link>
          </Button>
        )}
      </div>
    </div>
  )
}
