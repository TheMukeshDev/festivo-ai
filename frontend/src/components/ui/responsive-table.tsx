import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export function TableWrap({
  children,
  className,
  label,
}: {
  children: ReactNode
  className?: string
  label?: string
}) {
  return (
    <div
      className={cn('w-full overflow-x-auto rounded-md border border-line', className)}
      tabIndex={0}
      role="region"
      aria-label={label ?? 'Scrollable table'}
    >
      {children}
    </div>
  )
}

export function Table({ children }: { children: ReactNode }) {
  return (
    <table className="w-full min-w-[44rem] border-collapse text-left text-sm">
      {children}
    </table>
  )
}

export function Th({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <th
      scope="col"
      className={cn(
        'border-b border-line bg-canvas/80 px-4 py-3 text-xs font-semibold uppercase tracking-[0.08em] text-muted',
        className,
      )}
    >
      {children}
    </th>
  )
}

export function Td({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <td className={cn('border-b border-line px-4 py-3 align-top', className)}>
      {children}
    </td>
  )
}
