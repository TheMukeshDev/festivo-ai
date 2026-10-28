import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useWatch } from 'react-hook-form'
import { ArrowLeft, Save, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { ErrorState } from '@/components/ui/error-state'
import { FormField } from '@/components/ui/form-field'
import { Input, Textarea } from '@/components/ui/input'
import { PageHeader } from '@/components/ui/page-header'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PageSkeleton } from '@/components/ui/skeleton'
import { useEventQuery } from '@/features/events/queries'
import { ApiError } from '@/lib/api/errors'
import { eventsApi, queryKeys } from '@/lib/api/queries'
import { todayInputValue } from '@/lib/format'
import { EVENT_TYPES } from '@/lib/labels'
import { COMMON_TIMEZONES } from '@/lib/timezones'
import {
  createEventFormSchema,
  eventFormDefaults,
  joinLines,
  splitLines,
  type EventFormValues,
} from '@/lib/validation/event'
import type { EventCreateInput, EventRecord, EventUpdateInput } from '@/types/api'

function valuesFromEvent(event: EventRecord): EventFormValues {
  return {
    name: event.name,
    event_type: event.event_type,
    event_date: event.event_date,
    location: event.location,
    guest_count: event.guest_count,
    budget_amount: event.budget_amount,
    currency: event.currency,
    timezone: event.timezone,
    description: event.description ?? '',
    preferences_text: joinLines(event.preferences),
    constraints_text: joinLines(event.constraints),
  }
}

function basePayload(values: EventFormValues): EventCreateInput {
  return {
    name: values.name.trim(),
    event_type: values.event_type,
    event_date: values.event_date,
    location: values.location.trim(),
    guest_count: values.guest_count,
    budget_amount: values.budget_amount.trim(),
    currency: values.currency.trim().toUpperCase(),
    timezone: values.timezone.trim(),
    description: values.description.trim() || null,
    preferences: splitLines(values.preferences_text),
    constraints: splitLines(values.constraints_text),
  }
}

function sameList(left: string[], right: string[]): boolean {
  return (
    left.length === right.length && left.every((value, index) => value === right[index])
  )
}

function buildUpdatePayload(values: EventFormValues, event: EventRecord): EventUpdateInput {
  const next = basePayload(values)
  const payload: EventUpdateInput = {}
  if (next.name !== event.name) payload.name = next.name
  if (next.event_type !== event.event_type) payload.event_type = next.event_type
  if (next.event_date !== event.event_date) payload.event_date = next.event_date
  if (next.location !== event.location) payload.location = next.location
  if (next.guest_count !== event.guest_count) payload.guest_count = next.guest_count
  if (Number(next.budget_amount) !== Number(event.budget_amount)) {
    payload.budget_amount = next.budget_amount
  }
  if (next.currency !== event.currency) payload.currency = next.currency
  const timezone = next.timezone ?? event.timezone
  if (timezone !== event.timezone) payload.timezone = timezone
  if ((next.description ?? null) !== (event.description ?? null)) {
    payload.description = next.description ?? null
  }
  if (!sameList(next.preferences, event.preferences)) {
    payload.preferences = next.preferences
  }
  if (!sameList(next.constraints, event.constraints)) {
    payload.constraints = next.constraints
  }
  return payload
}

const fieldAliases: Record<string, keyof EventFormValues> = {
  'body.name': 'name',
  'body.event_type': 'event_type',
  'body.event_date': 'event_date',
  'body.location': 'location',
  'body.guest_count': 'guest_count',
  'body.budget_amount': 'budget_amount',
  'body.currency': 'currency',
  'body.timezone': 'timezone',
  'body.description': 'description',
  'body.preferences': 'preferences_text',
  'body.constraints': 'constraints_text',
  name: 'name',
  event_type: 'event_type',
  event_date: 'event_date',
  location: 'location',
  guest_count: 'guest_count',
  budget_amount: 'budget_amount',
  currency: 'currency',
  timezone: 'timezone',
  description: 'description',
  preferences: 'preferences_text',
  constraints: 'constraints_text',
}

