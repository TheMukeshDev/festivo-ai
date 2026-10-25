import { Link, useParams } from 'react-router-dom'
import { ArrowRight, Download } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { FeatureUnavailable } from '@/components/ui/feature-unavailable'
import { useEventQuery } from '@/features/events/queries'

export function ExportsPage() {
  const { eventId } = useParams()
  const eventQuery = useEventQuery(eventId)

  if (!eventId) return null

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-2xl text-ink">Exports</h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
          A future home for downloadable event plans, budgets, and timelines.
        </p>
      </div>

      <FeatureUnavailable
        icon={Download}
        title="Exports are not available in this build"
        description={`Festivo cannot generate a PDF or CSV for ${eventQuery.data?.name ?? 'this event'} yet. No download button has been added because there is no file to download.`}
        reasons={[
          'The backend does not expose PDF or CSV export endpoints.',
          'Generating a file entirely in the browser would not use the authoritative event, budget, timeline, and vendor records.',
          'A placeholder download would be misleading and could be mistaken for a complete planning document.',
        ]}
        alternatives={
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button asChild variant="outline">
              <Link to={`/app/events/${eventId}`}>
                Review the event overview
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to={`/app/events/${eventId}/budget`}>
                Review the budget
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          </div>
        }
      />
    </div>
  )
}
