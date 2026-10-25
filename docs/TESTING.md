# Festivo AI testing guide

## Backend checks

Run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests scripts
```

The suite uses memory repositories and mocked/injected services by default. Live PostgreSQL tests
remain skipped unless `TEST_SUPABASE_DB_URL` points to an isolated test database:

```powershell
$env:TEST_SUPABASE_DB_URL = "postgresql://..."
.\.venv\Scripts\python.exe -m pytest tests/test_postgres_infrastructure.py -q
```

Never use a production database for tests.

## Frontend checks

Run from `frontend/`:

```powershell
npm ci
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
```

Frontend tests use Vitest, jsdom, and Testing Library. They verify routing, validation, API error
handling, formatting, and core component behavior. Authenticated Supabase flows and real export
downloads require manual verification against a configured development backend.

## Release evidence

Record exact pass/fail/skip counts from the commands above. A passing local build is not evidence
that a live Supabase, Gemini, or deployed-host integration is available.
