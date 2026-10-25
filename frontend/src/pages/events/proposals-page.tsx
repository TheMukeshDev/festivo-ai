import { Link, useParams } from 'react-router-dom'
import { ArrowRight, FileSignature } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { FeatureUnavailable } from '@/components/ui/feature-unavailable'
import { useEventQuery } from '@/features/events/queries'

export function ProposalsPage() {
  const { eventId } = useParams()
  const eventQuery = useEventQuery(eventId)

  if (!eventId) return null

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-2xl text-ink">Proposals</h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
          A future home for vendor proposals, approvals, and decision history.
        </p>
      </div>

      <FeatureUnavailable
        icon={FileSignature}
        title="Proposal approval is not available in this build"
        description={`Proposal workflows are not connected for ${eventQuery.data?.name ?? 'this event'}. Festivo will not pretend a proposal has been created, sent, or approved.`}
        reasons={[
          'The backend has no proposal endpoint or proposal data model yet.',
          'The proposals database migration is an empty placeholder, so nothing could be stored safely.',
          'Creating a client-side-only proposal would produce a misleading record that disappears or cannot be reviewed.',
        ]}
        alternatives={
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button asChild variant="outline">
              <Link to={`/app/events/${eventId}/vendors`}>
                Track vendors and quotes
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to={`/app/events/${eventId}/budget`}>
                Record budget decisions
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
          </div>
        }
      />
    </div>
  )
}
