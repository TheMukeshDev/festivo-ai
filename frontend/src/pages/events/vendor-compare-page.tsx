import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  CircleSlash,
  Scale,
  Sparkles,
  Store,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { FormField } from '@/components/ui/form-field'
import { Input } from '@/components/ui/input'
import { PageSkeleton } from '@/components/ui/skeleton'
import { VendorStatusBadge } from '@/components/ui/status-badge'
import { useEventQuery, useVendorsQuery } from '@/features/events/queries'
import {
  BUDGET_FIT_LABELS,
  PREFERENCE_MATCH_LABELS,
  vendorPriceRange,
} from '@/features/vendors/vendor-utils'
import { vendorsApi } from '@/lib/api/queries'
import { formatMoney } from '@/lib/format'
import { vendorCategoryLabel } from '@/lib/labels'
import type { VendorCompareItem, VendorCompareResponse } from '@/types/api'

const missingLabels: Record<string, string> = {
  'price/quote': 'Price or quote',
  rating: 'Rating',
  availability: 'Availability',
  service_area: 'Service area',
}

function ComparisonPrice({ item }: { item: VendorCompareItem }) {
  if (item.quoted_cost) {
    return (
      <div>
        <p className="text-[0.65rem] font-semibold uppercase tracking-[0.08em] text-muted">
          Quoted
        </p>
        <p className="font-display text-2xl text-ink">
          {formatMoney(item.quoted_cost, item.currency)}
        </p>
      </div>
    )
  }
  if (item.final_cost) {
    return (
      <div>
        <p className="text-[0.65rem] font-semibold uppercase tracking-[0.08em] text-muted">
          Final cost
        </p>
        <p className="font-display text-2xl text-ink">
          {formatMoney(item.final_cost, item.currency)}
        </p>
      </div>
    )
  }
  if (item.estimated_cost) {
    return (
      <div>
        <p className="text-[0.65rem] font-semibold uppercase tracking-[0.08em] text-muted">
          Estimate
        </p>
        <p className="font-display text-2xl text-ink">
          {formatMoney(item.estimated_cost, item.currency)}
        </p>
      </div>
    )
  }
  if (item.price_min || item.price_max) {
    return (
      <div>
        <p className="text-[0.65rem] font-semibold uppercase tracking-[0.08em] text-muted">
          Listed range
        </p>
        <p className="font-display text-xl text-ink">
          {item.price_min ? formatMoney(item.price_min, item.currency) : '—'}
          {' – '}
          {item.price_max ? formatMoney(item.price_max, item.currency) : '—'}
        </p>
      </div>
    )
  }
  return (
    <div>
      <p className="text-[0.65rem] font-semibold uppercase tracking-[0.08em] text-muted">
        Price
      </p>
      <p className="font-display text-xl text-muted">Not recorded</p>
    </div>
  )
}

