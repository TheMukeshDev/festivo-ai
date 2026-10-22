# Festivo AI

Festivo AI is a GenAI-powered event planning assistant for weddings, birthdays, college
celebrations, and community events. It is being built for PromptWars Virtual Challenge 5:
Celebration & Event Planner.

## Problem statement

Planning an event requires juggling a budget, a timeline, vendors, tasks, menus, themes, and
contingency options. These decisions are interdependent: changing a budget limit can invalidate
vendor bookings and shift the event timeline. Generic chat interfaces are poor at preserving these
constraints and turning advice into an editable plan.

## Project objective

Build an accessible planning assistant that produces and maintains an event plan containing:

- A budget breakdown and spending limits.
- An adaptive timeline and actionable tasks.
- Vendor checklists and booking status.
- AI-generated themes, menu ideas, and lower-cost alternatives.
- Editable plans and downloadable summaries.

## Current implementation

Phases 1-3 are implemented:

1. Secure FastAPI foundation, validation, safe errors, configuration, and tests.
2. Validated event CRUD with timezone-aware date policy and deterministic pagination.
3. Decimal-safe budget planning, planned expenses, optimistic concurrency, Supabase PostgreSQL
   repositories, and versioned SQL migrations.

Phase 4 has not been started. There is no timeline engine, vendor workflow, AI generation, or
frontend yet. Authentication is also still outstanding; see the security limitations in
[backend/README.md](backend/README.md).

## Architecture overview

```text
festivo-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Health, event, and budget routes
│   │   ├── core/            # Settings, clock, money rules, safe errors
│   │   ├── db/              # psycopg connection boundary
│   │   ├── models/          # Immutable event and budget domain models
│   │   ├── repositories/    # Memory and PostgreSQL persistence
│   │   ├── schemas/         # Pydantic request/response contracts
│   │   ├── services/        # Event and budget use cases/calculations
│   │   └── main.py          # ASGI app factory and storage selection
│   ├── scripts/             # Transactional migration runner
│   ├── tests/               # Deterministic unit, API, and security tests
│   └── requirements.txt     # Exact validated dependency set
├── frontend/                # Documented placeholder
├── supabase/migrations/     # Versioned PostgreSQL/RLS migration
├── docs/architecture.md     # Design, security, testing, and deployment notes
└── README.md
```

The backend serves `/health`, `/api/v1/health`, `/api/v1/config/status`, event CRUD, and nested
budget/expense routes. Event and budget data use process-local memory by default for development and
tests. Production requires Supabase PostgreSQL through a server-only `SUPABASE_DB_URL`.

## Technology stack

Backend:

- Python 3.15.0 (validated interpreter)
- FastAPI, Pydantic v2, and Pydantic Settings
- psycopg 3 with binary wheels for direct PostgreSQL access
- Uvicorn as the local ASGI server
- pytest with FastAPI TestClient
- Ruff for linting and formatting

Planned AI provider: Google Gemini, configured through `LLM_PROVIDER` and `LLM_MODEL`. Gemini remains
disabled and is not integrated in Phase 3. No live provider call is made by the application or tests.

Planned frontend: React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Lucide icons, Recharts, and
Motion for React.

## Development roadmap

1. Secure backend foundation, architecture, testing, and validation. **Done**
2. Event planning domain model and persistence boundary. **Done**
3. Budget engine, planned expenses, and Supabase persistence. **Done**
4. Adaptive timeline and task engine.
5. Vendor checklists and booking lifecycle.
6. Gemini provider integration and plan-generation workflows.
7. Plan editing, versioning, and regeneration safeguards.
8. Frontend foundation and accessible event intake experience.
9. Planning dashboard, task views, and budget visualizations.
10. Export, accessibility validation, performance, and deployment hardening.

## Quick start

For memory-backed local development:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Memory storage disappears on restart. To use Supabase PostgreSQL, set `STORAGE_BACKEND=postgres`,
configure `SUPABASE_DB_URL` as a server-side secret, and apply the migration:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\apply_migrations.py
```

A live Supabase project was configured manually for Phase 3 verification; credentials and project
details are not committed. The schema, live integration test, and API-to-database smoke test passed.
Follow [backend/README.md](backend/README.md) and [supabase/README.md](supabase/README.md) before
production use; authentication and browser-facing RLS remain unfinished.

Run checks:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check app tests scripts
.\.venv\Scripts\ruff.exe format --check app tests scripts
```

See [docs/architecture.md](docs/architecture.md) for design decisions, budget formulas, concurrency,
database safety, and unresolved risks.
