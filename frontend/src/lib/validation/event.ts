import { z } from 'zod'

import { todayInputValue } from '@/lib/format'

const moneyPattern = /^\d{1,9}(\.\d{1,2})?$/

function validateLines(value: string, label: string) {
  const lines = value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  if (lines.length > 20) {
    return `${label} can include at most 20 entries.`
  }
  if (lines.some((line) => line.length > 200)) {
    return `Each ${label.toLowerCase().replace(/s$/, '')} must be 200 characters or fewer.`
  }
  return true
}

export function createEventFormSchema(options: { allowPastDate?: boolean } = {}) {
  return z.object({
    name: z
      .string()
      .trim()
      .min(1, 'Enter an event name.')
      .max(100, 'Use 100 characters or fewer.'),
    event_type: z.enum(['wedding', 'birthday', 'college_event', 'community_event'], {
      errorMap: () => ({ message: 'Choose an event type.' }),
    }),
    event_date: z
      .string()
      .min(1, 'Choose an event date.')
      .refine(
        (value) => options.allowPastDate === true || value >= todayInputValue(),
        'Event date must be today or later.',
      ),
    location: z
      .string()
      .trim()
      .min(1, 'Enter a location.')
      .max(200, 'Use 200 characters or fewer.'),
    guest_count: z
      .number({ invalid_type_error: 'Enter the expected guest count.' })
      .int('Guest count must be a whole number.')
      .min(1, 'Guest count must be at least 1.')
      .max(10_000, 'Guest count cannot exceed 10,000.'),
    budget_amount: z
      .string()
      .trim()
      .min(1, 'Enter a budget.')
      .regex(moneyPattern, 'Use a valid amount with up to two decimal places.')
      .refine((value) => Number(value) > 0, 'Budget must be greater than zero.'),
    currency: z
      .string()
      .trim()
      .length(3, 'Use a three-letter currency code.')
      .regex(/^[A-Za-z]{3}$/, 'Use a three-letter currency code.'),
    timezone: z.string().trim().min(1, 'Choose a timezone.'),
    description: z.string().max(2000, 'Use 2,000 characters or fewer.'),
    preferences_text: z
      .string()
      .max(4000, 'Keep preferences concise.')
      .superRefine((value, context) => {
        const result = validateLines(value, 'Preferences')
        if (result !== true) context.addIssue({ code: 'custom', message: result })
      }),
    constraints_text: z
      .string()
      .max(4000, 'Keep constraints concise.')
      .superRefine((value, context) => {
        const result = validateLines(value, 'Constraints')
        if (result !== true) context.addIssue({ code: 'custom', message: result })
      }),
  })
}

export const eventFormSchema = createEventFormSchema()

export type EventFormValues = z.infer<typeof eventFormSchema>

export function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 20)
}

export function joinLines(value: string[] | null | undefined): string {
  return (value ?? []).join('\n')
}

export const eventFormDefaults: EventFormValues = {
  name: '',
  event_type: 'wedding',
  event_date: todayInputValue(),
  location: '',
  guest_count: 100,
  budget_amount: '100000.00',
  currency: 'INR',
  timezone: 'Asia/Kolkata',
  description: '',
  preferences_text: '',
  constraints_text: '',
}
