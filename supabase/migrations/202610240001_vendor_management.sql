-- Phase 6: Vendor management, comparison, and booking workflow.
-- Apply with the Supabase CLI or backend/scripts/apply_migrations.py.
-- Backend uses service-role in postgres mode and enforces ownership explicitly.
-- RLS policies are provided for authenticated users.

create table if not exists public.event_vendors (
    id uuid primary key,
    event_id uuid not null references public.events (id) on delete cascade,
    owner_id uuid not null references auth.users (id) on delete cascade,
    name text not null check (length(btrim(name)) between 1 and 120),
    category text not null check (category in (
        'venue','catering','decoration','photography_videography',
        'entertainment_music','makeup_styling','invitations_printing',
        'transportation','equipment_rentals','event_coordination','other'
    )),
    description text check (description is null or length(description) <= 2000),
    contact_name text check (contact_name is null or length(btrim(contact_name)) between 1 and 120),
    email text,
    phone text,
    website_url text,
    service_area text check (service_area is null or length(btrim(service_area)) between 1 and 200),
    price_min numeric(12,2) check (price_min is null or (price_min >= 0 and price_min <= 100000000.00)),
    price_max numeric(12,2) check (price_max is null or (price_max >= 0 and price_max <= 100000000.00)),
    currency text not null check (currency ~ '^[A-Z]{3}$'),
    estimated_cost numeric(12,2) check (estimated_cost is null or (estimated_cost >= 0 and estimated_cost <= 100000000.00)),
    quoted_cost numeric(12,2) check (quoted_cost is null or (quoted_cost >= 0 and quoted_cost <= 100000000.00)),
    final_cost numeric(12,2) check (final_cost is null or (final_cost >= 0 and final_cost <= 100000000.00)),
    pricing_notes text check (pricing_notes is null or length(pricing_notes) <= 1000),
    status text not null check (status in ('discovered','shortlisted','contacted','quoted','selected','booked','rejected','cancelled')),
    rating numeric(2,1) check (rating is null or (rating >= 0 and rating <= 5)),
    notes text check (notes is null or length(notes) <= 2000),
    availability text check (availability is null or length(btrim(availability)) between 1 and 200),
    created_at timestamptz not null,
    updated_at timestamptz not null,
    check (updated_at >= created_at),
    check (price_min is null or price_max is null or price_min <= price_max)
);

comment on table public.event_vendors is
    'Vendors associated with events; owner-scoped and must not be accessible across users.';

create index if not exists event_vendors_owner_event_idx on public.event_vendors (owner_id, event_id);
create index if not exists event_vendors_event_category_idx on public.event_vendors (event_id, category);
create index if not exists event_vendors_event_status_idx on public.event_vendors (event_id, status);

create table if not exists public.vendor_status_history (
    id uuid primary key,
    vendor_id uuid not null references public.event_vendors (id) on delete cascade,
    event_id uuid not null references public.events (id) on delete cascade,
    owner_id uuid not null references auth.users (id) on delete cascade,
    from_status text,
    to_status text not null,
    reason text,
    created_at timestamptz not null
);

create index if not exists vendor_status_history_vendor_idx on public.vendor_status_history (vendor_id, created_at);

alter table public.event_vendors enable row level security;
alter table public.vendor_status_history enable row level security;

drop policy if exists event_vendors_owner_all on public.event_vendors;
create policy event_vendors_owner_all on public.event_vendors
    for all to authenticated
    using (owner_id = auth.uid())
    with check (owner_id = auth.uid());

drop policy if exists vendor_status_history_owner_all on public.vendor_status_history;
create policy vendor_status_history_owner_all on public.vendor_status_history
    for all to authenticated
    using (owner_id = auth.uid())
    with check (owner_id = auth.uid());
