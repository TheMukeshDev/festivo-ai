import { beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  AiPlanRequest,
  BudgetCreateInput,
  BudgetUpdateInput,
  EventCreateInput,
  EventUpdateInput,
  ExpenseCreateInput,
  ExpenseUpdateInput,
  TaskCreateInput,
  TaskUpdateInput,
  VendorCompareInput,
  VendorCreateInput,
  VendorUpdateInput,
} from '@/types/api'
import {
  aiPlanningApi,
  budgetsApi,
  eventsApi,
  exportsApi,
  proposalsApi,
  queryKeys,
  timelinesApi,
  vendorsApi,
} from './queries'

const client = vi.hoisted(() => ({
  API_PREFIX: '/api',
  apiRequest: vi.fn(),
  apiDownload: vi.fn(),
}))

vi.mock('@/lib/api/client', () => client)

const { apiRequest, apiDownload } = client

beforeEach(() => {
  apiRequest.mockReset().mockResolvedValue({})
  apiDownload.mockReset().mockResolvedValue({
    blob: new Blob(['file']),
    filename: 'file',
    contentType: 'application/octet-stream',
  })
})

describe('eventsApi', () => {
  const eventPayload = { name: 'Wedding' } as EventCreateInput
  const eventUpdate = { name: 'Updated' } as EventUpdateInput

  it('lists events with pagination defaults and overrides', async () => {
    await eventsApi.list()
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events?limit=100&offset=0')

    await eventsApi.list(20, 40)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events?limit=20&offset=40')
  })

  it('gets, creates, updates, and removes an event', async () => {
    await eventsApi.get('event/one')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event%2Fone')

    await eventsApi.create(eventPayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events', {
      method: 'POST',
      body: eventPayload,
    })

    await eventsApi.update('event-1', eventUpdate)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1', {
      method: 'PATCH',
      body: eventUpdate,
    })

    await eventsApi.remove('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1', {
      method: 'DELETE',
    })
  })
})

describe('budgetsApi', () => {
  const createPayload = { total_limit: '1000.00' } as BudgetCreateInput
  const updatePayload = { expected_version: 1 } as BudgetUpdateInput
  const expensePayload: ExpenseCreateInput = {
    expected_version: 1,
    category: 'decor',
    name: 'Decor',
    amount: '1000.00',
    amount_status: 'estimated',
  }
  const expenseUpdate = { expected_version: 2 } as ExpenseUpdateInput

  it('gets, creates, and updates the budget', async () => {
    await budgetsApi.get('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/budget')

    await budgetsApi.create('event-1', createPayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/budget', {
      method: 'POST',
      body: createPayload,
    })

    await budgetsApi.update('event-1', updatePayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/budget', {
      method: 'PATCH',
      body: updatePayload,
    })
  })

  it('adds, updates, and deletes expenses', async () => {
    await budgetsApi.addExpense('event-1', expensePayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/budget/expenses', {
      method: 'POST',
      body: expensePayload,
    })

    await budgetsApi.updateExpense('event-1', 'expense/one', expenseUpdate)
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/budget/expenses/expense%2Fone',
      { method: 'PATCH', body: expenseUpdate },
    )

    await budgetsApi.deleteExpense('event-1', 'expense-1', 3)
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/budget/expenses/expense-1?expected_version=3',
      { method: 'DELETE' },
    )
  })
})

describe('timelinesApi', () => {
  const taskPayload = { title: 'Book venue' } as TaskCreateInput
  const taskUpdate = { title: 'Book venue now' } as TaskUpdateInput

  it('gets, generates, and regenerates a timeline', async () => {
    await timelinesApi.get('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/timeline')

    await timelinesApi.generate('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/timeline', {
      method: 'POST',
    })

    await timelinesApi.regenerate('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/timeline/regenerate', {
      method: 'POST',
    })
  })

  it('builds task filters and manages tasks', async () => {
    await timelinesApi.listTasks('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/tasks?limit=100&offset=0',
    )

    await timelinesApi.listTasks('event-1', {
      status: 'completed',
      priority: 'high',
      timelineId: 'timeline/one',
    })
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/tasks?limit=100&offset=0&status=completed&priority=high&timeline_id=timeline%2Fone',
    )

    await timelinesApi.createTask('event-1', taskPayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/tasks', {
      method: 'POST',
      body: taskPayload,
    })

    await timelinesApi.updateTask('event-1', 'task/one', taskUpdate)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/tasks/task%2Fone', {
      method: 'PATCH',
      body: taskUpdate,
    })

    await timelinesApi.deleteTask('event-1', 'task-1')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/tasks/task-1', {
      method: 'DELETE',
    })
  })
})

