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
      <img src="/favicon.svg" alt="Festivo AI logo" className="size-9 rounded-[0.7rem] shadow-sm" />
      {!compact ? (
        <span className="font-display text-[1.35rem] tracking-[-0.02em] text-ink">
          Festivo <span className="text-primary">AI</span>
        </span>
      ) : null}
    </Link>
  )
}
