-- Phase 8: Planning proposals, approval workflow, and export support.
-- Apply with the Supabase CLI or backend/scripts/apply_migrations.py.
-- Backend uses service-role in postgres mode and enforces ownership explicitly.
-- Proposals are advisory; only explicit approval applies supported item actions.

create table if not exists public.planning_proposals (
    id uuid primary key,
    event_id uuid not null references public.events (id) on delete cascade,
    owner_id uuid not null references auth.users (id) on delete cascade,
    proposal_type text not null check (proposal_type in ('ai_planning')),
    title text not null check (length(btrim(title)) between 1 and 200),
    summary text not null check (length(btrim(summary)) between 1 and 6000),
    payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
    status text not null check (status in (
        'pending','partially_approved','approved','rejected','expired'
    )),
    version integer not null default 1 check (version >= 1),
    source_snapshot jsonb not null default '{}'::jsonb
        check (jsonb_typeof(source_snapshot) = 'object'),
    created_at timestamptz not null,
    updated_at timestamptz not null,
    expires_at timestamptz not null,
    approved_at timestamptz,
    rejected_at timestamptz,
    check (updated_at >= created_at),
    check (expires_at >= created_at)
);

comment on table public.planning_proposals is
    'Owner-scoped advisory planning proposals; approval never mutates budgets automatically.';

create index if not exists planning_proposals_owner_event_idx
    on public.planning_proposals (owner_id, event_id);
create index if not exists planning_proposals_event_status_created_idx
    on public.planning_proposals (event_id, status, created_at, id);
create index if not exists planning_proposals_owner_expires_idx
    on public.planning_proposals (owner_id, expires_at);

alter table public.planning_proposals enable row level security;

drop policy if exists planning_proposals_owner_all on public.planning_proposals;
create policy planning_proposals_owner_all on public.planning_proposals
    for all to authenticated
    using (owner_id = auth.uid())
    with check (owner_id = auth.uid());
