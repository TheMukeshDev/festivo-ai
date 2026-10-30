import { Route, Routes } from 'react-router-dom'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { toast } from 'sonner'

import type { AuthContextValue } from '@/features/auth/auth-context'
import { DashboardPage } from '@/pages/dashboard-page'
import { SettingsPage } from '@/pages/settings-page'
import { renderWithProviders, signedInSession } from '@/test/render'
import {
  makeBudget,
  makeEvent,
  makeEventList,
  makeTask,
  makeTaskList,
} from '@/test/fixtures'

const queries = vi.hoisted(() => {
  function query(data: unknown) {
    return {
      data,
      isLoading: false,
      isError: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    }
  }

  return {
    events: query(null),
    budget: query(null),
    tasks: query(null),
  }
})

vi.mock('@/features/events/queries', () => ({
  useEventsQuery: () => queries.events,
  useBudgetQuery: () => queries.budget,
  useTasksQuery: () => queries.tasks,
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

function resetQuery(target: object, data: unknown) {
  Object.assign(target, {
    data,
    isLoading: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  })
}

function dateOffset(days: number): string {
  return new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10)
}

function renderPage(
  element: React.ReactElement,
  route: string,
  auth: Partial<AuthContextValue> = {},
) {
  return renderWithProviders(
    <Routes>
      <Route path={route} element={element} />
      <Route path="*" element={<p>Navigated</p>} />
    </Routes>,
    {
      route,
      auth: { user: signedInSession, session: signedInSession, ...auth },
    },
  )
}

describe('dashboard page', () => {
  beforeEach(() => {
    resetQuery(queries.events, makeEventList([]))
    resetQuery(queries.budget, null)
    resetQuery(queries.tasks, null)
  })

  it('welcomes a planner with no events and points to event creation', () => {
    renderPage(<DashboardPage />, '/app')

    expect(screen.getByRole('heading', { level: 1, name: /Aarav/ })).toBeInTheDocument()
    expect(screen.getByText('Your first event starts here')).toBeInTheDocument()
    const createLinks = screen.getAllByRole('link', { name: /create/i })
    expect(createLinks.length).toBeGreaterThanOrEqual(2)
    for (const link of createLinks) expect(link).toHaveAttribute('href', '/app/events/new')
  })

  it('summarizes upcoming plans, budget health, and open tasks', () => {
    const nearest = makeEvent({
      event_id: 'event-1',
      name: 'Meera and Arjun reception',
      event_date: dateOffset(30),
      guest_count: 180,
    })
    const later = makeEvent({
      event_id: 'event-2',
      name: 'Diwali office party',
      event_date: dateOffset(60),
      guest_count: 40,
    })
    const past = makeEvent({
      event_id: 'event-3',
      name: 'Last year anniversary',
      event_date: dateOffset(-30),
    })

    resetQuery(queries.events, makeEventList([later, past, nearest]))
    resetQuery(queries.budget, makeBudget())
    resetQuery(
      queries.tasks,
      makeTaskList([
        makeTask({
          task_id: 'task-1',
          title: 'Confirm the catering headcount',
          status: 'in_progress',
          due_at: '2026-11-20T12:00:00.000Z',
        }),
        makeTask({
          task_id: 'task-2',
          title: 'Send the save-the-date',
          status: 'completed',
          completed_at: '2026-10-01T12:00:00.000Z',
          due_at: null,
        }),
      ]),
    )

    renderPage(<DashboardPage />, '/app')

    expect(screen.getByText('Next celebration')).toBeInTheDocument()
    expect(screen.getAllByText('Meera and Arjun reception').length).toBeGreaterThan(0)
    expect(screen.getByText('1 of 2')).toBeInTheDocument()
    expect(screen.getByText('Confirm the catering headcount')).toBeInTheDocument()
    expect(screen.getByText(/remains after the reserve/)).toBeInTheDocument()
    expect(screen.getByText('220')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open/i })).toHaveAttribute(
      'href',
      '/app/events/event-1',
    )
  })

  it('explains missing budget and task setup without inventing numbers', () => {
    resetQuery(queries.events, makeEventList([makeEvent({ event_date: dateOffset(20) })]))
    resetQuery(queries.budget, null)
    resetQuery(queries.tasks, makeTaskList([]))

    renderPage(<DashboardPage />, '/app')

    expect(screen.getByText('Budget not set up yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Set up the budget' })).toHaveAttribute(
      'href',
      '/app/events/event-1/budget',
    )
    expect(screen.getByText('No tasks yet')).toBeInTheDocument()
    expect(screen.getByText(/Nothing open right now/)).toBeInTheDocument()
  })

  it('handles a workspace containing only completed events', () => {
    resetQuery(
      queries.events,
      makeEventList([
        makeEvent({ event_id: 'event-1', event_date: dateOffset(-40) }),
        makeEvent({ event_id: 'event-2', event_date: dateOffset(-10) }),
      ]),
    )

    renderPage(<DashboardPage />, '/app')

    expect(screen.getByText('No upcoming events')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.getByText('2 completed events in your workspace')).toBeInTheDocument()
  })

  it('shows a retry action when the workspace cannot load', async () => {
    Object.assign(queries.events, {
      data: null,
      isLoading: false,
      isError: true,
      isFetching: false,
      error: new Error('Planning service is unavailable.'),
      refetch: vi.fn(),
    })

    renderPage(<DashboardPage />, '/app')

    expect(screen.getByRole('alert')).toHaveTextContent('Your workspace could not load')
    expect(screen.getByText('Planning service is unavailable.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(queries.events.refetch).toHaveBeenCalled()
  })
})

describe('settings page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('presents account details, authentication status, and workspace links', () => {
    renderPage(<SettingsPage />, '/app/settings')

    expect(screen.getByRole('heading', { level: 1, name: 'Settings' })).toBeInTheDocument()
    expect(screen.getByText('Aarav Sharma')).toBeInTheDocument()
    expect(screen.getByText('planner@example.com')).toBeInTheDocument()
    expect(screen.getByText('Confirmed')).toBeInTheDocument()
    expect(screen.getByText('Configured')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /reset password by email/i })).toHaveAttribute(
      'href',
      '/forgot-password',
    )
    expect(screen.getByRole('link', { name: 'Manage events' })).toHaveAttribute(
      'href',
      '/app/events',
    )
  })

  it('flags an unconfirmed account without a display name and shows config guidance', () => {
    renderPage(<SettingsPage />, '/app/settings', {
      user: {
        ...signedInSession,
        email: 'new.planner@example.com',
        user_metadata: {},
        email_confirmed_at: null,
      },
      configured: false,
      configurationMessage: 'Add Firebase environment variables before signing in.',
    })

    expect(screen.getByText('No display name set')).toBeInTheDocument()
    expect(screen.getByText('Unconfirmed')).toBeInTheDocument()
    expect(screen.getByText('Not configured')).toBeInTheDocument()
    expect(
      screen.getByText('Add Firebase environment variables before signing in.'),
    ).toBeInTheDocument()
    expect(screen.getByText('N')).toBeInTheDocument()
  })

  it('signs out, clears the cache, and returns to the landing page', async () => {
    const signOut = vi.fn(async () => undefined)
    renderPage(<SettingsPage />, '/app/settings', { signOut })

    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Navigated')).toBeInTheDocument()
    expect(toast.success).toHaveBeenCalledWith('Signed out.')
  })

  it('reports a sign-out failure and stays on the settings page', async () => {
    const signOut = vi.fn(async () => {
      throw new Error('Could not reach the identity service.')
    })
    renderPage(<SettingsPage />, '/app/settings', { signOut })

    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Could not reach the identity service.'),
    )
    expect(screen.queryByText('Navigated')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Settings' })).toBeInTheDocument()
  })
})
