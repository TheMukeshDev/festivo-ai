import type {
  AiPlanResponse,
  AiPlanStatus,
  BudgetResponse,
  EventListResponse,
  EventRecord,
  ProposalListResponse,
  ProposalRecord,
  TaskListResponse,
  TaskRecord,
  TimelineRecord,
  VendorCompareResponse,
  VendorListResponse,
  VendorRecord,
} from '@/types/api'

const now = '2026-06-01T10:00:00.000Z'

export function makeEvent(overrides: Partial<EventRecord> = {}): EventRecord {
  return {
    event_id: 'event-1',
    name: 'Ananya and Rohan wedding',
    event_type: 'wedding',
    event_date: '2026-12-12',
    location: 'Jaipur, Rajasthan',
    guest_count: 180,
    budget_amount: '2500000.00',
    currency: 'INR',
    timezone: 'Asia/Kolkata',
    description: 'A garden celebration with family and friends.',
    preferences: ['garden theme', 'vegetarian menu'],
    constraints: ['no fireworks'],
    created_at: now,
    updated_at: now,
    ...overrides,
  }
}

export function makeEventList(items: EventRecord[] = [makeEvent()]): EventListResponse {
  return { items, total: items.length, limit: 100, offset: 0 }
}

export function makeBudget(overrides: Partial<BudgetResponse> = {}): BudgetResponse {
  return {
    budget_id: 'budget-1',
    event_id: 'event-1',
    total_limit: '2500000.00',
    currency: 'INR',
    reserve: { type: 'percentage', value: '10.00', amount: '250000.00' },
    planned_spending: '1465000.00',
    available_for_planning: '785000.00',
    remaining_total: '1035000.00',
    remaining_after_reserve: '785000.00',
    budget_overrun: '0.00',
    reserve_consumed: '0.00',
    cost_per_guest: '8138.89',
    status: 'within_allocation',
    version: 3,
    issues: [],
    category_totals: [
      { category: 'Venue and Logistics', amount: '900000.00' },
      { category: 'Catering and Refreshments', amount: '565000.00' },
    ],
    expenses: [
      {
        expense_id: 'expense-1',
        category: 'Venue and Logistics',
        name: 'Courtyard booking',
        amount: '900000.00',
        amount_status: 'confirmed',
        notes: 'Deposit paid.',
        created_at: now,
        updated_at: now,
      },
      {
        expense_id: 'expense-2',
        category: 'Catering and Refreshments',
        name: 'Dinner estimate',
        amount: '565000.00',
        amount_status: 'estimated',
        notes: null,
        created_at: now,
        updated_at: now,
      },
    ],
    created_at: now,
    updated_at: now,
    ...overrides,
  }
}

export function makeTimeline(overrides: Partial<TimelineRecord> = {}): TimelineRecord {
  return {
    timeline_id: 'timeline-1',
    event_id: 'event-1',
    start_date: '2026-06-01',
    end_date: '2026-12-12',
    timezone: 'Asia/Kolkata',
    generated_at: now,
    created_at: now,
    updated_at: now,
    ...overrides,
  }
}

export function makeTask(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    task_id: 'task-1',
    event_id: 'event-1',
    timeline_id: 'timeline-1',
    template_key: 'book_venue',
    title: 'Confirm the catering headcount',
    description: 'Confirm final guest count with the caterer.',
    status: 'in_progress',
    priority: 'high',
    due_at: '2026-11-20T12:00:00.000Z',
    assigned_to: 'Ananya',
    estimated_cost: '50000.00',
    actual_cost: null,
    currency: 'INR',
    sort_order: 1,
    completed_at: null,
    created_at: now,
    updated_at: now,
    ...overrides,
  }
}

export function makeTaskList(items: TaskRecord[] = [makeTask()]): TaskListResponse {
  return { items, total: items.length, limit: 100, offset: 0 }
}

export function makeVendor(overrides: Partial<VendorRecord> = {}): VendorRecord {
  return {
    vendor_id: 'vendor-1',
    event_id: 'event-1',
    name: 'Saffron Table',
    category: 'catering',
    description: 'Seasonal vegetarian menus for celebrations.',
    contact_name: 'Meera Rao',
    email: 'hello@saffrontable.example',
    phone: '+91 98765 43210',
    website_url: 'https://saffrontable.example',
    service_area: 'Jaipur',
    price_min: '450000.00',
    price_max: '650000.00',
    currency: 'INR',
    estimated_cost: '565000.00',
    quoted_cost: '575000.00',
    final_cost: null,
    pricing_notes: 'Quote includes service staff.',
    status: 'quoted',
    rating: '4.50',
    notes: 'Tasting scheduled.',
    availability: 'Available in December',
    created_at: now,
    updated_at: now,
    ...overrides,
  }
}

