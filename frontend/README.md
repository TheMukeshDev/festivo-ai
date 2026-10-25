# Festivo AI Frontend

A React application for planning celebrations: events, budgets, timelines, tasks, vendor
shortlists, vendor comparison, and human-reviewed AI planning suggestions.

## Stack

- React 19, TypeScript, and Vite
- Tailwind CSS v4 with project design tokens
- Radix UI primitives and Lucide icons
- React Router, TanStack Query, React Hook Form, and Zod
- Supabase Auth in the browser
- Vitest and Testing Library

## Prerequisites

- Node.js 20 or newer
- The FastAPI backend running locally or at a reachable URL
- A Supabase project with authentication enabled

## Environment

Copy `.env.example` to `.env.local` and set:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-public-anon-key
```

Only public browser values belong here. Never add a Supabase service-role key, database URL,
Gemini credential, or any backend secret to a `VITE_` variable. AI calls and database access go
through the backend.

The backend must allow the frontend origin through CORS. The default development origin is
`http://localhost:5173`.

## Commands

```bash
npm install
npm run dev
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
```

`npm run build` also runs the TypeScript build.

## Routes

- `/` landing page
- `/sign-in`, `/sign-up`, `/forgot-password`, `/reset-password`, `/auth/callback`
- `/app` dashboard
- `/app/events` event list and creation
- `/app/events/:eventId` overview, edit, budget, timeline, vendors, vendor comparison, AI plan
- `/app/settings`

## Behavior and safety

- Protected routes require an authenticated Supabase session.
- Budget and expense writes send `expected_version`; a `409` refresh prompt prevents blind
  overwrite.
- Event edits submit only changed fields, so unchanged past dates do not block unrelated edits.
- Vendor status changes are limited to transitions allowed by the backend lifecycle.
- AI results are suggestions only. Nothing is saved or applied automatically.
- Missing prices, ratings, or availability are shown as unknown rather than invented.

## Current limitations

- End-to-end authentication and authenticated API flows require real Supabase credentials and a
  configured backend; they are not exercised by the unit tests.
- Proposal generation depends on the backend AI provider configuration. Proposals remain advisory
  until an explicit approval is confirmed by the backend.
- PDF and CSV exports require the authenticated backend export service to be available.
