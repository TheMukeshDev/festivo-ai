import { useState } from 'react'
import { Link } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { ArrowRight, MailCheck } from 'lucide-react'
import { toast } from 'sonner'

import { AuthLayout } from '@/features/auth/auth-layout'
import { GoogleIcon } from '@/features/auth/google-icon'
import { PasswordInput } from '@/features/auth/password-input'
import { useAuth } from '@/features/auth/use-auth'
import { Button } from '@/components/ui/button'
import { FormField } from '@/components/ui/form-field'
import { Input } from '@/components/ui/input'
import { signUpSchema, type SignUpValues } from '@/lib/validation/auth'

export function SignUpPage() {
  const auth = useAuth()
  const [formError, setFormError] = useState<string | null>(null)
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    defaultValues: { fullName: '', email: '', password: '', confirmPassword: '' },
  })

  async function onSubmit(values: SignUpValues) {
    setFormError(null)
    try {
      const result = await auth.signUp(values.email, values.password, values.fullName)
      if (result.needsEmailConfirmation) {
        setAwaitingConfirmation(true)
      } else {
        toast.success('Your workspace is ready.')
      }
    } catch (error) {
      setFormError(
        error instanceof Error ? error.message : 'Could not create your account.',
      )
    }
  }

  if (awaitingConfirmation) {
    return (
      <AuthLayout
        title="Check your email"
        description="We sent a confirmation link so we can keep your event workspace private."
      >
        <div className="rounded-lg border border-line bg-surface p-6 text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-success-soft text-success">
            <MailCheck className="size-5" aria-hidden="true" />
          </span>
          <h2 className="mt-4 font-display text-2xl text-ink">One quick step</h2>
          <p className="mt-2 text-sm leading-6 text-muted">
            Open the link in your email to confirm your account, then sign in. If it does
            not arrive in a few minutes, check your spam folder.
          </p>
          <Button asChild className="mt-6 w-full">
            <Link to="/sign-in">
              Go to sign in
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Create your workspace"
      description="A private place to shape the budget, timeline, and vendor decisions."
      footer={
        <>
          Already have an account?{' '}
          <Link className="font-semibold text-primary hover:underline" to="/sign-in">
            Sign in
          </Link>
        </>
      }
    >
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
        <FormField
          id="fullName"
          label="Your name"
          error={errors.fullName?.message}
          required
        >
          <Input
            id="fullName"
            autoComplete="name"
            autoFocus
            placeholder="Aarav Sharma"
            aria-invalid={Boolean(errors.fullName)}
            aria-describedby={errors.fullName ? 'fullName-error' : undefined}
            {...register('fullName')}
          />
        </FormField>
        <FormField id="email" label="Email" error={errors.email?.message} required>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? 'email-error' : undefined}
            {...register('email')}
          />
        </FormField>
        <FormField
          id="password"
          label="Password"
          error={errors.password?.message}
          description="Use at least 8 characters."
          required
        >
          <PasswordInput
            id="password"
            autoComplete="new-password"
            placeholder="Choose a password"
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? 'password-error' : undefined}
            {...register('password')}
          />
        </FormField>
        <FormField
          id="confirmPassword"
          label="Confirm password"
          error={errors.confirmPassword?.message}
          required
        >
          <PasswordInput
            id="confirmPassword"
            autoComplete="new-password"
            placeholder="Repeat your password"
            aria-invalid={Boolean(errors.confirmPassword)}
            aria-describedby={errors.confirmPassword ? 'confirmPassword-error' : undefined}
            {...register('confirmPassword')}
          />
        </FormField>

        {formError ? (
          <p
            role="alert"
            className="rounded-sm bg-danger-soft px-3 py-2 text-sm text-danger"
          >
            {formError}
          </p>
        ) : null}

        <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Creating your workspace…' : 'Create account'}
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
              // The browser leaves for Google here; do not navigate or show a
              // success toast — that raced the redirect and bounced users back
              // to the sign-in page on return.
              await auth.signInWithGoogle()
            } catch (error) {
              setFormError(
                error instanceof Error
                  ? error.message
                  : 'Could not continue with Google.',
              )
            }
          }}
        >
          <GoogleIcon />
          Continue with Google
        </Button>
        <p className="text-xs leading-5 text-muted">
          By creating an account you agree to keep vendor and payment decisions under your
          own review. Festivo provides planning tools, not booking or payment services.
        </p>
      </form>
    </AuthLayout>
  )
}
