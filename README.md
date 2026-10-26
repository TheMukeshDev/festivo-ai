# Festivo AI

Festivo AI is a GenAI-powered event planning assistant for weddings, birthdays, college
celebrations, and community events. It turns an event brief into an editable budget, timeline,
vendor checklist, and AI-generated improvement proposals while preserving explicit user approval.

## Current implementation

The backend is at version **0.8.0** and includes:

- Secure FastAPI foundation with strict validation, safe errors, explicit CORS, and versioned routes.
- Firebase ID-token authentication and owner-scoped event access.
- Event CRUD with timezone-aware date policy and deterministic pagination.
- Decimal-safe budget planning, planned expenses, and optimistic concurrency.
- Deterministic timeline generation and task lifecycle management.
- Vendor checklists, booking status, pricing fields, and comparison.
- Gemini-backed AI planning with validated structured output and safe provider error mapping.
- Persisted planning proposals with stale-snapshot detection, explicit approval/rejection,
  resumable partial approval, idempotent task application, and advisory recommendations.
- Owner-scoped downloadable PDF and CSV event reports.
- Memory and Supabase PostgreSQL repositories with versioned SQL migrations and RLS policies.

The React client lives in [`frontend/`](frontend/README.md). See [`backend/README.md`](backend/README.md)
for backend setup, configuration, endpoints, and security behavior.

## Release documentation

- [Deployment guide](docs/DEPLOYMENT.md)
- [Testing guide](docs/TESTING.md)
- [Security notes](docs/SECURITY.md)
- [Demo script](docs/DEMO_SCRIPT.md)
- [Submission checklist](docs/SUBMISSION_CHECKLIST.md)

## Architecture

```text
festivo-ai/
|-- backend/
|   |-- app/
|   |   |-- api/v1/          # Health, events, budgets, timelines, tasks, vendors,
|   |   |                    # proposals, AI planning, and exports
|   |   |-- core/            # Settings, auth, clock, money, safe errors
|   |   |-- db/              # psycopg connection boundary
|   |   |-- models/          # Immutable domain models
|   |   |-- repositories/    # Memory and PostgreSQL persistence
|   |   |-- schemas/         # Strict Pydantic HTTP contracts
|   |   |-- services/        # Domain use cases and AI/report services
|   |   `-- main.py          # ASGI app factory and storage/auth wiring
|   |-- scripts/             # Transactional migration runner
|   |-- tests/               # Unit, API, security, migration, and integration tests
|   `-- requirements.txt     # Exact validated dependency set
|-- frontend/                # React/TypeScript client
|-- supabase/migrations/     # Versioned PostgreSQL schema and RLS migrations
|-- docs/architecture.md     # Design decisions and known limitations
`-- README.md
```

Event, budget, timeline, task, vendor, and proposal data use process-local memory by default for
development and tests. Production requires Supabase PostgreSQL through a server-only
`SUPABASE_DB_URL`. The API fails closed when Supabase JWT verification is not configured.

## Technology stack

Backend:

- Python 3.15 (validated interpreter)
- FastAPI, Pydantic v2, and Pydantic Settings
- psycopg 3 for direct PostgreSQL access
- Google Gemini through `google-genai`
- ReportLab for PDF exports
- Firebase Admin SDK for server-side ID-token verification
- pytest with FastAPI TestClient
- Ruff for linting

Frontend: React, TypeScript, Vite, Tailwind CSS, React Query, React Router, and related UI tooling.

## Quick start

For memory-backed local development:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The health and configuration routes start without credentials, but protected product routes require a
valid Firebase ID token. Configure `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, and
`FIREBASE_PRIVATE_KEY` in `backend/.env`. Do not commit real credentials.

Memory storage disappears on restart. To use Supabase PostgreSQL, set `STORAGE_BACKEND=postgres`,
configure `SUPABASE_DB_URL` as a server-side secret, and apply migrations:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\apply_migrations.py
```

## Checks

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests scripts
```

From `frontend/`:

```powershell
npm run lint
npm run typecheck
npm test
```

Live Supabase integration tests are skipped unless `TEST_SUPABASE_DB_URL` points to an isolated test
database. Never point it at production data.

See [docs/architecture.md](docs/architecture.md) for design decisions, security boundaries, and
known limitations. Live Supabase, Gemini, and deployed-host checks require credentials and are not
represented as complete by the local test suite.
