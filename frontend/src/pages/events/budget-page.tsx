import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CircleDollarSign,
  Pencil,
  Plus,
  ReceiptText,
  RefreshCcw,
  Settings2,
  ShieldCheck,
  Trash2,
  Wallet,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
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
import { ErrorState } from '@/components/ui/error-state'
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
import { ExpenseStatusBadge, BudgetStatusBadge } from '@/components/ui/status-badge'
import { useBudgetQuery, useEventQuery } from '@/features/events/queries'
import { ApiError } from '@/lib/api/errors'
import { budgetsApi, queryKeys } from '@/lib/api/queries'
import { formatMoney, percentage } from '@/lib/format'
import { DEFAULT_EXPENSE_CATEGORIES, EXPENSE_STATUSES } from '@/lib/labels'
import {
  budgetCreateSchema,
  expenseFormSchema,
  type BudgetCreateValues,
  type ExpenseFormValues,
} from '@/lib/validation/budget'
import type { BudgetResponse, ExpenseRecord, ExpenseStatus, ReserveType } from '@/types/api'

function SetupBudgetPanel({
  eventId,
  suggestedTotal,
  currency,
}: {
  eventId: string
  suggestedTotal: string
  currency: string
}) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<BudgetCreateValues>({
    resolver: zodResolver(budgetCreateSchema),
    defaultValues: {
      total_limit: Number(suggestedTotal).toFixed(2),
      reserve_type: 'percentage',
      reserve_value: '10.00',
    },
  })
  const reserveType = watch('reserve_type')

  const mutation = useMutation({
    mutationFn: (values: BudgetCreateValues) =>
      budgetsApi.create(eventId, {
        total_limit: values.total_limit.trim(),
        reserve: {
          type: values.reserve_type,
          value: values.reserve_value.trim(),
        },
      }),
  })

  async function onSubmit(values: BudgetCreateValues) {
    setFormError(null)
    try {
      const budget = await mutation.mutateAsync(values)
      queryClient.setQueryData(queryKeys.budget(eventId), budget)
      toast.success('Budget created.')
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) {
        for (const field of error.fields) {
          if (field.field.endsWith('total_limit')) {
            setError('total_limit', { type: 'server', message: field.message })
          } else if (field.field.endsWith('reserve.value')) {
            setError('reserve_value', { type: 'server', message: field.message })
          } else {
            setFormError(field.message)
          }
        }
      } else {
        setFormError(
          error instanceof Error ? error.message : 'Could not create the budget.',
        )
      }
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Set up the budget</CardTitle>
          <CardDescription>
            The event budget is suggested below. You can adjust the total and keep a reserve
            untouched for surprises.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
            <FormField
              id="total_limit"
              label={`Total budget (${currency})`}
              error={errors.total_limit?.message}
              description="This is the hard ceiling for planned spending."
              required
            >
              <Input
                id="total_limit"
                inputMode="decimal"
                aria-invalid={Boolean(errors.total_limit)}
                aria-describedby={errors.total_limit ? 'total_limit-error' : undefined}
                {...register('total_limit')}
              />
            </FormField>

            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                id="reserve_type"
                label="Reserve type"
                error={errors.reserve_type?.message}
                required
              >
                <Select
                  value={reserveType}
                  onValueChange={(value) =>
                    setValue('reserve_type', value as ReserveType, {
                      shouldValidate: true,
                    })
                  }
                >
                  <SelectTrigger id="reserve_type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="percentage">Percentage of total</SelectItem>
                    <SelectItem value="fixed_amount">Fixed amount</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>
              <FormField
                id="reserve_value"
                label={
                  reserveType === 'percentage' ? 'Reserve percentage' : 'Reserve amount'
                }
                error={errors.reserve_value?.message}
                required
              >
                <Input
                  id="reserve_value"
                  inputMode="decimal"
                  aria-invalid={Boolean(errors.reserve_value)}
                  aria-describedby={
                    errors.reserve_value ? 'reserve_value-error' : undefined
                  }
                  {...register('reserve_value')}
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

            <Button type="submit" disabled={isSubmitting || mutation.isPending}>
              <CircleDollarSign aria-hidden="true" />
              {isSubmitting || mutation.isPending ? 'Creating budget…' : 'Create budget'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

function BudgetSettingsDialog({
  open,
  onOpenChange,
  budget,
  eventId,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  budget: BudgetResponse
  eventId: string
}) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<BudgetCreateValues>({
    resolver: zodResolver(budgetCreateSchema),
    defaultValues: {
      total_limit: budget.total_limit,
      reserve_type: budget.reserve.type,
      reserve_value: budget.reserve.value,
    },
  })
  const reserveType = watch('reserve_type')

  useEffect(() => {
    if (open) {
      reset({
        total_limit: budget.total_limit,
        reserve_type: budget.reserve.type,
        reserve_value: budget.reserve.value,
      })
      setFormError(null)
    }
  }, [open, budget, reset])

  const mutation = useMutation({
    mutationFn: (values: BudgetCreateValues) =>
      budgetsApi.update(eventId, {
        expected_version: budget.version,
        total_limit: values.total_limit.trim(),
        reserve: {
          type: values.reserve_type,
          value: values.reserve_value.trim(),
        },
      }),
  })

  async function onSubmit(values: BudgetCreateValues) {
    setFormError(null)
    try {
      const updated = await mutation.mutateAsync(values)
      queryClient.setQueryData(queryKeys.budget(eventId), updated)
      toast.success('Budget settings updated.')
      onOpenChange(false)
    } catch (error) {
      if (error instanceof ApiError && error.isConflict) {
        await queryClient.invalidateQueries({ queryKey: queryKeys.budget(eventId) })
        setFormError(
          'This budget changed elsewhere. The latest version is now loaded; reopen the dialog to try again.',
        )
        return
      }
      if (error instanceof ApiError && error.isValidation) {
        for (const field of error.fields) {
          if (field.field.endsWith('total_limit')) {
            setError('total_limit', { type: 'server', message: field.message })
          } else if (field.field.endsWith('reserve.value')) {
            setError('reserve_value', { type: 'server', message: field.message })
          } else {
            setFormError(field.message)
          }
        }
      } else {
        setFormError(
          error instanceof Error ? error.message : 'Could not update the budget.',
        )
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Budget settings</DialogTitle>
          <DialogDescription>
            Changes use optimistic concurrency. If another tab changed this budget, you will
            be asked to review the latest version.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
          <FormField
            id="settings_total_limit"
            label={`Total budget (${budget.currency})`}
            error={errors.total_limit?.message}
            required
          >
            <Input
              id="settings_total_limit"
              inputMode="decimal"
              aria-invalid={Boolean(errors.total_limit)}
              {...register('total_limit')}
            />
          </FormField>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="settings_reserve_type"
              label="Reserve type"
              error={errors.reserve_type?.message}
              required
            >
              <Select
                value={reserveType}
                onValueChange={(value) =>
                  setValue('reserve_type', value as ReserveType, {
                    shouldValidate: true,
                  })
                }
              >
                <SelectTrigger id="settings_reserve_type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="percentage">Percentage of total</SelectItem>
                  <SelectItem value="fixed_amount">Fixed amount</SelectItem>
                </SelectContent>
              </Select>
            </FormField>
            <FormField
              id="settings_reserve_value"
              label={reserveType === 'percentage' ? 'Reserve percentage' : 'Reserve amount'}
              error={errors.reserve_value?.message}
              required
            >
              <Input
                id="settings_reserve_value"
                inputMode="decimal"
                aria-invalid={Boolean(errors.reserve_value)}
                {...register('reserve_value')}
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
              {isSubmitting || mutation.isPending ? 'Saving…' : 'Save settings'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function ExpenseDialog({
  open,
  onOpenChange,
  budget,
  eventId,
  expense,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  budget: BudgetResponse
  eventId: string
  expense?: ExpenseRecord
}) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ExpenseFormValues>({
    resolver: zodResolver(expenseFormSchema),
    defaultValues: {
      category: expense?.category ?? DEFAULT_EXPENSE_CATEGORIES[0]!,
      name: expense?.name ?? '',
      amount: expense?.amount ?? '',
      amount_status: expense?.amount_status ?? 'estimated',
      notes: expense?.notes ?? '',
    },
  })
  const status = watch('amount_status')

  useEffect(() => {
    if (!open) return
    reset({
      category: expense?.category ?? DEFAULT_EXPENSE_CATEGORIES[0]!,
      name: expense?.name ?? '',
      amount: expense?.amount ?? '',
      amount_status: expense?.amount_status ?? 'estimated',
      notes: expense?.notes ?? '',
    })
    setFormError(null)
  }, [open, expense, reset])

  const mutation = useMutation({
    mutationFn: (values: ExpenseFormValues) => {
      if (expense) {
        return budgetsApi.updateExpense(eventId, expense.expense_id, {
          expected_version: budget.version,
          category: values.category.trim(),
          name: values.name.trim(),
          amount: values.amount.trim(),
          amount_status: values.amount_status,
          notes: values.notes.trim() || null,
        })
      }
      return budgetsApi.addExpense(eventId, {
        expected_version: budget.version,
        category: values.category.trim(),
        name: values.name.trim(),
        amount: values.amount.trim(),
        amount_status: values.amount_status,
        notes: values.notes.trim() || null,
      })
    },
  })

  async function onSubmit(values: ExpenseFormValues) {
    setFormError(null)
    try {
      const updated = await mutation.mutateAsync(values)
      queryClient.setQueryData(queryKeys.budget(eventId), updated)
      toast.success(expense ? 'Expense updated.' : 'Expense added.')
      onOpenChange(false)
    } catch (error) {
      if (error instanceof ApiError && error.isConflict) {
        await queryClient.invalidateQueries({ queryKey: queryKeys.budget(eventId) })
        setFormError(
          'The budget changed while you were editing. The latest version is loaded; reopen this dialog and try again.',
        )
        return
      }
      if (error instanceof ApiError && error.isValidation) {
        for (const field of error.fields) {
          const key = field.field.replace(/^body\./, '')
          if (
            key === 'category' ||
            key === 'name' ||
            key === 'amount' ||
            key === 'amount_status' ||
            key === 'notes'
          ) {
            setError(key, { type: 'server', message: field.message })
          } else {
            setFormError(field.message)
          }
        }
      } else {
        setFormError(error instanceof Error ? error.message : 'Could not save the expense.')
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{expense ? 'Edit expense' : 'Add expense'}</DialogTitle>
          <DialogDescription>
            Mark a cost as estimated, quoted, or confirmed. Only confirmed expenses are
            treated as committed.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="expense_category"
              label="Category"
              error={errors.category?.message}
              required
            >
              <Input
                id="expense_category"
                list="expense-categories"
                aria-invalid={Boolean(errors.category)}
                {...register('category')}
              />
              <datalist id="expense-categories">
                {DEFAULT_EXPENSE_CATEGORIES.map((category) => (
                  <option key={category} value={category} />
                ))}
              </datalist>
            </FormField>
            <FormField
              id="expense_status"
              label="Status"
              error={errors.amount_status?.message}
              required
            >
              <Select
                value={status}
                onValueChange={(value) =>
                  setValue('amount_status', value as ExpenseStatus, {
                    shouldValidate: true,
                  })
                }
              >
                <SelectTrigger id="expense_status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EXPENSE_STATUSES.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          </div>
          <FormField
            id="expense_name"
            label="Expense name"
            error={errors.name?.message}
            required
          >
            <Input
              id="expense_name"
              placeholder="Venue deposit"
              aria-invalid={Boolean(errors.name)}
              {...register('name')}
            />
          </FormField>
          <FormField
            id="expense_amount"
            label={`Amount (${budget.currency})`}
            error={errors.amount?.message}
            required
          >
            <Input
              id="expense_amount"
              inputMode="decimal"
              placeholder="25000.00"
              aria-invalid={Boolean(errors.amount)}
              {...register('amount')}
            />
          </FormField>
          <FormField
            id="expense_notes"
            label="Notes"
            error={errors.notes?.message}
            description="Optional. Note whether a price is verified or only a working estimate."
          >
            <Textarea
              id="expense_notes"
              rows={3}
              placeholder="Quoted by the venue on 12 March; not yet confirmed."
              aria-invalid={Boolean(errors.notes)}
              {...register('notes')}
            />
          </FormField>
          {status ? (
            <p className="text-xs leading-5 text-muted">
              {EXPENSE_STATUSES.find((item) => item.value === status)?.helper}
            </p>
          ) : null}
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
                : expense
                  ? 'Save expense'
                  : 'Add expense'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function BudgetContent({ eventId }: { eventId: string }) {
  const eventQuery = useEventQuery(eventId)
  const budgetQuery = useBudgetQuery(eventId)
  const queryClient = useQueryClient()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [expenseDialogOpen, setExpenseDialogOpen] = useState(false)
  const [editingExpense, setEditingExpense] = useState<ExpenseRecord | undefined>()
  const [deletingExpense, setDeletingExpense] = useState<ExpenseRecord | undefined>()
  const [statusFilter, setStatusFilter] = useState<ExpenseStatus | 'all'>('all')

  const budget = budgetQuery.data
  const expenses = useMemo(() => {
    const items = budget?.expenses ?? []
    return statusFilter === 'all'
      ? items
      : items.filter((expense) => expense.amount_status === statusFilter)
  }, [budget?.expenses, statusFilter])

  const deleteMutation = useMutation({
    mutationFn: async (expense: ExpenseRecord) => {
      if (!budget) throw new Error('No budget loaded.')
      return budgetsApi.deleteExpense(eventId, expense.expense_id, budget.version)
    },
  })

  async function handleDeleteExpense() {
    if (!deletingExpense) return
    try {
      const updated = await deleteMutation.mutateAsync(deletingExpense)
      queryClient.setQueryData(queryKeys.budget(eventId), updated)
      toast.success('Expense removed.')
      setDeletingExpense(undefined)
    } catch (error) {
      if (error instanceof ApiError && error.isConflict) {
        await queryClient.invalidateQueries({ queryKey: queryKeys.budget(eventId) })
        toast.error('The budget changed. The latest version is loaded; try again.')
        setDeletingExpense(undefined)
        return
      }
      toast.error(error instanceof Error ? error.message : 'Could not remove the expense.')
    }
  }

  function openAddExpense() {
    setEditingExpense(undefined)
    setExpenseDialogOpen(true)
  }

  function openEditExpense(expense: ExpenseRecord) {
    setEditingExpense(expense)
    setExpenseDialogOpen(true)
  }

  if (budgetQuery.isLoading) return <PageSkeleton />

  if (budgetQuery.isError) {
    return (
      <ErrorState
        title="Budget could not load"
        error={budgetQuery.error}
        onRetry={() => void budgetQuery.refetch()}
      />
    )
  }

  if (!budget) {
    return (
      <SetupBudgetPanel
        eventId={eventId}
        suggestedTotal={eventQuery.data?.budget_amount ?? '100000.00'}
        currency={eventQuery.data?.currency ?? 'INR'}
      />
    )
  }

  const budgetUsed = percentage(budget.planned_spending, budget.available_for_planning)
  const reserveUsed = percentage(budget.reserve_consumed, budget.reserve.amount)
  const maxCategory = Math.max(
    1,
    ...budget.category_totals.map((category) => Number(category.amount)),
  )

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <BudgetStatusBadge status={budget.status} />
          <Badge tone="neutral">Version {budget.version}</Badge>
          <span className="text-xs text-muted">
            Totals calculated by the planning service
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setSettingsOpen(true)}
          >
            <Settings2 aria-hidden="true" />
            Budget settings
          </Button>
          <Button type="button" size="sm" onClick={openAddExpense}>
            <Plus aria-hidden="true" />
            Add expense
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total limit"
          value={formatMoney(budget.total_limit, budget.currency)}
          helper={`${formatMoney(budget.cost_per_guest ?? '0', budget.currency, { compact: true })} per guest`}
          icon={Wallet}
        />
        <StatCard
          label="Planned spending"
          value={formatMoney(budget.planned_spending, budget.currency)}
          helper={`${Math.round(budgetUsed)}% of planning budget`}
          icon={ReceiptText}
          tone={budgetUsed > 85 ? 'warning' : 'primary'}
        />
        <StatCard
          label="Remaining after reserve"
          value={formatMoney(budget.remaining_after_reserve, budget.currency)}
          helper={`${formatMoney(budget.remaining_total, budget.currency)} before reserve`}
          icon={
            budget.remaining_after_reserve.startsWith('-') ? ArrowDownRight : ArrowUpRight
          }
          tone={budget.remaining_after_reserve.startsWith('-') ? 'danger' : 'success'}
        />
        <StatCard
          label="Reserve"
          value={formatMoney(budget.reserve.amount, budget.currency)}
          helper={
            budget.reserve.type === 'percentage'
              ? `${budget.reserve.value}% · ${formatMoney(budget.reserve_consumed, budget.currency)} used`
              : `${formatMoney(budget.reserve_consumed, budget.currency)} used`
          }
          icon={ShieldCheck}
          tone={reserveUsed > 100 ? 'danger' : reserveUsed > 0 ? 'warning' : 'default'}
        />
      </div>

      {budget.issues.length > 0 ? (
        <div className="space-y-2">
          {budget.issues.map((issue) => (
            <div
              key={`${issue.code}-${issue.message}`}
              className="flex items-start gap-3 rounded-md border border-warning/25 bg-warning-soft p-3 text-sm text-ink-soft"
              role="status"
            >
              <AlertTriangle
                className="mt-0.5 size-4 shrink-0 text-warning"
                aria-hidden="true"
              />
              <div>
                <p className="font-semibold text-ink">
                  {issue.severity === 'error' ? 'Budget issue' : 'Budget warning'}
                </p>
                <p className="mt-0.5 leading-5">{issue.message}</p>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">
        <Card>
          <CardHeader>
            <CardTitle>Budget health</CardTitle>
            <CardDescription>
              The reserve is excluded from the amount available to plan with.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <div className="flex justify-between text-xs">
                <span className="font-medium text-ink">Planning budget used</span>
                <span className="text-muted">{Math.round(budgetUsed)}%</span>
              </div>
              <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-line">
                <div
                  className={
                    budget.status === 'over_budget'
                      ? 'h-full rounded-full bg-danger'
                      : budgetUsed > 85
                        ? 'h-full rounded-full bg-warning'
                        : 'h-full rounded-full bg-primary'
                  }
                  style={{ width: `${budgetUsed}%` }}
                />
              </div>
              <div className="mt-2 flex justify-between text-xs text-muted">
                <span>{formatMoney(budget.planned_spending, budget.currency)} planned</span>
                <span>
                  {formatMoney(budget.available_for_planning, budget.currency)} available
                </span>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-xs">
                <span className="font-medium text-ink">Reserve consumed</span>
                <span className="text-muted">{Math.round(reserveUsed)}%</span>
              </div>
              <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-line">
                <div
                  className={
                    reserveUsed > 100
                      ? 'h-full rounded-full bg-danger'
                      : reserveUsed > 0
                        ? 'h-full rounded-full bg-warning'
                        : 'h-full rounded-full bg-success'
                  }
                  style={{ width: `${Math.min(100, reserveUsed)}%` }}
                />
              </div>
              <div className="mt-2 flex justify-between text-xs text-muted">
                <span>{formatMoney(budget.reserve_consumed, budget.currency)} used</span>
                <span>{formatMoney(budget.reserve.amount, budget.currency)} reserve</span>
              </div>
            </div>
            {Number(budget.budget_overrun) > 0 ? (
              <div className="rounded-sm bg-danger-soft p-3 text-xs leading-5 text-danger">
                Planned spending exceeds the available planning budget by{' '}
                <strong>{formatMoney(budget.budget_overrun, budget.currency)}</strong>.
              </div>
            ) : (
              <div className="rounded-sm bg-success-soft p-3 text-xs leading-5 text-success">
                Planned spending is within the available budget.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Category breakdown</CardTitle>
            <CardDescription>Planned spending grouped by category.</CardDescription>
          </CardHeader>
          <CardContent>
            {budget.category_totals.length === 0 ? (
              <p className="text-sm text-muted">
                Add an expense to see how spending is distributed.
              </p>
            ) : (
              <ul className="space-y-4">
                {[...budget.category_totals]
                  .sort((a, b) => Number(b.amount) - Number(a.amount))
                  .map((category) => {
                    const share = (Number(category.amount) / maxCategory) * 100
                    return (
                      <li key={category.category}>
                        <div className="flex items-center justify-between gap-3 text-sm">
                          <span className="truncate text-ink-soft">
                            {category.category}
                          </span>
                          <span className="shrink-0 font-medium text-ink">
                            {formatMoney(category.amount, budget.currency, {
                              compact: true,
                            })}
                          </span>
                        </div>
                        <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-line">
                          <div
                            className="h-full rounded-full bg-primary/75"
                            style={{ width: `${Math.max(3, share)}%` }}
                          />
                        </div>
                      </li>
                    )
                  })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Expenses</CardTitle>
            <CardDescription>
              {budget.expenses.length}{' '}
              {budget.expenses.length === 1 ? 'expense' : 'expenses'} in this budget.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-40">
              <Select
                value={statusFilter}
                onValueChange={(value) => setStatusFilter(value as ExpenseStatus | 'all')}
              >
                <SelectTrigger aria-label="Filter expenses by status" className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  {EXPENSE_STATUSES.map((status) => (
                    <SelectItem key={status.value} value={status.value}>
                      {status.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={openAddExpense}>
              <Plus aria-hidden="true" />
              Add
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {budget.expenses.length === 0 ? (
            <EmptyState
              compact
              icon={ReceiptText}
              title="No expenses yet"
              description="Add venue, catering, decor, or any other planned cost. Mark each one as estimated, quoted, or confirmed."
              action={
                <Button type="button" size="sm" onClick={openAddExpense}>
                  <Plus aria-hidden="true" />
                  Add the first expense
                </Button>
              }
            />
          ) : expenses.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-muted">No expenses match that status.</p>
              <Button
                type="button"
                variant="link"
                size="sm"
                onClick={() => setStatusFilter('all')}
              >
                Show all expenses
              </Button>
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {expenses.map((expense) => (
                <li
                  key={expense.expense_id}
                  className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-ink">{expense.name}</p>
                      <ExpenseStatusBadge status={expense.amount_status} />
                    </div>
                    <p className="mt-1 text-xs text-muted">{expense.category}</p>
                    {expense.notes ? (
                      <p className="mt-1 text-xs leading-5 text-ink-soft">
                        {expense.notes}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2 sm:pl-4">
                    <span className="mr-2 text-sm font-semibold text-ink">
                      {formatMoney(expense.amount, budget.currency)}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => openEditExpense(expense)}
                      aria-label={`Edit ${expense.name}`}
                    >
                      <Pencil aria-hidden="true" />
                    </Button>
                    <Button
                      type="button"
                      variant="danger-ghost"
                      size="icon-sm"
                      onClick={() => setDeletingExpense(expense)}
                      aria-label={`Delete ${expense.name}`}
                    >
                      <Trash2 aria-hidden="true" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <div className="flex items-start gap-2 rounded-md border border-line bg-surface px-4 py-3 text-xs leading-5 text-muted">
        <RefreshCcw className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        Every change returns a freshly calculated budget from the server. If two tabs edit
        at once, the older save is rejected rather than silently overwriting the newer one.
      </div>

      <BudgetSettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        budget={budget}
        eventId={eventId}
      />

      <ExpenseDialog
        open={expenseDialogOpen}
        onOpenChange={(open) => {
          setExpenseDialogOpen(open)
          if (!open) setEditingExpense(undefined)
        }}
        budget={budget}
        eventId={eventId}
        {...(editingExpense ? { expense: editingExpense } : {})}
      />

      <ConfirmDialog
        open={Boolean(deletingExpense)}
        onOpenChange={(open) => {
          if (!open) setDeletingExpense(undefined)
        }}
        title="Remove this expense?"
        description={
          deletingExpense
            ? `“${deletingExpense.name}” (${formatMoney(deletingExpense.amount, budget.currency)}) will be removed from the planned budget.`
            : ''
        }
        confirmLabel="Remove expense"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={handleDeleteExpense}
      />
    </div>
  )
}

export function BudgetPage() {
  const { eventId } = useParams()
  if (!eventId) return null
  return <BudgetContent eventId={eventId} />
}
