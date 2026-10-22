# Festivo AI Backend

FastAPI backend for the Festivo AI event planner. Phase 3 adds a Decimal-safe budget engine, planned
expenses, optimistic concurrency, and a Supabase PostgreSQL persistence path while preserving Phase 2
event CRUD.

Phase 4 has not been implemented. There is no timeline, vendor, AI generation, or frontend work in
this phase.

## Supported Python version

Python **3.15.0** has been used to install and validate the pinned dependency set on Windows x64.
`pyproject.toml` constrains the project to Python `>=3.15,<3.16`. The pinned `tzdata` package supplies
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
| `FRONTEND_ORIGIN` | One explicit CORS origin | `http://localhost:5173` |
| `FRONTEND_ORIGINS` | Comma-separated or JSON-array CORS origins | Uses `FRONTEND_ORIGIN` |
| `LLM_PROVIDER` | LLM provider identifier | `gemini` |
| `LLM_MODEL` | Provider model identifier | unset |
| `GEMINI_API_KEY` | Server-side Gemini credential | unset |
| `LLM_ENABLED` | Enables the future LLM feature boundary | `false` |
| `LLM_TIMEOUT_SECONDS` | Future provider request timeout, 0-300 | `30` |
| `LLM_MAX_RETRIES` | Future provider retries, 0-10 | `2` |
| `DEBUG` | FastAPI debug mode; rejected in production | `false` |
| `DOCS_ENABLED` | Override OpenAPI/docs exposure | enabled outside production |
| `CONFIG_STATUS_ENABLED` | Override configuration diagnostics exposure | enabled outside production |

Important configuration behavior:

- Wildcard CORS origins are rejected. CORS credentials are always disabled.
- `APP_TIMEZONE` must be a valid IANA zone.
- `APP_ENV=production` requires `STORAGE_BACKEND=postgres`; production cannot silently use volatile
  memory.
- `STORAGE_BACKEND=postgres` requires a valid `postgres://` or `postgresql://` URL.
- `SUPABASE_DB_URL` is stored as `SecretStr` and is never included in API responses or configuration
  diagnostics.
- When `LLM_ENABLED=true`, both `GEMINI_API_KEY` and `LLM_MODEL` are required. No live Gemini call is
  implemented in Phase 3.

## Storage modes

### Memory

`STORAGE_BACKEND=memory` is intended for local development and tests. Events, budgets, and expenses
disappear on process restart, and separate worker processes do not share data. In-memory version
checks use a re-entrant lock.

### Supabase PostgreSQL

`STORAGE_BACKEND=postgres` stores events, budgets, and expenses in PostgreSQL. The backend uses
`psycopg==3.3.6` with `psycopg-binary==3.3.6` and short-lived direct database connections.

The backend does **not** use the Supabase JavaScript/Python SDK or Supabase API keys. Direct
PostgreSQL access was chosen because budget mutations require explicit transactions, row locks, and
optimistic version checks. Only `SUPABASE_DB_URL` is read by the backend; `SUPABASE_URL`,
`SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, and `SUPABASE_ANON_KEY` are reserved for future
frontend/authentication work.

Before using PostgreSQL:

1. Create or select an isolated Supabase project.
2. Obtain a direct or pooler connection URI from the Supabase dashboard.
3. URL-encode special characters in the database password.
4. Use TLS as required by the provider, typically with `sslmode=require`.
5. Configure the URI only in the backend environment or `.env`; never commit it or send it to the
   frontend.
6. Apply the migration described below.

The Phase 3 schema has been applied to a live Supabase project configured outside this repository and
verified with a direct connection, the opt-in PostgreSQL integration test, and an API-to-database
smoke test. See [../supabase/README.md](../supabase/README.md) for the remaining RLS/auth limitations.

## Database migrations

The initial migration is:

```text
supabase/migrations/202610230001_initial_budget_engine.sql
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
migration creates `events`, `event_budgets`, and `budget_expenses`, constraints, indexes, and
owner-oriented RLS policies. It does not create users or authenticate the API.

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

`GET /api/v1/events` defaults to `limit=20` and `offset=0`; the maximum limit is `100`. Results use
creation order so repeated reads are deterministic.

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
- `409 conflict`: duplicate budget or stale `expected_version`.
- `422 validation_error`: malformed body, unknown field, invalid money, or invalid reserve.
- `503 service_unavailable`: database connectivity failure. Provider details are not exposed.
- `500 internal_error`: unexpected failure with no stack trace or exception text.

The API never returns database URLs, provider credentials, environment dumps, stack traces, or
filesystem paths in error responses. Unhandled errors are logged only with the HTTP method and path.

## Tests and checks

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check app tests scripts
.\.venv\Scripts\ruff.exe format --check app tests scripts
```

Tests use isolated settings, isolated storage, a fixed event clock, dummy credentials, and no live
provider calls. Date-policy tests do not depend on the real current date.

The budget tests cover calculations, rounding, reserves, statuses, category grouping, validation,
version conflicts, no-op updates, API contracts, safe 404/409/503 responses, and event deletion
behavior. Migration tests validate SQL structure and runner safety. No test connects to Supabase by
default.

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
- Database failures return a generic `503`; connection details stay server-side.
- **There is still no authentication or authorization on any event or budget route.**
- The migration prepares nullable `owner_id` columns and RLS policies, but the current API does not
  assign owners or authenticate users. The backend database role can bypass RLS. RLS is not a
  substitute for the missing API authentication.
- No rate limiting, request-size protection, quota controls, or audit logging exist yet.
- Event CRUD and budget routes must not be publicly exposed without authentication and
  platform-level protections.

## Current limitations

- No authentication, ownership enforcement, or user isolation.
- Browser-facing RLS behavior is unverified because API authentication and owner assignment are absent.
- No connection pool; each repository operation opens a short-lived database connection. This is
  acceptable for the current MVP but should be reconsidered for sustained production traffic.
- No automatic budget re-baselining when event budget/currency changes.
- Memory mode retains an unreachable budget object after event deletion until process restart;
  PostgreSQL mode deletes budgets and expenses by foreign-key cascade.
- No foreign exchange, taxes, vendor payments, or actual-expense reconciliation.
- No timeline, tasks, vendors, AI planning, or frontend.
- Offset pagination only; no cursor pagination for large persistent datasets.

See [../docs/architecture.md](../docs/architecture.md) for detailed design decisions and the path to
the remaining phases.
