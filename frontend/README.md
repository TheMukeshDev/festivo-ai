# Festivo AI Frontend

This directory remains a placeholder through Phase 3. No React application or UI screens are
implemented yet.

## Planned stack

- React and TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Lucide icons
- Recharts for budget visualizations
- Motion for React where interaction benefits from it

## Integration contract

The future frontend will use a configurable API base URL and call the versioned backend routes:

- `GET /health` for a basic availability check.
- `GET /api/v1/health` for versioned API identity.
- `GET /api/v1/config/status` only in development or an authorized operational view.
- Event CRUD under `/api/v1/events`.
- Budget and expense operations under `/api/v1/events/{event_id}/budget`.

The frontend must not receive, store, or request Gemini credentials or `SUPABASE_DB_URL`. AI work and
database access remain server-side. Budget mutations must send the current `expected_version` and
handle `409 conflict` by refreshing the summary before retrying.

Error responses include a stable `error.code`, a safe `error.message`, and optional `error.fields`
entries whose `field` values can be mapped to form controls and announced accessibly. API calls
should surface field errors next to their controls while also providing a summary for assistive
technology.

Browser requests must originate from one of the backend's explicitly configured CORS origins. The
default development origin is `http://localhost:5173`.

Implementation begins in Phase 8 of the project roadmap.
