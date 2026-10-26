import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { ArrowLeft, MailCheck } from 'lucide-react'

import { AuthLayout } from '@/features/auth/auth-layout'
import { useAuth } from '@/features/auth/use-auth'
import { Button } from '@/components/ui/button'
import { FormField } from '@/components/ui/form-field'
import { Input } from '@/components/ui/input'
import { forgotPasswordSchema, type ForgotPasswordValues } from '@/lib/validation/auth'

export function ForgotPasswordPage() {
  const auth = useAuth()
  const [formError, setFormError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const [cooldownSeconds, setCooldownSeconds] = useState(0)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  })

  useEffect(() => {
    if (cooldownSeconds === 0) return
    const timer = window.setInterval(() => {
      setCooldownSeconds((seconds) => Math.max(0, seconds - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [cooldownSeconds])

  async function onSubmit(values: ForgotPasswordValues) {
    setFormError(null)
    try {
      await auth.requestPasswordReset(values.email)
      setSent(true)
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Could not send the reset email.'
      setFormError(message)
      if (message.includes('temporarily rate-limited')) {
        setCooldownSeconds(60)
      }
    }
  }

  if (sent) {
    return (
      <AuthLayout
        title="Check your email"
        description="If an account exists for that address, a password reset link is on its way."
      >
        <div className="rounded-lg border border-line bg-surface p-6 text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-success-soft text-success">
            <MailCheck className="size-5" aria-hidden="true" />
          </span>
          <p className="mt-4 text-sm leading-6 text-muted">
            The link expires after a short time. If you do not see the email, check your
            spam folder before requesting another.
          </p>
          <Button asChild variant="outline" className="mt-6 w-full">
            <Link to="/sign-in">
              <ArrowLeft aria-hidden="true" />
              Back to sign in
            </Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Reset your password"
      description="Enter the email you use for Festivo and we will send a reset link."
      footer={
        <Link className="font-semibold text-primary hover:underline" to="/sign-in">
          Back to sign in
        </Link>
      }
    >
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

        {formError ? (
          <p
            role="alert"
            className="rounded-sm bg-danger-soft px-3 py-2 text-sm text-danger"
          >
            {formError}
          </p>
        ) : null}

        <Button
          type="submit"
          className="w-full"
          size="lg"
          disabled={isSubmitting || cooldownSeconds > 0}
        >
          {isSubmitting
            ? 'Sending reset link…'
            : cooldownSeconds > 0
              ? `Try again in ${cooldownSeconds}s`
              : 'Send reset link'}
        </Button>
      </form>
    </AuthLayout>
  )
}
