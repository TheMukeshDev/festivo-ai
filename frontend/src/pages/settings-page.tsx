import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  CalendarDays,
  CheckCircle2,
  KeyRound,
  LogOut,
  ShieldCheck,
  UserRound,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/page-header'
import { useAuth } from '@/features/auth/use-auth'
import { formatDateTime } from '@/lib/format'

export function SettingsPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [signingOut, setSigningOut] = useState(false)
  const user = auth.user
  const fullName =
    typeof user?.user_metadata.full_name === 'string'
      ? user.user_metadata.full_name.trim()
      : ''

  async function handleSignOut() {
    setSigningOut(true)
    try {
      queryClient.clear()
      await auth.signOut()
      toast.success('Signed out.')
      navigate('/', { replace: true })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not sign out.')
    } finally {
      setSigningOut(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Settings"
        description="Your account and workspace configuration. Festivo does not store payment details or vendor credentials."
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserRound className="size-4 text-primary" aria-hidden="true" />
              Account
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary-soft font-display text-lg text-primary-strong">
                {(fullName || user?.email || 'U').slice(0, 1).toUpperCase()}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-ink">
                  {fullName || 'No display name set'}
                </p>
                <p className="truncate text-xs text-muted">{user?.email ?? '—'}</p>
              </div>
            </div>

            <dl className="space-y-3 border-t border-line pt-4 text-sm">
              <div className="flex items-start justify-between gap-4">
                <dt className="text-muted">Email status</dt>
                <dd>
                  {user?.email_confirmed_at ? (
                    <Badge tone="success">
                      <CheckCircle2 className="size-3" aria-hidden="true" />
                      Confirmed
                    </Badge>
                  ) : (
                    <Badge tone="warning">Unconfirmed</Badge>
                  )}
                </dd>
              </div>
              <div className="flex items-start justify-between gap-4">
                <dt className="text-muted">Account created</dt>
                <dd className="text-right text-ink-soft">
                  {formatDateTime(user?.created_at)}
                </dd>
              </div>
              <div className="flex items-start justify-between gap-4">
                <dt className="text-muted">Last sign-in</dt>
                <dd className="text-right text-ink-soft">
                  {formatDateTime(user?.last_sign_in_at)}
                </dd>
              </div>
            </dl>

            <div className="flex flex-wrap gap-2 border-t border-line pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={handleSignOut}
                disabled={signingOut}
              >
                <LogOut aria-hidden="true" />
                {signingOut ? 'Signing out…' : 'Sign out'}
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" aria-hidden="true" />
                Authentication
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted">Provider</span>
                <span className="font-medium text-ink">Email & Google (Firebase)</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-muted">Configuration</span>
                <Badge tone={auth.configured ? 'success' : 'warning'}>
                  {auth.configured ? 'Configured' : 'Not configured'}
                </Badge>
              </div>
              {!auth.configured && auth.configurationMessage ? (
                <p className="rounded-sm bg-warning-soft p-3 text-xs leading-5 text-ink-soft">
                  {auth.configurationMessage}
                </p>
              ) : null}
              <p className="border-t border-line pt-3 text-xs leading-5 text-muted">
                Password changes are handled through the secure reset flow. Festivo never
                displays or stores your password.
              </p>
              <Button asChild variant="ghost" size="sm" className="-ml-3">
                <Link to="/forgot-password">
                  <KeyRound aria-hidden="true" />
                  Reset password by email
                </Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CalendarDays className="size-4 text-primary" aria-hidden="true" />
                Planning workspace
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="leading-6 text-ink-soft">
                Festivo stores events, budgets, expenses, timelines, tasks, vendor
                shortlists, and AI proposals. PDF and CSV exports download straight from
                this workspace.
              </p>
              <Button asChild variant="outline" size="sm">
                <Link to="/app/events">Manage events</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
