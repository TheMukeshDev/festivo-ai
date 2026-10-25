import { Badge } from '@/components/ui/badge'
import {
  BUDGET_STATUS_LABELS,
  expenseStatusLabel,
  taskPriorityLabel,
  taskPriorityTone,
  taskStatusLabel,
  taskStatusTone,
  vendorStatusLabel,
  vendorStatusTone,
} from '@/lib/labels'
import type {
  BudgetStatus,
  ExpenseStatus,
  TaskPriority,
  TaskStatus,
  VendorStatus,
} from '@/types/api'

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return <Badge tone={taskStatusTone[status]}>{taskStatusLabel(status)}</Badge>
}

export function TaskPriorityBadge({ priority }: { priority: TaskPriority }) {
  return <Badge tone={taskPriorityTone[priority]}>{taskPriorityLabel(priority)}</Badge>
}

export function VendorStatusBadge({ status }: { status: VendorStatus }) {
  return <Badge tone={vendorStatusTone[status]}>{vendorStatusLabel(status)}</Badge>
}

export function ExpenseStatusBadge({ status }: { status: ExpenseStatus }) {
  const tone =
    status === 'confirmed' ? 'success' : status === 'quoted' ? 'warning' : 'neutral'
  return <Badge tone={tone}>{expenseStatusLabel(status)}</Badge>
}

export function BudgetStatusBadge({ status }: { status: BudgetStatus }) {
  const tone =
    status === 'over_budget'
      ? 'danger'
      : status === 'reserve_consumed'
        ? 'warning'
        : 'success'
  return <Badge tone={tone}>{BUDGET_STATUS_LABELS[status]}</Badge>
}
