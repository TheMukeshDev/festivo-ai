import type * as React from 'react'

import { cn } from '@/lib/utils'

export function Field({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('flex flex-col gap-2', className)} {...props} />
}

export function FieldDescription({ className, ...props }: React.ComponentProps<'p'>) {
  return <p className={cn('text-xs leading-5 text-muted', className)} {...props} />
}

export function FieldError({
  id,
  message,
  className,
}: {
  id?: string
  message?: string
  className?: string
}) {
  if (!message) return null
  return (
    <p id={id} role="alert" className={cn('text-xs font-medium text-danger', className)}>
      {message}
    </p>
  )
}

export function RequiredMark() {
  return (
    <span className="text-danger" aria-hidden="true">
      {' '}
      *
    </span>
  )
}
