-- Phase 5: deterministic event timelines and user-editable tasks.
-- Apply with the Supabase CLI or backend/scripts/apply_migrations.py.
-- The backend service-role connection bypasses RLS; API enforces authenticated ownership.
-- Legacy events.owner_id may be null, but application queries filter by owner_id.

alter table public.events
    add column if not exists timezone text not null default 'Asia/Kolkata'
        check (length(btrim(timezone)) between 1 and 100);

create table if not exists public.event_timelines (
    id uuid primary key,
    event_id uuid not null unique references public.events (id) on delete cascade,
    owner_id uuid not null references auth.users (id) on delete cascade,
    start_date date not null,
    end_date date not null,
    timezone text not null check (length(btrim(timezone)) between 1 and 100),
    generated_at timestamptz not null,
    created_at timestamptz not null,
    updated_at timestamptz not null,
    check (end_date >= start_date),
    check (updated_at >= created_at)
);

comment on table public.event_timelines is
    'At most one planning timeline per event; date boundaries are interpreted in timezone.';

create index if not exists event_timelines_owner_id_idx on public.event_timelines (owner_id);
create index if not exists event_timelines_event_id_idx on public.event_timelines (event_id);

create table if not exists public.event_tasks (
    id uuid primary key,
    event_id uuid not null references public.events (id) on delete cascade,
    owner_id uuid not null references auth.users (id) on delete cascade,
    timeline_id uuid references public.event_timelines (id) on delete set null,
    template_key text,
    title text not null check (length(btrim(title)) between 1 and 200),
    description text check (description is null or length(description) <= 2000),
    status text not null check (status in ('pending', 'in_progress', 'completed', 'cancelled')),
    priority text not null check (priority in ('low', 'medium', 'high', 'urgent')),
    due_at timestamptz,
    assigned_to text check (assigned_to is null or length(btrim(assigned_to)) between 1 and 120),
    estimated_cost numeric(12, 2) check (estimated_cost is null or (estimated_cost >= 0 and estimated_cost <= 100000000.00)),
    actual_cost numeric(12, 2) check (actual_cost is null or (actual_cost >= 0 and actual_cost <= 100000000.00)),
    currency text not null check (currency ~ '^[A-Z]{3}$'),
    sort_order integer not null default 0 check (sort_order >= 0),
    completed_at timestamptz,
    created_at timestamptz not null,
    updated_at timestamptz not null,
    check (updated_at >= created_at),
    check (completed_at is null or completed_at >= created_at),
    check (
        (status = 'completed' and completed_at is not null)
        or (status <> 'completed' and completed_at is null)
    )
);

create or replace function public.validate_event_task_timeline()
returns trigger
language plpgsql
as $$
begin
    if new.timeline_id is not null and not exists (
        select 1
        from public.event_timelines
        where event_timelines.id = new.timeline_id
          and event_timelines.event_id = new.event_id
          and event_timelines.owner_id = new.owner_id
    ) then
        raise exception
            'event_tasks.timeline_id must reference a timeline for the same event and owner'
            using errcode = '23514';
    end if;
    return new;
end;
$$;

drop trigger if exists event_tasks_timeline_consistency on public.event_tasks;
create trigger event_tasks_timeline_consistency
    before insert or update of timeline_id, event_id, owner_id on public.event_tasks
    for each row execute function public.validate_event_task_timeline();

comment on table public.event_tasks is
    'Planning tasks owned by the authenticated user; currency inherited from the event.';

create index if not exists event_tasks_owner_event_idx on public.event_tasks (owner_id, event_id);
create index if not exists event_tasks_event_created_idx on public.event_tasks (event_id, created_at, id);
create index if not exists event_tasks_timeline_idx on public.event_tasks (timeline_id);
create unique index if not exists event_tasks_event_template_unique
    on public.event_tasks (event_id, template_key)
    where template_key is not null;

alter table public.event_timelines enable row level security;
alter table public.event_tasks enable row level security;

drop policy if exists event_timelines_owner_all on public.event_timelines;
create policy event_timelines_owner_all on public.event_timelines
    for all to authenticated
    using (owner_id = auth.uid())
    with check (owner_id = auth.uid());

drop policy if exists event_tasks_owner_all on public.event_tasks;
create policy event_tasks_owner_all on public.event_tasks
    for all to authenticated
    using (owner_id = auth.uid())
    with check (owner_id = auth.uid());
