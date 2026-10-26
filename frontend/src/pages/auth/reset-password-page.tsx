import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { ArrowRight, Link2Off } from 'lucide-react'
import { toast } from 'sonner'

import { AuthLayout } from '@/features/auth/auth-layout'
import { PasswordInput } from '@/features/auth/password-input'
import { useAuth } from '@/features/auth/use-auth'
import { Button } from '@/components/ui/button'
import { FormField } from '@/components/ui/form-field'
import { resetPasswordSchema, type ResetPasswordValues } from '@/lib/validation/auth'

export function ResetPasswordPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const actionCode = useMemo(() => new URLSearchParams(window.location.search).get('oobCode'), [])
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '', confirmPassword: '' },
  })

  async function onSubmit(values: ResetPasswordValues) {
    setFormError(null)
    try {
      await auth.updatePassword(values.password, actionCode ?? undefined)
      toast.success('Password updated. Sign in with your new password.')
      await auth.signOut()
      navigate('/sign-in', { replace: true })
    } catch (error) {
      setFormError(
        error instanceof Error ? error.message : 'Could not update your password.',
      )
    }
  }

  if (!actionCode) {
    return (
      <AuthLayout
        title="Reset link expired"
        description="Password reset links are short-lived and can only be used once."
      >
        <div className="rounded-lg border border-line bg-surface p-6 text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-warning-soft text-warning">
            <Link2Off className="size-5" aria-hidden="true" />
          </span>
          <p className="mt-4 text-sm leading-6 text-muted">
            Request a fresh link and open it on this device.
          </p>
          <Button asChild className="mt-6 w-full">
            <Link to="/forgot-password">
              Request a new link
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Choose a new password"
      description="Use at least 8 characters. You will sign in again after saving."
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        <FormField
          id="password"
          label="New password"
          error={errors.password?.message}
          required
        >
          <PasswordInput
            id="password"
            autoComplete="new-password"
            autoFocus
            placeholder="New password"
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? 'password-error' : undefined}
            {...register('password')}
          />
        </FormField>
        <FormField
          id="confirmPassword"
          label="Confirm new password"
          error={errors.confirmPassword?.message}
          required
        >
          <PasswordInput
            id="confirmPassword"
            autoComplete="new-password"
            placeholder="Repeat new password"
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
          {isSubmitting ? 'Saving password…' : 'Save new password'}
        </Button>
      </form>
    </AuthLayout>
  )
}
