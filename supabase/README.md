# Supabase PostgreSQL Setup

This directory contains versioned SQL migrations for the Festivo AI backend.

This repository does not provision the Supabase project. The initial migration was applied to a
configured live project during local Phase 3 verification; repeat the steps below for each new
environment.

## What the migration creates

`migrations/202610230001_initial_budget_engine.sql` creates:

- `public.events`: event data previously held only in memory.
- `public.event_budgets`: at most one budget per event, enforced by a unique `event_id`.
- `public.budget_expenses`: planned expenses linked to a budget.
- Foreign keys with cascade deletion from events to budgets to expenses.
- Checks for positive bounded money, two-decimal monetary values, reserve rules, expense status,
  currency format, and text lengths.
- Indexes for owner lookup, creation order, and budget expense ordering.
- Row-level security enablement and owner-oriented policies for future authenticated access.

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
- The backend reads only `SUPABASE_DB_URL`. Supabase URL, publishable/secret/anon keys, and JWKS
  settings are reserved for future frontend/authentication work and are not used in Phase 3.
- The backend opens short-lived connections and does not include a connection pool.
- If the deployment platform requires a pooler, use the connection string supplied by Supabase for
  that deployment mode. Verify the chosen port and TLS requirements in the Supabase dashboard.

## Apply the migration

From the repository root, using the backend virtual environment:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\apply_migrations.py
```

The runner reads `backend/.env` and the process environment. It records applied migrations and
checksums in `public.schema_migrations`, refuses edited applied migrations, and wraps pending work in a
transaction.

Alternatively, the migration directory follows the Supabase CLI layout. Apply it with the Supabase CLI
only if that workflow is already configured for the target project. Do not apply the same migration
through both tools.

## Security and RLS status

The migration enables row-level security on all three tables and defines `authenticated`-role policies
based on `auth.uid()`. However:

- `owner_id` is nullable and the current API does not authenticate users or assign ownership.
- The backend connects with a database role that can bypass RLS, as required for current
  unauthenticated operation.
- RLS policies therefore do **not** make the current HTTP API multi-user safe.
- Until authentication and owner assignment are implemented, do not expose the API publicly.

Do not grant browser clients direct table access as a workaround. The budget calculations, optimistic
version checks, and validation must remain server-side.

## Optional integration test

The live integration test is skipped unless a dedicated test database is configured:

```powershell
$env:TEST_SUPABASE_DB_URL = "postgresql://..."
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_postgres_infrastructure.py
```

Use an isolated project with the migration applied. Never point this test variable at production data.

## Manual verification

After applying the migration to a test project, verify that the expected tables and RLS state exist:

```sql
select schemaname, tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('events', 'event_budgets', 'budget_expenses');

select version, checksum, applied_at
from public.schema_migrations
order by version;
```

These queries verify structure and migration accounting, not API authentication or live application
connectivity.
