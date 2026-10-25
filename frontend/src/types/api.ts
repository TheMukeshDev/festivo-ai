export type EventType = 'wedding' | 'birthday' | 'college_event' | 'community_event'

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled'
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'

export type ExpenseStatus = 'estimated' | 'quoted' | 'confirmed'
export type ReserveType = 'percentage' | 'fixed_amount'
export type BudgetStatus = 'within_allocation' | 'reserve_consumed' | 'over_budget'
export type IssueSeverity = 'warning' | 'error'

export type VendorCategory =
  | 'venue'
  | 'catering'
  | 'decoration'
  | 'photography_videography'
  | 'entertainment_music'
  | 'makeup_styling'
  | 'invitations_printing'
  | 'transportation'
  | 'equipment_rentals'
  | 'event_coordination'
  | 'other'

export type VendorStatus =
  | 'discovered'
  | 'shortlisted'
  | 'contacted'
  | 'quoted'
  | 'selected'
  | 'booked'
  | 'rejected'
  | 'cancelled'

export interface ApiFieldError {
  field: string
  message: string
  type: string
}

export interface EventRecord {
  event_id: string
  name: string
  event_type: EventType
  event_date: string
  location: string
  guest_count: number
  budget_amount: string
  currency: string
  timezone: string
  description: string | null
  preferences: string[]
  constraints: string[]
  created_at: string
  updated_at: string
}

export interface EventListResponse {
  items: EventRecord[]
  total: number
  limit: number
  offset: number
}

export interface EventCreateInput {
  name: string
  event_type: EventType
  event_date: string
  location: string
  guest_count: number
  budget_amount: string
  currency: string
  timezone?: string | null
  description?: string | null
  preferences: string[]
  constraints: string[]
}

export type EventUpdateInput = Partial<Omit<EventCreateInput, 'timezone'>> & {
  timezone?: string | null
}

export interface ReserveResponse {
  type: ReserveType
  value: string
  amount: string
}

export interface ExpenseRecord {
  expense_id: string
  category: string
  name: string
  amount: string
  amount_status: ExpenseStatus
  notes: string | null
  created_at: string
  updated_at: string
}

export interface CategoryTotal {
  category: string
  amount: string
}

export interface BudgetIssue {
  code: string
  severity: IssueSeverity
  message: string
}

export interface BudgetResponse {
  budget_id: string
  event_id: string
  total_limit: string
  currency: string
  reserve: ReserveResponse
  planned_spending: string
  available_for_planning: string
  remaining_total: string
  remaining_after_reserve: string
  budget_overrun: string
  reserve_consumed: string
  cost_per_guest: string | null
  status: BudgetStatus
  version: number
  issues: BudgetIssue[]
  category_totals: CategoryTotal[]
  expenses: ExpenseRecord[]
  created_at: string
  updated_at: string
}

export interface BudgetCreateInput {
  total_limit?: string
  reserve?: { type: ReserveType; value: string }
}

export interface BudgetUpdateInput {
  expected_version: number
  total_limit?: string
  reserve?: { type: ReserveType; value: string }
}

export interface ExpenseCreateInput {
  expected_version: number
  category: string
  name: string
  amount: string
  amount_status: ExpenseStatus
  notes?: string | null
}

export interface ExpenseUpdateInput {
  expected_version: number
  category?: string
  name?: string
  amount?: string
  amount_status?: ExpenseStatus
  notes?: string | null
}

export interface TimelineRecord {
  timeline_id: string
  event_id: string
  start_date: string
  end_date: string
  timezone: string
  generated_at: string
  created_at: string
  updated_at: string
}

