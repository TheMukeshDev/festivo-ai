import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { AlertTriangle, ArrowRight } from 'lucide-react'
import { toast } from 'sonner'

import { AuthLayout } from '@/features/auth/auth-layout'
import { GoogleIcon } from '@/features/auth/google-icon'
import { PasswordInput } from '@/features/auth/password-input'
import { useAuth } from '@/features/auth/use-auth'
import { Button } from '@/components/ui/button'
import { FormField } from '@/components/ui/form-field'
import { Input } from '@/components/ui/input'
import { signInSchema, type SignInValues } from '@/lib/validation/auth'
import { env } from '@/lib/env'

export function SignInPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    setValue,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: '', password: '' },
  })

  const fromState = (location.state as { from?: unknown } | null)?.from
  const redirectTo =
    typeof fromState === 'string' && fromState.startsWith('/') ? fromState : '/app'
  const demoConfigured = Boolean(env.demoEmail && env.demoPassword)

  async function onSubmit(values: SignInValues) {
    setFormError(null)
    try {
      await auth.signIn(values.email, values.password)
      auth.clearSessionExpired()
      toast.success('Welcome back.')
      navigate(redirectTo, { replace: true })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not sign in.'
      setFormError(message)
    }
  }

  return (
    <AuthLayout
      title="Sign in"
      description="Pick up where you left off with your event plan."
      footer={
        <>
          New to Festivo?{' '}
          <Link className="font-semibold text-primary hover:underline" to="/sign-up">
            Create an account
          </Link>
        </>
      }
    >
      {auth.sessionExpired ? (
        <div
          className="mb-5 flex items-start gap-3 rounded-md border border-warning/25 bg-warning-soft p-3 text-sm text-ink-soft"
          role="status"
        >
          <AlertTriangle
            className="mt-0.5 size-4 shrink-0 text-warning"
            aria-hidden="true"
          />
          Your session expired. Please sign in again.
        </div>
      ) : null}

      {!auth.configured ? (
        <div
          className="mb-5 rounded-md border border-warning/25 bg-warning-soft p-3 text-sm text-ink-soft"
          role="status"
        >
          {auth.configurationMessage ??
            'Authentication is not configured. Add the Firebase web app settings to the frontend environment.'}
        </div>
      ) : null}

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        <FormField id="email" label="Email" error={errors.email?.message} required>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            autoFocus
            placeholder="you@example.com"
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? 'email-error' : undefined}
            {...register('email')}
          />
        </FormField>
        <FormField id="password" label="Password" error={errors.password?.message} required>
          <PasswordInput
            id="password"
            autoComplete="current-password"
            placeholder="Your password"
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? 'password-error' : undefined}
            {...register('password')}
          />
        </FormField>

        <div className="flex justify-end">
          <Link
            to="/forgot-password"
            className="text-sm font-medium text-primary hover:underline"
          >
            Forgot your password?
          </Link>
        </div>

        {formError ? (
          <p
            role="alert"
            className="rounded-sm bg-danger-soft px-3 py-2 text-sm text-danger"
          >
            {formError}
          </p>
        ) : null}

        <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
          {!isSubmitting ? <ArrowRight aria-hidden="true" /> : null}
        </Button>
        <Button
          type="button"
          variant="outline"
          className="w-full"
          size="lg"
          disabled={isSubmitting}
          onClick={async () => {
            setFormError(null)
            try {
              // Redirects to Google; the return trip lands in the workspace
              // once the session is restored (no client-side navigation here).
              await auth.signInWithGoogle()
            } catch (error) {
              setFormError(error instanceof Error ? error.message : 'Could not sign in with Google.')
            }
          }}
        >
          <GoogleIcon />
          Continue with Google
        </Button>
        {demoConfigured ? (
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            disabled={isSubmitting}
            onClick={() => {
              setValue('email', env.demoEmail)
              setValue('password', env.demoPassword)
              setFormError(null)
            }}
          >
            Use demo account
          </Button>
        ) : null}
      </form>
    </AuthLayout>
  )
}