describe('vendorsApi', () => {
  const vendorPayload = { name: 'Caterer' } as VendorCreateInput
  const vendorUpdate = { name: 'Caterer Ltd' } as VendorUpdateInput
  const comparePayload = { vendor_ids: ['vendor-1'] } as VendorCompareInput

  it('builds vendor filters and fetches records', async () => {
    await vendorsApi.list('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/vendors?limit=100&offset=0',
    )

    await vendorsApi.list('event-1', {
      category: 'catering',
      status: 'shortlisted',
      name: 'Saffron Table',
    })
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/vendors?limit=100&offset=0&category=catering&status=shortlisted&name=Saffron+Table',
    )

    await vendorsApi.get('event-1', 'vendor/one')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/vendors/vendor%2Fone')
  })

  it('creates, updates, removes, and compares vendors', async () => {
    await vendorsApi.create('event-1', vendorPayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/vendors', {
      method: 'POST',
      body: vendorPayload,
    })

    await vendorsApi.update('event-1', 'vendor-1', vendorUpdate)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/vendors/vendor-1', {
      method: 'PATCH',
      body: vendorUpdate,
    })

    await vendorsApi.remove('event-1', 'vendor-1')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/vendors/vendor-1', {
      method: 'DELETE',
    })

    await vendorsApi.compare('event-1', comparePayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/vendors/compare', {
      method: 'POST',
      body: comparePayload,
    })
  })
})

describe('AI and proposal APIs', () => {
  const planPayload = {
    preferences: {},
    focus_areas: ['budget'],
  } as AiPlanRequest

  it('reads AI status and sends generation and refinement requests', async () => {
    await aiPlanningApi.status('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/ai-plan/status')

    await aiPlanningApi.generate('event-1', planPayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/ai-plan', {
      method: 'POST',
      body: planPayload,
      timeoutMs: 75_000,
    })

    await aiPlanningApi.refine('event-1', planPayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/ai-plan/refine', {
      method: 'POST',
      body: planPayload,
      timeoutMs: 75_000,
    })
  })

  it('lists and generates proposals', async () => {
    await proposalsApi.list('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/proposals?limit=100&offset=0',
    )

    await proposalsApi.generate('event-1')
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/proposals/generate', {
      method: 'POST',
      body: { preferences: {}, focus_areas: [] },
      timeoutMs: 75_000,
    })

    await proposalsApi.generate('event-1', planPayload)
    expect(apiRequest).toHaveBeenLastCalledWith('/api/events/event-1/proposals/generate', {
      method: 'POST',
      body: planPayload,
      timeoutMs: 75_000,
    })
  })

  it('approves and rejects proposals with optional item lists and reasons', async () => {
    await proposalsApi.approve('event-1', 'proposal/one')
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/proposals/proposal%2Fone/approve',
      { method: 'POST', body: {} },
    )

    await proposalsApi.approve('event-1', 'proposal-1', ['item-1'])
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/proposals/proposal-1/approve',
      { method: 'POST', body: { item_ids: ['item-1'] } },
    )

    await proposalsApi.reject('event-1', 'proposal-1')
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/proposals/proposal-1/reject',
      { method: 'POST', body: {} },
    )

    await proposalsApi.reject('event-1', 'proposal-1', ['item-1', 'item-2'], 'Too costly')
    expect(apiRequest).toHaveBeenLastCalledWith(
      '/api/events/event-1/proposals/proposal-1/reject',
      {
        method: 'POST',
        body: { item_ids: ['item-1', 'item-2'], reason: 'Too costly' },
      },
    )
  })
})

describe('exportsApi', () => {
  it('downloads PDF and CSV exports with stable filenames', async () => {
    await exportsApi.pdf('event/one')
    expect(apiDownload).toHaveBeenLastCalledWith(
      '/api/events/event%2Fone/export/pdf',
      'festivo-event/one.pdf',
    )

    await exportsApi.csv('event-1')
    expect(apiDownload).toHaveBeenLastCalledWith(
      '/api/events/event-1/export/csv',
      'festivo-event-1.csv',
    )
  })
})

describe('queryKeys', () => {
  it('builds stable cache keys for event resources', () => {
    expect(queryKeys.events).toEqual(['events'])
    expect(queryKeys.event('event-1')).toEqual(['events', 'event-1'])
    expect(queryKeys.budget('event-1')).toEqual(['events', 'event-1', 'budget'])
    expect(queryKeys.timeline('event-1')).toEqual(['events', 'event-1', 'timeline'])
    expect(queryKeys.tasks('event-1')).toEqual(['events', 'event-1', 'tasks', {}])
    expect(queryKeys.tasks('event-1', { status: 'pending' })).toEqual([
      'events',
      'event-1',
      'tasks',
      { status: 'pending' },
    ])
    expect(queryKeys.vendors('event-1')).toEqual(['events', 'event-1', 'vendors', {}])
    expect(queryKeys.vendor('event-1', 'vendor-1')).toEqual([
      'events',
      'event-1',
      'vendors',
      'detail',
      'vendor-1',
    ])
    expect(queryKeys.vendorCompare('event-1')).toEqual([
      'events',
      'event-1',
      'vendors',
      'compare',
    ])
    expect(queryKeys.aiStatus('event-1')).toEqual([
      'events',
      'event-1',
      'ai-plan',
      'status',
    ])
    expect(queryKeys.aiPlan('event-1')).toEqual(['events', 'event-1', 'ai-plan'])
    expect(queryKeys.proposals('event-1')).toEqual(['events', 'event-1', 'proposals'])
  })
})
