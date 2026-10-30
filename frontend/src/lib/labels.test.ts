import { describe, expect, it } from 'vitest'

import {
  BUDGET_STATUS_LABELS,
  DEFAULT_EXPENSE_CATEGORIES,
  EVENT_TYPES,
  TASK_PRIORITIES,
  TASK_STATUSES,
  VENDOR_CATEGORIES,
  VENDOR_STATUSES,
  eventTypeLabel,
  expenseStatusLabel,
  taskPriorityLabel,
  taskStatusLabel,
  vendorCategoryLabel,
  vendorStatusLabel,
} from '@/lib/labels'

describe('planning labels', () => {
  it('exposes a label for every supported option', () => {
    expect(EVENT_TYPES.map((item) => item.label)).toEqual([
      'Wedding',
      'Birthday',
      'College event',
      'Community event',
    ])
    expect(VENDOR_CATEGORIES).toHaveLength(11)
    expect(VENDOR_STATUSES).toHaveLength(8)
    expect(TASK_STATUSES).toHaveLength(4)
    expect(TASK_PRIORITIES).toHaveLength(4)
    expect(DEFAULT_EXPENSE_CATEGORIES.length).toBeGreaterThan(0)
    expect(Object.keys(BUDGET_STATUS_LABELS)).toEqual([
      'within_allocation',
      'reserve_consumed',
      'over_budget',
    ])
  })

  it('resolves known values and falls back to the raw value', () => {
    expect(eventTypeLabel('wedding')).toBe('Wedding')
    expect(vendorCategoryLabel('photography_videography')).toBe('Photography & video')
    expect(vendorStatusLabel('shortlisted')).toBe('Shortlisted')
    expect(taskStatusLabel('in_progress')).toBe('In progress')
    expect(taskPriorityLabel('urgent')).toBe('Urgent')
    expect(expenseStatusLabel('confirmed')).toBe('Confirmed')
    expect(eventTypeLabel('unknown' as never)).toBe('unknown')
    expect(vendorCategoryLabel('unknown' as never)).toBe('unknown')
    expect(vendorStatusLabel('unknown' as never)).toBe('unknown')
    expect(taskStatusLabel('unknown' as never)).toBe('unknown')
    expect(taskPriorityLabel('unknown' as never)).toBe('unknown')
    expect(expenseStatusLabel('unknown' as never)).toBe('unknown')
  })
})
