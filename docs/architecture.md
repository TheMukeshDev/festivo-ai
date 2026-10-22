# Festivo AI Architecture

## Scope

Phases 1-3 are implemented:

1. Secure FastAPI foundation, settings, validation, safe errors, and deterministic tests.
2. Event CRUD, timezone-aware date policy, server-managed identity/timestamps, and pagination.
3. Budget planning, planned expenses, Decimal-safe calculations, optimistic concurrency, Supabase
   PostgreSQL persistence, and versioned SQL migrations.

Phase 4 has not been started. Timelines, tasks, vendors, AI generation, plan versioning, and frontend
screens remain future work.

## System boundaries

```text
Browser (React, future)
        |
        | HTTPS + JSON, explicit CORS origin
        v
FastAPI application
  ├── /health                         process health
  ├── /api/v1/health                  versioned API health
  ├── /api/v1/config/status           safe diagnostics
  ├── /api/v1/events*                 event CRUD
  ├── /api/v1/events/*/budget*        budget and expense operations
  ├── Pydantic contracts              request/response and error schemas
  ├── EventService                    event policy and persistence orchestration
  ├── BudgetService                   lifecycle, version policy, summary assembly
  ├── BudgetCalculator                pure Decimal calculations/issues
  ├── Repositories                    memory and PostgreSQL implementations
  └── Settings                        validated environment configuration
        |
        | psycopg 3, parameterized SQL, TLS
        v
Supabase PostgreSQL
  ├── events
  ├── event_budgets
  ├── budget_expenses
  └── schema_migrations (migration runner)
```

The frontend and backend are independently deployable. Credentials are available only to the backend
environment. There is no provider key or database URL in frontend code.

Gemini remains configured but not integrated. No startup, health, event, or budget operation contacts
Gemini.

## Backend structure

- `app/main.py` contains the ASGI app factory. It selects memory or PostgreSQL repositories and allows
  tests to inject isolated event and budget services. It owns the application version (`0.3.0`).
- `app/core/config.py` parses and validates environment settings, including storage selection and the
  secret database URL.
- `app/core/clock.py` provides an injectable timezone-aware UTC clock and normalization.
- `app/core/money.py` centralizes two-decimal, half-up monetary rounding.
- `app/core/exceptions.py` defines safe domain errors and HTTP error translation.
- `app/db/postgres.py` owns short-lived psycopg connections and translates connectivity failures.
- `app/models/event.py` and `app/models/budget.py` define immutable domain objects and enums.
- `app/schemas/` defines strict Pydantic HTTP contracts.
- `app/services/event_service.py` applies event policy and update semantics.
- `app/services/budget_calculator.py` is a pure function layer with no database or HTTP knowledge.
- `app/services/budget_service.py` applies budget policy, creates server-managed fields, and calls the
  calculator.
- `app/repositories/` contains persistence contracts, thread-safe memory implementations, and
  PostgreSQL implementations.
- `app/api/v1/events.py` and `app/api/v1/budgets.py` translate HTTP requests into service calls and
  explicit response models.
- `scripts/apply_migrations.py` applies checksum-tracked SQL migrations transactionally.
- `supabase/migrations/` contains the versioned schema and RLS policies.

The unversioned `/health` route remains intentionally minimal for platform process checks. Product
and diagnostic routes live under `/api/v1`.

## Storage selection

`STORAGE_BACKEND` selects storage:

- `memory`: process-local, thread-safe repositories. This is the development and test default.
- `postgres`: psycopg-backed repositories using Supabase PostgreSQL.

`APP_ENV=production` requires `STORAGE_BACKEND=postgres`. Production cannot silently fall back to
volatile process memory. Selecting `postgres` requires `SUPABASE_DB_URL`; an invalid or incomplete URL
prevents startup.

No fallback from a failed database connection to memory is implemented. A connectivity failure becomes
a generic `503 service_unavailable` response rather than a false success with lost data.

## PostgreSQL access decision

The backend uses direct PostgreSQL access through `psycopg` instead of the Supabase Python SDK. This is
deliberate:

- Budget mutations need a transaction covering version verification, expense writes, and version
  increments.
- PostgreSQL row locks (`SELECT ... FOR UPDATE`) prevent concurrent writers from applying changes based
  on the same version.
- Unique constraints enforce one budget per event even under races.
- Foreign keys provide cascade deletion and referential integrity.
- The API remains independent of provider-specific client objects.

Only `SUPABASE_DB_URL` is read by the backend. Supabase URL/API keys/JWKS settings are present for
future frontend and authentication work but are not used in Phase 3.
The backend opens a connection per repository operation and relies on the connection context manager
for transaction commit/rollback. There is no connection pool yet; this is a known MVP limitation.

