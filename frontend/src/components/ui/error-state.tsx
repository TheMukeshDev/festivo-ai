import { AlertTriangle, RotateCcw } from 'lucide-react'

import { ApiError } from '@/lib/api/errors'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ErrorStateProps {
  title?: string
  error?: unknown
  onRetry?: () => void
  className?: string
  compact?: boolean
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isNetwork) {
      return 'The planning service could not be reached. Start the backend or check your connection, then retry.'
    }
    return error.message
  }
  if (error instanceof Error && error.message) return error.message
  return 'Something went wrong while loading this section.'
}

export function ErrorState({
  title = 'This section could not load',
  error,
  onRetry,
  className,
  compact = false,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-danger/20 bg-danger-soft/50 px-5 text-left',
        compact ? 'py-4' : 'py-6',
        className,
      )}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-danger/10 text-danger-strong">
          <AlertTriangle className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-ink-soft">{describeError(error)}</p>
          {onRetry ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onRetry}
              className="mt-3 bg-surface"
            >
              <RotateCcw aria-hidden="true" />
              Try again
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