function ComparisonCard({ item, index }: { item: VendorCompareItem; index: number }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
              Option {index + 1}
            </p>
            <CardTitle className="mt-1">{item.name}</CardTitle>
            <p className="mt-1 text-xs text-muted">{vendorCategoryLabel(item.category)}</p>
          </div>
          <VendorStatusBadge status={item.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <ComparisonPrice item={item} />

        <div className="flex flex-wrap gap-2">
          {item.comparable_price ? (
            <Badge tone="success">
              <CheckCircle2 className="size-3" aria-hidden="true" />
              Price can be compared
            </Badge>
          ) : (
            <Badge tone="warning">
              <CircleSlash className="size-3" aria-hidden="true" />
              Price not fairly comparable
            </Badge>
          )}
          {item.budget_fit ? (
            <Badge
              tone={
                item.budget_fit === 'within_event_budget'
                  ? 'success'
                  : item.budget_fit === 'over_event_budget'
                    ? 'warning'
                    : 'neutral'
              }
            >
              {BUDGET_FIT_LABELS[item.budget_fit] ?? item.budget_fit}
            </Badge>
          ) : null}
        </div>

        <dl className="grid grid-cols-2 gap-3 border-y border-line py-3 text-sm">
          <div>
            <dt className="text-xs text-muted">Rating</dt>
            <dd className="mt-0.5 font-medium text-ink">
              {item.rating ? `${item.rating} / 5` : 'Not recorded'}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Availability</dt>
            <dd className="mt-0.5 font-medium text-ink">
              {item.availability ?? 'Not recorded'}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Service area</dt>
            <dd className="mt-0.5 font-medium text-ink">
              {item.service_area ?? 'Not recorded'}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Currency</dt>
            <dd className="mt-0.5 font-medium text-ink">{item.currency}</dd>
          </div>
        </dl>

        {item.preference_match.length > 0 ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">
              Matches your preferences
            </p>
            <ul className="mt-2 space-y-1.5">
              {item.preference_match.map((match) => (
                <li key={match} className="flex items-start gap-2 text-xs text-ink-soft">
                  <CheckCircle2
                    className="mt-0.5 size-3.5 shrink-0 text-success"
                    aria-hidden="true"
                  />
                  {PREFERENCE_MATCH_LABELS[match] ?? match}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {item.missing.length > 0 ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">
              Missing information
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {item.missing.map((missing) => (
                <Badge key={missing} tone="neutral">
                  {missingLabels[missing] ?? missing}
                </Badge>
              ))}
            </div>
          </div>
        ) : null}

        {item.reasons_cannot_compare_fairly.length > 0 ? (
          <div className="rounded-sm bg-warning-soft p-3">
            <p className="text-xs font-semibold text-ink">
              What prevents a fair comparison
            </p>
            <ul className="mt-1.5 space-y-1">
              {item.reasons_cannot_compare_fairly.map((reason) => (
                <li
                  key={reason}
                  className="flex items-start gap-2 text-xs leading-5 text-ink-soft"
                >
                  <AlertTriangle
                    className="mt-0.5 size-3 shrink-0 text-warning"
                    aria-hidden="true"
                  />
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {item.notes ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">
              Notes
            </p>
            <p className="mt-1 text-xs leading-5 text-ink-soft">{item.notes}</p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function CompareContent({ eventId }: { eventId: string }) {
  const eventQuery = useEventQuery(eventId)
  const vendorsQuery = useVendorsQuery(eventId)
  const [searchParams] = useSearchParams()
  const initialIds = useMemo(
    () =>
      (searchParams.get('ids') ?? '')
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean),
    [searchParams],
  )
  const [selected, setSelected] = useState<string[]>(initialIds)
  const [maxPrice, setMaxPrice] = useState('')
  const [preferArea, setPreferArea] = useState('')
  const [quickResponse, setQuickResponse] = useState(false)
  const [priceError, setPriceError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [result, setResult] = useState<VendorCompareResponse | null>(null)

  const event = eventQuery.data
  const vendors = vendorsQuery.data?.items ?? []

  const compareMutation = useMutation({
    mutationFn: () => {
      if (selected.length < 2) throw new Error('Select at least two vendors to compare.')
      if (selected.length > 10) throw new Error('Compare no more than ten vendors at once.')
      return vendorsApi.compare(eventId, {
        vendor_ids: selected,
        ...(maxPrice.trim() ? { max_price: maxPrice.trim() } : {}),
        ...(preferArea.trim() ? { prefer_service_area: preferArea.trim() } : {}),
        prefer_quick_response: quickResponse,
      })
    },
  })

  function toggleSelected(vendorId: string) {
    setResult(null)
    setFormError(null)
    setSelected((current) => {
      if (current.includes(vendorId)) return current.filter((id) => id !== vendorId)
      return [...current, vendorId]
    })
  }

  async function handleCompare() {
    setPriceError(null)
    setFormError(null)
    if (maxPrice.trim() && !/^\d{1,9}(\.\d{1,2})?$/.test(maxPrice.trim())) {
      setPriceError('Enter a valid maximum price with up to two decimal places.')
      return
    }
    try {
      const response = await compareMutation.mutateAsync()
      setResult(response)
    } catch (error) {
      setFormError(
        error instanceof Error ? error.message : 'Could not compare these vendors.',
      )
    }
  }

  if (vendorsQuery.isLoading || !event) return <PageSkeleton />

  if (vendors.length < 2) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link to={`/app/events/${eventId}/vendors`}>
            <ArrowLeft aria-hidden="true" />
            Back to vendors
          </Link>
        </Button>
        <EmptyState
          icon={Scale}
          title="Add at least two vendors"
          description="Comparison needs at least two saved vendor options. Add them first, then select the ones you want to compare."
          action={
            <Button asChild>
              <Link to={`/app/events/${eventId}/vendors`}>
                <Store aria-hidden="true" />
                Go to vendors
              </Link>
            </Button>
          }
        />
      </div>
    )
  }

  const selectedVendors = vendors.filter((vendor) => selected.includes(vendor.vendor_id))

  return (
    <div className="space-y-5">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link to={`/app/events/${eventId}/vendors`}>
          <ArrowLeft aria-hidden="true" />
          Back to vendors
        </Link>
      </Button>

      <div>
        <h2 className="font-display text-2xl text-ink">Compare vendors</h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
          This comparison shows the information you recorded. It does not declare a winner,
          contact vendors, or assume missing prices.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select vendors and criteria</CardTitle>
          <CardDescription>
            Choose 2–10 vendors. Preferences only add context; they do not override missing
            facts.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {vendors.map((vendor) => {
              const isSelected = selected.includes(vendor.vendor_id)
              return (
                <label
                  key={vendor.vendor_id}
                  className={
                    isSelected
                      ? 'flex cursor-pointer items-start gap-2.5 rounded-md border border-primary bg-primary-soft/40 p-3'
                      : 'flex cursor-pointer items-start gap-2.5 rounded-md border border-line bg-surface-raised p-3 hover:border-line-strong'
                  }
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelected(vendor.vendor_id)}
                    className="mt-0.5 size-4 shrink-0 accent-primary"
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-ink">
                      {vendor.name}
                    </span>
                    <span className="mt-0.5 block text-xs text-muted">
                      {vendorCategoryLabel(vendor.category)}
                    </span>
                    <span className="mt-1 block text-xs text-ink-soft">
                      {vendorPriceRange(vendor)}
                    </span>
                  </span>
                </label>
              )
            })}
          </div>

          <div className="grid gap-4 border-t border-line pt-4 sm:grid-cols-2">
            <FormField
              id="compare_max_price"
              label={`Maximum price (${event.currency})`}
              error={priceError ?? undefined}
              description="Optional. Used to flag whether recorded prices fit your limit."
            >
              <Input
                id="compare_max_price"
                inputMode="decimal"
                placeholder="100000.00"
                value={maxPrice}
                onChange={(changeEvent) => {
                  setMaxPrice(changeEvent.target.value)
                  setPriceError(null)
                  setResult(null)
                }}
              />
            </FormField>
            <FormField
              id="compare_area"
              label="Preferred service area"
              description="Optional. Matches are noted only when the vendor has a service area recorded."
            >
              <Input
                id="compare_area"
                placeholder="Bengaluru"
                value={preferArea}
                onChange={(changeEvent) => {
                  setPreferArea(changeEvent.target.value)
                  setResult(null)
                }}
              />
            </FormField>
          </div>

          <label className="flex items-start gap-2.5 text-sm text-ink-soft">
            <input
              type="checkbox"
              checked={quickResponse}
              onChange={(changeEvent) => {
                setQuickResponse(changeEvent.target.checked)
                setResult(null)
              }}
              className="mt-1 size-4 accent-primary"
            />
            <span>
              Prefer vendors already contacted or quoted
              <span className="mt-0.5 block text-xs text-muted">
                This uses recorded status only. It is not a response-time measurement.
              </span>
            </span>
          </label>

          {formError ? (
            <p
              role="alert"
              className="rounded-sm border border-danger/20 bg-danger-soft px-3 py-2 text-sm text-danger-strong"
            >
              {formError}
            </p>
          ) : null}

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted">
              {selected.length} of 10 selected · {selectedVendors.length} valid for
              comparison
            </p>
            <div className="flex gap-2">
              {result ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setResult(null)
                    setFormError(null)
                    setPriceError(null)
                  }}
                >
                  Clear results
                </Button>
              ) : null}
              <Button
                type="button"
                onClick={handleCompare}
                disabled={selected.length < 2 || compareMutation.isPending}
              >
                <Scale aria-hidden="true" />
                {compareMutation.isPending ? 'Comparing…' : 'Compare selected'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {result ? (
        <div className="space-y-5">
          <Card className="border-primary/20 bg-primary-soft/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="size-5 text-primary" aria-hidden="true" />
                How Festivo compared
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="leading-6 text-ink-soft">{result.ordering}</p>
              {result.criteria.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted">
                    Criteria
                  </p>
                  <ul className="mt-1.5 grid gap-1 sm:grid-cols-2">
                    {result.criteria.map((criterion) => (
                      <li key={criterion} className="text-xs leading-5 text-ink-soft">
                        {criterion}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {result.limitations.length > 0 ? (
                <div className="rounded-sm bg-surface/80 p-3">
                  <p className="text-xs font-semibold text-ink">Limitations</p>
                  <ul className="mt-1.5 space-y-1">
                    {result.limitations.map((limitation) => (
                      <li
                        key={limitation}
                        className="flex items-start gap-2 text-xs leading-5 text-ink-soft"
                      >
                        <AlertTriangle
                          className="mt-0.5 size-3 shrink-0 text-warning"
                          aria-hidden="true"
                        />
                        {limitation}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            {result.items.map((item, index) => (
              <ComparisonCard key={item.vendor_id} item={item} index={index} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

export function VendorComparePage() {
  const { eventId } = useParams()
  if (!eventId) return null
  return <CompareContent eventId={eventId} />
}