Database failures are translated at the connection boundary. Raw provider details never reach clients.

## Data model

### Events

`public.events` stores the event domain:

- UUID primary key.
- Nullable `owner_id` referencing `auth.users`, prepared for future authenticated ownership.
- Name, type, date, location, guest count, decimal budget, and three-letter currency.
- Optional description.
- JSON arrays for preferences and event constraints.
- UTC timestamps.

The database column `event_constraints` avoids using the SQL keyword `constraints`; the HTTP contract
still exposes `constraints`.

### Budgets

`public.event_budgets` stores at most one budget per event:

- Unique `event_id` with cascade deletion from `events`.
- Positive bounded `total_limit`.
- Currency inherited from the event at creation.
- `reserve_type` of `percentage` or `fixed_amount`.
- Non-negative `reserve_value`, with checks for percentage range and fixed reserve not exceeding the
  total limit.
- Integer `version`, starting at 1.
- UTC timestamps.

The application always recalculates reserve amount, spending totals, status, issues, and cost per
guest. These derived values are not authoritative database columns.

### Expenses

`public.budget_expenses` stores planned line items:

- UUID primary key and cascade-linked `budget_id`.
- Category and name.
- Positive bounded two-decimal amount.
- `amount_status` of `estimated`, `quoted`, or `confirmed`.
- Optional notes.
- UTC timestamps.

Expense status records the confidence of an amount. It is not a vendor booking, payment, or verified
quotation state.

### Migration accounting

`public.schema_migrations` is created by the migration runner. It records version filename, SHA-256
checksum, and application timestamp. An applied migration cannot be edited silently; the runner
refuses to continue when its checksum changes.

## Event domain and storage

An event has a server-generated UUID, supported type, calendar date, location, guest count, decimal
budget, currency, optional description, preference/constraint lists, and UTC timestamps. Clients cannot
provide server-managed fields.

The repository abstraction isolates event policy from storage. The memory implementation uses a
re-entrant lock and returns deep copies. The PostgreSQL implementation uses bound parameters and
explicit column lists, with JSONB for preference and constraint arrays.

Creation order is used for deterministic pagination. The API requires both `limit` and `offset`, bounds
the limit to 100, and returns `total` with the page. Memory mode has process-lifetime durability only.
PostgreSQL mode is durable, subject to the configured Supabase project and connection.

## Budget domain and calculations

Each event has at most one budget. On creation:

- `total_limit` defaults to the event's `budget_amount`; a positive override is allowed.
- Currency is inherited from the event.
- Reserve defaults to 0% and can be a percentage or fixed amount.
- Version starts at 1.

No foreign-exchange conversion exists. If an event's budget or currency changes later, an existing
budget is not silently re-based. The current values remain until a future explicit re-baseline
operation is designed.

### Money

- Python `Decimal` is authoritative. Binary floating-point is not used for stored/calculated values.
- Inputs allow at most two decimal places.
- Values are rounded with `ROUND_HALF_UP` to two decimal places.
- Individual amounts and total limits are bounded at `100,000,000.00`.
- Expense amounts must be greater than zero.
- All totals, category sums, and statuses are server-derived.

### Formulas

For a percentage reserve, `reserve_amount = round(total_limit * reserve_value / 100)`. For a fixed
reserve, `reserve_amount = reserve_value`.

```text
available_for_planning = total_limit - reserve_amount
planned_spending       = sum(expense.amount)
remaining_total        = total_limit - planned_spending
remaining_after_reserve = total_limit - planned_spending - reserve_amount
budget_overrun         = max(0, planned_spending - total_limit)
reserve_consumed       = max(0, planned_spending - available_for_planning)
cost_per_guest         = round(planned_spending / guest_count), when guest_count > 0
```

Statuses:

- `within_allocation` when planned spending is at or below available-for-planning.
- `reserve_consumed` when spending exceeds available-for-planning but not the total limit.
- `over_budget` when spending exceeds the total limit.

Reserve consumption creates a deterministic warning (`reserve_consumed`). A total overrun creates a
deterministic error (`total_budget_exceeded`). Spending exactly at a boundary does not incorrectly move
to the next state.

Default categories cover venue/logistics, catering, decoration, photography/videography,
entertainment, transportation, and miscellaneous. Custom categories are preserved. Category totals are
ordered by the default category order, then custom categories case-insensitively.

## Optimistic concurrency

Every budget update and expense mutation carries `expected_version`:

