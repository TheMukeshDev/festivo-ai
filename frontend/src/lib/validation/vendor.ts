import { z } from 'zod'

const optionalMoney = z
  .string()
  .trim()
  .refine(
    (value) => value === '' || /^\d{1,9}(\.\d{1,2})?$/.test(value),
    'Use a valid amount with up to two decimal places.',
  )

const optionalRating = z
  .string()
  .trim()
  .refine(
    (value) => value === '' || /^[0-5](\.\d)?$/.test(value),
    'Rating must be between 0 and 5 with one decimal place.',
  )

export const vendorFormSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, 'Enter the vendor name.')
      .max(120, 'Use 120 characters or fewer.'),
    category: z.enum([
      'venue',
      'catering',
      'decoration',
      'photography_videography',
      'entertainment_music',
      'makeup_styling',
      'invitations_printing',
      'transportation',
      'equipment_rentals',
      'event_coordination',
      'other',
    ]),
    description: z.string().max(2000, 'Use 2,000 characters or fewer.'),
    contact_name: z.string().max(120, 'Use 120 characters or fewer.'),
    email: z
      .string()
      .trim()
      .refine(
        (value) => value === '' || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value),
        'Enter a valid email address.',
      ),
    phone: z
      .string()
      .trim()
      .refine(
        (value) => value === '' || /^[0-9+\-\s()]{3,40}$/.test(value),
        'Use a valid phone number.',
      ),
    website_url: z
      .string()
      .trim()
      .refine(
        (value) => value === '' || /^https?:\/\/[^\s]+$/i.test(value),
        'Enter a valid http(s) website URL.',
      ),
    service_area: z.string().max(200, 'Use 200 characters or fewer.'),
    price_min: optionalMoney,
    price_max: optionalMoney,
    estimated_cost: optionalMoney,
    quoted_cost: optionalMoney,
    final_cost: optionalMoney,
    currency: z
      .string()
      .trim()
      .length(3, 'Use a three-letter currency code.')
      .regex(/^[A-Za-z]{3}$/, 'Use a three-letter currency code.'),
    pricing_notes: z.string().max(1000, 'Use 1,000 characters or fewer.'),
    status: z.enum([
      'discovered',
      'shortlisted',
      'contacted',
      'quoted',
      'selected',
      'booked',
      'rejected',
      'cancelled',
    ]),
    rating: optionalRating,
    availability: z.string().max(200, 'Use 200 characters or fewer.'),
    notes: z.string().max(2000, 'Use 2,000 characters or fewer.'),
  })
  .refine(
    (values) =>
      !values.price_min ||
      !values.price_max ||
      Number(values.price_min) <= Number(values.price_max),
    { message: 'Minimum price cannot exceed maximum price.', path: ['price_min'] },
  )

export type VendorFormValues = z.infer<typeof vendorFormSchema>

export const emptyVendorForm: VendorFormValues = {
  name: '',
  category: 'venue',
  description: '',
  contact_name: '',
  email: '',
  phone: '',
  website_url: '',
  service_area: '',
  price_min: '',
  price_max: '',
  estimated_cost: '',
  quoted_cost: '',
  final_cost: '',
  currency: 'INR',
  pricing_notes: '',
  status: 'discovered',
  rating: '',
  availability: '',
  notes: '',
}
