import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  CalendarDays,
  CalendarPlus,
  MapPin,
  Search,
  SlidersHorizontal,
  Users,
  X,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { Input } from '@/components/ui/input'
import { PageHeader } from '@/components/ui/page-header'
import { PageSkeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useEventsQuery } from '@/features/events/queries'
import {
  eventPhaseLabel,
  sortEventsByDate,
  splitUpcomingAndPast,
} from '@/features/events/event-utils'
import { formatDate, formatMoney } from '@/lib/format'
import { EVENT_TYPES, eventTypeLabel } from '@/lib/labels'
import type { EventRecord, EventType } from '@/types/api'

type TypeFilter = EventType | 'all'
type StatusFilter = 'all' | 'upcoming' | 'past'

function EventListItem({ event }: { event: EventRecord }) {
  return (
    <Link
      to={`/app/events/${event.event_id}`}
      className="group flex flex-col gap-4 rounded-lg border border-line bg-surface p-5 transition-shadow hover:shadow-raised sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex min-w-0 items-start gap-4">
        <span className="hidden size-12 shrink-0 flex-col items-center justify-center rounded-md bg-canvas text-center sm:flex">
          <span className="text-[0.6rem] font-semibold uppercase tracking-[0.08em] text-muted">
            {new Date(`${event.event_date}T00:00:00`).toLocaleDateString(undefined, {
              month: 'short',
            })}
          </span>
          <span className="font-display text-lg leading-none text-ink">
            {new Date(`${event.event_date}T00:00:00`).getDate()}
          </span>
        </span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="primary">{eventTypeLabel(event.event_type)}</Badge>
            <Badge tone={eventPhaseLabel(event) === 'Completed' ? 'neutral' : 'info'}>
              {eventPhaseLabel(event)}
            </Badge>
          </div>
          <h2 className="mt-2 truncate font-display text-xl text-ink group-hover:text-primary-strong">
            {event.name}
          </h2>
          <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
            <span className="inline-flex items-center gap-1.5">
              <CalendarDays className="size-3.5" aria-hidden="true" />
              {formatDate(event.event_date)}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="size-3.5" aria-hidden="true" />
              {event.location}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Users className="size-3.5" aria-hidden="true" />
              {event.guest_count.toLocaleString()} guests
            </span>
          </div>
        </div>
      </div>
      <div className="flex shrink-0 items-center justify-between gap-4 border-t border-line pt-3 sm:justify-end sm:border-0 sm:pt-0">
        <div className="text-left sm:text-right">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.08em] text-muted">
            Budget
          </p>
          <p className="text-sm font-semibold text-ink">
            {formatMoney(event.budget_amount, event.currency)}
          </p>
        </div>
        <ArrowRight
          className="size-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-primary"
          aria-hidden="true"
        />
      </div>
    </Link>
  )
}

export function EventsListPage() {
  const eventsQuery = useEventsQuery()
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [sort, setSort] = useState<'date-asc' | 'date-desc' | 'name'>('date-asc')

  const filtered = useMemo(() => {
    const events = eventsQuery.data?.items ?? []
    const query = search.trim().toLowerCase()
    const result = events.filter((event) => {
      if (typeFilter !== 'all' && event.event_type !== typeFilter) return false
      if (query) {
        const haystack = `${event.name} ${event.location}`.toLowerCase()
        if (!haystack.includes(query)) return false
      }
      const phase = eventPhaseLabel(event)
      if (statusFilter === 'upcoming' && phase === 'Completed') return false
      if (statusFilter === 'past' && phase !== 'Completed') return false
      return true
    })
    if (sort === 'name') return [...result].sort((a, b) => a.name.localeCompare(b.name))
    return sortEventsByDate(result, sort === 'date-asc')
  }, [eventsQuery.data, search, typeFilter, statusFilter, sort])

  if (eventsQuery.isLoading) return <PageSkeleton />

  if (eventsQuery.isError) {
    return (
      <ErrorState
        title="Events could not load"
        error={eventsQuery.error}
        onRetry={() => void eventsQuery.refetch()}
      />
    )
  }

  const allEvents = eventsQuery.data?.items ?? []
  const { upcoming, past } = splitUpcomingAndPast(allEvents)
  const filtersActive =
    search.trim() !== '' || typeFilter !== 'all' || statusFilter !== 'all'

  function clearFilters() {
    setSearch('')
    setTypeFilter('all')
    setStatusFilter('all')
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Events"
        title="Your celebrations"
        description="Every event has its own budget, timeline, task list, and vendor shortlist."
        actions={
          <Button asChild>
            <Link to="/app/events/new">
              <CalendarPlus aria-hidden="true" />
              Create event
            </Link>
          </Button>
        }
      />

      {allEvents.length === 0 ? (
        <EmptyState
          icon={CalendarPlus}
          title="No events yet"
          description="Create a workspace for a wedding, birthday, college fest, or community gathering."
          action={
            <Button asChild>
              <Link to="/app/events/new">Create your first event</Link>
            </Button>
          }
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="surface-card px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
                All events
              </p>
              <p className="mt-1 font-display text-2xl text-ink">{allEvents.length}</p>
            </div>
            <div className="surface-card px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
                Upcoming
              </p>
              <p className="mt-1 font-display text-2xl text-ink">{upcoming.length}</p>
            </div>
            <div className="surface-card px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
                Completed
              </p>
              <p className="mt-1 font-display text-2xl text-ink">{past.length}</p>
            </div>
          </div>

          <div className="surface-card space-y-4 p-4 sm:p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
              <div className="relative flex-1">
                <Search
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                  aria-hidden="true"
                />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search by event name or location"
                  className="pl-9"
                  aria-label="Search events"
                />
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <div className="w-full sm:w-44">
                  <Select
                    value={typeFilter}
                    onValueChange={(value) => setTypeFilter(value as TypeFilter)}
                  >
                    <SelectTrigger aria-label="Filter by event type">
                      <SelectValue placeholder="All types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All types</SelectItem>
                      {EVENT_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="w-full sm:w-40">
                  <Select
                    value={statusFilter}
                    onValueChange={(value) => setStatusFilter(value as StatusFilter)}
                  >
                    <SelectTrigger aria-label="Filter by status">
                      <SelectValue placeholder="All events" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All events</SelectItem>
                      <SelectItem value="upcoming">Upcoming</SelectItem>
                      <SelectItem value="past">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="w-full sm:w-44">
                  <Select
                    value={sort}
                    onValueChange={(value) =>
                      setSort(value as 'date-asc' | 'date-desc' | 'name')
                    }
                  >
                    <SelectTrigger aria-label="Sort events">
                      <SlidersHorizontal
                        className="size-3.5 text-muted"
                        aria-hidden="true"
                      />
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="date-asc">Soonest first</SelectItem>
                      <SelectItem value="date-desc">Latest first</SelectItem>
                      <SelectItem value="name">Name A–Z</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            {filtersActive ? (
              <div className="flex items-center justify-between gap-3 border-t border-line pt-3">
                <p className="text-xs text-muted">
                  Showing {filtered.length} of {allEvents.length} events
                </p>
                <Button type="button" variant="ghost" size="sm" onClick={clearFilters}>
                  <X aria-hidden="true" />
                  Clear filters
                </Button>
              </div>
            ) : null}
          </div>

          {filtered.length === 0 ? (
            <EmptyState
              compact
              icon={Search}
              title="No events match those filters"
              description="Try a different search term or clear the filters to see everything."
              action={
                <Button type="button" variant="outline" onClick={clearFilters}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <div className="space-y-3">
              {filtered.map((event) => (
                <EventListItem key={event.event_id} event={event} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
