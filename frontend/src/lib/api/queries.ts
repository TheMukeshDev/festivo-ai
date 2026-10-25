import type {
  AiPlanRequest,
  BudgetCreateInput,
  BudgetUpdateInput,
  EventCreateInput,
  EventUpdateInput,
  ExpenseCreateInput,
  ExpenseUpdateInput,
  TaskCreateInput,
  TaskPriority,
  TaskStatus,
  TaskUpdateInput,
  VendorCompareInput,
  VendorCreateInput,
  VendorStatus,
  VendorUpdateInput,
} from '@/types/api'
import { API_PREFIX, apiRequest } from '@/lib/api/client'

const events = `${API_PREFIX}/events`

function eventPath(eventId: string): string {
  return `${events}/${encodeURIComponent(eventId)}`
}

export const eventsApi = {
  list(limit = 100, offset = 0) {
    return apiRequest<import('@/types/api').EventListResponse>(
      `${events}?limit=${limit}&offset=${offset}`,
    )
  },
  get(eventId: string) {
    return apiRequest<import('@/types/api').EventRecord>(eventPath(eventId))
  },
  create(payload: EventCreateInput) {
    return apiRequest<import('@/types/api').EventRecord>(events, {
      method: 'POST',
      body: payload,
    })
  },
  update(eventId: string, payload: EventUpdateInput) {
    return apiRequest<import('@/types/api').EventRecord>(eventPath(eventId), {
      method: 'PATCH',
      body: payload,
    })
  },
  remove(eventId: string) {
    return apiRequest<void>(eventPath(eventId), { method: 'DELETE' })
  },
}

export const budgetsApi = {
  get(eventId: string) {
    return apiRequest<import('@/types/api').BudgetResponse>(`${eventPath(eventId)}/budget`)
  },
  create(eventId: string, payload: BudgetCreateInput) {
    return apiRequest<import('@/types/api').BudgetResponse>(
      `${eventPath(eventId)}/budget`,
      { method: 'POST', body: payload },
    )
  },
  update(eventId: string, payload: BudgetUpdateInput) {
    return apiRequest<import('@/types/api').BudgetResponse>(
      `${eventPath(eventId)}/budget`,
      { method: 'PATCH', body: payload },
    )
  },
  addExpense(eventId: string, payload: ExpenseCreateInput) {
    return apiRequest<import('@/types/api').BudgetResponse>(
      `${eventPath(eventId)}/budget/expenses`,
      { method: 'POST', body: payload },
    )
  },
  updateExpense(eventId: string, expenseId: string, payload: ExpenseUpdateInput) {
    return apiRequest<import('@/types/api').BudgetResponse>(
      `${eventPath(eventId)}/budget/expenses/${encodeURIComponent(expenseId)}`,
      { method: 'PATCH', body: payload },
    )
  },
  deleteExpense(eventId: string, expenseId: string, expectedVersion: number) {
    return apiRequest<import('@/types/api').BudgetResponse>(
      `${eventPath(eventId)}/budget/expenses/${encodeURIComponent(expenseId)}?expected_version=${expectedVersion}`,
      { method: 'DELETE' },
    )
  },
}

export interface TaskFilters {
  status?: TaskStatus
  priority?: TaskPriority
  timelineId?: string
}

export const timelinesApi = {
  get(eventId: string) {
    return apiRequest<import('@/types/api').TimelineRecord>(
      `${eventPath(eventId)}/timeline`,
    )
  },
  generate(eventId: string) {
    return apiRequest<import('@/types/api').TimelineRecord>(
      `${eventPath(eventId)}/timeline`,
      { method: 'POST' },
    )
  },
  regenerate(eventId: string) {
    return apiRequest<import('@/types/api').TimelineRecord>(
      `${eventPath(eventId)}/timeline/regenerate`,
      { method: 'POST' },
    )
  },
  listTasks(eventId: string, filters: TaskFilters = {}) {
    const params = new URLSearchParams({ limit: '100', offset: '0' })
    if (filters.status) params.set('status', filters.status)
    if (filters.priority) params.set('priority', filters.priority)
    if (filters.timelineId) params.set('timeline_id', filters.timelineId)
    return apiRequest<import('@/types/api').TaskListResponse>(
      `${eventPath(eventId)}/tasks?${params.toString()}`,
    )
  },
  createTask(eventId: string, payload: TaskCreateInput) {
    return apiRequest<import('@/types/api').TaskRecord>(`${eventPath(eventId)}/tasks`, {
      method: 'POST',
      body: payload,
    })
  },
  updateTask(eventId: string, taskId: string, payload: TaskUpdateInput) {
    return apiRequest<import('@/types/api').TaskRecord>(
      `${eventPath(eventId)}/tasks/${encodeURIComponent(taskId)}`,
      { method: 'PATCH', body: payload },
    )
  },
  deleteTask(eventId: string, taskId: string) {
    return apiRequest<void>(`${eventPath(eventId)}/tasks/${encodeURIComponent(taskId)}`, {
      method: 'DELETE',
    })
  },
}

