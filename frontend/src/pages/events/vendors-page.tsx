import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  ExternalLink,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Plus,
  Search,
  Star,
  Store,
  Trash2,
  UsersRound,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardHeader } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { Input } from '@/components/ui/input'
import { PageSkeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { VendorStatusBadge } from '@/components/ui/status-badge'
import { useEventQuery, useVendorsQuery } from '@/features/events/queries'
import { VendorFormDialog } from '@/features/vendors/vendor-form-dialog'
import { vendorPriceRange } from '@/features/vendors/vendor-utils'
import { vendorsApi } from '@/lib/api/queries'
import { VENDOR_CATEGORIES, VENDOR_STATUSES, vendorCategoryLabel } from '@/lib/labels'
import type { VendorCategory, VendorRecord, VendorStatus } from '@/types/api'

function VendorCard({
  vendor,
  selected,
  onToggle,
  onEdit,
  onDelete,
}: {
  vendor: VendorRecord
  selected: boolean
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <article
      className={
        selected
          ? 'rounded-lg border border-primary bg-primary-soft/30 p-5'
          : 'rounded-lg border border-line bg-surface p-5 transition-shadow hover:shadow-raised'
      }
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          aria-label={`Select ${vendor.name} for comparison`}
          className="mt-1 size-4 shrink-0 rounded-xs border-line-strong accent-primary"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="truncate font-display text-lg text-ink">{vendor.name}</h3>
              <p className="mt-0.5 text-xs text-muted">
                {vendorCategoryLabel(vendor.category)}
              </p>
            </div>
            <VendorStatusBadge status={vendor.status} />
          </div>

          {vendor.description ? (
            <p className="mt-2 line-clamp-2 text-sm leading-5 text-ink-soft">
              {vendor.description}
            </p>
          ) : null}

          <div className="mt-3 grid gap-1.5 text-xs text-muted sm:grid-cols-2">
            <span className="inline-flex items-center gap-1.5">
              <span className="font-semibold text-ink-soft">Price:</span>
              {vendorPriceRange(vendor)}
            </span>
            {vendor.rating ? (
              <span className="inline-flex items-center gap-1.5">
                <Star className="size-3" aria-hidden="true" />
                Rating {vendor.rating} / 5
              </span>
            ) : null}
            {vendor.service_area ? (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="size-3" aria-hidden="true" />
                {vendor.service_area}
              </span>
            ) : null}
            {vendor.availability ? (
              <span className="inline-flex items-center gap-1.5">
                <UsersRound className="size-3" aria-hidden="true" />
                {vendor.availability}
              </span>
            ) : null}
          </div>

          {vendor.contact_name || vendor.email || vendor.phone || vendor.website_url ? (
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 border-t border-line pt-3 text-xs">
              {vendor.contact_name ? (
                <span className="text-muted">{vendor.contact_name}</span>
              ) : null}
              {vendor.email ? (
                <a
                  href={`mailto:${vendor.email}`}
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  <Mail className="size-3" aria-hidden="true" />
                  Email
                </a>
              ) : null}
              {vendor.phone ? (
                <a
                  href={`tel:${vendor.phone}`}
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  <Phone className="size-3" aria-hidden="true" />
                  Call
                </a>
              ) : null}
              {vendor.website_url ? (
                <a
                  href={vendor.website_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  <ExternalLink className="size-3" aria-hidden="true" />
                  Website
                </a>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-end gap-2 border-t border-line pt-3">
        <Button type="button" variant="ghost" size="sm" onClick={onEdit}>
          <Pencil aria-hidden="true" />
          Edit
        </Button>
        {vendor.status === 'booked' ? (
          <span className="text-[0.68rem] leading-4 text-muted">
            Booked vendors cannot be deleted
          </span>
        ) : (
          <Button type="button" variant="danger-ghost" size="sm" onClick={onDelete}>
            <Trash2 aria-hidden="true" />
            Delete
          </Button>
        )}
      </div>
    </article>
  )
}

function VendorsContent({ eventId }: { eventId: string }) {
  const navigate = useNavigate()
  const eventQuery = useEventQuery(eventId)
  const vendorsQuery = useVendorsQuery(eventId)
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<VendorCategory | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<VendorStatus | 'all'>('all')
  const [selected, setSelected] = useState<string[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingVendor, setEditingVendor] = useState<VendorRecord | undefined>()
  const [deletingVendor, setDeletingVendor] = useState<VendorRecord | undefined>()

  const event = eventQuery.data
  const vendors = useMemo(() => vendorsQuery.data?.items ?? [], [vendorsQuery.data])
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return vendors.filter((vendor) => {
      if (categoryFilter !== 'all' && vendor.category !== categoryFilter) return false
      if (statusFilter !== 'all' && vendor.status !== statusFilter) return false
      if (query) {
        const haystack = `${vendor.name} ${vendor.description ?? ''} ${vendor.service_area ?? ''}`
        if (!haystack.toLowerCase().includes(query)) return false
      }
      return true
    })
  }, [vendors, search, categoryFilter, statusFilter])

  const deleteMutation = useMutation({
    mutationFn: (vendor: VendorRecord) => vendorsApi.remove(eventId, vendor.vendor_id),
  })

  function toggleSelected(vendorId: string) {
    setSelected((current) => {
      if (current.includes(vendorId)) return current.filter((id) => id !== vendorId)
      if (current.length >= 10) {
        toast.info('You can compare up to 10 vendors at once.')
        return current
      }
      return [...current, vendorId]
    })
  }

  async function handleDelete() {
    if (!deletingVendor) return
    try {
      await deleteMutation.mutateAsync(deletingVendor)
      await queryClient.invalidateQueries({
        queryKey: ['events', eventId, 'vendors'],
      })
      setSelected((current) => current.filter((id) => id !== deletingVendor.vendor_id))
      toast.success('Vendor removed.')
      setDeletingVendor(undefined)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not delete the vendor.')
    }
  }

  if (vendorsQuery.isLoading || !event) return <PageSkeleton />

  if (vendorsQuery.isError) {
    return (
      <ErrorState
        title="Vendors could not load"
        error={vendorsQuery.error}
        onRetry={() => void vendorsQuery.refetch()}
      />
    )
  }

  const compareHref = `/app/events/${eventId}/vendors/compare?ids=${encodeURIComponent(selected.join(','))}`

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-2xl text-ink">Vendor shortlist</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Keep quotes, statuses, and what you actually know. Festivo does not verify
            vendors, contact them, or make bookings.
          </p>
        </div>
        <Button
          type="button"
          onClick={() => {
            setEditingVendor(undefined)
            setDialogOpen(true)
          }}
        >
          <Plus aria-hidden="true" />
          Add vendor
        </Button>
      </div>

      {vendors.length === 0 ? (
        <EmptyState
          icon={Store}
          title="Start a vendor shortlist"
          description="Add the venues, caterers, photographers, or other vendors you are considering. You can compare up to 10 side by side."
          action={
            <Button
              type="button"
              onClick={() => {
                setEditingVendor(undefined)
                setDialogOpen(true)
              }}
            >
              <Plus aria-hidden="true" />
              Add your first vendor
            </Button>
          }
        />
      ) : (
        <>
          <Card>
            <CardHeader className="gap-3">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
                <div className="relative flex-1">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                    aria-hidden="true"
                  />
                  <Input
                    value={search}
                    onChange={(changeEvent) => setSearch(changeEvent.target.value)}
                    placeholder="Search vendors, notes, or service areas"
                    className="pl-9"
                    aria-label="Search vendors"
                  />
                </div>
                <div className="w-full sm:w-48">
                  <Select
                    value={categoryFilter}
                    onValueChange={(value) =>
                      setCategoryFilter(value as VendorCategory | 'all')
                    }
                  >
                    <SelectTrigger aria-label="Filter by category">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All categories</SelectItem>
                      {VENDOR_CATEGORIES.map((item) => (
                        <SelectItem key={item.value} value={item.value}>
                          {item.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="w-full sm:w-40">
                  <Select
                    value={statusFilter}
                    onValueChange={(value) =>
                      setStatusFilter(value as VendorStatus | 'all')
                    }
                  >
                    <SelectTrigger aria-label="Filter by vendor status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All statuses</SelectItem>
                      {VENDOR_STATUSES.map((item) => (
                        <SelectItem key={item.value} value={item.value}>
                          {item.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex flex-col gap-2 border-t border-line pt-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-muted">
                  Showing {filtered.length} of {vendors.length} vendors · {selected.length}{' '}
                  selected for comparison
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  {selected.length > 0 ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelected([])}
                    >
                      Clear selection
                    </Button>
                  ) : null}
                  <Button
                    type="button"
                    size="sm"
                    disabled={selected.length < 2}
                    onClick={() => navigate(compareHref)}
                  >
                    Compare {selected.length >= 2 ? `(${selected.length})` : ''}
                    <ArrowRight aria-hidden="true" />
                  </Button>
                </div>
              </div>
            </CardHeader>
          </Card>

          {filtered.length === 0 ? (
            <EmptyState
              compact
              icon={Search}
              title="No vendors match those filters"
              description="Try a different search, category, or status."
              action={
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setSearch('')
                    setCategoryFilter('all')
                    setStatusFilter('all')
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {filtered.map((vendor) => (
                <VendorCard
                  key={vendor.vendor_id}
                  vendor={vendor}
                  selected={selected.includes(vendor.vendor_id)}
                  onToggle={() => toggleSelected(vendor.vendor_id)}
                  onEdit={() => {
                    setEditingVendor(vendor)
                    setDialogOpen(true)
                  }}
                  onDelete={() => setDeletingVendor(vendor)}
                />
              ))}
            </div>
          )}

          {vendors.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              {VENDOR_STATUSES.filter((status) =>
                vendors.some((vendor) => vendor.status === status.value),
              ).map((status) => (
                <Badge key={status.value} tone="neutral">
                  {status.label}:{' '}
                  {vendors.filter((vendor) => vendor.status === status.value).length}
                </Badge>
              ))}
            </div>
          ) : null}
        </>
      )}

      <VendorFormDialog
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open)
          if (!open) setEditingVendor(undefined)
        }}
        eventId={eventId}
        defaultCurrency={event.currency}
        {...(editingVendor ? { vendor: editingVendor } : {})}
      />

      <ConfirmDialog
        open={Boolean(deletingVendor)}
        onOpenChange={(open) => {
          if (!open) setDeletingVendor(undefined)
        }}
        title="Remove this vendor?"
        description={
          deletingVendor
            ? `“${deletingVendor.name}” and all recorded contact and pricing notes will be permanently removed.`
            : ''
        }
        confirmLabel="Remove vendor"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={handleDelete}
      />
    </div>
  )
}

export function VendorsPage() {
  const { eventId } = useParams()
  if (!eventId) return null
  return <VendorsContent eventId={eventId} />
}
