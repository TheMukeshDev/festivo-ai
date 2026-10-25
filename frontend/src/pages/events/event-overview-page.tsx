import { Link, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowRight,
  CalendarRange,
  Check,
  CircleDollarSign,
  CircleDot,
  ClipboardList,
  Sparkles,
  Store,
  Target,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { StatCard } from '@/components/ui/stat-card'
import { TaskStatusBadge } from '@/components/ui/status-badge'
import {
  useAiStatusQuery,
  useBudgetQuery,
  useEventQuery,
  useTasksQuery,
  useTimelineQuery,
  useVendorsQuery,
} from '@/features/events/queries'
import { formatDateTime, formatMoney, isPastDateTime, percentage } from '@/lib/format'
import { eventTypeLabel, vendorStatusLabel } from '@/lib/labels'
import type { EventRecord } from '@/types/api'

function ChecklistItem({
  complete,
  title,
  description,
  to,
  action,
}: {
  complete: boolean
  title: string
  description: string
  to: string
  action: string
}) {
  return (
    <li className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <span
          className={
            complete
              ? 'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-success-soft text-success'
              : 'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border border-line-strong text-muted'
          }
          aria-hidden="true"
        >
          {complete ? <Check className="size-3" /> : <CircleDot className="size-3" />}
        </span>
        <div>
          <p className="text-sm font-semibold text-ink">
            {title}
            <span className="sr-only">{complete ? ' — complete' : ' — not started'}</span>
          </p>
          <p className="mt-0.5 text-xs leading-5 text-muted">{description}</p>
        </div>
      </div>
      {!complete ? (
        <Button asChild variant="outline" size="sm">
          <Link to={to}>
            {action}
            <ArrowRight aria-hidden="true" />
          </Link>
        </Button>
      ) : (
        <Badge tone="success">Done</Badge>
      )}
    </li>
  )
}

function OverviewContent({ event }: { event: EventRecord }) {
  const base = `/app/events/${event.event_id}`
  const budgetQuery = useBudgetQuery(event.event_id)
  const timelineQuery = useTimelineQuery(event.event_id)
  const tasksQuery = useTasksQuery(event.event_id)
  const vendorsQuery = useVendorsQuery(event.event_id)
  const aiStatusQuery = useAiStatusQuery(event.event_id)

  const budget = budgetQuery.data
  const timeline = timelineQuery.data
  const tasks = tasksQuery.data?.items ?? []
  const vendors = vendorsQuery.data?.items ?? []
  const aiStatus = aiStatusQuery.data

  const openTasks = tasks.filter(
    (task) => task.status === 'pending' || task.status === 'in_progress',
  )
  const completedTasks = tasks.filter((task) => task.status === 'completed')
  const overdueTasks = openTasks.filter((task) => isPastDateTime(task.due_at))
  const upcomingTasks = [...openTasks]
    .sort((a, b) => {
      if (!a.due_at && !b.due_at) return a.sort_order - b.sort_order
      if (!a.due_at) return 1
      if (!b.due_at) return -1
      return a.due_at.localeCompare(b.due_at)
    })
    .slice(0, 5)
  const budgetUsed = budget
    ? percentage(budget.planned_spending, budget.available_for_planning)
    : 0
  const taskProgress = tasks.length > 0 ? (completedTasks.length / tasks.length) * 100 : 0
  const vendorCounts = vendors.reduce<Record<string, number>>((counts, vendor) => {
    counts[vendor.status] = (counts[vendor.status] ?? 0) + 1
    return counts
  }, {})
  const aiUnavailableReason =
    aiStatus?.configuration_state === 'disabled'
      ? 'AI planning is disabled by the server administrator.'
      : aiStatus?.configuration_state === 'incomplete'
        ? 'AI planning is not configured on the server yet.'
        : null

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Budget remaining"
          value={
            budget
              ? formatMoney(budget.remaining_after_reserve, budget.currency, {
                  compact: true,
                })
              : 'Not set'
          }
          helper={
            budget
              ? `${formatMoney(budget.planned_spending, budget.currency, { compact: true })} planned`
              : 'Set up a budget to start tracking'
          }
          icon={CircleDollarSign}
          tone={budget?.status === 'over_budget' ? 'danger' : 'primary'}
        />
        <StatCard
          label="Open tasks"
          value={String(openTasks.length)}
          helper={
            overdueTasks.length > 0
              ? `${overdueTasks.length} overdue`
              : `${completedTasks.length} of ${tasks.length} complete`
          }
          icon={ClipboardList}
          tone={overdueTasks.length > 0 ? 'warning' : 'default'}
        />
        <StatCard
          label="Vendors"
          value={String(vendors.length)}
          helper={
            vendorCounts.booked
              ? `${vendorCounts.booked} booked`
              : vendors.length > 0
                ? 'No vendors booked yet'
                : 'No vendor options saved'
          }
          icon={Store}
        />
        <StatCard
          label="Timeline"
          value={timeline ? 'Ready' : 'Not generated'}
          helper={
            timeline
              ? `${formatDateTime(timeline.start_date)} → ${formatDateTime(timeline.end_date)}`
              : 'Generate a working timeline'
          }
          icon={CalendarRange}
          tone={timeline ? 'success' : 'default'}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Planning checklist</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y divide-line">
              <ChecklistItem
                complete={Boolean(budget)}
                title="Set up the budget"
                description="Total limit, reserve, and the first expenses."
                to={`${base}/budget`}
                action="Open budget"
              />
              <ChecklistItem
                complete={Boolean(timeline)}
                title="Generate a timeline"
                description="Turn the event date into structured planning milestones."
                to={`${base}/timeline`}
                action="Open timeline"
              />
              <ChecklistItem
                complete={tasks.length > 0}
                title="Build the task list"
                description="Add the next actions, due dates, and owners."
                to={`${base}/timeline`}
                action="Add tasks"
              />
              <ChecklistItem
                complete={vendors.length > 0}
                title="Save vendor options"
                description="Keep quotes, contacts, and status in one shortlist."
                to={`${base}/vendors`}
                action="Open vendors"
              />
            </ul>
          </CardContent>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle>Progress</CardTitle>
                <p className="mt-1 text-sm text-muted">
                  Based on the data in this workspace.
                </p>
              </div>
              <Target className="size-5 text-primary" aria-hidden="true" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-xs">
                  <span className="font-medium text-ink">Budget used</span>
                  <span className="text-muted">{Math.round(budgetUsed)}%</span>
                </div>
                <Progress
                  value={budgetUsed}
                  label="Budget used"
                  tone={
                    budget?.status === 'over_budget'
                      ? 'danger'
                      : budgetUsed > 85
                        ? 'warning'
                        : 'primary'
                  }
                  className="mt-2"
                />
              </div>
              <div>
                <div className="flex justify-between text-xs">
                  <span className="font-medium text-ink">Tasks complete</span>
                  <span className="text-muted">{Math.round(taskProgress)}%</span>
                </div>
                <Progress
                  value={taskProgress}
                  label="Tasks complete"
                  tone={taskProgress === 100 && tasks.length > 0 ? 'success' : 'primary'}
                  className="mt-2"
                />
              </div>
              {overdueTasks.length > 0 ? (
                <div className="flex items-start gap-2 rounded-sm bg-warning-soft p-3 text-xs leading-5 text-ink-soft">
                  <AlertCircle
                    className="mt-0.5 size-4 shrink-0 text-warning"
                    aria-hidden="true"
                  />
                  {overdueTasks.length}{' '}
                  {overdueTasks.length === 1 ? 'task is' : 'tasks are'} past the due date.
                  Review them in the timeline.
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI planning</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-start gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary-soft text-primary">
                  <Sparkles className="size-4" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-sm font-semibold text-ink">
                    {aiStatus?.enabled
                      ? 'Ready for a draft'
                      : aiStatus
                        ? 'Not available'
                        : 'Checking availability'}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-muted">
                    {aiUnavailableReason ??
                      'Generate a draft grounded in this event, then apply only the ideas you choose.'}
                  </p>
                  <Button asChild variant="link" size="sm" className="mt-2 h-auto px-0">
                    <Link to={`${base}/ai-plan`}>
                      Open AI planning
                      <ArrowRight aria-hidden="true" />
                    </Link>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Next tasks</CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link to={`${base}/timeline`}>
                View timeline
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {tasksQuery.isLoading ? (
              <p className="text-sm text-muted">Loading tasks…</p>
            ) : upcomingTasks.length === 0 ? (
              <p className="text-sm leading-6 text-muted">
                No open tasks. Add one from the timeline or generate a timeline to get a
                starting checklist.
              </p>
            ) : (
              <ul className="divide-y divide-line">
                {upcomingTasks.map((task) => (
                  <li
                    key={task.task_id}
                    className="flex items-start justify-between gap-3 py-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink">{task.title}</p>
                      <p className="mt-0.5 text-xs text-muted">
                        {task.due_at
                          ? `Due ${formatDateTime(task.due_at, event.timezone)}`
                          : 'No due date'}
                        {task.assigned_to ? ` · ${task.assigned_to}` : ''}
                      </p>
                    </div>
                    <TaskStatusBadge status={task.status} />
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Event brief</CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link to={`${base}/edit`}>Edit</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex items-center justify-between gap-4 border-b border-line pb-3">
              <span className="text-muted">Type</span>
              <span className="font-medium text-ink">
                {eventTypeLabel(event.event_type)}
              </span>
            </div>
            <div>
              <p className="text-muted">Description</p>
              <p className="mt-1 leading-6 text-ink-soft">
                {event.description || 'No description added yet.'}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-muted">Preferences</p>
                {event.preferences.length > 0 ? (
                  <ul className="mt-1.5 space-y-1">
                    {event.preferences.map((preference) => (
                      <li
                        key={preference}
                        className="flex items-start gap-2 text-xs text-ink-soft"
                      >
                        <Check
                          className="mt-0.5 size-3 shrink-0 text-success"
                          aria-hidden="true"
                        />
                        {preference}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-xs text-muted">None added.</p>
                )}
              </div>
              <div>
                <p className="text-muted">Constraints</p>
                {event.constraints.length > 0 ? (
                  <ul className="mt-1.5 space-y-1">
                    {event.constraints.map((constraint) => (
                      <li
                        key={constraint}
                        className="flex items-start gap-2 text-xs text-ink-soft"
                      >
                        <AlertCircle
                          className="mt-0.5 size-3 shrink-0 text-warning"
                          aria-hidden="true"
                        />
                        {constraint}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-xs text-muted">None added.</p>
                )}
              </div>
            </div>
            {vendors.length > 0 ? (
              <div className="border-t border-line pt-3">
                <p className="text-muted">Vendor status</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(vendorCounts).map(([status, count]) => (
                    <Badge key={status} tone="neutral">
                      {vendorStatusLabel(status as Parameters<typeof vendorStatusLabel>[0])}
                      : {count}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export function EventOverviewPage() {
  const { eventId } = useParams()
  const eventQuery = useEventQuery(eventId)

  if (!eventQuery.data) return null

  return <OverviewContent event={eventQuery.data} />
}
