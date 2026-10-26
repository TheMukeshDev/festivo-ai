# Festivo AI Backend

FastAPI backend for the Festivo AI event planner. Version 0.8.0 provides authenticated event,
budget, timeline, task, vendor, AI proposal, approval, and export workflows with memory or Supabase
PostgreSQL persistence.

Implemented capabilities:

- Supabase access-token verification with fail-closed ownership enforcement.
- Decimal-safe budget planning with optimistic concurrency.
- Deterministic timeline generation and task management.
- Vendor checklists, booking status, pricing fields, and comparison.
- Gemini-backed structured plan generation with validated output and safe errors.
- Persisted proposals with stale-snapshot checks, explicit approval/rejection, resumable partial
  approval, idempotent task application, and advisory recommendations.
- Owner-scoped PDF and CSV reports.

## Supported Python version

Python **3.12** is used to install and validate the pinned dependency set locally and on Vercel;
Python 3.15 remains supported. `pyproject.toml` constrains the project to Python `>=3.12,<3.16`.
The pinned `tzdata` package supplies
IANA timezone data on platforms such as Windows that do not provide it system-wide.

## Setup

Run the following from the `backend` directory in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The application can start without Gemini credentials or a database. Memory storage is the default.
Protected product routes still require authentication, so configure Supabase JWKS/issuer settings (or
inject a test verifier) before calling them. Health and safe configuration diagnostics remain
available without credentials.

## Environment configuration

Settings are validated with Pydantic Settings. Process environment variables take precedence over
the local `.env` file.

| Variable | Purpose | Default |
| --- | --- | --- |
| `APP_NAME` | Public application name | `Festivo AI` |
| `APP_ENV` | `development`, `test`, or `production` | `development` |
| `API_V1_PREFIX` | Versioned API prefix | `/api/v1` |
| `APP_TIMEZONE` | IANA timezone for event-date policy | `Asia/Kolkata` |
| `STORAGE_BACKEND` | `memory` or `postgres` | `memory` |
| `SUPABASE_DB_URL` | Server-only PostgreSQL URI; required for `postgres` | unset |
| `SUPABASE_DB_CONNECT_TIMEOUT_SECONDS` | Database connection timeout, 1-60 | `10` |
| `SUPABASE_URL` | Project URL used to derive the JWKS URL and issuer | unset |
| `SUPABASE_JWKS_URL` | Explicit Supabase JWKS endpoint | derived from `SUPABASE_URL` |
| `SUPABASE_JWT_ISSUER` | Explicit token issuer | derived from `SUPABASE_URL` |
| `SUPABASE_JWT_AUDIENCE` | Required token audience | `authenticated` |
| `SUPABASE_JWT_LEEWAY_SECONDS` | Clock-skew allowance, 0-300 | `30` |
| `FRONTEND_ORIGIN` | One explicit CORS origin | `http://localhost:5173` |
| `FRONTEND_ORIGINS` | Comma-separated or JSON-array CORS origins | Uses `FRONTEND_ORIGIN` |
| `LLM_PROVIDER` | LLM provider identifier | `gemini` |
| `LLM_MODEL` | Provider model identifier | unset |
| `GEMINI_API_KEY` | Server-side Gemini credential | unset |
| `LLM_ENABLED` | Enables AI proposal generation | `false` |
| `LLM_TIMEOUT_SECONDS` | Provider request timeout, 0-300 | `30` |
| `LLM_MAX_RETRIES` | Provider retries, 0-10 | `2` |
| `LLM_MAX_OUTPUT_TOKENS` | Provider output cap, 1-8192 | `2048` |
| `LLM_TEMPERATURE` | Provider sampling temperature, 0-2 | `0.4` |
| `PROPOSAL_TTL_HOURS` | Proposal lifetime, 1-720 hours | `168` |
| `DEBUG` | FastAPI debug mode; rejected in production | `false` |
| `DOCS_ENABLED` | Override OpenAPI/docs exposure | enabled outside production |
| `CONFIG_STATUS_ENABLED` | Override configuration diagnostics exposure | enabled outside production |

For compatibility with an existing Vercel project, `DATABASE_URL` is also accepted as
`SUPABASE_DB_URL`, and `CORS_ORIGINS` is also accepted as `FRONTEND_ORIGINS`.

Important configuration behavior:

- Wildcard CORS origins are rejected. CORS credentials are always disabled.
- `APP_TIMEZONE` must be a valid IANA zone.
- `APP_ENV=production` requires `STORAGE_BACKEND=postgres`; production cannot silently use volatile
  memory.