export interface VendorFilters {
  category?: string
  status?: VendorStatus
  name?: string
}

export const vendorsApi = {
  list(eventId: string, filters: VendorFilters = {}) {
    const params = new URLSearchParams({ limit: '100', offset: '0' })
    if (filters.category) params.set('category', filters.category)
    if (filters.status) params.set('status', filters.status)
    if (filters.name) params.set('name', filters.name)
    return apiRequest<import('@/types/api').VendorListResponse>(
      `${eventPath(eventId)}/vendors?${params.toString()}`,
    )
  },
  get(eventId: string, vendorId: string) {
    return apiRequest<import('@/types/api').VendorRecord>(
      `${eventPath(eventId)}/vendors/${encodeURIComponent(vendorId)}`,
    )
  },
  create(eventId: string, payload: VendorCreateInput) {
    return apiRequest<import('@/types/api').VendorRecord>(`${eventPath(eventId)}/vendors`, {
      method: 'POST',
      body: payload,
    })
  },
  update(eventId: string, vendorId: string, payload: VendorUpdateInput) {
    return apiRequest<import('@/types/api').VendorRecord>(
      `${eventPath(eventId)}/vendors/${encodeURIComponent(vendorId)}`,
      { method: 'PATCH', body: payload },
    )
  },
  remove(eventId: string, vendorId: string) {
    return apiRequest<void>(
      `${eventPath(eventId)}/vendors/${encodeURIComponent(vendorId)}`,
      { method: 'DELETE' },
    )
  },
  compare(eventId: string, payload: VendorCompareInput) {
    return apiRequest<import('@/types/api').VendorCompareResponse>(
      `${eventPath(eventId)}/vendors/compare`,
      { method: 'POST', body: payload },
    )
  },
}

export const aiPlanningApi = {
  status(eventId: string) {
    return apiRequest<import('@/types/api').AiPlanStatus>(
      `${eventPath(eventId)}/ai-plan/status`,
    )
  },
  generate(eventId: string, payload: AiPlanRequest) {
    return apiRequest<import('@/types/api').AiPlanResponse>(
      `${eventPath(eventId)}/ai-plan`,
      { method: 'POST', body: payload, timeoutMs: 75_000 },
    )
  },
  refine(eventId: string, payload: AiPlanRequest) {
    return apiRequest<import('@/types/api').AiPlanResponse>(
      `${eventPath(eventId)}/ai-plan/refine`,
      { method: 'POST', body: payload, timeoutMs: 75_000 },
    )
  },
}

export const queryKeys = {
  events: ['events'] as const,
  event: (eventId: string) => ['events', eventId] as const,
  budget: (eventId: string) => ['events', eventId, 'budget'] as const,
  timeline: (eventId: string) => ['events', eventId, 'timeline'] as const,
  tasks: (eventId: string, filters: TaskFilters = {}) =>
    ['events', eventId, 'tasks', filters] as const,
  vendors: (eventId: string, filters: VendorFilters = {}) =>
    ['events', eventId, 'vendors', filters] as const,
  vendor: (eventId: string, vendorId: string) =>
    ['events', eventId, 'vendors', 'detail', vendorId] as const,
  vendorCompare: (eventId: string) => ['events', eventId, 'vendors', 'compare'] as const,
  aiStatus: (eventId: string) => ['events', eventId, 'ai-plan', 'status'] as const,
  aiPlan: (eventId: string) => ['events', eventId, 'ai-plan'] as const,
}
