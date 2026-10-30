import type { ReactElement } from 'react'
import { Route, Routes } from 'react-router-dom'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AiPlanPage } from '@/pages/events/ai-plan-page'
import { BudgetPage } from '@/pages/events/budget-page'
import { ExportsPage } from '@/pages/events/exports-page'
import { ProposalsPage } from '@/pages/events/proposals-page'
import { TimelinePage } from '@/pages/events/timeline-page'
import { VendorComparePage } from '@/pages/events/vendor-compare-page'
import { VendorsPage } from '@/pages/events/vendors-page'
import { aiPlanningApi, exportsApi, vendorsApi } from '@/lib/api/queries'
import { renderWithProviders } from '@/test/render'
import {
  makeAiPlan,
  makeAiStatus,
  makeBudget,
  makeEvent,
  makeProposal,
  makeProposalList,
  makeTaskList,
  makeTimeline,
  makeVendor,
  makeVendorCompare,
  makeVendorList,
} from '@/test/fixtures'

const saveDownloadedFile = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api/client')>()
  return { ...actual, saveDownloadedFile }
})

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

function resetWorkspace() {
  resetQuery(queries.event, makeEvent())
  resetQuery(queries.budget, makeBudget())
  resetQuery(queries.timeline, makeTimeline())
  resetQuery(queries.tasks, makeTaskList())
  resetQuery(queries.vendors, makeVendorList())
  resetQuery(queries.aiStatus, makeAiStatus())
  resetQuery(queries.proposals, makeProposalList())
}

function renderPage(
  element: ReactElement,
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

beforeEach(() => {
  vi.restoreAllMocks()
  saveDownloadedFile.mockClear()
  resetWorkspace()
})

describe('vendors page', () => {
  it('renders vendor records and comparison selection', async () => {
    const user = userEvent.setup()
    renderPage(<VendorsPage />)

    expect(await screen.findByText('Vendor shortlist')).toBeInTheDocument()
    expect(screen.getByText('Saffron Table')).toBeInTheDocument()
    expect(screen.getByText('INR 575000.00 (quoted)')).toBeInTheDocument()

    await user.click(
      screen.getByRole('checkbox', { name: 'Select Saffron Table for comparison' }),
    )

    expect(screen.getByText(/1 selected for comparison/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /compare/i })).toBeDisabled()
  })

  it('shows the empty shortlist state', async () => {
    resetQuery(queries.vendors, makeVendorList([]))
    renderPage(<VendorsPage />)

    expect(await screen.findByText('Start a vendor shortlist')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /add your first vendor/i }),
    ).toBeInTheDocument()
  })
})

describe('budget page', () => {
  it('renders budget health, categories, and expenses', async () => {
    renderPage(<BudgetPage />)

    expect(await screen.findByText('Budget health')).toBeInTheDocument()
    expect(screen.getByText('Category breakdown')).toBeInTheDocument()
    expect(screen.getByText('Courtyard booking')).toBeInTheDocument()
    expect(
      screen.getByText('Planned spending is within the available budget.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add expense/i })).toBeInTheDocument()
  })

  it('prompts for budget setup when none exists', async () => {
    resetQuery(queries.budget, null)
    renderPage(<BudgetPage />)

    expect(await screen.findByText('Set up the budget')).toBeInTheDocument()
    expect(screen.getByLabelText(/total budget/i)).toHaveValue('2500000.00')
  })
})

describe('timeline page', () => {
  it('renders the generated timeline and task list', async () => {
    renderPage(<TimelinePage />)

    expect(await screen.findByText('Task list')).toBeInTheDocument()
    expect(screen.getByText('All tasks')).toBeInTheDocument()
    expect(screen.getByText('Confirm the catering headcount')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /add missing starter tasks/i }),
    ).toBeInTheDocument()
  })

  it('offers timeline generation when none exists', async () => {
    resetQuery(queries.timeline, null)
    resetQuery(queries.tasks, makeTaskList([]))
    renderPage(<TimelinePage />)

    expect(
      await screen.findByText('Tasks without a generated timeline'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'No tasks yet', level: 3 }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /generate timeline/i })).toBeInTheDocument()
  })
})

