import type * as React from 'react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export function Card({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('surface-card', className)} {...props} />
}

export function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('flex flex-col gap-1.5 p-5 sm:p-6', className)} {...props} />
}

export function CardTitle({
  children,
  className,
  ...props
}: React.ComponentProps<'h2'> & { children: ReactNode }) {
  return (
    <h2
      className={cn('font-display text-xl tracking-[-0.01em] text-ink', className)}
      {...props}
    >
      {children}
    </h2>
  )
}

export function CardDescription({ className, ...props }: React.ComponentProps<'p'>) {
  return <p className={cn('text-sm leading-6 text-muted', className)} {...props} />
}

export function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('p-5 pt-0 sm:p-6 sm:pt-0', className)} {...props} />
}

export function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-3 border-t border-line px-5 py-4 sm:px-6',
        className,
      )}
      {...props}
    />
  )
}