- `STORAGE_BACKEND=postgres` requires a valid `postgres://` or `postgresql://` URL.
- `SUPABASE_DB_URL` is stored as `SecretStr` and is never included in API responses or configuration
  diagnostics.
- Authentication is configured from `SUPABASE_URL`, or explicit JWKS/issuer settings. Without a
  verifier configuration, every protected route rejects tokens; the application never falls back to
  anonymous access.
- When `LLM_ENABLED=true`, both `GEMINI_API_KEY` and `LLM_MODEL` are required. Proposal generation
  returns a safe `503` when AI configuration or provider access is unavailable.
- `PROPOSAL_TTL_HOURS` is the default lifetime for new proposals. Expired proposals cannot be
  approved or rejected.

## Storage modes

### Memory

`STORAGE_BACKEND=memory` is intended for local development and tests. Events, budgets, timelines,
tasks, vendors, and proposals disappear on process restart, and separate worker processes do not
share data. In-memory version checks use re-entrant locks.

### Supabase PostgreSQL

`STORAGE_BACKEND=postgres` stores events, budgets, timelines/tasks, vendors, and planning proposals in
PostgreSQL. The backend uses `psycopg==3.3.6` with `psycopg-binary==3.3.6` and short-lived direct
database connections.

The backend does **not** use the Supabase JavaScript/Python SDK. Direct PostgreSQL access was chosen
because budget and proposal mutations require explicit transactions, row locks, and optimistic
version checks. `SUPABASE_DB_URL` is the database credential. `SUPABASE_URL` or the explicit
JWKS/issuer settings are used separately for access-token verification. Browser keys belong in the
frontend environment and are not read by the backend.

Before using PostgreSQL:

1. Create or select an isolated Supabase project.
2. Obtain a direct or pooler connection URI from the Supabase dashboard.
3. URL-encode special characters in the database password.
4. Use TLS as required by the provider, typically with `sslmode=require`.
5. Configure the URI only in the backend environment or `.env`; never commit it or send it to the
   frontend.
6. Apply the migration described below.

The latest schema includes the Phase 3 budget engine and the Phase 8 proposal table. Live Supabase
integration remains opt-in because it requires a dedicated `TEST_SUPABASE_DB_URL`. See
[../supabase/README.md](../supabase/README.md) for migration and RLS details.

## Database migrations

The versioned migrations are:

```text
supabase/migrations/202610230001_initial_budget_engine.sql
supabase/migrations/202610230002_timeline_task_engine.sql
supabase/migrations/202610240001_vendor_management.sql
supabase/migrations/202610250001_planning_proposals.sql
```

Apply pending migrations with the transactional runner:

```powershell
.\.venv\Scripts\python.exe scripts\apply_migrations.py
```

The runner:

- Reads `SUPABASE_DB_URL` from the environment or `backend/.env`.
- Acquires an advisory transaction lock.
- Records applied filenames and SHA-256 checksums in `public.schema_migrations`.
- Applies pending files in one transaction.
- Refuses to continue if an already-applied file was edited.

You can also apply the SQL with the Supabase CLI, but do not apply the same migration twice. The
migrations create the event, budget, expense, timeline task, vendor, and proposal tables with
constraints, indexes, and owner-oriented RLS policies. They do not create Supabase Auth users.