- The service verifies the version before expensive/no-op logic where possible.
- The repository re-verifies under its respective lock.
- In memory, a re-entrant lock surrounds check-and-mutate.
- In PostgreSQL, `SELECT ... FOR UPDATE` serializes writers for the budget row.
- The version increments in the same transaction as the mutation.
- A stale version returns `409 conflict`.
- A no-op update does not increment the version.

This prevents two requests from applying separate changes based on the same old budget state.

## Validation layers

Validation is split deliberately:

1. Pydantic request schemas reject malformed types, unknown fields, excessive lengths, invalid enums,
   non-finite or over-precision money, invalid reserve shapes, and missing/incorrect version values.
2. Services enforce server-state policies: event existence, one-budget-per-event, fixed reserve not
   exceeding the selected total, explicit-null update rules, identifier validity, and version checks.
3. The calculator independently validates direct financial inputs so it cannot rely on HTTP schemas.
4. Database constraints provide a final integrity boundary for persistence.

Important event rules:

- Text is stripped; required text cannot be blank.
- Guest count is a strict integer.
- Event dates use `YYYY-MM-DD`; datetimes are rejected. Dates before today in `APP_TIMEZONE` are
  rejected.
- Currency is three ASCII letters, normalized to uppercase.
- A no-op event update preserves `updated_at`; a real change produces a timestamp later than the
  current clock and previous value.
- Malformed, non-canonical, or nonexistent UUIDs produce the same `404 not_found`.

Important budget rules:

- Budget and expense bodies reject unknown fields, including client-supplied currency, totals, status,
  or version fields in responses-only positions.
- `expected_version` is a strict positive integer. Strings such as `"1"` are rejected.
- Explicit `null` is rejected for budget limit and reserve updates.
- Explicit `null` is rejected for expense category/name/amount/status updates; `notes: null` is allowed
  to clear notes.
- A stale/no-op update still requires a matching current version.

## Configuration flow

Configuration resolves in this order:

1. Process environment variables supplied by the deployment platform or shell.
2. `backend/.env` for local development, if present.
3. Validation defaults in `Settings`.

Tests construct `Settings(_env_file=None, ...)` so a developer's local `.env` cannot alter results.

Key behavior:

- `APP_TIMEZONE` defaults to `Asia/Kolkata`; pinned `tzdata` supplies IANA data on Windows.
- `STORAGE_BACKEND` defaults to `memory`.
- Production rejects `memory`, `DEBUG=true`, and missing database configuration.
- `SUPABASE_DB_URL` is a `SecretStr`; status diagnostics expose only booleans, never the URL.
- `LLM_ENABLED=false` by default. Enabling it requires both a Gemini key and model.
- No provider request is made at import, startup, or health-check time.
- Docs and configuration diagnostics are enabled outside production and disabled in production by
  default.

## API contracts and versioning

- Product routes use `/api/v1`. Breaking response changes require `/api/v2`.
- `/health` remains outside the versioned namespace for infrastructure checks.
- Successful payloads use explicit Pydantic response models.
- Error envelopes use `error.code`, `error.message`, and optional `error.fields[]` with `field`,
  `message`, and `type`.
- Validation field paths use the `body.` prefix for frontend form mapping.
- `404`, `409`, and `503` use the same envelope with safe messages.
- Unhandled exceptions return generic `500 internal_error`; stack traces and exception text are never
  exposed.
- OpenAPI generation is enabled outside production by default and configurable elsewhere.

Expense deletion uses a query parameter for `expected_version` and returns the recalculated budget
summary with `200`, rather than an empty `204`, so clients immediately receive the new version and
totals.

## Security decisions

- CORS accepts an explicit origin list; wildcards are rejected.
- CORS credentials are always disabled. Introducing authentication requires a deliberate review of
  this decision.
- Provider credentials and the database URL are `SecretStr` and never returned by API/status/OpenAPI.
- Database failure responses are generic; provider details are not exposed.
- SQL values are always bound parameters. SQL identifiers/column lists are fixed constants, never
  client input.
- Unhandled exceptions log only the HTTP method and path. Request bodies, headers, credentials, and
  exception messages are not logged.
- Event and budget validation rejects unknown fields and bounds text, collection sizes, money, and
  versions. This does not replace platform-level body/rate limits.
- Debug mode cannot be enabled in production.
- The application makes no Gemini request during startup or ordinary API operation.
- No dynamic evaluation or arbitrary code execution is used.
- No SQL, shell, or filesystem path is built from client input.

### RLS is not authentication

The migration enables RLS and defines `authenticated`-role policies based on `auth.uid()` and nullable
`owner_id`. The current API has no authentication and no owner assignment. The backend connection role
can bypass RLS for current operation. Therefore:

