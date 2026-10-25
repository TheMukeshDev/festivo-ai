import { describe, expect, it } from 'vitest'

import {
  daysUntil,
  isPastDateTime,
  utcIsoToZonedInput,
  zonedInputToUtcIso,
} from '@/lib/format'

describe('date and timezone helpers', () => {
  it('converts a zoned local input to UTC and back', () => {
    const utc = zonedInputToUtcIso('2030-06-15T18:30', 'Asia/Kolkata')
    expect(utc).toBe('2030-06-15T13:00:00.000Z')
    expect(utcIsoToZonedInput(utc, 'Asia/Kolkata')).toBe('2030-06-15T18:30')
  })

  it('handles daylight-saving offsets', () => {
    expect(zonedInputToUtcIso('2030-07-01T12:00', 'America/New_York')).toBe(
      '2030-07-01T16:00:00.000Z',
    )
    expect(zonedInputToUtcIso('2030-01-01T12:00', 'America/New_York')).toBe(
      '2030-01-01T17:00:00.000Z',
    )
  })

  it('reports past deadlines without treating missing dates as overdue', () => {
    expect(isPastDateTime(null)).toBe(false)
    expect(isPastDateTime('invalid')).toBe(false)
    expect(isPastDateTime('2020-01-01T00:00:00.000Z')).toBe(true)
    expect(isPastDateTime('2099-01-01T00:00:00.000Z')).toBe(false)
  })

  it('counts whole calendar days in the event timezone', () => {
    const now = new Date('2030-06-10T02:00:00.000Z')
    expect(daysUntil('2030-06-10', 'Asia/Kolkata', now)).toBe(0)
    expect(daysUntil('2030-06-15', 'Asia/Kolkata', now)).toBe(5)
  })
})