## Run the server

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Development documentation is available at `http://127.0.0.1:8000/docs` and the OpenAPI schema at
`http://127.0.0.1:8000/openapi.json`. Both are disabled by default when `APP_ENV=production` unless
explicitly overridden.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Minimal process health |
| `GET` | `/api/v1/health` | Versioned API health |
| `GET` | `/api/v1/config/status` | Safe configuration diagnostics |
| `POST` | `/api/v1/events` | Create an event |
| `GET` | `/api/v1/events` | List events with pagination |
| `GET` | `/api/v1/events/{event_id}` | Read one event |
| `PATCH` | `/api/v1/events/{event_id}` | Partially update an event |
| `DELETE` | `/api/v1/events/{event_id}` | Delete an event |
| `POST` | `/api/v1/events/{event_id}/budget` | Create the event budget |
| `GET` | `/api/v1/events/{event_id}/budget` | Read the calculated budget summary |
| `PATCH` | `/api/v1/events/{event_id}/budget` | Update limit or reserve |
| `POST` | `/api/v1/events/{event_id}/budget/expenses` | Add a planned expense |
| `PATCH` | `/api/v1/events/{event_id}/budget/expenses/{expense_id}` | Update a planned expense |
| `DELETE` | `/api/v1/events/{event_id}/budget/expenses/{expense_id}` | Delete a planned expense |
| `POST` | `/api/v1/events/{event_id}/timeline` | Generate the event timeline |
| `GET` | `/api/v1/events/{event_id}/timeline` | Read the timeline and tasks |
| `POST` | `/api/v1/events/{event_id}/timeline/regenerate` | Regenerate incomplete timeline tasks |
| `POST` | `/api/v1/events/{event_id}/tasks` | Add a task |
| `GET` | `/api/v1/events/{event_id}/tasks` | List and filter tasks |
| `GET` | `/api/v1/events/{event_id}/tasks/{task_id}` | Read one task |
| `PATCH` | `/api/v1/events/{event_id}/tasks/{task_id}` | Update task fields or status |
| `DELETE` | `/api/v1/events/{event_id}/tasks/{task_id}` | Delete a task |
| `POST` | `/api/v1/events/{event_id}/vendors` | Add a vendor |
| `GET` | `/api/v1/events/{event_id}/vendors` | List vendors |
| `GET` | `/api/v1/events/{event_id}/vendors/{vendor_id}` | Read one vendor |
| `PATCH` | `/api/v1/events/{event_id}/vendors/{vendor_id}` | Update vendor or booking state |
| `DELETE` | `/api/v1/events/{event_id}/vendors/{vendor_id}` | Delete a vendor |
| `POST` | `/api/v1/events/{event_id}/vendors/compare` | Compare selected vendors |
| `POST` | `/api/v1/events/{event_id}/proposals/generate` | Generate and persist an AI proposal |
| `GET` | `/api/v1/events/{event_id}/proposals` | List proposals |
| `GET` | `/api/v1/events/{event_id}/proposals/{proposal_id}` | Read one proposal |
| `POST` | `/api/v1/events/{event_id}/proposals/{proposal_id}/approve` | Apply selected proposal items |
| `POST` | `/api/v1/events/{event_id}/proposals/{proposal_id}/reject` | Reject a pending proposal |
| `POST` | `/api/v1/events/{event_id}/ai-plan` | Legacy proposal generation alias |
| `POST` | `/api/v1/events/{event_id}/ai-plan/refine` | Legacy preference-driven regeneration |
| `GET` | `/api/v1/events/{event_id}/ai-plan/status` | Safe AI configuration status |
| `GET` | `/api/v1/events/{event_id}/export/pdf` | Download the event report as PDF |
| `GET` | `/api/v1/events/{event_id}/export/csv` | Download the event report as CSV |

Every product route requires `Authorization: Bearer <supabase-access-token>`. Invalid or missing
tokens return `401`; a different owner receives `404` for the resource. `GET /api/v1/events` defaults
to `limit=20` and `offset=0`; the maximum limit is `100`. Results use creation order so repeated
reads are deterministic.

Budget deletion uses a required `expected_version` query parameter, for example:

```text
DELETE /api/v1/events/{event_id}/budget/expenses/{expense_id}?expected_version=3
```

Successful expense deletion returns `200` with the recalculated budget rather than an empty `204`
response.

## Event validation

| Field | Rules |
| --- | --- |
| `name` | Trimmed, 1-100 characters, cannot be blank |
| `event_type` | `wedding`, `birthday`, `college_event`, or `community_event` |
| `event_date` | `YYYY-MM-DD`; today or later in `APP_TIMEZONE` |
| `location` | Trimmed, 1-200 characters, cannot be blank |
| `guest_count` | Strict integer from 1 to 10,000; booleans and fractions are rejected |
| `budget_amount` | Decimal greater than 0 and at most 100,000,000.00, with at most 2 decimal places |
| `currency` | Three ASCII letters, normalized to uppercase; defaults to `INR` |
| `description` | Optional, trimmed, at most 2,000 characters |
| `preferences` | Optional list of at most 20 trimmed strings, each 1-200 characters |
| `constraints` | Optional list of at most 20 trimmed strings, each 1-200 characters |

Requests reject unknown fields. `event_id`, `created_at`, and `updated_at` are server-managed. On
output, `budget_amount` is a normalized decimal string, for example `"750000.00"`.

`PATCH` changes only supplied fields. Explicit `null` is rejected for every field except
`description`, where it clears the value. A no-op event update does not change `updated_at`. Invalid
or nonexistent UUID paths return the same `404 not_found` response.

## Budget model

Each event can have at most one budget. The budget inherits the event's currency. On creation,
`total_limit` defaults to the event's `budget_amount`; a different positive limit may be supplied.
There is no foreign-exchange conversion and no currency conversion after creation.

