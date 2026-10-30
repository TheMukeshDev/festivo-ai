import { useEffect, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useWatch } from 'react-hook-form'
import { AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { FormField } from '@/components/ui/form-field'
import { Input, Textarea } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ApiError } from '@/lib/api/errors'
import { vendorsApi } from '@/lib/api/queries'
import { VENDOR_CATEGORIES, VENDOR_STATUSES, vendorStatusLabel } from '@/lib/labels'
import {
  emptyVendorForm,
  vendorFormSchema,
  type VendorFormValues,
} from '@/lib/validation/vendor'
import { allowedVendorStatuses } from '@/features/vendors/vendor-utils'
import type {
  VendorCategory,
  VendorCreateInput,
  VendorRecord,
  VendorStatus,
  VendorUpdateInput,
} from '@/types/api'

function vendorValues(vendor: VendorRecord): VendorFormValues {
  return {
    name: vendor.name,
    category: vendor.category,
    description: vendor.description ?? '',
    contact_name: vendor.contact_name ?? '',
    email: vendor.email ?? '',
    phone: vendor.phone ?? '',
    website_url: vendor.website_url ?? '',
    service_area: vendor.service_area ?? '',
    price_min: vendor.price_min ?? '',
    price_max: vendor.price_max ?? '',
    estimated_cost: vendor.estimated_cost ?? '',
    quoted_cost: vendor.quoted_cost ?? '',
    final_cost: vendor.final_cost ?? '',
    currency: vendor.currency,
    pricing_notes: vendor.pricing_notes ?? '',
    status: vendor.status,
    rating: vendor.rating ?? '',
    availability: vendor.availability ?? '',
    notes: vendor.notes ?? '',
  }
}

