import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useWatch } from 'react-hook-form'
import {
  AlertTriangle,
  CalendarRange,
  Check,
  CheckCircle2,
  Clock,
  Pencil,
  Plus,
  RefreshCcw,
  Search,
  Trash2,
  UserRound,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { FormField } from '@/components/ui/form-field'
import { Input, Textarea } from '@/components/ui/input'
import { PageSkeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { StatCard } from '@/components/ui/stat-card'
import { TaskPriorityBadge, TaskStatusBadge } from '@/components/ui/status-badge'
import { useEventQuery, useTasksQuery, useTimelineQuery } from '@/features/events/queries'
import { ApiError } from '@/lib/api/errors'
import { queryKeys, timelinesApi } from '@/lib/api/queries'
import {
  formatDate,
  formatDateTime,
  formatMoney,
  isPastDateTime,
  utcIsoToZonedInput,
  zonedInputToUtcIso,
} from '@/lib/format'
import { TASK_PRIORITIES, TASK_STATUSES } from '@/lib/labels'
import { emptyTaskForm, taskFormSchema, type TaskFormValues } from '@/lib/validation/task'
import type {
  EventRecord,
  TaskPriority,
  TaskRecord,
  TaskStatus,
  TaskUpdateInput,
} from '@/types/api'

function taskValues(task: TaskRecord, timezone: string): TaskFormValues {
  return {
    title: task.title,
    description: task.description ?? '',
    status: task.status,
    priority: task.priority,
    due_at: utcIsoToZonedInput(task.due_at, timezone),
    assigned_to: task.assigned_to ?? '',
    estimated_cost: task.estimated_cost ?? '',
    actual_cost: task.actual_cost ?? '',
  }
}

function TaskDialog({
  open,
  onOpenChange,
  event,
  task,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  event: EventRecord
  task?: TaskRecord
}) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    control,
    setValue,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<TaskFormValues>({
    resolver: zodResolver(taskFormSchema),
    defaultValues: task ? taskValues(task, event.timezone) : emptyTaskForm,
  })
  const status = useWatch({ control, name: 'status' })
  const priority = useWatch({ control, name: 'priority' })

  useEffect(() => {
    if (!open) return
    reset(task ? taskValues(task, event.timezone) : emptyTaskForm)
  }, [open, task, event.timezone, reset])

  const mutation = useMutation({
    mutationFn: async (values: TaskFormValues) => {
      const dueAt = values.due_at ? zonedInputToUtcIso(values.due_at, event.timezone) : null
      if (task) {
        const payload: TaskUpdateInput = {
          title: values.title.trim(),
          description: values.description.trim() || null,
          status: values.status,
          priority: values.priority,
          due_at: dueAt,
          assigned_to: values.assigned_to.trim() || null,
          estimated_cost: values.estimated_cost.trim() || null,
          actual_cost: values.actual_cost.trim() || null,
        }
        return timelinesApi.updateTask(event.event_id, task.task_id, payload)
      }
      return timelinesApi.createTask(event.event_id, {
        title: values.title.trim(),
        description: values.description.trim() || null,
        status: values.status,
        priority: values.priority,
        due_at: dueAt,
        assigned_to: values.assigned_to.trim() || null,
        estimated_cost: values.estimated_cost.trim() || null,
        actual_cost: values.actual_cost.trim() || null,
      })
    },
  })

  async function onSubmit(values: TaskFormValues) {
    setFormError(null)
    try {
      await mutation.mutateAsync(values)
      toast.success(task ? 'Task updated.' : 'Task added.')
      onOpenChange(false)
      // Refresh in the background so the dialog closes immediately instead of
      // waiting for a full refetch round trip on top of the save request.
      void queryClient.invalidateQueries({
        queryKey: queryKeys.tasks(event.event_id),
      })
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) {
        for (const field of error.fields) {
          const key = field.field.replace(/^body\./, '')
          if (
            key === 'title' ||
            key === 'description' ||
            key === 'status' ||
            key === 'priority' ||
            key === 'due_at' ||
            key === 'assigned_to' ||
            key === 'estimated_cost' ||
            key === 'actual_cost'
          ) {
            setError(key, { type: 'server', message: field.message })
          } else {
            setFormError(field.message)
          }
        }
      } else {
        setFormError(error instanceof Error ? error.message : 'Could not save the task.')
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{task ? 'Edit task' : 'Add task'}</DialogTitle>
          <DialogDescription>
            Due dates are interpreted in {event.timezone}.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
          <FormField id="task_title" label="Task" error={errors.title?.message} required>
            <Input
              id="task_title"
              placeholder="Confirm the catering headcount"
              aria-invalid={Boolean(errors.title)}
              {...register('title')}
            />
          </FormField>

          <FormField
            id="task_description"
            label="Details"
            error={errors.description?.message}
          >
            <Textarea
              id="task_description"
              rows={3}
              placeholder="What needs to happen, and with whom?"
              aria-invalid={Boolean(errors.description)}
              {...register('description')}
            />
          </FormField>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="task_status"
              label="Status"
              error={errors.status?.message}
              required
            >
              <Select
                value={status}
                onValueChange={(value) =>
                  setValue('status', value as TaskStatus, { shouldValidate: true })
                }
              >
                <SelectTrigger id="task_status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TASK_STATUSES.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField
              id="task_priority"
              label="Priority"
              error={errors.priority?.message}
              required
            >
              <Select
                value={priority}
                onValueChange={(value) =>
                  setValue('priority', value as TaskPriority, { shouldValidate: true })
                }
              >
                <SelectTrigger id="task_priority">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TASK_PRIORITIES.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="task_due_at"
              label="Due date and time"
              error={errors.due_at?.message}
              description="Optional. Leave blank for no deadline."
            >
              <Input
                id="task_due_at"
                type="datetime-local"
                aria-invalid={Boolean(errors.due_at)}
                {...register('due_at')}
              />
            </FormField>
            <FormField
              id="task_assigned_to"
              label="Assigned to"
              error={errors.assigned_to?.message}
            >
              <Input
                id="task_assigned_to"
                placeholder="Ananya"
                aria-invalid={Boolean(errors.assigned_to)}
                {...register('assigned_to')}
              />
            </FormField>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="task_estimated_cost"
              label={`Estimated cost (${event.currency})`}
              error={errors.estimated_cost?.message}
              description="Optional task-level estimate; does not change the event budget."
            >
              <Input
                id="task_estimated_cost"
                inputMode="decimal"
                placeholder="15000.00"
                aria-invalid={Boolean(errors.estimated_cost)}
                {...register('estimated_cost')}
              />
            </FormField>
            <FormField
              id="task_actual_cost"
              label={`Actual cost (${event.currency})`}
              error={errors.actual_cost?.message}
              description="Optional. Record only what you have actually spent."
            >
              <Input
                id="task_actual_cost"
                inputMode="decimal"
                placeholder="14000.00"
                aria-invalid={Boolean(errors.actual_cost)}
                {...register('actual_cost')}
              />
            </FormField>
          </div>

          {formError ? (
            <p
              role="alert"
              className="rounded-sm bg-danger-soft px-3 py-2 text-sm text-danger"
            >
              {formError}
            </p>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || mutation.isPending}>
              {isSubmitting || mutation.isPending
                ? 'Saving…'
                : task
                  ? 'Save task'
                  : 'Add task'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function TimelineContent({ event }: { event: EventRecord }) {
  const queryClient = useQueryClient()
  const timelineQuery = useTimelineQuery(event.event_id)
  const tasksQuery = useTasksQuery(event.event_id)
  const [taskDialogOpen, setTaskDialogOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<TaskRecord | undefined>()
  const [deletingTask, setDeletingTask] = useState<TaskRecord | undefined>()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all')
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | 'all'>('all')

  const timeline = timelineQuery.data
  const tasks = useMemo(() => tasksQuery.data?.items ?? [], [tasksQuery.data])
  const openTasks = tasks.filter(
    (task) => task.status === 'pending' || task.status === 'in_progress',
  )
  const completedTasks = tasks.filter((task) => task.status === 'completed')
  const overdueTasks = openTasks.filter((task) => isPastDateTime(task.due_at))

  const filteredTasks = useMemo(() => {
    const query = search.trim().toLowerCase()
    return tasks
      .filter((task) => {
        if (statusFilter !== 'all' && task.status !== statusFilter) return false
        if (priorityFilter !== 'all' && task.priority !== priorityFilter) return false
        if (query) {
          const haystack =
            `${task.title} ${task.description ?? ''} ${task.assigned_to ?? ''}`.toLowerCase()
          if (!haystack.includes(query)) return false
        }
        return true
      })
      .sort((a, b) => {
        const statusRank = (task: TaskRecord) =>
          task.status === 'in_progress' ? 0 : task.status === 'pending' ? 1 : 2
        if (statusRank(a) !== statusRank(b)) return statusRank(a) - statusRank(b)
        if (a.due_at && b.due_at) return a.due_at.localeCompare(b.due_at)
        if (a.due_at) return -1
        if (b.due_at) return 1
        return a.sort_order - b.sort_order
      })
  }, [tasks, statusFilter, priorityFilter, search])

  const generateMutation = useMutation({
    mutationFn: () => timelinesApi.generate(event.event_id),
  })
  const regenerateMutation = useMutation({
    mutationFn: () => timelinesApi.regenerate(event.event_id),
  })
  const updateMutation = useMutation({
    mutationFn: ({ task, payload }: { task: TaskRecord; payload: TaskUpdateInput }) =>
      timelinesApi.updateTask(event.event_id, task.task_id, payload),
  })
  const deleteMutation = useMutation({
    mutationFn: (task: TaskRecord) => timelinesApi.deleteTask(event.event_id, task.task_id),
  })

  async function refreshTimelineData() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.timeline(event.event_id) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.tasks(event.event_id) }),
    ])
  }

  async function handleGenerate() {
    try {
      const created = await generateMutation.mutateAsync()
      queryClient.setQueryData(queryKeys.timeline(event.event_id), created)
      await refreshTimelineData()
      toast.success('Timeline generated with a starter checklist.')
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Could not generate the timeline.',
      )
    }
  }

  async function handleRegenerate() {
    try {
      const updated = await regenerateMutation.mutateAsync()
      queryClient.setQueryData(queryKeys.timeline(event.event_id), updated)
      await refreshTimelineData()
      toast.success('Timeline refreshed. Any missing starter tasks were added.')
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Could not regenerate the timeline.',
      )
    }
  }

  async function toggleComplete(task: TaskRecord) {
    try {
      await updateMutation.mutateAsync({
        task,
        payload: {
          status: task.status === 'completed' ? 'pending' : 'completed',
        },
      })
      toast.success(task.status === 'completed' ? 'Task reopened.' : 'Task completed.')
      void queryClient.invalidateQueries({
        queryKey: queryKeys.tasks(event.event_id),
      })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not update the task.')
    }
  }

  async function handleDelete() {
    if (!deletingTask) return
    try {
      await deleteMutation.mutateAsync(deletingTask)
      await queryClient.invalidateQueries({
        queryKey: queryKeys.tasks(event.event_id),
      })
      toast.success('Task deleted.')
      setDeletingTask(undefined)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not delete the task.')
    }
  }

  if (timelineQuery.isLoading) return <PageSkeleton />

  if (timelineQuery.isError) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-line bg-surface p-6">
          <div className="flex items-start gap-4">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary-soft text-primary">
              <CalendarRange className="size-5" aria-hidden="true" />
            </span>
            <div>
              <h2 className="font-display text-2xl text-ink">Build a working timeline</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                Generate a checklist of eight practical planning milestones for this event.
                Tasks start without due dates so you can set realistic deadlines yourself.
              </p>
              <Button
                type="button"
                className="mt-4"
                onClick={handleGenerate}
                disabled={generateMutation.isPending}
              >
                <CalendarRange aria-hidden="true" />
                {generateMutation.isPending ? 'Generating…' : 'Generate timeline'}
              </Button>
            </div>
          </div>
        </div>
        <EmptyState
          compact
          icon={Clock}
          title="No timeline yet"
          description="You can still add individual tasks without generating a timeline."
          action={
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setEditingTask(undefined)
                setTaskDialogOpen(true)
              }}
            >
              <Plus aria-hidden="true" />
              Add a task
            </Button>
          }
        />
        <TaskDialog
          open={taskDialogOpen}
          onOpenChange={setTaskDialogOpen}
          event={event}
          {...(editingTask ? { task: editingTask } : {})}
        />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          {timeline ? (
            <>
              <Badge tone="primary">
                {formatDate(timeline.start_date)} → {formatDate(timeline.end_date)}
              </Badge>
              <span className="text-xs text-muted">
                Generated {formatDateTime(timeline.generated_at, timeline.timezone)}
              </span>
            </>
          ) : (
            <Badge tone="neutral">Tasks without a generated timeline</Badge>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {timeline ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleRegenerate}
              disabled={regenerateMutation.isPending}
            >
              <RefreshCcw aria-hidden="true" />
              {regenerateMutation.isPending ? 'Refreshing…' : 'Add missing starter tasks'}
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
            >
              <CalendarRange aria-hidden="true" />
              {generateMutation.isPending ? 'Generating…' : 'Generate timeline'}
            </Button>
          )}
          <Button
            type="button"
            size="sm"
            onClick={() => {
              setEditingTask(undefined)
              setTaskDialogOpen(true)
            }}
          >
            <Plus aria-hidden="true" />
            Add task
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="All tasks" value={String(tasks.length)} icon={Clock} />
        <StatCard
          label="Open"
          value={String(openTasks.length)}
          helper={
            overdueTasks.length > 0 ? `${overdueTasks.length} overdue` : 'Nothing overdue'
          }
          icon={CalendarRange}
          tone={overdueTasks.length > 0 ? 'warning' : 'primary'}
        />
        <StatCard
          label="Completed"
          value={String(completedTasks.length)}
          helper={
            tasks.length > 0
              ? `${Math.round((completedTasks.length / tasks.length) * 100)}% of all tasks`
              : 'No tasks yet'
          }
          icon={CheckCircle2}
          tone="success"
        />
        <StatCard
          label="High priority open"
          value={String(
            openTasks.filter(
              (task) => task.priority === 'high' || task.priority === 'urgent',
            ).length,
          )}
          helper="High and urgent tasks still open"
          icon={AlertTriangle}
          tone="warning"
        />
      </div>

      <Card>
        <CardHeader className="flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <CardTitle>Task list</CardTitle>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                aria-hidden="true"
              />
              <Input
                value={search}
                onChange={(changeEvent) => setSearch(changeEvent.target.value)}
                placeholder="Search tasks"
                className="h-9 pl-9 sm:w-52"
                aria-label="Search tasks"
              />
            </div>
            <div className="w-full sm:w-36">
              <Select
                value={statusFilter}
                onValueChange={(value) => setStatusFilter(value as TaskStatus | 'all')}
              >
                <SelectTrigger className="h-9" aria-label="Filter by status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  {TASK_STATUSES.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-full sm:w-36">
              <Select
                value={priorityFilter}
                onValueChange={(value) => setPriorityFilter(value as TaskPriority | 'all')}
              >
                <SelectTrigger className="h-9" aria-label="Filter by priority">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All priorities</SelectItem>
                  {TASK_PRIORITIES.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {tasksQuery.isLoading ? (
            <p className="py-6 text-center text-sm text-muted">Loading tasks…</p>
          ) : tasks.length === 0 ? (
            <EmptyState
              compact
              icon={CheckCircle2}
              title="No tasks yet"
              description="Add the next action, or generate a starter timeline for this event."
              action={
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    setEditingTask(undefined)
                    setTaskDialogOpen(true)
                  }}
                >
                  <Plus aria-hidden="true" />
                  Add a task
                </Button>
              }
            />
          ) : filteredTasks.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-muted">No tasks match those filters.</p>
              <Button
                type="button"
                variant="link"
                size="sm"
                onClick={() => {
                  setSearch('')
                  setStatusFilter('all')
                  setPriorityFilter('all')
                }}
              >
                Clear filters
              </Button>
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {filteredTasks.map((task) => {
                const overdue =
                  isPastDateTime(task.due_at) &&
                  task.status !== 'completed' &&
                  task.status !== 'cancelled'
                return (
                  <li key={task.task_id} className="flex gap-3 py-4">
                    <button
                      type="button"
                      onClick={() => void toggleComplete(task)}
                      disabled={updateMutation.isPending}
                      className={
                        task.status === 'completed'
                          ? 'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-success text-white'
                          : 'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border border-line-strong text-transparent transition-colors hover:border-primary hover:text-primary'
                      }
                      aria-label={
                        task.status === 'completed'
                          ? `Reopen ${task.title}`
                          : `Mark ${task.title} as complete`
                      }
                    >
                      <Check className="size-3" aria-hidden="true" />
                    </button>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p
                          className={
                            task.status === 'completed'
                              ? 'text-sm font-semibold text-muted line-through'
                              : 'text-sm font-semibold text-ink'
                          }
                        >
                          {task.title}
                        </p>
                        <TaskStatusBadge status={task.status} />
                        <TaskPriorityBadge priority={task.priority} />
                      </div>
                      {task.description ? (
                        <p className="mt-1 text-xs leading-5 text-muted">
                          {task.description}
                        </p>
                      ) : null}
                      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                        <span
                          className={
                            overdue
                              ? 'inline-flex items-center gap-1 font-medium text-warning'
                              : 'inline-flex items-center gap-1'
                          }
                        >
                          <Clock className="size-3" aria-hidden="true" />
                          {task.due_at
                            ? `Due ${formatDateTime(task.due_at, event.timezone)}`
                            : 'No deadline'}
                        </span>
                        {task.assigned_to ? (
                          <span className="inline-flex items-center gap-1">
                            <UserRound className="size-3" aria-hidden="true" />
                            {task.assigned_to}
                          </span>
                        ) : null}
                        {task.estimated_cost ? (
                          <span>
                            Estimate {formatMoney(task.estimated_cost, task.currency)}
                          </span>
                        ) : null}
                        {task.actual_cost ? (
                          <span>Actual {formatMoney(task.actual_cost, task.currency)}</span>
                        ) : null}
                      </div>
                    </div>
                    <div className="flex shrink-0 items-start gap-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => {
                          setEditingTask(task)
                          setTaskDialogOpen(true)
                        }}
                        aria-label={`Edit ${task.title}`}
                      >
                        <Pencil aria-hidden="true" />
                      </Button>
                      <Button
                        type="button"
                        variant="danger-ghost"
                        size="icon-sm"
                        onClick={() => setDeletingTask(task)}
                        aria-label={`Delete ${task.title}`}
                      >
                        <Trash2 aria-hidden="true" />
                      </Button>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      <div className="rounded-md border border-line bg-surface px-4 py-3 text-xs leading-5 text-muted">
        Completing a task is a planning record, not proof that a vendor delivered. Generated
        starter tasks have no deadlines until you set them. “Add missing starter tasks”
        never deletes or rewrites your existing tasks.
      </div>

      <TaskDialog
        open={taskDialogOpen}
        onOpenChange={(open) => {
          setTaskDialogOpen(open)
          if (!open) setEditingTask(undefined)
        }}
        event={event}
        {...(editingTask ? { task: editingTask } : {})}
      />

      <ConfirmDialog
        open={Boolean(deletingTask)}
        onOpenChange={(open) => {
          if (!open) setDeletingTask(undefined)
        }}
        title="Delete this task?"
        description={
          deletingTask
            ? `“${deletingTask.title}” will be permanently removed from this event.`
            : ''
        }
        confirmLabel="Delete task"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={handleDelete}
      />
    </div>
  )
}

export function TimelinePage() {
  const { eventId } = useParams()
  const eventQuery = useEventQuery(eventId)

  if (!eventQuery.data) return null

  return <TimelineContent event={eventQuery.data} />
}
