import { Link } from 'react-router-dom'
import {
  ArrowRight,
  CalendarCheck2,
  CalendarClock,
  CalendarDays,
  CircleDollarSign,
  ClipboardList,
  Plus,
  Users,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { PageHeader } from '@/components/ui/page-header'
import { Progress } from '@/components/ui/progress'
import { PageSkeleton } from '@/components/ui/skeleton'
import { StatCard } from '@/components/ui/stat-card'
import { TaskStatusBadge } from '@/components/ui/status-badge'
import { useAuth } from '@/features/auth/use-auth'
import { useBudgetQuery, useEventsQuery, useTasksQuery } from '@/features/events/queries'
import { eventPhaseLabel, splitUpcomingAndPast } from '@/features/events/event-utils'
import {
  daysUntil,
  formatDate,
  formatDateTime,
  formatMoney,
  percentage,
} from '@/lib/format'
import { eventTypeLabel } from '@/lib/labels'
import type { EventRecord } from '@/types/api'

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function EventCard({ event }: { event: EventRecord }) {
  const countdown = daysUntil(event.event_date, event.timezone)
  return (
    <Link
      to={`/app/events/${event.event_id}`}
      className="group surface-card flex flex-col p-5 transition-shadow hover:shadow-raised"
    >
      <div className="flex items-start justify-between gap-3">
        <Badge tone="primary">{eventTypeLabel(event.event_type)}</Badge>
        <Badge tone={countdown < 0 ? 'neutral' : countdown <= 14 ? 'warning' : 'info'}>
          {eventPhaseLabel(event)}
        </Badge>
      </div>
      <h3 className="mt-3 font-display text-xl leading-snug text-ink group-hover:text-primary-strong">
        {event.name}
      </h3>
      <p className="mt-1 text-sm text-muted">{event.location}</p>
      <div className="mt-auto flex flex-wrap gap-x-4 gap-y-1 pt-4 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <CalendarDays className="size-3.5" aria-hidden="true" />
          {formatDate(event.event_date)}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Users className="size-3.5" aria-hidden="true" />
          {event.guest_count.toLocaleString()}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <CircleDollarSign className="size-3.5" aria-hidden="true" />
          {formatMoney(event.budget_amount, event.currency, { compact: true })}
        </span>
      </div>
    </Link>
  )
}

function NearestEventPanel({ event }: { event: EventRecord }) {
  const budgetQuery = useBudgetQuery(event.event_id)
  const tasksQuery = useTasksQuery(event.event_id)
  const budget = budgetQuery.data
  const tasks = tasksQuery.data?.items ?? []
  const openTasks = tasks
    .filter((task) => task.status === 'pending' || task.status === 'in_progress')
    .sort((a, b) => {
      if (!a.due_at && !b.due_at) return a.sort_order - b.sort_order
      if (!a.due_at) return 1
      if (!b.due_at) return -1
      return a.due_at.localeCompare(b.due_at)
    })
    .slice(0, 4)
  const completed = tasks.filter((task) => task.status === 'completed').length
  const taskProgress = tasks.length > 0 ? (completed / tasks.length) * 100 : 0
  const budgetUsed = budget
    ? percentage(budget.planned_spending, budget.available_for_planning)
    : 0

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Next celebration</p>
          <CardTitle className="mt-1">{event.name}</CardTitle>
          <p className="mt-1 text-sm text-muted">
            {formatDate(event.event_date)} · {event.location}
          </p>
        </div>
        <Button asChild size="sm" variant="outline">
          <Link to={`/app/events/${event.event_id}`}>
            Open
            <ArrowRight aria-hidden="true" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-5">
        <div>
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-ink">Budget used</span>
            <span className="text-muted">
              {budget
                ? `${formatMoney(budget.planned_spending, budget.currency, { compact: true })} of ${formatMoney(budget.available_for_planning, budget.currency, { compact: true })}`
                : 'Budget not set up yet'}
            </span>
          </div>
          <Progress
            value={budgetUsed}
            label="Share of planning budget used"
            tone={
              budget?.status === 'over_budget'
                ? 'danger'
                : budgetUsed > 85
                  ? 'warning'
                  : 'primary'
            }
            className="mt-2"
          />
          {budget ? (
            <p className="mt-2 text-xs text-muted">
              {formatMoney(budget.remaining_after_reserve, budget.currency)} remains after
              the reserve.
            </p>
          ) : (
            <Button asChild variant="link" size="sm" className="mt-1 h-auto px-0">
              <Link to={`/app/events/${event.event_id}/budget`}>Set up the budget</Link>
            </Button>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-ink">Tasks complete</span>
            <span className="text-muted">
              {tasks.length > 0 ? `${completed} of ${tasks.length}` : 'No tasks yet'}
            </span>
          </div>
          <Progress
            value={taskProgress}
            label="Share of tasks completed"
            tone={taskProgress === 100 && tasks.length > 0 ? 'success' : 'primary'}
            className="mt-2"
          />
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
            Next tasks
          </p>
          {tasksQuery.isLoading ? (
            <p className="mt-3 text-sm text-muted">Loading tasks…</p>
          ) : openTasks.length === 0 ? (
            <p className="mt-3 text-sm text-muted">
              Nothing open right now. Add a task or regenerate the timeline.
            </p>
          ) : (
            <ul className="mt-3 divide-y divide-line">
              {openTasks.map((task) => (
                <li
                  key={task.task_id}
                  className="flex items-start justify-between gap-3 py-2.5"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink">{task.title}</p>
                    <p className="mt-0.5 text-xs text-muted">
                      {task.due_at
                        ? `Due ${formatDateTime(task.due_at, event.timezone)}`
                        : 'No due date'}
                    </p>
                  </div>
                  <TaskStatusBadge status={task.status} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const auth = useAuth()
  const eventsQuery = useEventsQuery()

  if (eventsQuery.isLoading) return <PageSkeleton />

  if (eventsQuery.isError) {
    return (
      <ErrorState
        title="Your workspace could not load"
        error={eventsQuery.error}
        onRetry={() => void eventsQuery.refetch()}
      />
    )
  }

  const events = eventsQuery.data?.items ?? []
  const { upcoming, past } = splitUpcomingAndPast(events)
  const nearest = upcoming[0]
  const upcomingGuests = upcoming.reduce((total, event) => total + event.guest_count, 0)
  const name =
    (auth.user?.user_metadata.full_name as string | undefined)?.trim().split(' ')[0] ||
    auth.user?.email?.split('@')[0] ||
    'planner'
  const nextCountdown = nearest ? daysUntil(nearest.event_date, nearest.timezone) : null

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Workspace"
        title={`${greeting()}, ${name}.`}
        description={
          events.length > 0
            ? 'Here is the current state of your plans. The details live in each event workspace.'
            : 'Start with one celebration. You can shape the budget, timeline, and vendors as the plan becomes clearer.'
        }
        actions={
          <Button asChild>
            <Link to="/app/events/new">
              <Plus aria-hidden="true" />
              Create event
            </Link>
          </Button>
        }
      />

      {events.length === 0 ? (
        <EmptyState
          icon={CalendarCheck2}
          title="Your first event starts here"
          description="Add a date, guest count, and budget. Festivo will give you a budget workspace, timeline, task list, and vendor shortlist to build on."
          action={
            <Button asChild>
              <Link to="/app/events/new">
                <Plus aria-hidden="true" />
                Create your first event
              </Link>
            </Button>
          }
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Upcoming events"
              value={String(upcoming.length)}
              helper={`${past.length} completed ${past.length === 1 ? 'event' : 'events'} in your workspace`}
              icon={CalendarClock}
              tone="primary"
            />
            <StatCard
              label="Guests planned"
              value={upcomingGuests.toLocaleString()}
              helper="Across upcoming events"
              icon={Users}
            />
            <StatCard
              label="Next event"
              value={
                nextCountdown === null
                  ? '—'
                  : nextCountdown === 0
                    ? 'Today'
                    : `${nextCountdown}d`
              }
              helper={nearest ? nearest.name : 'No upcoming event'}
              icon={CalendarDays}
              tone={nextCountdown !== null && nextCountdown <= 14 ? 'warning' : 'default'}
            />
            <StatCard
              label="Planning tools"
              value="4"
              helper="Budget, timeline, tasks, and vendors"
              icon={ClipboardList}
            />
          </div>

          <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
            {nearest ? (
              <NearestEventPanel event={nearest} />
            ) : (
              <EmptyState
                compact
                icon={CalendarCheck2}
                title="No upcoming events"
                description="Every event in this workspace has already taken place. Create a new one to start planning again."
                action={
                  <Button asChild size="sm">
                    <Link to="/app/events/new">Create event</Link>
                  </Button>
                }
              />
            )}

            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle>Recent events</CardTitle>
                <Button asChild variant="ghost" size="sm">
                  <Link to="/app/events">
                    View all
                    <ArrowRight aria-hidden="true" />
                  </Link>
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                {events.slice(0, 3).map((event) => (
                  <EventCard key={event.event_id} event={event} />
                ))}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