A reserve is either:

```json
{"type": "percentage", "value": "10.00"}
```

or:

```json
{"type": "fixed_amount", "value": "75000.00"}
```

A percentage must be between 0 and 100. A fixed reserve cannot exceed the total limit. The default is
a 0% percentage reserve.

Budget creation example:

```json
{
  "total_limit": "750000.00",
  "reserve": {"type": "percentage", "value": "10.00"}
}
```

Expense creation example:

```json
{
  "expected_version": 1,
  "category": "Catering and Refreshments",
  "name": "Dinner service",
  "amount": "180000.00",
  "amount_status": "quoted",
  "notes": "Venue catering proposal, not independently verified."
}
```

Supported expense statuses are `estimated`, `quoted`, and `confirmed`. They describe the confidence of
the recorded amount; they do not prove that a vendor is booked or paid. `notes` is optional and limited
to 500 characters.

Default categories are:

- Venue and Logistics
- Catering and Refreshments
- Decoration and Theme
- Photography and Videography
- Entertainment and Activities
- Transportation
- Miscellaneous

Custom category names are allowed. Categories are trimmed and limited to 80 characters.

### Money rules

- Authoritative financial values use Python `Decimal`, never binary floating point.
- Inputs allow at most two decimal places.
- Rounding uses `ROUND_HALF_UP` to two decimal places.
- Individual monetary values and the total limit are bounded at `100,000,000.00`.
- Expense amounts must be greater than zero.
- The server recalculates every derived value; clients cannot submit totals or statuses.

### Calculation rules

| Field | Calculation |
| --- | --- |
| `reserve.amount` | Percentage of `total_limit`, or the fixed value |
| `available_for_planning` | `total_limit - reserve.amount` |
| `planned_spending` | Sum of all expense amounts |
| `remaining_total` | `total_limit - planned_spending` |
| `remaining_after_reserve` | `total_limit - planned_spending - reserve.amount` |
| `budget_overrun` | `max(0, planned_spending - total_limit)` |
| `reserve_consumed` | `max(0, planned_spending - available_for_planning)` |
| `cost_per_guest` | `planned_spending / guest_count`, rounded; `null` if guests are unavailable or zero |

Budget status is deterministic:

- `within_allocation`: planned spending does not exceed the amount available after reserve.
- `reserve_consumed`: planned spending exceeds the available allocation but not the total limit.
- `over_budget`: planned spending exceeds the total limit.

Issues are also deterministic. Reserve consumption produces a warning with code `reserve_consumed`.
A total overrun produces an error with code `total_budget_exceeded`.

### Versioning and concurrency

Every budget update and expense mutation requires the current `expected_version`. The server locks the budget row,
verifies the version, applies the mutation, and increments the version atomically. A stale version
returns `409 conflict`.

- Budget setting changes increment the version.
- Expense create, update, and delete increment the version.
- A no-op budget or expense update does not increment the version.
- Two concurrent writers cannot both apply changes from the same version.
- In-memory and PostgreSQL repositories implement the same external version semantics.

The budget limit does not automatically follow later changes to the event's `budget_amount` or
`currency`. The budget retains the values with which it was created. This avoids silently changing an
active spending plan; a future phase may add an explicit re-baseline operation.

## Authentication and ownership

Protected routes verify Supabase access tokens against the project JWKS. Verification requires the
token issuer, audience (`authenticated` by default), signature, expiry, issued-at time, and an
`authenticated` role claim. The user's `sub` UUID becomes the owner ID for every event-scoped query.

- Missing, malformed, expired, or misconfigured tokens return `401`.
- A reachable but invalid token has the same `401` response.
- An unavailable JWKS endpoint returns a safe `503`.
- Events owned by another user return `404`, never `403`, to avoid confirming resource existence.
- The backend fails closed when authentication is not configured; there is no anonymous fallback.

## AI proposals and approval

Generate a proposal with `POST /api/v1/events/{event_id}/proposals/generate`. The request may include
planning preferences and an `allow_advisory` flag. Generation captures a snapshot of the event,
budget version, task count, and vendor count.

Proposal statuses are `pending`, `partially_approved`, `approved`, `rejected`, and `expired`. New
proposals expire after `PROPOSAL_TTL_HOURS`.

Approval semantics:

- Only explicitly selected items are applied. Omitted items remain pending.
- Supported actions add tasks, update task due dates, add vendor follow-up tasks, and suggest budget
  allocations.
- Advisory items never change application data.
- Task creation uses deterministic proposal/item keys, making repeated requests idempotent.
- Approval rechecks the proposal version and source snapshot. A stale snapshot returns `409` and asks
  the user to regenerate instead of silently applying outdated advice.
