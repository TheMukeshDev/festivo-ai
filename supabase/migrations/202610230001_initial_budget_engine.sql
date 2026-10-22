-- Phase 3: durable events, one budget per event, and planned expenses.
-- Apply with the Supabase CLI or backend/scripts/apply_migrations.py.
-- The current API has no authentication. owner_id is nullable and RLS policies
-- are prepared for a future authenticated ownership model. The backend's
-- service-role connection bypasses RLS, so the API must not be treated as
-- multi-user safe until authentication and owner assignment are implemented.

create table if not exists public.events (
    id uuid primary key,
    owner_id uuid references auth.users (id) on delete cascade,
    name text not null check (length(btrim(name)) between 1 and 100),
    event_type text not null check (length(event_type) between 1 and 50),
    event_date date not null,
    location text not null check (length(btrim(location)) between 1 and 200),
    guest_count integer not null check (guest_count between 1 and 10000),
    budget_amount numeric(12, 2) not null
        check (budget_amount > 0 and budget_amount <= 100000000.00),
    currency text not null default 'INR' check (currency ~ '^[A-Z]{3}$'),
    description text,
    preferences jsonb not null default '[]'::jsonb
        check (jsonb_typeof(preferences) = 'array'),
    event_constraints jsonb not null default '[]'::jsonb
        check (jsonb_typeof(event_constraints) = 'array'),
    created_at timestamptz not null,
    updated_at timestamptz not null,
    check (updated_at >= created_at)
);

comment on table public.events is
    'Celebration events. owner_id is reserved for authenticated ownership.';
comment on column public.events.event_constraints is
    'Event planning constraints; named to avoid the SQL constraints keyword.';

create index if not exists events_owner_id_idx on public.events (owner_id);
create index if not exists events_created_at_idx on public.events (created_at, id);

create table if not exists public.event_budgets (
    id uuid primary key,
    event_id uuid not null unique
        references public.events (id) on delete cascade,
    total_limit numeric(12, 2) not null
        check (total_limit > 0 and total_limit <= 100000000.00),
    currency text not null check (currency ~ '^[A-Z]{3}$'),
    reserve_type text not null default 'percentage'
        check (reserve_type in ('percentage', 'fixed_amount')),
    reserve_value numeric(12, 2) not null default 0
        check (reserve_value >= 0 and reserve_value <= 100000000.00),
    version integer not null default 1 check (version >= 1),
    created_at timestamptz not null,
    updated_at timestamptz not null,
    check (updated_at >= created_at),
    check (
        reserve_type <> 'percentage'
        or (reserve_value >= 0 and reserve_value <= 100)
    ),
    check (
        reserve_type <> 'fixed_amount'
        or reserve_value <= total_limit
    )
);

comment on table public.event_budgets is
    'At most one planned budget per event, protected by optimistic versioning.';

create table if not exists public.budget_expenses (
    id uuid primary key,
    budget_id uuid not null references public.event_budgets (id) on delete cascade,
    category text not null check (length(btrim(category)) between 1 and 80),
    name text not null check (length(btrim(name)) between 1 and 120),
    amount numeric(12, 2) not null
        check (amount > 0 and amount <= 100000000.00),
    amount_status text not null default 'estimated'
        check (amount_status in ('estimated', 'quoted', 'confirmed')),
    notes text check (notes is null or length(notes) <= 500),
    created_at timestamptz not null,
    updated_at timestamptz not null,
    check (updated_at >= created_at)
);

comment on table public.budget_expenses is
    'Planned expense amounts; status describes confidence, not verified payment.';

create index if not exists budget_expenses_budget_created_idx
    on public.budget_expenses (budget_id, created_at, id);

alter table public.events enable row level security;
alter table public.event_budgets enable row level security;
alter table public.budget_expenses enable row level security;

drop policy if exists events_owner_select on public.events;
create policy events_owner_select on public.events
    for select to authenticated
    using (owner_id = auth.uid());

drop policy if exists events_owner_insert on public.events;
create policy events_owner_insert on public.events
    for insert to authenticated
    with check (owner_id = auth.uid());

drop policy if exists events_owner_update on public.events;
create policy events_owner_update on public.events
    for update to authenticated
    using (owner_id = auth.uid())
    with check (owner_id = auth.uid());

drop policy if exists events_owner_delete on public.events;
create policy events_owner_delete on public.events
    for delete to authenticated
    using (owner_id = auth.uid());

drop policy if exists event_budgets_owner_all on public.event_budgets;
create policy event_budgets_owner_all on public.event_budgets
    for all to authenticated
    using (
        exists (
            select 1
            from public.events
            where events.id = event_budgets.event_id
              and events.owner_id = auth.uid()
        )
    )
    with check (
        exists (
            select 1
            from public.events
            where events.id = event_budgets.event_id
              and events.owner_id = auth.uid()
        )
    );

drop policy if exists budget_expenses_owner_all on public.budget_expenses;
create policy budget_expenses_owner_all on public.budget_expenses
    for all to authenticated
    using (
        exists (
            select 1
            from public.event_budgets
            join public.events on events.id = event_budgets.event_id
            where event_budgets.id = budget_expenses.budget_id
              and events.owner_id = auth.uid()
        )
    )
    with check (
        exists (
            select 1
            from public.event_budgets
            join public.events on events.id = event_budgets.event_id
            where event_budgets.id = budget_expenses.budget_id
              and events.owner_id = auth.uid()
        )
    );
