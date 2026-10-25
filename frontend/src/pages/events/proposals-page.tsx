import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Check, FileSignature, RefreshCw, X } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { Skeleton } from '@/components/ui/skeleton'
import { useEventQuery, useProposalsQuery } from '@/features/events/queries'
import { proposalsApi, queryKeys } from '@/lib/api/queries'
import { formatDateTime } from '@/lib/format'
import type { ProposalRecord } from '@/types/api'

const statusLabels: Record<ProposalRecord['status'], string> = {
  pending: 'Pending review',
  partially_approved: 'Partially approved',
  approved: 'Approved',
  rejected: 'Rejected',
  expired: 'Expired',
}

export function ProposalsPage() {
  const { eventId } = useParams()
  const eventQuery = useEventQuery(eventId)
  const proposalsQuery = useProposalsQuery(eventId)
  const client = useQueryClient()
  const [confirm, setConfirm] = useState<{
    action: 'approve' | 'reject'
    proposal: ProposalRecord
  } | null>(null)

  const refresh = () => {
    void proposalsQuery.refetch()
  }
  const generate = useMutation({
    mutationFn: () => proposalsApi.generate(eventId!, { preferences: {}, focus_areas: [] }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.proposals(eventId!) })
      toast.success('Proposal generated and ready for review.')
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const approve = useMutation({
    mutationFn: (proposal: ProposalRecord) =>
      proposalsApi.approve(eventId!, proposal.proposal_id),
    onSuccess: () => {
      setConfirm(null)
      void client.invalidateQueries({ queryKey: queryKeys.proposals(eventId!) })
      void client.invalidateQueries({ queryKey: queryKeys.tasks(eventId!) })
      void client.invalidateQueries({ queryKey: queryKeys.budget(eventId!) })
      toast.success('Eligible proposal items were applied.')
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const reject = useMutation({
    mutationFn: (proposal: ProposalRecord) =>
      proposalsApi.reject(eventId!, proposal.proposal_id),
    onSuccess: () => {
      setConfirm(null)
      void client.invalidateQueries({ queryKey: queryKeys.proposals(eventId!) })
      toast.success('Proposal rejected.')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  if (!eventId) return null
  if (proposalsQuery.isLoading)
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  if (proposalsQuery.isError)
    return (
      <ErrorState
        title="Proposals could not load"
        error={proposalsQuery.error}
        onRetry={refresh}
      />
    )
  const proposals = proposalsQuery.data?.items ?? []

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Human review required</p>
          <h2 className="font-display text-2xl text-ink">Proposals</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
            Review suggested planning changes before anything is added to{' '}
            {eventQuery.data?.name ?? 'this event'}.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={refresh} disabled={proposalsQuery.isFetching}>
            <RefreshCw aria-hidden="true" />
            Refresh
          </Button>
          <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
            <FileSignature aria-hidden="true" />
            {generate.isPending ? 'Generating…' : 'Generate proposal'}
          </Button>
        </div>
      </div>
      {proposals.length === 0 ? (
        <EmptyState
          icon={FileSignature}
          title="No proposals yet"
          description="Generate a proposal when you want AI suggestions collected into a reviewable, explicitly approvable plan."
        />
      ) : (
        <div className="space-y-4">
          {proposals.map((proposal) => (
            <Card key={proposal.proposal_id}>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle>{proposal.title}</CardTitle>
                    <p className="mt-1 text-sm text-muted">{proposal.summary}</p>
                  </div>
                  <span className="rounded-full bg-primary-soft px-3 py-1 text-xs font-semibold text-primary-strong">
                    {statusLabels[proposal.status]}
                  </span>
                </div>
                <p className="text-xs text-muted">
                  Created {formatDateTime(proposal.created_at)} · Expires{' '}
                  {formatDateTime(proposal.expires_at)}
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  {proposal.items.map((item) => (
                    <div
                      key={item.item_id}
                      className="rounded-sm border border-line bg-canvas/50 p-3"
                    >
                      <div className="flex items-start gap-2">
                        <AlertTriangle
                          className="mt-0.5 size-4 text-warning-strong"
                          aria-hidden="true"
                        />
                        <div>
                          <p className="text-sm font-semibold text-ink">{item.label}</p>
                          <p className="text-xs text-muted">
                            {item.result_message ??
                              `Suggested ${item.action_type.replaceAll('_', ' ')}`}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                {proposal.pending_item_count > 0 && proposal.status !== 'expired' ? (
                  <div className="flex flex-wrap gap-2 border-t border-line pt-4">
                    <Button onClick={() => setConfirm({ action: 'approve', proposal })}>
                      <Check aria-hidden="true" />
                      Approve eligible items
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setConfirm({ action: 'reject', proposal })}
                    >
                      <X aria-hidden="true" />
                      Reject proposal
                    </Button>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <ConfirmDialog
        open={Boolean(confirm)}
        onOpenChange={(open) => {
          if (!open) setConfirm(null)
        }}
        title={
          confirm?.action === 'approve' ? 'Approve this proposal?' : 'Reject this proposal?'
        }
        description={
          confirm?.action === 'approve'
            ? 'Supported changes will be applied by the backend. Advisory suggestions are recorded without changing confirmed finances.'
            : 'Pending suggestions will be marked rejected and will not change your event.'
        }
        confirmLabel={
          confirm?.action === 'approve' ? 'Approve eligible items' : 'Reject proposal'
        }
        destructive={confirm?.action === 'reject'}
        loading={approve.isPending || reject.isPending}
        onConfirm={() => {
          if (!confirm) return
          if (confirm.action === 'approve') {
            approve.mutate(confirm.proposal)
          } else {
            reject.mutate(confirm.proposal)
          }
        }}
      />
    </div>
  )
}