describe('proposals page', () => {
  it('shows proposals and opens approval confirmation', async () => {
    const user = userEvent.setup()
    renderPage(<ProposalsPage />)

    expect(await screen.findByText('Garden celebration plan')).toBeInTheDocument()
    expect(screen.getByText('Pending review')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /approve eligible items/i }))

    expect(await screen.findByText('Approve this proposal?')).toBeInTheDocument()
  })

  it('shows the empty proposals state', async () => {
    resetQuery(queries.proposals, makeProposalList([]))
    renderPage(<ProposalsPage />)

    expect(await screen.findByText('No proposals yet')).toBeInTheDocument()
  })
})

describe('exports page', () => {
  it('downloads the PDF report', async () => {
    const file = {
      blob: new Blob(['report']),
      filename: 'festivo-event-1.pdf',
      contentType: 'application/pdf',
    }
    const pdf = vi.spyOn(exportsApi, 'pdf').mockResolvedValue(file)
    const user = userEvent.setup()
    renderPage(<ExportsPage />)

    await user.click(await screen.findByRole('button', { name: /download pdf/i }))

    await waitFor(() => expect(pdf).toHaveBeenCalledWith('event-1'))
    expect(saveDownloadedFile).toHaveBeenCalledWith(file)
  })
})

describe('AI planning page', () => {
  it('requires a focus area and renders generated suggestions', async () => {
    const generate = vi.spyOn(aiPlanningApi, 'generate').mockResolvedValue({
      ...makeProposal(),
      ai_plan: makeAiPlan(),
    })
    const user = userEvent.setup()
    renderPage(<AiPlanPage />)

    expect(await screen.findByText('Provider status')).toBeInTheDocument()
    expect(screen.getByText(/AI provider configured/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /generate suggestions/i }))

    expect(
      await screen.findByText('Choose at least one focus area for the plan.'),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: /budget allocation/i }))
    await user.click(screen.getByRole('button', { name: /generate suggestions/i }))

    await waitFor(() => expect(generate).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Planning suggestions')).toBeInTheDocument()
    expect(
      screen.getByText(
        'A garden celebration with a clear budget and a practical task order.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('Timeline notes')).toBeInTheDocument()
  })

  it('disables generation when the provider is unavailable', async () => {
    resetQuery(
      queries.aiStatus,
      makeAiStatus({ enabled: false, configuration_state: 'incomplete' }),
    )
    renderPage(<AiPlanPage />)

    expect(await screen.findByText('Unavailable')).toBeInTheDocument()
    expect(
      screen.getByText(/AI planning is not available for this workspace/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /generate suggestions/i })).toBeDisabled()
  })
})

describe('vendor comparison page', () => {
  it('validates the maximum price and renders a comparison', async () => {
    resetQuery(
      queries.vendors,
      makeVendorList([
        makeVendor(),
        makeVendor({
          vendor_id: 'vendor-2',
          name: 'Marigold Kitchens',
          status: 'contacted',
          quoted_cost: null,
          estimated_cost: null,
          price_min: null,
          price_max: null,
          rating: null,
        }),
      ]),
    )
    const compare = vi.spyOn(vendorsApi, 'compare').mockResolvedValue(makeVendorCompare())
    const user = userEvent.setup()
    renderPage(
      <VendorComparePage />,
      '/app/events/:eventId/vendors/compare',
      '/app/events/event-1/vendors/compare?ids=vendor-1,vendor-2',
    )

    expect(await screen.findByText('Compare vendors')).toBeInTheDocument()
    expect(
      screen.getByText('2 of 10 selected · 2 valid for comparison'),
    ).toBeInTheDocument()

    await user.type(screen.getByLabelText(/maximum price/i), 'not-a-price')
    await user.click(screen.getByRole('button', { name: /compare selected/i }))

    expect(
      await screen.findByText('Enter a valid maximum price with up to two decimal places.'),
    ).toBeInTheDocument()
    expect(compare).not.toHaveBeenCalled()

    await user.clear(screen.getByLabelText(/maximum price/i))
    await user.type(screen.getByLabelText(/maximum price/i), '600000')
    await user.click(screen.getByRole('button', { name: /compare selected/i }))

    await waitFor(() => expect(compare).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('How Festivo compared')).toBeInTheDocument()
    expect(
      screen.getByText('Saffron Table has the most complete recorded price information.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Missing prices are not guessed.')).toBeInTheDocument()
  })
})
