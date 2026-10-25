import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { AlertTriangle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function FeatureUnavailable({
  icon: Icon,
  title,
  description,
  reasons,
  alternatives,
}: {
  icon: LucideIcon
  title: string
  description: string
  reasons: string[]
  alternatives?: ReactNode
}) {
  return (
    <Card className="border-warning/30 bg-warning-soft/30">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface text-warning-strong">
              <Icon className="size-5" aria-hidden="true" />
            </span>
            <div>
              <CardTitle>{title}</CardTitle>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-ink-soft">
                {description}
              </p>
            </div>
          </div>
          <Badge tone="warning">Not available yet</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-[0.08em] text-muted">
            <AlertTriangle className="size-3.5" aria-hidden="true" />
            Why this is unavailable
          </p>
          <ul className="mt-2 space-y-1.5">
            {reasons.map((reason) => (
              <li
                key={reason}
                className="flex items-start gap-2 text-sm leading-6 text-ink-soft"
              >
                <span
                  className="mt-2.5 size-1 shrink-0 rounded-full bg-warning"
                  aria-hidden="true"
                />
                {reason}
              </li>
            ))}
          </ul>
        </div>
        {alternatives ? (
          <div className="border-t border-warning/20 pt-4">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">
              What you can do instead
            </p>
            <div className="mt-2.5">{alternatives}</div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
