import { cn } from '@/lib/utils'

interface ProgressProps {
  value: number
  label: string
  tone?: 'primary' | 'warning' | 'danger' | 'success'
  className?: string
}

const toneClasses = {
  primary: 'bg-primary',
  warning: 'bg-warning',
  danger: 'bg-danger',
  success: 'bg-success',
} as const

export function Progress({ value, label, tone = 'primary', className }: ProgressProps) {
  const clamped = Math.min(100, Math.max(0, value))
  return (
    <div
      className={cn('h-2 w-full overflow-hidden rounded-full bg-line', className)}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped)}
    >
      <div
        className={cn('h-full rounded-full transition-[width]', toneClasses[tone])}
        style={{ width: `${clamped}%` }}
      />
    </div>
  )
}