export interface TaskRecord {
  task_id: string
  event_id: string
  timeline_id: string | null
  template_key: string | null
  title: string
  description: string | null
  status: TaskStatus
  priority: TaskPriority
  due_at: string | null
  assigned_to: string | null
  estimated_cost: string | null
  actual_cost: string | null
  currency: string
  sort_order: number
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface TaskListResponse {
  items: TaskRecord[]
  total: number
  limit: number
  offset: number
}

export interface TaskCreateInput {
  title: string
  description?: string | null
  status?: TaskStatus
  priority?: TaskPriority
  due_at?: string | null
  assigned_to?: string | null
  estimated_cost?: string | null
  actual_cost?: string | null
}

export interface TaskUpdateInput {
  title?: string
  description?: string | null
  status?: TaskStatus
  priority?: TaskPriority
  due_at?: string | null
  assigned_to?: string | null
  estimated_cost?: string | null
  actual_cost?: string | null
}

export interface VendorRecord {
  vendor_id: string
  event_id: string
  name: string
  category: VendorCategory
  description: string | null
  contact_name: string | null
  email: string | null
  phone: string | null
  website_url: string | null
  service_area: string | null
  price_min: string | null
  price_max: string | null
  currency: string
  estimated_cost: string | null
  quoted_cost: string | null
  final_cost: string | null
  pricing_notes: string | null
  status: VendorStatus
  rating: string | null
  notes: string | null
  availability: string | null
  created_at: string
  updated_at: string
}

export interface VendorListResponse {
  items: VendorRecord[]
  total: number
  limit: number
  offset: number
}

export interface VendorCreateInput {
  name: string
  category: VendorCategory
  description?: string | null
  contact_name?: string | null
  email?: string | null
  phone?: string | null
  website_url?: string | null
  service_area?: string | null
  price_min?: string | null
  price_max?: string | null
  currency: string
  estimated_cost?: string | null
  quoted_cost?: string | null
  pricing_notes?: string | null
  status?: VendorStatus
  rating?: string | null
  notes?: string | null
  availability?: string | null
}

export type VendorUpdateInput = Partial<
  Omit<VendorCreateInput, 'name' | 'category' | 'currency'>
> & {
  name?: string
  category?: VendorCategory
  currency?: string
  final_cost?: string | null
}

export interface VendorCompareInput {
  vendor_ids: string[]
  max_price?: string
  prefer_service_area?: string
  prefer_quick_response?: boolean
}

export interface VendorCompareItem {
  vendor_id: string
  name: string
  category: VendorCategory
  status: VendorStatus
  currency: string
  price_min: string | null
  price_max: string | null
  estimated_cost: string | null
  quoted_cost: string | null
  final_cost: string | null
  rating: string | null
  service_area: string | null
  availability: string | null
  budget_fit: string | null
  preference_match: string[]
  missing: string[]
  comparable_price: boolean
  reasons_cannot_compare_fairly: string[]
  notes: string | null
}

export interface VendorCompareResponse {
  items: VendorCompareItem[]
  criteria: string[]
  limitations: string[]
  ordering: string
}

export type AiPriority = 'low' | 'medium' | 'high' | 'critical'
export type BudgetSource =
  | 'suggested_allocation'
  | 'user_provided_budget'
  | 'existing_estimate_or_quote'
  | 'confirmed_expense'

export interface AiRecommendation {
  category: string
  description: string
  rationale: string
  priority: AiPriority
  assumptions: string[]
}

export interface AiTaskSuggestion {
  title: string
  explanation: string
  suggested_timing: string | null
  relative_deadline: string | null
  priority: AiPriority
  category: string | null
}

export interface AiBudgetSuggestion {
  category: string
  description: string
  source: BudgetSource
  suggested_amount: string | null
  currency: string
  rationale: string
  exceeds_available: boolean
  assumptions: string[]
}

export interface AiVendorCategorySuggestion {
  category: string
  rationale: string
  priority: AiPriority
  notes: string | null
}

export interface AiPlanResponse {
  event_id: string
  summary: string
  theme_ideas: string[]
  recommendations: AiRecommendation[]
  budget_suggestions: AiBudgetSuggestion[]
  timeline_suggestions: string[]
  task_suggestions: AiTaskSuggestion[]
  vendor_category_suggestions: AiVendorCategorySuggestion[]
  risks_and_constraints: string[]
  assumptions: string[]
  next_steps: string[]
  generated_at: string
  model_used: string
}

export interface AiPlanRequest {
  preferences: Record<string, unknown>
  focus_areas: string[]
  additional_notes?: string | null
}

export interface AiPlanStatus {
  event_id: string
  provider: string
  enabled: boolean
  configuration_state: 'disabled' | 'incomplete' | 'configured'
  model_configured: boolean
  credential_configured: boolean
  timeout_seconds: number
  max_retries: number
}
