import { describe, expect, it } from 'vitest'

import { budgetCreateSchema, expenseFormSchema } from '@/lib/validation/budget'
import { createEventFormSchema, eventFormSchema, splitLines } from '@/lib/validation/event'
import { taskFormSchema } from '@/lib/validation/task'
import { allowedVendorStatuses } from '@/features/vendors/vendor-utils'

const validEvent = {
  name: 'Garden wedding',
  event_type: 'wedding' as const,
  event_date: '2030-06-15',
  location: 'Bengaluru',
  guest_count: 120,
  budget_amount: '450000.00',
  currency: 'INR',
  timezone: 'Asia/Kolkata',
  description: '',
  preferences_text: 'Vegetarian menu\nLive acoustic music',
  constraints_text: 'No loud music after 10 pm',
}

describe('event validation', () => {
  it('accepts a valid future event', () => {
    expect(eventFormSchema.safeParse(validEvent).success).toBe(true)
  })

  it('rejects a past date for new events and allows it when editing', () => {
    const past = { ...validEvent, event_date: '2000-01-01' }
    expect(eventFormSchema.safeParse(past).success).toBe(false)
    expect(createEventFormSchema({ allowPastDate: true }).safeParse(past).success).toBe(
      true,
    )
  })

  it('rejects invalid budget precision and guest count', () => {
    const result = eventFormSchema.safeParse({
      ...validEvent,
      budget_amount: '1000.999',
      guest_count: 0,
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      const fields = result.error.issues.map((issue) => issue.path.join('.'))
      expect(fields).toContain('budget_amount')
      expect(fields).toContain('guest_count')
    }
  })

  it('caps line-based preferences at 20 entries', () => {
    const result = eventFormSchema.safeParse({
      ...validEvent,
      preferences_text: Array.from({ length: 21 }, (_, index) => `Item ${index}`).join(
        '\n',
      ),
    })
    expect(result.success).toBe(false)
  })

  it('splits and trims non-empty lines', () => {
    expect(splitLines(' one \n\n two \n')).toEqual(['one', 'two'])
  })
})

describe('budget, expense, and task validation', () => {
  it('requires positive money with at most two decimals', () => {
    expect(
      budgetCreateSchema.safeParse({
        total_limit: '100000.50',
        reserve_type: 'percentage',
        reserve_value: '10',
      }).success,
    ).toBe(true)
    expect(
      budgetCreateSchema.safeParse({
        total_limit: '0',
        reserve_type: 'fixed_amount',
        reserve_value: '100',
      }).success,
    ).toBe(false)
  })

  it('accepts only supported expense statuses', () => {
    const base = {
      category: 'Catering',
      name: 'Dinner',
      amount: '5000.00',
      amount_status: 'quoted',
      notes: '',
    }
    expect(expenseFormSchema.safeParse(base).success).toBe(true)
    expect(expenseFormSchema.safeParse({ ...base, amount_status: 'paid' }).success).toBe(
      false,
    )
  })

  it('allows empty optional task costs', () => {
    expect(
      taskFormSchema.safeParse({
        title: 'Confirm menu',
        description: '',
        status: 'pending',
        priority: 'high',
        due_at: '',
        assigned_to: '',
        estimated_cost: '',
        actual_cost: '',
      }).success,
    ).toBe(true)
  })
})

describe('vendor transitions', () => {
  it('only exposes valid lifecycle statuses', () => {
    expect(allowedVendorStatuses('booked')).toEqual(['booked', 'cancelled'])
    expect(allowedVendorStatuses('discovered')).toContain('shortlisted')
    expect(allowedVendorStatuses('rejected')).toEqual(['rejected'])
  })
})
