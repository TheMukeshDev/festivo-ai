import type { EventRecord } from '@/types/api'
import { daysUntil } from '@/lib/format'

export type EventPhase = 'past' | 'imminent' | 'upcoming'

export function eventPhase(event: EventRecord, now = new Date()): EventPhase {
  const days = daysUntil(event.event_date, event.timezone, now)
  if (days < 0) return 'past'
  if (days <= 14) return 'imminent'
  return 'upcoming'
}

export function eventPhaseLabel(event: EventRecord, now = new Date()): string {
  const days = daysUntil(event.event_date, event.timezone, now)
  if (days < 0) return 'Completed'
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days <= 14) return `${days} days to go`
  if (days <= 60) return `In ${Math.round(days / 7)} weeks`
  return 'Upcoming'
}

export function sortEventsByDate(events: EventRecord[], ascending = true): EventRecord[] {
  return [...events].sort((a, b) => {
    const comparison = a.event_date.localeCompare(b.event_date)
    return ascending ? comparison : -comparison
  })
}

export function splitUpcomingAndPast(events: EventRecord[], now = new Date()) {
  const upcoming: EventRecord[] = []
  const past: EventRecord[] = []
  for (const event of events) {
    if (eventPhase(event, now) === 'past') past.push(event)
    else upcoming.push(event)
  }
  return {
    upcoming: sortEventsByDate(upcoming, true),
    past: sortEventsByDate(past, false),
  }
}
