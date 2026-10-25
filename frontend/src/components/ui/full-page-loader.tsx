import { LoaderCircle } from 'lucide-react'

export function FullPageLoader({ label = 'Loading' }: { label?: string }) {
  return (
    <div
      className="flex min-h-screen items-center justify-center bg-canvas"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3 rounded-md border border-line bg-surface px-4 py-3 text-sm text-ink-soft shadow-soft">
        <LoaderCircle className="size-4 animate-spin text-primary" aria-hidden="true" />
        {label}
      </div>
    </div>
  )
}

export function InlineLoader({ label = 'Loading' }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted" role="status">
      <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
      {label}
    </span>
  )
}