- RLS policies are preparation, not an active API authorization boundary.
- There is no user/session isolation in the HTTP API.
- Direct browser access to tables is not a workaround and should not be granted.
- The API must remain private until authentication and ownership assignment are implemented.

## Migrations and deployment

The initial SQL migration lives under `supabase/migrations/` and follows the Supabase CLI naming
layout. The backend includes a separate transactional runner because no Supabase project is provisioned
here.

The runner:

- Uses `SUPABASE_DB_URL` from environment or `.env`.
- Acquires an advisory transaction lock.
- Creates `schema_migrations` if absent.
- Checks checksums for applied files.
- Applies all pending files in one transaction.
- Refuses edited applied migrations.

The schema is not applied automatically at application startup. Startup must not mutate production
schema implicitly, and a failed migration should be an explicit deployment failure.

The Phase 3 schema has been applied to a live Supabase project and verified with the opt-in
PostgreSQL integration test plus an API-to-database event/budget/expense smoke test. Browser-facing
RLS behavior remains unverified because API authentication and owner assignment are not implemented.

## Assumptions

- TLS terminates at the hosting platform or reverse proxy.
- Deployment environments supply secrets through environment configuration, not committed files.
- Browser origins are known before deployment and configured explicitly.
- Only the backend reaches the database; browsers use the HTTP API.
- The Supabase database role supplied to the backend may bypass RLS, as required by the current
  unauthenticated API.
- Short-lived direct connections are acceptable for MVP traffic until pooling is introduced.
- Budgets are single-currency plans with no FX conversion.
- Planned expenses are estimates/quotations/confirmed amounts, not vendor payments.
- Event budget/currency changes do not automatically re-base an existing budget.
- In-memory storage is development/test only.

## Required before public deployment

- Authentication and authorization on every event and budget operation.
- Owner assignment and an API access model reconciled with RLS policies.
- A real Supabase project, applied migration, verified connection, backups, and recovery plan.
- Connection pooling or an explicitly verified Supabase pooler configuration.
- Rate limiting, request-size limits, quota controls, and abuse protection.
- Audit logging that excludes credentials and sensitive event content.
- Dependency and secret scanning in CI.
- Platform-level security headers and TLS verification.
- Opt-in live database integration tests in CI against an isolated project.
- A policy for event budget/currency changes after budget creation.
- Verified Gemini model access and live-provider tests before AI features ship.
- Prompt-injection and untrusted-output handling for generated plans.

## Testing strategy

Tests are deterministic and use FastAPI TestClient with isolated Settings, isolated repositories, and
a fixed 2030 clock.

- Health/contract tests verify status, schema generation, route inventory, and safe failures.
- Configuration tests cover credential-free startup, `.env` precedence, invalid timeouts/retries/
  timezones, production storage enforcement, database URL validation, and secret non-disclosure.
- Security tests cover CORS allow/deny behavior, wildcard rejection, credential non-disclosure,
  no credential logging, safe production errors, and debug rejection.
- Event tests cover CRUD, validation, timezone-aware dates, pagination, no-op updates, nullable rules,
  404 consistency, state isolation, and concurrent creation.
- Calculator tests cover formulas, half-up rounding, reserves, boundary statuses, issues, category
  ordering/grouping, cost per guest, and invalid financial input.
- Budget service tests cover defaults, custom settings, duplicate budgets, expense lifecycle,
  no-op behavior, version conflicts, explicit-null rules, and fixed-reserve limits.
- Budget API tests cover routes, response contracts, error envelopes, validation, 404/409/503 paths,
  version increments, and event deletion behavior.
- Migration tests cover required tables/constraints/RLS, migration naming, and runner safety without a
  live database.
- A PostgreSQL connectivity test verifies safe DSN failure translation.
- Live PostgreSQL integration tests are opt-in through `TEST_SUPABASE_DB_URL` and skipped otherwise.

No test calls Gemini, consumes provider quota, or connects to Supabase by default.

## Path to the event planner

Later services map directly to product requirements:

- Timeline/task service: dependency-aware schedules and rescheduling.
- Vendor service: checklists and booking state transitions.
- AI planning service: provider-agnostic theme, menu, and cost-optimization proposals.
- Plan service: versioned edits, validation, and export.
- Authentication/ownership service: user identity, ownership assignment, and RLS-aligned API access.

The event/budget domain, repository boundaries, transactional versioning, safe error format, migration
path, and server-only credential handling support this evolution without turning the backend into a
generic chatbot proxy.