- Item-level validation or missing-resource failures are reported as skipped; valid applied work is
  retained so a later approval can resume.
- Approval does not mutate budgets or expenses automatically and does not book or pay vendors.
- Rejection requires a pending proposal and stores an optional reason.

PDF and CSV exports contain the event, budget, timeline/tasks, vendors, and applied plan
recommendations. They are owner-scoped, use download headers, and do not include arbitrary secrets.
Report text is escaped, and CSV cells are guarded against spreadsheet formula injection.

Gemini returns structured output that is validated before persistence. Provider failures map to safe
public statuses: `503` for configuration/authentication/service failures, `429` for rate limits, `504`
for timeouts, and `422` for invalid model output. Provider messages, credentials, and raw model output
are not returned to clients.

## API behavior

Successful responses use explicit Pydantic response models. Errors use one envelope:

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

Relevant HTTP statuses:

- `404 not_found`: unknown event, budget, expense, or malformed identifier.
- `401 unauthorized`: missing, invalid, or expired access token.
- `409 conflict`: duplicate budget, stale version, stale proposal snapshot, or a proposal that cannot
  transition from its current status.
- `422 validation_error`: malformed body, unknown field, invalid money, invalid reserve, or invalid
  AI output.
- `429 too_many_requests`: AI provider quota or rate limit.
- `503 service_unavailable`: database, auth-key, or AI provider availability failure.
- `504 gateway_timeout`: AI provider timeout.
- `500 internal_error`: unexpected failure with no stack trace or exception text.

The API never returns database URLs, provider credentials, environment dumps, stack traces, or
filesystem paths in error responses. Unhandled errors are logged only with the HTTP method and path.

## Tests and checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests scripts
```

Tests use isolated settings, isolated storage, a fixed event clock, injected auth verifiers, dummy
credentials, and no live provider calls. Date-policy tests do not depend on the real current date.
Coverage includes domain rules, API contracts, ownership isolation, safe errors, budgets, timelines,
vendors, AI proposals/approval, PDF/CSV exports, migration SQL, and the opt-in PostgreSQL integration
test. No test connects to Supabase by default.

Optional live PostgreSQL integration tests are skipped unless a dedicated test database is supplied:

```powershell
$env:TEST_SUPABASE_DB_URL = "postgresql://..."
.\.venv\Scripts\python.exe -m pytest tests/test_postgres_infrastructure.py
```

Use an isolated test project with the migration already applied. Do not point this variable at
production data.

## Security notes

- Provider and database credentials are read only by the backend and are represented as `SecretStr`.
- API responses and OpenAPI output do not include `GEMINI_API_KEY` or `SUPABASE_DB_URL`.
- CORS uses an explicit origin list and never enables credentialed cross-origin requests.
- Debug mode is rejected in production.
- Production disables docs and configuration diagnostics by default.
- Health endpoints do not contact external services.
- SQL queries use bound parameters for all client-derived values. SQL identifiers are fixed
  constants, never request input.
- Database and AI provider failures return a generic `503`; connection details stay server-side.
- Every protected product route requires a verified Supabase token and enforces owner scoping.
- Cross-user resource access returns `404` to avoid confirming existence.
- AI output is validated as structured data before persistence; advisory content is never executed.
- Report text is escaped and CSV exports neutralize spreadsheet formula prefixes.
- The backend database role bypasses RLS by design. API ownership checks are the primary boundary;
  RLS remains defense in depth for browser-facing access.
- No application-level rate limiting, request-size protection, quota controls, or audit logging exist
  yet. Apply platform-level limits before public production exposure.

## Current limitations

- No connection pool; each repository operation opens a short-lived database connection. This is
  acceptable for the current MVP but should be reconsidered for sustained production traffic.
- Proposal approval can span multiple service calls. It is resumable and avoids re-applying completed
  items, but it is not a single transaction across every affected table.
- Proposal TTL is evaluated when an action is attempted; listing proposals does not rewrite every
  expired row.
- No automatic budget re-baselining when event budget/currency changes.
- Memory mode does not share data across worker processes and loses data on restart.
- No foreign exchange, taxes, actual-expense reconciliation, or vendor payment processing.
- Offset pagination only; no cursor pagination for large persistent datasets.
- Live Supabase migrations and PostgreSQL integration tests require separate configured credentials;
  they are not part of the default test run.

See [../docs/architecture.md](../docs/architecture.md) for detailed design decisions and the path to
the remaining phases.
