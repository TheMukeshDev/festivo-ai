import type { VendorRecord, VendorStatus } from '@/types/api'
import { ALLOWED_VENDOR_TRANSITIONS } from '@/lib/labels'

export function vendorPriceRange(vendor: VendorRecord): string {
  const currency = vendor.currency
  if (vendor.quoted_cost) return `${currency} ${vendor.quoted_cost} (quoted)`
  if (vendor.estimated_cost) return `${currency} ${vendor.estimated_cost} (estimate)`
  if (vendor.price_min && vendor.price_max) {
    return `${currency} ${vendor.price_min}–${vendor.price_max}`
  }
  if (vendor.price_min) return `${currency} ${vendor.price_min}+`
  if (vendor.price_max) return `Up to ${currency} ${vendor.price_max}`
  return 'No price recorded'
}

export function allowedVendorStatuses(current: VendorStatus): VendorStatus[] {
  return [current, ...ALLOWED_VENDOR_TRANSITIONS[current]]
}

export const BUDGET_FIT_LABELS: Record<string, string> = {
  within_event_budget: 'Within event budget',
  over_event_budget: 'Over event budget',
  unknown_due_to_missing_price_or_currency:
    'Budget fit unknown — missing price or different currency',
}

export const PREFERENCE_MATCH_LABELS: Record<string, string> = {
  service_area_match: 'Matches preferred service area',
  active_response_state: 'Contacted or quoted',
  high_recorded_rating: 'Recorded rating of 4.0 or higher',
}
