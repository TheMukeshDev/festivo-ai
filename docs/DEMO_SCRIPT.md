# Festivo AI demo script

This is a realistic 2–3 minute script. Use a configured development backend and test account; do
not present mocked or unavailable provider responses as live results.

- **0:00–0:15** — Introduce Festivo AI as a workspace for turning an event brief into an editable
  budget, timeline, vendor shortlist, and reviewable AI suggestions.
- **0:15–0:35** — Sign in and create a wedding, birthday, college, or community event with date,
  guests, location, budget, currency, and constraints.
- **0:35–1:00** — Open Budget. Set the reserve, add an estimated or quoted expense, and show that
  totals and remaining amounts come from the backend's deterministic calculation.
- **1:00–1:20** — Generate the timeline, review tasks, change a priority/status, and show the
  distinction between completed planning work and external vendor delivery.
- **1:20–1:40** — Add vendors, record quote/rating/availability data, shortlist a vendor, and open
  the comparison view. Call out incomplete or incompatible quote data instead of inventing values.
- **1:40–2:05** — Request the AI plan when Gemini is configured. Explain that the output is
  validated, advisory, and not persisted as a decision until explicit proposal approval.
- **2:05–2:25** — Open Proposals, review individual suggestions, approve or reject eligible items,
  and show the refreshed tasks/budget state.
- **2:25–2:45** — Download the PDF or CSV report and explain that exports are authenticated and
  generated from authoritative backend records.
- **2:45–3:00** — Briefly explain Supabase Auth/JWT verification, owner-scoped access, PostgreSQL/RLS,
  deterministic money calculations, and the React/FastAPI boundary.
