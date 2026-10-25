# Festivo AI Architecture

## Scope

The backend is at version 0.8.0. It implements:

1. Secure FastAPI foundation, validated settings, safe errors, CORS, and deterministic tests.
2. Supabase access-token authentication and owner-scoped event CRUD.
3. Decimal-safe budgets, planned expenses, optimistic concurrency, and PostgreSQL persistence.
4. Deterministic timelines and task lifecycle management.
5. Vendor checklists, booking status, pricing fields, and comparison.
6. Gemini integration with structured, validated AI output.
7. Persisted proposals with approval/rejection, stale-snapshot detection, and idempotent task
   application.
8. Owner-scoped PDF and CSV event reports.

The React client is maintained separately in `frontend/`. Deployment automation, live monitoring, and
production operations are outside this backend implementation.

## System boundaries

```text
Browser (React)
    |
    | HTTPS + JSON + Bearer access token, explicit CORS origin
    v
FastAPI application
    |-- /health                         process health
    |-- /api/v1/health                  versioned API health
    |-- /api/v1/config/status           safe diagnostics
    |-- /api/v1/events*                 events, budgets, timelines, tasks
    |-- /api/v1/events/*/vendors*       vendor workflow and comparison
    |-- /api/v1/events/*/proposals*     AI proposal generation and approval
    |-- /api/v1/events/*/ai-plan*       legacy AI planning aliases
    |-- /api/v1/events/*/export*        PDF and CSV reports
    |-- Supabase JWT verification       JWKS, issuer, audience, role
    |-- Gemini provider                 structured proposal generation
    |-- Pydantic contracts              strict request/response/error schemas
    |-- Services                        domain policy and orchestration
    `-- Repositories                    memory and PostgreSQL implementations
    |
    | psycopg 3, parameterized SQL, TLS
    v
Supabase PostgreSQL
    |-- events
    |-- event_budgets
    |-- budget_expenses
    |-- event_timelines
    |-- event_tasks
    |-- event_vendors
    |-- vendor_status_history
    |-- planning_proposals
    `-- schema_migrations (migration runner)
```

Credentials exist only in the backend environment. Browser clients use their Supabase access token;
they never receive the database URL, Gemini API key, or service-role credentials.

## Backend structure

- `app/main.py` owns the ASGI factory, version, service wiring, storage selection, auth verifier, and
  middleware. Tests can inject deterministic services and verifiers.
- `app/core/config.py` validates environment settings and derives the Supabase JWKS/issuer.
- `app/core/auth.py` verifies ES256/RS256 access tokens and extracts the owner UUID.
- `app/core/exceptions.py` defines safe domain errors and converts them to one JSON envelope.
- `app/core/clock.py`, `money.py`, and planning rules centralize deterministic calculations.
- `app/db/postgres.py` owns short-lived psycopg connections and translates connectivity failures.
- `app/models/` contains immutable domain dataclasses and enums.
- `app/schemas/` contains strict Pydantic HTTP contracts.
- `app/services/` contains event, budget, timeline, task, vendor, proposal, orchestration, AI, and
  report use cases.
- `app/repositories/` contains persistence protocols plus thread-safe memory and PostgreSQL
  implementations.
- `app/api/v1/` provides health, event, budget, timeline/task, vendor, proposal, AI planning, and
  export routes.
- `scripts/apply_migrations.py` applies checksum-tracked migrations transactionally.
- `supabase/migrations/` contains the versioned schema and RLS policies.

## Authentication and ownership

Supabase access tokens are verified against the project JWKS. Verification requires a valid signature,
issuer, `aud`, `exp`, `iat`, and an `authenticated` role claim. The token `sub` becomes the owner ID.

Authentication fails closed:

- Missing, malformed, expired, or invalid tokens return `401`.
- Unreachable signing keys return a safe `503`.
- If no verifier is configured, every protected route rejects tokens.
- Every event-scoped repository query includes the owner ID.
- Cross-user resources return `404`, not `403`, to avoid confirming that they exist.

The backend database role bypasses RLS by design. API ownership checks are the primary authorization
boundary; RLS remains defense in depth for browser-facing access.

## Storage selection

`STORAGE_BACKEND` selects storage:

- `memory`: process-local, thread-safe repositories for development and tests.
- `postgres`: psycopg-backed repositories using Supabase PostgreSQL.

Production requires PostgreSQL; it cannot silently fall back to volatile memory. Database connection
failures become `503 service_unavailable` rather than false success or data loss. There is no automatic
fallback to memory.

The backend uses direct PostgreSQL access through `psycopg` because budget and proposal mutations need
transactions, row locks, optimistic version checks, and unique constraints. A connection is opened per
repository operation; connection pooling remains a production hardening item.

## Data model

### Events

`public.events` stores the event identity, name/type/date/location, guest count, Decimal budget,
currency, optional description, preferences, constraints, and UTC timestamps. `owner_id` is required
by the application and references `auth.users` where configured. The SQL column for constraints is
`event_constraints`; the API still exposes `constraints`.

### Budgets and expenses

`public.event_budgets` has at most one row per event, a positive bounded limit, currency inherited at
creation, reserve type/value, integer version, and timestamps. `public.budget_expenses` stores
planned line items linked by `budget_id` with cascade deletion.

Authoritative financial values use Python `Decimal`, never binary floating point. Inputs allow at most
two decimal places and are rounded half-up. Derived totals, reserve consumption, status, issues, and
cost per guest are recalculated server-side and are not authoritative columns.

