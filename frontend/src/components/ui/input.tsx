import type * as React from 'react'

import { cn } from '@/lib/utils'

export function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      className={cn(
        'flex h-10 w-full rounded-sm border border-line-strong bg-surface-raised px-3 py-2 text-sm text-ink shadow-xs transition-colors placeholder:text-muted/70 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-60',
        className,
      )}
      {...props}
    />
  )
}

export function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      className={cn(
        'flex min-h-24 w-full rounded-sm border border-line-strong bg-surface-raised px-3 py-2 text-sm leading-6 text-ink shadow-xs transition-colors placeholder:text-muted/70 focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-60',
        className,
      )}
      {...props}
    />
  )
}
