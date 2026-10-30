import { Route, Routes } from 'react-router-dom'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { toast } from 'sonner'

import { AppShell } from '@/components/layout/app-shell'
import type { AuthContextValue } from '@/features/auth/auth-context'
import { renderWithProviders, signedInSession } from '@/test/render'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

function renderShell(auth: Partial<AuthContextValue> = {}) {
  return renderWithProviders(
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/app" element={<p>Dashboard content</p>} />
        <Route path="*" element={<p>Navigated</p>} />
      </Route>
    </Routes>,
    {
      route: '/app',
      auth: { user: signedInSession, session: signedInSession, ...auth },
    },
  )
}

describe('app shell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('provides skip navigation, workspace links, and the signed-in planner', () => {
    renderShell()

    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute(
      'href',
      '#main-content',
    )
    expect(
      screen.getByRole('navigation', { name: 'Workspace navigation' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/app')
    expect(screen.getByRole('link', { name: 'Events' })).toHaveAttribute(
      'href',
      '/app/events',
    )
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute(
      'href',
      '/app/settings',
    )
    expect(screen.getAllByRole('link', { name: /create event/i })[0]).toHaveAttribute(
      'href',
      '/app/events/new',
    )
    expect(screen.getByText('Aarav Sharma')).toBeInTheDocument()
    expect(screen.getByText('planner@example.com')).toBeInTheDocument()
    expect(screen.getByText(/AI suggestions are drafts/)).toBeInTheDocument()
    expect(screen.getByText('Dashboard content')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /about festivo/i })).toHaveAttribute(
      'href',
      '/',
    )
  })

  it('falls back to the email when no display name is set', () => {
    renderShell({
      user: { ...signedInSession, user_metadata: {} },
    })

    expect(screen.getByText('planner@example.com')).toBeInTheDocument()
    expect(screen.getAllByText('planner@example.com')).toHaveLength(1)
  })

  it('opens the mobile workspace menu and closes it after choosing a destination', async () => {
    renderShell()

    await userEvent.click(screen.getByRole('button', { name: 'Open workspace menu' }))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Festivo workspace')).toBeInTheDocument()

    const eventsLink = within(dialog).getByRole('link', { name: 'Events' })
    expect(eventsLink).toHaveAttribute('href', '/app/events')
    await userEvent.click(eventsLink)

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(await screen.findByText('Navigated')).toBeInTheDocument()
  })

  it('signs out from the workspace and returns to the landing page', async () => {
    const signOut = vi.fn(async () => undefined)
    renderShell({ signOut })

    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Navigated')).toBeInTheDocument()
    expect(toast.success).toHaveBeenCalledWith('Signed out.')
  })

  it('surfaces a sign-out failure instead of leaving the workspace', async () => {
    const signOut = vi.fn(async () => {
      throw new Error('The identity service is offline.')
    })
    renderShell({ signOut })

    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('The identity service is offline.'),
    )
    expect(screen.queryByText('Navigated')).not.toBeInTheDocument()
    expect(screen.getByText('Dashboard content')).toBeInTheDocument()
  })
})