function nullable(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

const formFieldNames = new Set<keyof VendorFormValues>([
  'name',
  'category',
  'description',
  'contact_name',
  'email',
  'phone',
  'website_url',
  'service_area',
  'price_min',
  'price_max',
  'estimated_cost',
  'quoted_cost',
  'final_cost',
  'currency',
  'pricing_notes',
  'status',
  'rating',
  'availability',
  'notes',
])

export function VendorFormDialog({
  open,
  onOpenChange,
  eventId,
  defaultCurrency,
  vendor,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  eventId: string
  defaultCurrency: string
  vendor?: VendorRecord
}) {
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    control,
    setValue,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<VendorFormValues>({
    resolver: zodResolver(vendorFormSchema),
    defaultValues: vendor
      ? vendorValues(vendor)
      : { ...emptyVendorForm, currency: defaultCurrency },
  })

  const category = useWatch({ control, name: 'category' })
  const status = useWatch({ control, name: 'status' })
  const currency = useWatch({ control, name: 'currency' }).toUpperCase()
  const quotedCost = useWatch({ control, name: 'quoted_cost' })
  const finalCost = useWatch({ control, name: 'final_cost' })
  const statusOptions = vendor
    ? allowedVendorStatuses(vendor.status)
    : VENDOR_STATUSES.map((item) => item.value)
  const bookingNeedsCost =
    status === 'booked' &&
    !quotedCost.trim() &&
    !finalCost.trim() &&
    !vendor?.quoted_cost &&
    !vendor?.final_cost

  useEffect(() => {
    if (!open) return
    reset(vendor ? vendorValues(vendor) : { ...emptyVendorForm, currency: defaultCurrency })
  }, [open, vendor, defaultCurrency, reset])

  const mutation = useMutation({
    mutationFn: (values: VendorFormValues) => {
      const common = {
        name: values.name.trim(),
        category: values.category,
        description: nullable(values.description),
        contact_name: nullable(values.contact_name),
        email: nullable(values.email),
        phone: nullable(values.phone),
        website_url: nullable(values.website_url),
        service_area: nullable(values.service_area),
        price_min: nullable(values.price_min),
        price_max: nullable(values.price_max),
        currency: values.currency.trim().toUpperCase(),
        estimated_cost: nullable(values.estimated_cost),
        quoted_cost: nullable(values.quoted_cost),
        pricing_notes: nullable(values.pricing_notes),
        status: values.status,
        rating: nullable(values.rating),
        notes: nullable(values.notes),
        availability: nullable(values.availability),
      }
      if (vendor) {
        const payload: VendorUpdateInput = {
          ...common,
          final_cost: nullable(values.final_cost),
        }
        return vendorsApi.update(eventId, vendor.vendor_id, payload)
      }
      const payload: VendorCreateInput = common
      return vendorsApi.create(eventId, payload)
    },
  })

  async function onSubmit(values: VendorFormValues) {
    setFormError(null)
    try {
      await mutation.mutateAsync(values)
      await queryClient.invalidateQueries({
        queryKey: ['events', eventId, 'vendors'],
      })
      toast.success(vendor ? 'Vendor updated.' : 'Vendor added.')
      onOpenChange(false)
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) {
        for (const field of error.fields) {
          const key = field.field.replace(/^body\./, '') as keyof VendorFormValues
          if (formFieldNames.has(key)) {
            setError(key, { type: 'server', message: field.message })
          } else {
            setFormError(field.message)
          }
        }
      } else {
        setFormError(error instanceof Error ? error.message : 'Could not save the vendor.')
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{vendor ? 'Edit vendor' : 'Add vendor'}</DialogTitle>
          <DialogDescription>
            Record what you know and leave the rest blank. Festivo never contacts vendors or
            verifies their claims.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-6">
          <section className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
              Basics
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                id="vendor_name"
                label="Vendor name"
                error={errors.name?.message}
                className="sm:col-span-2"
                required
              >
                <Input
                  id="vendor_name"
                  placeholder="The Courtyard"
                  aria-invalid={Boolean(errors.name)}
                  {...register('name')}
                />
              </FormField>
              <FormField
                id="vendor_category"
                label="Category"
                error={errors.category?.message}
                required
              >
                <Select
                  value={category}
                  onValueChange={(value) =>
                    setValue('category', value as VendorCategory, { shouldValidate: true })
                  }
                >
                  <SelectTrigger id="vendor_category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {VENDOR_CATEGORIES.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField
                id="vendor_status"
                label="Status"
                error={errors.status?.message}
                description={
                  vendor
                    ? `Only valid transitions from “${vendorStatusLabel(vendor.status)}” are listed.`
                    : undefined
                }
                required
              >
                <Select
                  value={status}
                  onValueChange={(value) =>
                    setValue('status', value as VendorStatus, { shouldValidate: true })
                  }
                >
                  <SelectTrigger id="vendor_status">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {statusOptions.map((value) => (
                      <SelectItem key={value} value={value}>
                        {vendorStatusLabel(value)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <FormField
                id="vendor_description"
                label="Description"
                error={errors.description?.message}
                className="sm:col-span-2"
              >
                <Textarea
                  id="vendor_description"
                  rows={2}
                  placeholder="Garden venue with an indoor backup space."
                  aria-invalid={Boolean(errors.description)}
                  {...register('description')}
                />
              </FormField>
            </div>
          </section>

          <section className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
              Contact
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                id="vendor_contact_name"
                label="Contact name"
                error={errors.contact_name?.message}
              >
                <Input
                  id="vendor_contact_name"
                  placeholder="Meera"
                  aria-invalid={Boolean(errors.contact_name)}
                  {...register('contact_name')}
                />
              </FormField>
              <FormField
                id="vendor_service_area"
                label="Service area"
                error={errors.service_area?.message}
              >
                <Input
                  id="vendor_service_area"
                  placeholder="Bengaluru"
                  aria-invalid={Boolean(errors.service_area)}
                  {...register('service_area')}
                />
              </FormField>
              <FormField id="vendor_email" label="Email" error={errors.email?.message}>
                <Input
                  id="vendor_email"
                  type="email"
                  placeholder="hello@example.com"
                  aria-invalid={Boolean(errors.email)}
                  {...register('email')}
                />
              </FormField>
              <FormField id="vendor_phone" label="Phone" error={errors.phone?.message}>
                <Input
                  id="vendor_phone"
                  type="tel"
                  placeholder="+91 98765 43210"
                  aria-invalid={Boolean(errors.phone)}
                  {...register('phone')}
                />
              </FormField>
              <FormField
                id="vendor_website"
                label="Website"
                error={errors.website_url?.message}
                className="sm:col-span-2"
              >
                <Input
                  id="vendor_website"
                  type="url"
                  placeholder="https://example.com"
                  aria-invalid={Boolean(errors.website_url)}
                  {...register('website_url')}
                />
              </FormField>
            </div>
          </section>

          <section className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
              Pricing
            </h3>
            <div className="grid gap-4 sm:grid-cols-3">
              <FormField
                id="vendor_price_min"
                label="Price from"
                error={errors.price_min?.message}
              >
                <Input
                  id="vendor_price_min"
                  inputMode="decimal"
                  aria-invalid={Boolean(errors.price_min)}
                  {...register('price_min')}
                />
              </FormField>
              <FormField
                id="vendor_price_max"
                label="Price to"
                error={errors.price_max?.message}
              >
                <Input
                  id="vendor_price_max"
                  inputMode="decimal"
                  aria-invalid={Boolean(errors.price_max)}
                  {...register('price_max')}
                />
              </FormField>
              <FormField
                id="vendor_currency"
                label="Currency"
                error={errors.currency?.message}
                required
              >
                <Input
                  id="vendor_currency"
                  maxLength={3}
                  className="uppercase"
                  aria-invalid={Boolean(errors.currency)}
                  {...register('currency')}
                />
              </FormField>
              <FormField
                id="vendor_estimated_cost"
                label="Estimated cost"
                error={errors.estimated_cost?.message}
              >
                <Input
                  id="vendor_estimated_cost"
                  inputMode="decimal"
                  aria-invalid={Boolean(errors.estimated_cost)}
                  {...register('estimated_cost')}
                />
              </FormField>
              <FormField
                id="vendor_quoted_cost"
                label="Quoted cost"
                error={errors.quoted_cost?.message}
              >
                <Input
                  id="vendor_quoted_cost"
                  inputMode="decimal"
                  aria-invalid={Boolean(errors.quoted_cost)}
                  {...register('quoted_cost')}
                />
              </FormField>
              {vendor ? (
                <FormField
                  id="vendor_final_cost"
                  label="Final cost"
                  error={errors.final_cost?.message}
                >
                  <Input
                    id="vendor_final_cost"
                    inputMode="decimal"
                    aria-invalid={Boolean(errors.final_cost)}
                    {...register('final_cost')}
                  />
                </FormField>
              ) : null}
              <FormField
                id="vendor_pricing_notes"
                label={`Pricing notes (${currency || 'currency'})`}
                error={errors.pricing_notes?.message}
                className="sm:col-span-3"
              >
                <Textarea
                  id="vendor_pricing_notes"
                  rows={2}
                  placeholder="Quote excludes GST and staffing."
                  aria-invalid={Boolean(errors.pricing_notes)}
                  {...register('pricing_notes')}
                />
              </FormField>
            </div>
            {bookingNeedsCost ? (
              <p className="flex items-start gap-2 rounded-sm bg-warning-soft p-3 text-xs leading-5 text-ink-soft">
                <AlertTriangle
                  className="mt-0.5 size-3.5 shrink-0 text-warning"
                  aria-hidden="true"
                />
                The server requires a quoted or final cost before a vendor can move to
                “Booked”.
              </p>
            ) : null}
          </section>

          <section className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">
              Notes and signals
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                id="vendor_rating"
                label="Recorded rating"
                error={errors.rating?.message}
                description="Optional, 0–5. Only use a rating you actually have."
              >
                <Input
                  id="vendor_rating"
                  inputMode="decimal"
                  placeholder="4.5"
                  aria-invalid={Boolean(errors.rating)}
                  {...register('rating')}
                />
              </FormField>
              <FormField
                id="vendor_availability"
                label="Availability note"
                error={errors.availability?.message}
                description="What the vendor told you; not independently verified."
              >
                <Input
                  id="vendor_availability"
                  placeholder="Available on the event date"
                  aria-invalid={Boolean(errors.availability)}
                  {...register('availability')}
                />
              </FormField>
              <FormField
                id="vendor_notes"
                label="Notes"
                error={errors.notes?.message}
                className="sm:col-span-2"
              >
                <Textarea
                  id="vendor_notes"
                  rows={3}
                  placeholder="Questions to ask, scope gaps, or context from your conversation."
                  aria-invalid={Boolean(errors.notes)}
                  {...register('notes')}
                />
              </FormField>
            </div>
          </section>

          {formError ? (
            <p
              role="alert"
              className="rounded-sm bg-danger-soft px-3 py-2 text-sm text-danger"
            >
              {formError}
            </p>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || mutation.isPending}>
              {isSubmitting || mutation.isPending
                ? 'Saving…'
                : vendor
                  ? 'Save vendor'
                  : 'Add vendor'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
