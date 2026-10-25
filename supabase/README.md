# Supabase PostgreSQL Setup

This directory contains versioned SQL migrations for the Festivo AI backend. The repository does not
provision the Supabase project, create Auth users, or manage provider secrets.

## Migrations

```text
migrations/202610230001_initial_budget_engine.sql
migrations/202610230002_timeline_task_engine.sql
migrations/202610240001_vendor_management.sql
migrations/202610250001_planning_proposals.sql
```

They create and extend:

- `public.events`: event data, owner, timezone, and JSON preference/constraint arrays.
- `public.event_budgets`: at most one budget per event.
- `public.budget_expenses`: planned expenses linked to a budget.
- `public.event_timelines`: at most one timeline per event.
- `public.event_tasks`: generated and user-editable planning tasks.
- `public.event_vendors`: vendor records and booking status.
- `public.vendor_status_history`: vendor status transitions.
- `public.planning_proposals`: AI proposal payload, source snapshot, lifecycle status, and version.

The schema includes foreign keys with cascade deletion, bounded money checks, two-decimal monetary
values, status/currency/text checks, ordering and ownership indexes, and row-level security policies.

The database column for event constraints is named `event_constraints` because `constraints` is an
SQL keyword. The HTTP API still exposes the field as `constraints`.

## Connection model

The backend connects directly with `psycopg` using a PostgreSQL URI:

```text
SUPABASE_DB_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require
```

Important:

- Treat `SUPABASE_DB_URL` as a server-side secret. Never commit it or expose it to browser code.
- URL-encode special characters in the password.
- `SUPABASE_DB_URL` is the database credential. `SUPABASE_URL` or explicit JWKS/issuer settings are
  used separately for access-token verification.
- The backend opens short-lived connections and does not include a connection pool.
- If the deployment platform requires a pooler, use the connection string supplied by Supabase for
  that deployment mode. Verify the chosen port and TLS requirements in the dashboard.

## Apply migrations

From the repository root, using the backend virtual environment:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\apply_migrations.py
```

The runner reads `backend/.env` and the process environment. It records applied filenames and SHA-256
checksums in `public.schema_migrations`, refuses to continue if an applied file was edited, and wraps
pending work in a transaction under an advisory lock.

Alternatively, the migration directory follows the Supabase CLI layout. Apply it with the Supabase CLI
only if that workflow is already configured for the target project. Do not apply the same migration
through both tools and do not edit an already-applied migration.

## Authentication and RLS

The API verifies Supabase access tokens against the project JWKS and resolves the owner UUID from the
token `sub`. Every event-scoped query also filters by owner in the application layer.

The migrations enable RLS and define `authenticated`-role policies based on `auth.uid()`:

- `events`
- `event_budgets`
- `budget_expenses`
- `event_timelines`
- `event_tasks`
- `event_vendors`
- `vendor_status_history`
- `planning_proposals`

The backend uses a database role that can bypass RLS. API ownership checks are the primary
authorization boundary; RLS is defense in depth for any browser-facing access path.

Do not grant browser clients direct table access as a workaround. Budget calculations, version checks,
proposal approval, and validation must remain server-side.

## Optional integration test

The live integration test is skipped unless a dedicated test database is configured:

```powershell
$env:TEST_SUPABASE_DB_URL = "postgresql://..."
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_postgres_infrastructure.py
```

Use an isolated project with every migration applied. Never point this variable at production data.

## Manual verification

After applying the migrations, verify tables, migration accounting, and RLS state:

```sql
select schemaname, tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in (
    'events',
    'event_budgets',
    'budget_expenses',
    'event_timelines',
    'event_tasks',
    'event_vendors',
    'vendor_status_history',
    'planning_proposals'
  )
order by tablename;

select version, checksum, applied_at
from public.schema_migrations
order by version;
```

These queries verify structure and migration accounting, not live API authentication or provider
connectivity.