Every budget or expense mutation requires `expected_version`. The repository locks the row, verifies
the version, applies the change, and increments the version atomically. Stale writes return `409`.

### Timelines and tasks

`public.event_timelines` stores at most one timeline per event with start/end dates and timezone.
`public.event_tasks` stores deterministic, event-linked tasks with template keys, priority, status,
due dates, costs, completion metadata, and unique insertion keys. Generation is deterministic for an
event snapshot; regeneration only creates missing template tasks and does not overwrite user edits.

### Vendors

`public.event_vendors` stores contact/category data, price ranges, estimated/quoted/final costs,
booking status, rating, availability, notes, and timestamps. `public.vendor_status_history` records
status transitions. Comparison is derived at request time and does not mutate vendor state. Booking
status is a planning record, not proof of payment.

### Planning proposals

`public.planning_proposals` stores:

- Event and owner IDs.
- Model/provider metadata.
- The validated proposal payload, including summary and structured actions.
- Source snapshot: event update time, budget version, task count, vendor count.
- Lifecycle status, integer version, expiry, approval/rejection timestamps, and rejection reason.

Proposal statuses are `pending`, `partially_approved`, `approved`, `rejected`, and `expired`.

## AI pipeline

`AIPlanningService` builds a bounded context from the event, budget, tasks, and vendors, sends a
structured prompt to Gemini, validates the response with Pydantic, and returns a typed plan.
`PlanningOrchestrationService` converts that plan into a persisted proposal.

The provider boundary uses:

- Missing configuration, authentication, and service failures -> `503`.
- Rate limits -> `429`.
- Timeouts -> `504`.
- Invalid structured output -> `422`.

Provider messages, credentials, prompts, and raw model output are not returned to clients. AI is
disabled unless `LLM_ENABLED=true`, `GEMINI_API_KEY`, and `LLM_MODEL` are configured.

## Proposal approval

Generation is advisory: it does not book vendors, move money, or mutate the event. Approval is an
explicit, separate action.

- Only selected item IDs are applied; omitted items remain pending.
- Supported actions add tasks, update task due dates, add vendor follow-up tasks, and advise on budget
  allocation.
- Advisory items are retained for display/export but never change application data.
- Task creation uses `proposal:{proposal_id}:{item_id}` for idempotency.
- Approval rechecks the proposal version and source snapshot. A changed event/budget/task/vendor
  snapshot returns `409` so stale advice is not silently applied.
- Item-level validation or missing-resource failures become skipped results. Previously applied work
  is retained so the user can resolve the issue and resume.
- Rejection requires a pending proposal and stores an optional reason.
- New proposals expire after `PROPOSAL_TTL_HOURS`; expiry is enforced when an action is attempted.

Approval can span multiple service calls. It is resumable and safe against duplicate task creation,
but it is not one transaction across every affected table.

## Reports

`ReportService` builds owner-scoped PDF and CSV reports from the event, budget, tasks, vendors, and
applied proposal recommendations.

- PDF uses ReportLab. User text is XML-escaped before paragraph markup is applied.
- CSV uses UTF-8, fixed section headers, and bounded row counts.
- Formula-like CSV cells are prefixed with `'` to reduce spreadsheet injection risk.
- Pending or rejected recommendations are excluded; advisory items are included only when allowed.
- Downloads use safe filenames and `Cache-Control: no-store`.
- Report generation does not call external services.

## API behavior

Successful responses use explicit Pydantic models or documented download media types. Errors use one
envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "fields": [
      {
        "field": "body.guest_count",
        "message": "Input should be greater than 0",
        "type": "greater_than"
      }
    ]
  }
}
```

Public statuses include `400`, `401`, `404`, `409`, `413`, `415`, `422`, `429`, `500`, `503`, and
`504`. Error responses never include stack traces, database URLs, provider credentials, environment
dumps, or filesystem paths. Unhandled exceptions are logged server-side with request method/path and
return a generic JSON error.

## Testing

Tests use isolated settings, memory repositories, injected clocks, and deterministic token verifiers.
They do not call Gemini. Optional live Supabase tests are skipped unless `TEST_SUPABASE_DB_URL` points
at a dedicated test database.

Coverage includes:

- Configuration, safe errors, CORS, health, and API contracts.
- Authentication, ownership isolation, and cross-user `404` behavior.
- Event validation and date policy.
- Budget arithmetic, reserves, statuses, version conflicts, and persistence contracts.
- Timeline/task generation and lifecycle.
- Vendor CRUD, booking-state rules, pricing fields, and comparison.
- Proposal generation, persistence, stale detection, approval/rejection, expiry, idempotency, and
  report inclusion.
- PDF/CSV content, headers, escaping, and formula guards.
- Migration SQL structure, RLS policies, and migration runner safety.

## Known limitations

- No connection pool; each repository operation opens a short-lived database connection.
- Proposal approval is resumable but not fully transactional across all affected services.
- Expired proposals are updated on attempted action; bulk listing does not rewrite expiry state.
- No application-level rate limiting, request-size protection, quota controls, or audit logging.
- No automatic budget re-baselining when event budget/currency changes.
- No foreign exchange, taxes, actual-expense reconciliation, or vendor payment processing.
- Offset pagination only; no cursor pagination for large persistent datasets.
- Live Supabase migration/integration verification requires separate credentials and is not part of
  the default test run.