export function makeVendorList(items: VendorRecord[] = [makeVendor()]): VendorListResponse {
  return { items, total: items.length, limit: 100, offset: 0 }
}

export function makeVendorCompare(
  overrides: Partial<VendorCompareResponse> = {},
): VendorCompareResponse {
  return {
    items: [
      {
        vendor_id: 'vendor-1',
        name: 'Saffron Table',
        category: 'catering',
        status: 'quoted',
        currency: 'INR',
        price_min: '450000.00',
        price_max: '650000.00',
        estimated_cost: '565000.00',
        quoted_cost: '575000.00',
        final_cost: null,
        rating: '4.50',
        service_area: 'Jaipur',
        availability: 'Available in December',
        budget_fit: 'within_event_budget',
        preference_match: ['service_area_match'],
        missing: [],
        comparable_price: true,
        reasons_cannot_compare_fairly: [],
        notes: 'Quote includes service staff.',
      },
      {
        vendor_id: 'vendor-2',
        name: 'Marigold Kitchens',
        category: 'catering',
        status: 'contacted',
        currency: 'INR',
        price_min: null,
        price_max: null,
        estimated_cost: null,
        quoted_cost: null,
        final_cost: null,
        rating: null,
        service_area: null,
        availability: null,
        budget_fit: null,
        preference_match: [],
        missing: ['price'],
        comparable_price: false,
        reasons_cannot_compare_fairly: ['No price has been recorded.'],
        notes: null,
      },
    ],
    criteria: ['Recorded price', 'Service area', 'Recorded rating'],
    limitations: ['Missing prices are not guessed.'],
    ordering: 'Saffron Table has the most complete recorded price information.',
    ...overrides,
  }
}

export function makeProposal(overrides: Partial<ProposalRecord> = {}): ProposalRecord {
  return {
    proposal_id: 'proposal-1',
    event_id: 'event-1',
    proposal_type: 'ai_plan',
    title: 'Garden celebration plan',
    summary: 'A practical plan that keeps the reserve intact.',
    status: 'pending',
    version: 1,
    items: [
      {
        item_id: 'item-1',
        action_type: 'add_task',
        status: 'pending',
        label: 'Confirm the catering headcount',
        data: {},
        applied_at: null,
        result_message: null,
        resource_id: null,
      },
    ],
    pending_item_count: 1,
    applied_item_count: 0,
    created_at: now,
    updated_at: now,
    expires_at: '2026-07-01T10:00:00.000Z',
    approved_at: null,
    rejected_at: null,
    ai_plan: null,
    ...overrides,
  }
}

export function makeProposalList(
  items: ProposalRecord[] = [makeProposal()],
): ProposalListResponse {
  return { items, total: items.length, limit: 100, offset: 0 }
}

export function makeAiStatus(overrides: Partial<AiPlanStatus> = {}): AiPlanStatus {
  return {
    event_id: 'event-1',
    provider: 'gemini',
    enabled: true,
    configuration_state: 'configured',
    model_configured: true,
    credential_configured: true,
    timeout_seconds: 60,
    max_retries: 2,
    ...overrides,
  }
}

export function makeAiPlan(overrides: Partial<AiPlanResponse> = {}): AiPlanResponse {
  return {
    event_id: 'event-1',
    summary: 'A garden celebration with a clear budget and a practical task order.',
    theme_ideas: ['Marigold accents', 'Courtyard dining'],
    recommendations: [
      {
        category: 'Catering',
        description: 'Confirm the vegetarian menu before the tasting.',
        rationale: 'The guest count is high and the menu drives cost.',
        priority: 'high',
        assumptions: ['The guest count stays near 180.'],
      },
    ],
    budget_suggestions: [
      {
        category: 'Catering',
        description: 'Hold the quoted catering range.',
        source: 'existing_estimate_or_quote',
        suggested_amount: '575000.00',
        currency: 'INR',
        rationale: 'A quote is already recorded.',
        exceeds_available: false,
        assumptions: [],
      },
    ],
    timeline_suggestions: ['Book the courtyard before the date is released.'],
    task_suggestions: [
      {
        title: 'Confirm the final guest count',
        explanation: 'The caterer needs the final number before the tasting.',
        suggested_timing: 'Two weeks before the event',
        relative_deadline: null,
        priority: 'high',
        category: 'Catering',
      },
    ],
    vendor_category_suggestions: [
      {
        category: 'Photography',
        rationale: 'A garden event benefits from natural-light coverage.',
        priority: 'medium',
        notes: null,
      },
    ],
    risks_and_constraints: ['December dates book quickly.'],
    assumptions: ['The venue remains available.'],
    next_steps: ['Compare two caterers and confirm the tasting.'],
    generated_at: now,
    model_used: 'gemini-2.5-flash',
    ...overrides,
  }
}
