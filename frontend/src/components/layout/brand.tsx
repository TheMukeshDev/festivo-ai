import { Link } from 'react-router-dom'

import { cn } from '@/lib/utils'

export function Brand({
  to = '/',
  compact = false,
  className,
}: {
  to?: string
  compact?: boolean
  className?: string
}) {
  return (
    <Link
      to={to}
      className={cn('inline-flex items-center gap-2.5 rounded-sm', className)}
      aria-label="Festivo AI home"
    >
      <span className="relative flex size-9 items-center justify-center rounded-[0.7rem] bg-primary text-white shadow-sm">
        <span className="font-display text-lg leading-none">F</span>
        <span
          className="absolute -right-1 -top-1 size-2.5 rounded-full border-2 border-canvas bg-accent"
          aria-hidden="true"
        />
      </span>
      {!compact ? (
        <span className="font-display text-[1.35rem] tracking-[-0.02em] text-ink">
          Festivo <span className="text-primary">AI</span>
        </span>
      ) : null}
    </Link>
  )
}
