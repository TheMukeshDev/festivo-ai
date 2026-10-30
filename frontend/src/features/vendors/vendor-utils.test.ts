import { describe, expect, it } from 'vitest'

import { allowedVendorStatuses, vendorPriceRange } from '@/features/vendors/vendor-utils'
import { makeVendor } from '@/test/fixtures'

describe('vendor planning helpers', () => {
  it('prefers a quoted price over an estimate and range', () => {
    expect(vendorPriceRange(makeVendor())).toBe('INR 575000.00 (quoted)')
    expect(
      vendorPriceRange(makeVendor({ quoted_cost: null, final_cost: '600000.00' })),
    ).toBe('INR 565000.00 (estimate)')
  })

  it('formats the available price shapes and a missing price', () => {
    expect(
      vendorPriceRange(
        makeVendor({
          quoted_cost: null,
          estimated_cost: null,
          price_min: '100',
          price_max: '200',
        }),
      ),
    ).toBe('INR 100–200')
    expect(
      vendorPriceRange(
        makeVendor({
          quoted_cost: null,
          estimated_cost: null,
          price_min: '100',
          price_max: null,
        }),
      ),
    ).toBe('INR 100+')
    expect(
      vendorPriceRange(
        makeVendor({
          quoted_cost: null,
          estimated_cost: null,
          price_min: null,
          price_max: '200',
        }),
      ),
    ).toBe('Up to INR 200')
    expect(
      vendorPriceRange(
        makeVendor({
          quoted_cost: null,
          estimated_cost: null,
          price_min: null,
          price_max: null,
        }),
      ),
    ).toBe('No price recorded')
  })

  it('returns the current status followed by its allowed transitions', () => {
    expect(allowedVendorStatuses('quoted')).toEqual([
      'quoted',
      'selected',
      'contacted',
      'rejected',
      'cancelled',
    ])
    expect(allowedVendorStatuses('booked')).toEqual(['booked', 'cancelled'])
    expect(allowedVendorStatuses('rejected')).toEqual(['rejected'])
  })
})