function EventForm({ event }: { event?: EventRecord }) {
  const isEdit = Boolean(event)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const schema = useMemo(() => createEventFormSchema({ allowPastDate: isEdit }), [isEdit])
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<EventFormValues>({
    resolver: zodResolver(schema),
    defaultValues: event ? valuesFromEvent(event) : eventFormDefaults,
    mode: 'onBlur',
  })

  useEffect(() => {
    if (event) reset(valuesFromEvent(event))
  }, [event, reset])

  const eventType = useWatch({ control, name: 'event_type' })
  const timezone = useWatch({ control, name: 'timezone' })

  const saveMutation = useMutation({
    mutationFn: async (values: EventFormValues) => {
      if (event) {
        const payload = buildUpdatePayload(values, event)
        if (Object.keys(payload).length === 0) return { event, unchanged: true as const }
        const updated = await eventsApi.update(event.event_id, payload)
        return { event: updated, unchanged: false as const }
      }
      const created = await eventsApi.create(basePayload(values))
      return { event: created, unchanged: false as const }
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!event) throw new Error('No event to delete.')
      await eventsApi.remove(event.event_id)
    },
  })

  async function onSubmit(values: EventFormValues) {
    setFormError(null)
    try {
      const result = await saveMutation.mutateAsync(values)
      await queryClient.invalidateQueries({ queryKey: queryKeys.events })
      queryClient.setQueryData(queryKeys.event(result.event.event_id), result.event)
      if (result.unchanged) {
        toast.info('No changes to save.')
      } else if (isEdit) {
        toast.success('Event updated.')
      } else {
        toast.success('Event created. Your planning workspace is ready.')
      }
      navigate(`/app/events/${result.event.event_id}`, { replace: !isEdit })
    } catch (error) {
      if (error instanceof ApiError && error.isValidation && error.fields.length > 0) {
        let unmatched: string | null = null
        for (const field of error.fields) {
          const key = fieldAliases[field.field]
          if (key) {
            setError(key, { type: 'server', message: field.message })
          } else {
            unmatched = field.message
          }
        }
        setFormError(
          unmatched ??
            (error.fields.some((field) => fieldAliases[field.field])
              ? 'Please correct the highlighted fields.'
              : error.message),
        )
      } else {
        setFormError(error instanceof Error ? error.message : 'Could not save this event.')
      }
    }
  }

  async function handleDelete() {
    try {
      await deleteMutation.mutateAsync()
      queryClient.removeQueries({ queryKey: queryKeys.event(event!.event_id) })
      await queryClient.invalidateQueries({ queryKey: queryKeys.events })
      toast.success('Event deleted.')
      setDeleteOpen(false)
      navigate('/app/events', { replace: true })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not delete this event.')
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-3">
          <Link to={event ? `/app/events/${event.event_id}` : '/app/events'}>
            <ArrowLeft aria-hidden="true" />
            {event ? 'Back to event' : 'All events'}
          </Link>
        </Button>
        <PageHeader
          eyebrow={isEdit ? 'Edit event' : 'New event'}
          title={isEdit ? event!.name : 'Create an event workspace'}
          description={
            isEdit
              ? 'Update the details that shape the budget, timeline, and AI context.'
              : 'Start with the facts you know. You can refine the plan inside the event workspace.'
          }
        />
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        <Card>
          <CardHeader>
            <CardTitle>Essentials</CardTitle>
            <CardDescription>
              The practical details your plan is built around.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5 sm:grid-cols-2">
            <FormField
              id="name"
              label="Event name"
              error={errors.name?.message}
              className="sm:col-span-2"
              required
            >
              <Input
                id="name"
                autoFocus={!isEdit}
                placeholder="Ananya & Rohan's wedding"
                aria-invalid={Boolean(errors.name)}
                aria-describedby={errors.name ? 'name-error' : undefined}
                {...register('name')}
              />
            </FormField>

            <FormField
              id="event_type"
              label="Event type"
              error={errors.event_type?.message}
              required
            >
              <Select
                value={eventType}
                onValueChange={(value) =>
                  setValue('event_type', value as EventFormValues['event_type'], {
                    shouldDirty: true,
                    shouldValidate: true,
                  })
                }
              >
                <SelectTrigger id="event_type" aria-invalid={Boolean(errors.event_type)}>
                  <SelectValue placeholder="Choose a type" />
                </SelectTrigger>
                <SelectContent>
                  {EVENT_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>

            <FormField
              id="event_date"
              label="Event date"
              error={errors.event_date?.message}
              required
            >
              <Input
                id="event_date"
                type="date"
                min={isEdit ? undefined : todayInputValue()}
                aria-invalid={Boolean(errors.event_date)}
                aria-describedby={errors.event_date ? 'event_date-error' : undefined}
                {...register('event_date')}
              />
            </FormField>

            <FormField
              id="location"
              label="Location"
              error={errors.location?.message}
              required
            >
              <Input
                id="location"
                placeholder="Bengaluru, Karnataka"
                aria-invalid={Boolean(errors.location)}
                aria-describedby={errors.location ? 'location-error' : undefined}
                {...register('location')}
              />
            </FormField>

            <FormField
              id="guest_count"
              label="Expected guests"
              error={errors.guest_count?.message}
              required
            >
              <Input
                id="guest_count"
                type="number"
                inputMode="numeric"
                min={1}
                max={10000}
                aria-invalid={Boolean(errors.guest_count)}
                aria-describedby={errors.guest_count ? 'guest_count-error' : undefined}
                {...register('guest_count', { valueAsNumber: true })}
              />
            </FormField>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Budget</CardTitle>
            <CardDescription>
              This becomes the total limit for the event. Expenses and categories are
              tracked separately in the budget workspace.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5 sm:grid-cols-[1fr_10rem]">
            <FormField
              id="budget_amount"
              label="Total budget"
              error={errors.budget_amount?.message}
              description="Up to two decimal places."
              required
            >
              <Input
                id="budget_amount"
                inputMode="decimal"
                placeholder="750000.00"
                aria-invalid={Boolean(errors.budget_amount)}
                aria-describedby={errors.budget_amount ? 'budget_amount-error' : undefined}
                {...register('budget_amount')}
              />
            </FormField>
            <FormField
              id="currency"
              label="Currency"
              error={errors.currency?.message}
              required
            >
              <Input
                id="currency"
                maxLength={3}
                placeholder="INR"
                className="uppercase"
                aria-invalid={Boolean(errors.currency)}
                aria-describedby={errors.currency ? 'currency-error' : undefined}
                {...register('currency')}
              />
            </FormField>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Planning context</CardTitle>
            <CardDescription>
              Optional details that help timelines, budget suggestions, and AI drafts feel
              more relevant.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5 sm:grid-cols-2">
            <FormField
              id="timezone"
              label="Event timezone"
              error={errors.timezone?.message}
              description="Used for task deadlines and calendar dates."
              required
            >
              <Input
                id="timezone"
                list="timezone-options"
                placeholder="Asia/Kolkata"
                aria-invalid={Boolean(errors.timezone)}
                aria-describedby={errors.timezone ? 'timezone-error' : undefined}
                {...register('timezone')}
              />
              <datalist id="timezone-options">
                {COMMON_TIMEZONES.map((zone) => (
                  <option key={zone} value={zone} />
                ))}
              </datalist>
              {timezone && !COMMON_TIMEZONES.includes(timezone) ? (
                <p className="text-xs text-muted">
                  Custom IANA timezone: {timezone}. The server will validate it on save.
                </p>
              ) : null}
            </FormField>

            <FormField
              id="description"
              label="Description"
              error={errors.description?.message}
              className="sm:col-span-2"
            >
              <Textarea
                id="description"
                rows={3}
                placeholder="A relaxed celebration with family and friends."
                aria-invalid={Boolean(errors.description)}
                aria-describedby={errors.description ? 'description-error' : undefined}
                {...register('description')}
              />
            </FormField>

            <FormField
              id="preferences_text"
              label="Preferences"
              error={errors.preferences_text?.message}
              description="One per line, up to 20. For example: pastel decor, vegetarian menu."
            >
              <Textarea
                id="preferences_text"
                rows={4}
                placeholder={'Pastel decor\nVegetarian menu'}
                aria-invalid={Boolean(errors.preferences_text)}
                aria-describedby={
                  errors.preferences_text ? 'preferences_text-error' : undefined
                }
                {...register('preferences_text')}
              />
            </FormField>

            <FormField
              id="constraints_text"
              label="Constraints"
              error={errors.constraints_text?.message}
              description="One per line, up to 20. For example: no loud music after 10 PM."
            >
              <Textarea
                id="constraints_text"
                rows={4}
                placeholder={'No loud music after 10 PM\nVenue must be accessible'}
                aria-invalid={Boolean(errors.constraints_text)}
                aria-describedby={
                  errors.constraints_text ? 'constraints_text-error' : undefined
                }
                {...register('constraints_text')}
              />
            </FormField>
          </CardContent>
        </Card>

        {formError ? (
          <p
            role="alert"
            className="rounded-sm border border-danger/20 bg-danger-soft px-4 py-3 text-sm text-danger"
          >
            {formError}
          </p>
        ) : null}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            {isEdit ? (
              <Button
                type="button"
                variant="danger-ghost"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 aria-hidden="true" />
                Delete event
              </Button>
            ) : null}
          </div>
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <Button asChild variant="outline">
              <Link to={event ? `/app/events/${event.event_id}` : '/app/events'}>
                Cancel
              </Link>
            </Button>
            <Button type="submit" disabled={isSubmitting || saveMutation.isPending}>
              <Save aria-hidden="true" />
              {isSubmitting || saveMutation.isPending
                ? 'Saving…'
                : isEdit
                  ? isDirty
                    ? 'Save changes'
                    : 'Save'
                  : 'Create event'}
            </Button>
          </div>
        </div>
      </form>

      {event ? (
        <ConfirmDialog
          open={deleteOpen}
          onOpenChange={setDeleteOpen}
          title="Delete this event?"
          description={`“${event.name}” and its budget, timeline, tasks, and vendors will be permanently removed. This cannot be undone.`}
          confirmLabel="Delete event"
          destructive
          loading={deleteMutation.isPending}
          onConfirm={handleDelete}
        />
      ) : null}
    </div>
  )
}

export function EventCreatePage() {
  return <EventForm />
}

export function EventEditPage() {
  const { eventId } = useParams()
  const eventQuery = useEventQuery(eventId)

  if (eventQuery.isLoading) return <PageSkeleton />

  if (eventQuery.isError || !eventQuery.data) {
    return (
      <ErrorState
        title="This event could not be loaded"
        error={eventQuery.error}
        onRetry={() => void eventQuery.refetch()}
      />
    )
  }

  return <EventForm event={eventQuery.data} />
}
