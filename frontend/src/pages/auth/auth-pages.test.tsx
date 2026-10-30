import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ForgotPasswordPage } from '@/pages/auth/forgot-password-page'
import { ResetPasswordPage } from '@/pages/auth/reset-password-page'
import { SignInPage } from '@/pages/auth/sign-in-page'
import { SignUpPage } from '@/pages/auth/sign-up-page'
import { expectNoA11yViolations } from '@/test/a11y'
import { renderWithProviders } from '@/test/render'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

afterEach(() => {
  window.history.replaceState({}, '', '/')
})

describe('authentication pages', () => {
  it('validates and submits the sign-in form', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockResolvedValue(undefined)
    const { container } = renderWithProviders(<SignInPage />, {
      auth: { signIn },
      route: '/sign-in',
    })

    await expectNoA11yViolations(container)
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))
    expect(await screen.findByText('Enter your email address.')).toBeInTheDocument()

    await user.type(screen.getByLabelText(/email/i), 'planner@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'strong-password')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))

    await waitFor(() => {
      expect(signIn).toHaveBeenCalledWith('planner@example.com', 'strong-password')
    })
  })

  it('shows sign-in failures and the configured auth warning', async () => {
    const user = userEvent.setup()
    const signIn = vi.fn().mockRejectedValue(new Error('Incorrect credentials.'))
    renderWithProviders(<SignInPage />, {
      auth: {
        signIn,
        configured: false,
        configurationMessage: 'Firebase settings are missing.',
        sessionExpired: true,
      },
      route: '/sign-in',
    })

    expect(screen.getByText('Firebase settings are missing.')).toBeInTheDocument()
    expect(
      screen.getByText('Your session expired. Please sign in again.'),
    ).toBeInTheDocument()

    await user.type(screen.getByLabelText(/email/i), 'planner@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'wrong-password')
    await user.click(screen.getByRole('button', { name: /^sign in$/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect credentials.')
  })

  it('surfaces a Google sign-in error without leaving the page', async () => {
    const user = userEvent.setup()
    const signInWithGoogle = vi.fn().mockRejectedValue(new Error('Popup blocked.'))
    renderWithProviders(<SignInPage />, {
      auth: { signInWithGoogle },
      route: '/sign-in',
    })

    await user.click(screen.getByRole('button', { name: /continue with google/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Popup blocked.')
  })

  it('validates sign-up fields and confirms the email step', async () => {
    const user = userEvent.setup()
    const signUp = vi.fn().mockResolvedValue({ needsEmailConfirmation: true })
    const { container } = renderWithProviders(<SignUpPage />, {
      auth: { signUp },
      route: '/sign-up',
    })

    await expectNoA11yViolations(container)
    await user.click(screen.getByRole('button', { name: /create account/i }))
    expect(await screen.findByText('Enter your name.')).toBeInTheDocument()

    await user.type(screen.getByLabelText(/your name/i), 'Aarav Sharma')
    await user.type(screen.getByLabelText(/^email/i), 'aarav@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'strong-password')
    await user.type(screen.getByLabelText(/confirm password/i), 'strong-password')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(
      await screen.findByRole('heading', { name: 'Check your email' }),
    ).toBeInTheDocument()
    expect(signUp).toHaveBeenCalledWith(
      'aarav@example.com',
      'strong-password',
      'Aarav Sharma',
    )
  })

  it('reports a sign-up failure and a configured-auth warning', async () => {
    const user = userEvent.setup()
    const signUp = vi.fn().mockRejectedValue(new Error('Email already in use.'))
    renderWithProviders(<SignUpPage />, {
      auth: { signUp, configured: false },
      route: '/sign-up',
    })

    await user.type(screen.getByLabelText(/your name/i), 'Aarav Sharma')
    await user.type(screen.getByLabelText(/^email/i), 'aarav@example.com')
    await user.type(screen.getByLabelText(/^password/i), 'strong-password')
    await user.type(screen.getByLabelText(/confirm password/i), 'strong-password')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Email already in use.')
    expect(screen.getByRole('status')).toHaveTextContent('Authentication is not configured')
  })

  it('sends a password reset email and shows the confirmation state', async () => {
    const user = userEvent.setup()
    const requestPasswordReset = vi.fn().mockResolvedValue(undefined)
    const { container } = renderWithProviders(<ForgotPasswordPage />, {
      auth: { requestPasswordReset },
      route: '/forgot-password',
    })

    await expectNoA11yViolations(container)
    await user.type(screen.getByLabelText(/email/i), 'planner@example.com')
    await user.click(screen.getByRole('button', { name: /send reset link/i }))

    expect(
      await screen.findByRole('heading', { name: 'Check your email' }),
    ).toBeInTheDocument()
    expect(requestPasswordReset).toHaveBeenCalledWith('planner@example.com')
  })

  it('shows a reset request error and starts a cooldown when rate limited', async () => {
    const user = userEvent.setup()
    const requestPasswordReset = vi
      .fn()
      .mockRejectedValue(new Error('The service is temporarily rate-limited.'))
    renderWithProviders(<ForgotPasswordPage />, {
      auth: { requestPasswordReset },
      route: '/forgot-password',
    })

    await user.type(screen.getByLabelText(/email/i), 'planner@example.com')
    await user.click(screen.getByRole('button', { name: /send reset link/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('rate-limited')
    expect(screen.getByRole('button', { name: /try again in/i })).toBeDisabled()
  })

  it('explains an expired reset link', async () => {
    const { container } = renderWithProviders(<ResetPasswordPage />, {
      route: '/reset-password',
    })

    expect(screen.getByRole('heading', { name: 'Reset link expired' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /request a new link/i })).toHaveAttribute(
      'href',
      '/forgot-password',
    )
    await expectNoA11yViolations(container)
  })

  it('updates a password with a valid reset code', async () => {
    const user = userEvent.setup()
    const updatePassword = vi.fn().mockResolvedValue(undefined)
    const signOut = vi.fn().mockResolvedValue(undefined)
    window.history.replaceState({}, '', '/reset-password?oobCode=test-code')

    renderWithProviders(<ResetPasswordPage />, {
      auth: { updatePassword, signOut },
      route: '/reset-password?oobCode=test-code',
    })

    await user.type(screen.getByLabelText(/^new password/i), 'new-strong-password')
    await user.type(screen.getByLabelText(/confirm new password/i), 'new-strong-password')
    await user.click(screen.getByRole('button', { name: /save new password/i }))

    await waitFor(() => {
      expect(updatePassword).toHaveBeenCalledWith('new-strong-password', 'test-code')
      expect(signOut).toHaveBeenCalled()
    })
  })
})
