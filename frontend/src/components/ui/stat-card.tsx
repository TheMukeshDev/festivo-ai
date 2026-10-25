import type { LucideIcon } from 'lucide-react'

import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string
  helper?: string
  icon?: LucideIcon
  tone?: 'default' | 'primary' | 'warning' | 'danger' | 'success'
  className?: string
}

const toneClasses = {
  default: 'bg-canvas text-ink-soft',
  primary: 'bg-primary-soft text-primary',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
  success: 'bg-success-soft text-success',
} as const

export function StatCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = 'default',
  className,
}: StatCardProps) {
  return (
    <div className={cn('surface-card p-5', className)}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
          {label}
        </p>
        {Icon ? (
          <span
            className={cn(
              'flex size-8 items-center justify-center rounded-full',
              toneClasses[tone],
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
          </span>
        ) : null}
      </div>
      <p className="mt-3 font-display text-3xl leading-none tracking-[-0.02em] text-ink">
        {value}
      </p>
      {helper ? <p className="mt-2 text-xs leading-5 text-muted">{helper}</p> : null}
    </div>
  )
}
