# Festivo AI deployment guide

This guide describes deployment of the existing React/Vite frontend, FastAPI backend, and Supabase
database. No deployment is currently published from this repository.

## Frontend

Deploy `frontend/` to Vercel or another static Vite host.

- Root directory: `frontend`
- Install command: `npm ci`
- Build command: `npm run build`
- Output directory: `dist`
- Required variables:
  - `VITE_API_BASE_URL`: public HTTPS URL of the FastAPI service
  - `VITE_SUPABASE_URL`: Supabase project URL
  - `VITE_SUPABASE_ANON_KEY`: public Supabase anon/publishable key

Configure the host for SPA fallback to `index.html`. Add the production frontend origin to the
backend `FRONTEND_ORIGIN` or `FRONTEND_ORIGINS` setting. Add the frontend URL to the Supabase Auth
redirect allow-list, including the callback path `/auth/callback`.

## Backend

The backend currently targets Python 3.15 (`>=3.15,<3.16`) and uses the pinned dependencies in
`backend/pyproject.toml`.

```powershell
cd backend
python -m pip install .
python -m uvicorn app.main:app --host 0.0.0.0 --port $env:PORT
```

Set `APP_ENV=production`, `STORAGE_BACKEND=postgres`, and configure:

- `SUPABASE_DB_URL`
- `SUPABASE_URL` or both `SUPABASE_JWKS_URL` and `SUPABASE_JWT_ISSUER`
- `SUPABASE_JWT_AUDIENCE`
- `FRONTEND_ORIGIN` or `FRONTEND_ORIGINS`
- `LLM_ENABLED`, `LLM_PROVIDER`, `LLM_MODEL`, and `GEMINI_API_KEY` when AI planning is enabled

Production startup rejects debug mode, missing PostgreSQL configuration, and missing authentication
configuration. Use `GET /health` as the platform health check. OpenAPI and configuration diagnostics
are disabled in production by default.

## Supabase

Apply migrations in filename order using the transactional runner:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\apply_migrations.py
```

The runner records checksums and refuses modified already-applied migrations. Verify RLS state and
migration accounting using the queries in [../supabase/README.md](../supabase/README.md). Use a
separate Supabase project for development, tests, and production.

## Smoke tests after deployment

1. Open the frontend and confirm the landing page loads.
2. Confirm `GET /health` returns a healthy response.
3. Sign in with a non-production test account.
4. Create an event, budget, task, and vendor.
5. Generate an AI plan only when Gemini is configured.
6. Review/approve a proposal and download PDF and CSV exports.
7. Confirm a second test account receives no access to the first account's event.

Do not run destructive smoke tests against production data.
