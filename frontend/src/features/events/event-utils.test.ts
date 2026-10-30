import { describe, expect, it } from 'vitest'

import {
  eventPhase,
  eventPhaseLabel,
  sortEventsByDate,
  splitUpcomingAndPast,
} from '@/features/events/event-utils'
import { makeEvent } from '@/test/fixtures'

const now = new Date('2026-06-10T02:00:00.000Z')

describe('event planning helpers', () => {
  it('classifies past, imminent, and upcoming events', () => {
    expect(eventPhase(makeEvent({ event_date: '2026-06-01' }), now)).toBe('past')
    expect(eventPhase(makeEvent({ event_date: '2026-06-20' }), now)).toBe('imminent')
    expect(eventPhase(makeEvent({ event_date: '2026-09-20' }), now)).toBe('upcoming')
  })

  it('labels the event countdown for every planning window', () => {
    expect(eventPhaseLabel(makeEvent({ event_date: '2026-06-01' }), now)).toBe('Completed')
    expect(eventPhaseLabel(makeEvent({ event_date: '2026-06-10' }), now)).toBe('Today')
    expect(eventPhaseLabel(makeEvent({ event_date: '2026-06-11' }), now)).toBe('Tomorrow')
    expect(eventPhaseLabel(makeEvent({ event_date: '2026-06-15' }), now)).toBe(
      '5 days to go',
    )
    expect(eventPhaseLabel(makeEvent({ event_date: '2026-07-01' }), now)).toBe('In 3 weeks')
    expect(eventPhaseLabel(makeEvent({ event_date: '2026-09-20' }), now)).toBe('Upcoming')
  })

  it('sorts copies of the event list without mutating the source', () => {
    const events = [
      makeEvent({ event_id: 'later', event_date: '2026-12-01' }),
      makeEvent({ event_id: 'sooner', event_date: '2026-07-01' }),
    ]

    expect(sortEventsByDate(events).map((event) => event.event_id)).toEqual([
      'sooner',
      'later',
    ])
    expect(sortEventsByDate(events, false).map((event) => event.event_id)).toEqual([
      'later',
      'sooner',
    ])
    expect(events[0]?.event_id).toBe('later')
  })

  it('splits upcoming and past events with the right ordering', () => {
    const result = splitUpcomingAndPast(
      [
        makeEvent({ event_id: 'old', event_date: '2025-01-01' }),
        makeEvent({ event_id: 'future', event_date: '2026-10-01' }),
        makeEvent({ event_id: 'recent', event_date: '2026-01-01' }),
        makeEvent({ event_id: 'soon', event_date: '2026-07-01' }),
      ],
      now,
    )

    expect(result.upcoming.map((event) => event.event_id)).toEqual(['soon', 'future'])
    expect(result.past.map((event) => event.event_id)).toEqual(['recent', 'old'])
  })
})
