import { Link, NavLink, Outlet, useParams } from 'react-router-dom'
import { ArrowLeft, CalendarDays, IndianRupee, MapPin, Pencil, Users } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ErrorState } from '@/components/ui/error-state'
import { PageSkeleton } from '@/components/ui/skeleton'
import { useEventQuery } from '@/features/events/queries'
import { daysUntil, formatDate, formatMoney } from '@/lib/format'
import { eventTypeLabel } from '@/lib/labels'
import { cn } from '@/lib/utils'

const eventNav = [
  { suffix: '', label: 'Overview', end: true },
  { suffix: 'budget', label: 'Budget' },
  { suffix: 'timeline', label: 'Timeline & tasks' },
  { suffix: 'vendors', label: 'Vendors' },
  { suffix: 'ai-plan', label: 'AI planning' },
  { suffix: 'proposals', label: 'Proposals' },
  { suffix: 'exports', label: 'Exports' },
]

export function EventLayout() {
  const { eventId } = useParams()
  const eventQuery = useEventQuery(eventId)

  if (eventQuery.isLoading) return <PageSkeleton />

  if (eventQuery.isError) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link to="/app/events">
            <ArrowLeft aria-hidden="true" />
            All events
          </Link>
        </Button>
        <ErrorState
          title="This event could not be loaded"
          error={eventQuery.error}
          onRetry={() => void eventQuery.refetch()}
        />
      </div>
    )
  }

  const event = eventQuery.data
  if (!event) return null

  const countdown = daysUntil(event.event_date, event.timezone)
  const base = `/app/events/${event.event_id}`

  return (
    <div className="space-y-6">
      <div>
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-3">
          <Link to="/app/events">
            <ArrowLeft aria-hidden="true" />
            All events
          </Link>
        </Button>

        <div className="surface-card overflow-hidden">
          <div className="flex flex-col gap-5 p-5 sm:p-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="primary">{eventTypeLabel(event.event_type)}</Badge>
                {countdown >= 0 ? (
                  <Badge tone={countdown <= 14 ? 'warning' : 'neutral'}>
                    {countdown === 0 ? 'Today' : `${countdown} days to go`}
                  </Badge>
                ) : (
                  <Badge tone="neutral">Date passed</Badge>
                )}
              </div>
              <h1 className="mt-3 font-display text-3xl leading-tight tracking-[-0.02em] text-ink sm:text-4xl">
                {event.name}
              </h1>
              <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted">
                <span className="inline-flex items-center gap-1.5">
                  <CalendarDays className="size-4" aria-hidden="true" />
                  {formatDate(event.event_date)}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="size-4" aria-hidden="true" />
                  {event.location}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Users className="size-4" aria-hidden="true" />
                  {event.guest_count.toLocaleString()} guests
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <IndianRupee className="size-4" aria-hidden="true" />
                  {formatMoney(event.budget_amount, event.currency)} budget
                </span>
              </div>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link to={`${base}/edit`}>
                <Pencil aria-hidden="true" />
                Edit event
              </Link>
            </Button>
          </div>

          <div className="overflow-x-auto border-t border-line bg-surface px-3 py-2 sm:px-5">
            <nav aria-label="Event sections" className="flex min-w-max items-center gap-1">
              {eventNav.map((item) => (
                <NavLink
                  key={item.suffix || 'overview'}
                  to={item.suffix ? `${base}/${item.suffix}` : base}
                  end={item.end ?? false}
                  className={({ isActive }) =>
                    cn(
                      'rounded-sm px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary-soft text-primary-strong'
                        : 'text-muted hover:bg-canvas hover:text-ink',
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      </div>

      <Outlet />
    </div>
  )
}
