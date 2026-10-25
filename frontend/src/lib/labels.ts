import type {
  BudgetStatus,
  EventType,
  ExpenseStatus,
  TaskPriority,
  TaskStatus,
  VendorCategory,
  VendorStatus,
} from '@/types/api'

export const EVENT_TYPES: { value: EventType; label: string; description: string }[] = [
  {
    value: 'wedding',
    label: 'Wedding',
    description: 'Ceremonies, receptions, and multi-day celebrations.',
  },
  {
    value: 'birthday',
    label: 'Birthday',
    description: 'Milestone parties, dinners, and intimate gatherings.',
  },
  {
    value: 'college_event',
    label: 'College event',
    description: 'Fests, cultural nights, and student celebrations.',
  },
  {
    value: 'community_event',
    label: 'Community event',
    description: 'Neighbourhood, club, and public gatherings.',
  },
]

export const eventTypeLabel = (value: EventType): string =>
  EVENT_TYPES.find((item) => item.value === value)?.label ?? value

export const VENDOR_CATEGORIES: { value: VendorCategory; label: string }[] = [
  { value: 'venue', label: 'Venue' },
  { value: 'catering', label: 'Catering' },
  { value: 'decoration', label: 'Decoration' },
  { value: 'photography_videography', label: 'Photography & video' },
  { value: 'entertainment_music', label: 'Entertainment & music' },
  { value: 'makeup_styling', label: 'Makeup & styling' },
  { value: 'invitations_printing', label: 'Invitations & printing' },
  { value: 'transportation', label: 'Transportation' },
  { value: 'equipment_rentals', label: 'Equipment rentals' },
  { value: 'event_coordination', label: 'Event coordination' },
  { value: 'other', label: 'Other' },
]

export const vendorCategoryLabel = (value: VendorCategory): string =>
  VENDOR_CATEGORIES.find((item) => item.value === value)?.label ?? value

export const VENDOR_STATUSES: { value: VendorStatus; label: string }[] = [
  { value: 'discovered', label: 'Discovered' },
  { value: 'shortlisted', label: 'Shortlisted' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'quoted', label: 'Quoted' },
  { value: 'selected', label: 'Selected' },
  { value: 'booked', label: 'Booked' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'cancelled', label: 'Cancelled' },
]

export const vendorStatusLabel = (value: VendorStatus): string =>
  VENDOR_STATUSES.find((item) => item.value === value)?.label ?? value

export const vendorStatusTone: Record<
  VendorStatus,
  'neutral' | 'primary' | 'info' | 'success' | 'warning' | 'danger'
> = {
  discovered: 'neutral',
  shortlisted: 'primary',
  contacted: 'info',
  quoted: 'warning',
  selected: 'primary',
  booked: 'success',
  rejected: 'danger',
  cancelled: 'danger',
}

export const ALLOWED_VENDOR_TRANSITIONS: Record<VendorStatus, VendorStatus[]> = {
  discovered: ['shortlisted', 'contacted', 'rejected', 'cancelled'],
  shortlisted: ['contacted', 'quoted', 'rejected', 'cancelled'],
  contacted: ['quoted', 'shortlisted', 'rejected', 'cancelled'],
  quoted: ['selected', 'contacted', 'rejected', 'cancelled'],
  selected: ['booked', 'quoted', 'rejected', 'cancelled'],
  booked: ['cancelled'],
  rejected: [],
  cancelled: [],
}

export const TASK_STATUSES: { value: TaskStatus; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
]

export const taskStatusLabel = (value: TaskStatus): string =>
  TASK_STATUSES.find((item) => item.value === value)?.label ?? value

export const taskStatusTone: Record<
  TaskStatus,
  'neutral' | 'primary' | 'info' | 'success' | 'warning' | 'danger'
> = {
  pending: 'neutral',
  in_progress: 'info',
  completed: 'success',
  cancelled: 'neutral',
}

export const TASK_PRIORITIES: { value: TaskPriority; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
]

export const taskPriorityLabel = (value: TaskPriority): string =>
  TASK_PRIORITIES.find((item) => item.value === value)?.label ?? value

export const taskPriorityTone: Record<
  TaskPriority,
  'neutral' | 'info' | 'warning' | 'danger'
> = {
  low: 'neutral',
  medium: 'info',
  high: 'warning',
  urgent: 'danger',
}

export const EXPENSE_STATUSES: { value: ExpenseStatus; label: string; helper: string }[] = [
  {
    value: 'estimated',
    label: 'Estimated',
    helper: 'A working number that has not been quoted by a vendor.',
  },
  {
    value: 'quoted',
    label: 'Quoted',
    helper: 'A figure supplied by a vendor or venue, not yet confirmed.',
  },
  {
    value: 'confirmed',
    label: 'Confirmed',
    helper: 'An amount you have explicitly confirmed for this plan.',
  },
]

export const expenseStatusLabel = (value: ExpenseStatus): string =>
  EXPENSE_STATUSES.find((item) => item.value === value)?.label ?? value

export const BUDGET_STATUS_LABELS: Record<BudgetStatus, string> = {
  within_allocation: 'Within allocation',
  reserve_consumed: 'Using reserve',
  over_budget: 'Over budget',
}

export const AI_PRIORITY_LABELS: Record<string, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

export const BUDGET_SOURCE_LABELS: Record<string, string> = {
  suggested_allocation: 'Suggested allocation',
  user_provided_budget: 'Provided budget',
  existing_estimate_or_quote: 'Existing estimate or quote',
  confirmed_expense: 'Confirmed expense',
}

export const DEFAULT_EXPENSE_CATEGORIES = [
  'Venue and Logistics',
  'Catering and Refreshments',
  'Decoration and Theme',
  'Photography and Videography',
  'Entertainment and Activities',
  'Transportation',
  'Miscellaneous',
]
