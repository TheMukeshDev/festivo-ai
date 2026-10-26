# Festivo AI deployment guide

This guide describes separate Vercel deployments for the React/Vite frontend and FastAPI backend,
with Firebase providing authentication and Supabase PostgreSQL persistence.

## Frontend

Deploy `frontend/` as its own Vercel project.

- Root directory: `frontend`
- Framework preset: `Vite`
- Install command: `npm ci`
- Build command: `npm run build`
- Output directory: `dist`
- Required variables:
  - `VITE_API_BASE_URL`: public HTTPS URL of the FastAPI service
  - `VITE_FIREBASE_API_KEY`
  - `VITE_FIREBASE_AUTH_DOMAIN`
  - `VITE_FIREBASE_PROJECT_ID`
  - `VITE_FIREBASE_STORAGE_BUCKET`
  - `VITE_FIREBASE_MESSAGING_SENDER_ID`
  - `VITE_FIREBASE_APP_ID`
  - Optional reviewer shortcut: `VITE_DEMO_EMAIL` and `VITE_DEMO_PASSWORD`, configured only
    with a dedicated non-production Firebase test account

`frontend/vercel.json` configures the SPA fallback to `index.html`. After deployment, add the
production frontend origin to the backend `FRONTEND_ORIGINS` setting and add the frontend URL to
Firebase Authentication authorized domains.

## Backend

Deploy `backend/` as a second Vercel project. `backend/vercel.json` and `backend/api/index.py`
expose the FastAPI `app` as a Vercel Python function.

Configure the Vercel project with:

- Root directory: `backend`
- Framework preset: `Other`
- Build command: leave empty
- Output directory: leave empty
- Runtime entry point: `api/index.py`

Set `APP_ENV=production`, `STORAGE_BACKEND=postgres`, and configure these Vercel environment
variables:

- `SUPABASE_DB_URL`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_CLIENT_EMAIL`
- `FIREBASE_PRIVATE_KEY`
- `FRONTEND_ORIGINS` with the exact frontend URL, for example
  `https://festivoai01.vercel.app` (the deployed backend also includes this origin by
  default, but setting the variable explicitly is recommended when using a custom domain)
- `LLM_ENABLED`, `LLM_PROVIDER`, `LLM_MODEL`, and `GEMINI_API_KEY` when AI planning is enabled

Production startup rejects debug mode, missing PostgreSQL configuration, and missing authentication
configuration. Use `GET /health` as the platform process check and
`GET /api/v1/health/database` as the database readiness check. The latter runs a lightweight
database query and returns HTTP 503 when PostgreSQL is unavailable. OpenAPI and configuration
diagnostics are disabled in production by default.

Do not set `STORAGE_BACKEND=memory` in the deployed backend. Vercel functions are ephemeral and
memory-backed events will disappear between invocations.

## Reviewer demo account

The deployed frontend includes an optional **Use demo account** shortcut backed by a dedicated
Firebase test user. The current reviewer credentials are:

- Email: `demo@festivoai.com`
- Password: `FestivoDemo@2026!`

This account is for testing only and must not contain real personal or event data. Rotate or
disable it in Firebase Authentication if it is abused.

## Vercel deployment sequence

1. Create a Vercel project from this repository with root directory `backend`; deploy it first.
2. Copy its HTTPS URL and verify `https://<backend-domain>/health`.
3. Create a second Vercel project with root directory `frontend`.
4. Set `VITE_API_BASE_URL` to the backend URL and set the Firebase public variables.
5. Deploy the frontend, then update backend `FRONTEND_ORIGINS` to the final frontend URL.
6. Add the frontend domain to Firebase Authentication authorized domains and enable the
   Email/Password and Google providers.
7. For password reset, remember that Firebase sends a secure reset link rather than an OTP. The
   user must exist in Firebase Authentication with Email/Password enabled; Google-only accounts
   do not have a password to reset. Check spam/promotions folders and Firebase Authentication
   email templates if delivery fails.
7. Redeploy the backend after changing CORS and run the smoke tests below.

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
3. Confirm `GET /api/v1/health/database` returns `{"status":"ok","database":"postgres"}`.
4. Sign in with a non-production test account.
5. Create an event, budget, task, and vendor.
6. Generate an AI plan only when Gemini is configured.
7. Review/approve a proposal and download PDF and CSV exports.
8. Confirm a second test account receives no access to the first account's event.

Do not run destructive smoke tests against production data.
