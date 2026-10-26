# Festivo AI security notes

## Trust boundaries

The browser receives only Firebase web configuration and short-lived ID tokens managed by Firebase
Authentication. The backend owns database access, Firebase Admin credentials, Gemini credentials, budget
calculations, proposal application, and report generation.

The API validates Firebase ID tokens with the Firebase Admin SDK, including signature, issuer,
audience, expiry, and revocation. Repository operations use a deterministic UUID derived from the
verified Firebase UID as the owner filter. Cross-owner resources return not-found responses rather
than confirming existence.

## Database controls

Production requires `STORAGE_BACKEND=postgres`; it cannot silently fall back to memory storage.
Migrations enable RLS on events, budgets, expenses, timelines, tasks, vendors, status history, and
planning proposals. Owner policies use `auth.uid()`. The backend database role is trusted and
therefore application ownership checks remain the primary API authorization boundary.

Apply and verify migrations in an isolated Supabase project before production use. Do not grant
browser clients direct database access as a workaround.

## Secrets

Never put any of these in a `VITE_*` variable, source file, report, or log:

- `SUPABASE_DB_URL`
- Firebase Admin service-account credentials
- `GEMINI_API_KEY`
- JWT signing secrets
- Database passwords

The tracked environment templates contain placeholders only. Local `.env` files, virtual
environments, caches, build output, and dependency directories are ignored by Git.

## Known operational limitations

- Live cross-user and RLS verification requires two isolated Supabase test users and a test database.
- Gemini behavior requires a configured provider credential and verified model identifier.
- There is no deployment, monitoring, or secret rotation automation in this repository.
