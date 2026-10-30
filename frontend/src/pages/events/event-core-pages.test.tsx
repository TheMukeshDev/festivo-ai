import { Route, Routes } from 'react-router-dom'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EventLayout } from '@/components/layout/event-layout'
import { EventCreatePage, EventEditPage } from '@/pages/events/event-form-page'
import { EventOverviewPage } from '@/pages/events/event-overview-page'
import { EventsListPage } from '@/pages/events/events-list-page'
import { eventsApi } from '@/lib/api/queries'
import { renderWithProviders } from '@/test/render'
import {
  makeAiStatus,
  makeBudget,
  makeEvent,
  makeEventList,
  makeTaskList,
  makeTimeline,
  makeVendorList,
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
    event: query(null),
    budget: query(null),
    timeline: query(null),
    tasks: query(null),
    vendors: query(null),
    aiStatus: query(null),
    proposals: query(null),
  }
})

vi.mock('@/features/events/queries', () => ({
  useEventsQuery: () => queries.events,
  useEventQuery: () => queries.event,
  useBudgetQuery: () => queries.budget,
  useTimelineQuery: () => queries.timeline,
  useTasksQuery: () => queries.tasks,
  useVendorsQuery: () => queries.vendors,
  useAiStatusQuery: () => queries.aiStatus,
  useProposalsQuery: () => queries.proposals,
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

function setLoadedWorkspace() {
  resetQuery(queries.events, makeEventList())
  resetQuery(queries.event, makeEvent())
  resetQuery(queries.budget, makeBudget())
  resetQuery(queries.timeline, makeTimeline())
  resetQuery(queries.tasks, makeTaskList())
  resetQuery(queries.vendors, makeVendorList())
  resetQuery(queries.aiStatus, makeAiStatus())
  resetQuery(queries.proposals, { items: [], total: 0, limit: 100, offset: 0 })
}

function renderPage(
  element: React.ReactElement,
  path = '/app/events/:eventId',
  route = '/app/events/event-1',
) {
  return renderWithProviders(
    <Routes>
      <Route path={path} element={element} />
      <Route path="*" element={<p>Navigated</p>} />
    </Routes>,
    { route },
  )
}

function dateOffset(days: number) {
  const value = new Date()
  value.setHours(12, 0, 0, 0)
  value.setDate(value.getDate() + days)
  return value.toISOString().slice(0, 10)
}

beforeEach(() => {
  setLoadedWorkspace()
})

describe('events list page', () => {
  it('renders events and filters them by search', async () => {
    resetQuery(
      queries.events,
      makeEventList([
        makeEvent({ event_date: dateOffset(60) }),
        makeEvent({
          event_id: 'event-2',
          name: 'Goa team offsite',
          event_type: 'community_event',
          event_date: dateOffset(-60),
          location: 'Goa',
        }),
      ]),
    )
    const user = userEvent.setup()
    renderWithProviders(<EventsListPage />)

    expect(await screen.findByText('Ananya and Rohan wedding')).toBeInTheDocument()
    expect(screen.getByText('Goa team offsite')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Search events'), 'goa')

    expect(screen.getByText('Goa team offsite')).toBeInTheDocument()
    expect(screen.queryByText('Ananya and Rohan wedding')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 2 events')).toBeInTheDocument()
  })

  it('shows the empty state when no events exist', async () => {
    resetQuery(queries.events, makeEventList([]))
    renderWithProviders(<EventsListPage />)

    expect(await screen.findByText('No events yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /create your first event/i })).toHaveAttribute(
      'href',
      '/app/events/new',
    )
  })
})

describe('event layout', () => {
  it('renders the event header, navigation, and child content', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/app/events/:eventId" element={<EventLayout />}>
          <Route index element={<p>Overview child</p>} />
        </Route>
      </Routes>,
      { route: '/app/events/event-1' },
    )

    expect(
      await screen.findByRole('heading', { name: 'Ananya and Rohan wedding' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Event sections' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Budget' })).toHaveAttribute(
      'href',
      '/app/events/event-1/budget',
    )
    expect(screen.getByText('Overview child')).toBeInTheDocument()
  })
})

describe('event overview page', () => {
  it('summarizes budget, tasks, vendors, and AI availability', async () => {
    renderPage(<EventOverviewPage />)

    expect(await screen.findByText('Planning checklist')).toBeInTheDocument()
    expect(screen.getByText('Budget remaining')).toBeInTheDocument()
    expect(screen.getByText('Confirm the catering headcount')).toBeInTheDocument()
    expect(screen.getByText('No vendors booked yet')).toBeInTheDocument()
    expect(screen.getByText('Ready for a draft')).toBeInTheDocument()
    expect(screen.getByText('garden theme')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /open ai planning/i })).toHaveAttribute(
      'href',
      '/app/events/event-1/ai-plan',
    )
  })

  it('explains why AI planning is unavailable', async () => {
    resetQuery(
      queries.aiStatus,
      makeAiStatus({ enabled: false, configuration_state: 'disabled' }),
    )
    renderPage(<EventOverviewPage />)

    expect(
      await screen.findByText('AI planning is disabled by the server administrator.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Not available')).toBeInTheDocument()
  })
})

describe('event form pages', () => {
  it('validates required create fields', async () => {
    const user = userEvent.setup()
    renderPage(<EventCreatePage />, '/app/events/new', '/app/events/new')

    await user.clear(screen.getByLabelText(/event name/i))
    await user.clear(screen.getByLabelText(/location/i))
    await user.click(screen.getByRole('button', { name: /create event/i }))

    expect(await screen.findByText('Enter an event name.')).toBeInTheDocument()
    expect(screen.getByText('Enter a location.')).toBeInTheDocument()
  })

  it('submits a new event payload', async () => {
    const create = vi
      .spyOn(eventsApi, 'create')
      .mockResolvedValue(makeEvent({ event_id: 'event-2', name: 'New celebration' }))
    const user = userEvent.setup()
    renderPage(<EventCreatePage />, '/app/events/new', '/app/events/new')

    await user.type(screen.getByLabelText(/event name/i), 'New celebration')
    await user.type(screen.getByLabelText(/location/i), 'Pune')
    await user.click(screen.getByRole('button', { name: /create event/i }))

    await waitFor(() => expect(create).toHaveBeenCalledTimes(1))
    expect(create).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'New celebration',
        location: 'Pune',
        currency: 'INR',
        guest_count: 100,
      }),
    )
  })

  it('prefills the edit form and exposes deletion', async () => {
    renderPage(<EventEditPage />)

    expect(await screen.findByDisplayValue('Ananya and Rohan wedding')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /delete event/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to event/i })).toHaveAttribute(
      'href',
      '/app/events/event-1',
    )
  })
})
