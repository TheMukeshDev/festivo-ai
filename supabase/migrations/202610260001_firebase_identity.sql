-- Firebase Auth owns identities; Supabase PostgreSQL remains the application database.
-- Firebase UIDs are mapped to deterministic UUIDs by the backend. Remove the old
-- auth.users foreign keys so new Firebase identities can create owner-scoped rows
-- while legacy Supabase-owned rows remain unchanged.

do $$
declare
    constraint_record record;
begin
    for constraint_record in
        select
            n.nspname as schema_name,
            c.relname as table_name,
            con.conname as constraint_name
        from pg_constraint con
        join pg_class c on c.oid = con.conrelid
        join pg_namespace n on n.oid = c.relnamespace
        join pg_class referenced_table on referenced_table.oid = con.confrelid
        join pg_namespace referenced_schema on referenced_schema.oid = referenced_table.relnamespace
        where con.contype = 'f'
          and n.nspname = 'public'
          and referenced_schema.nspname = 'auth'
          and referenced_table.relname = 'users'
          and con.conkey is not null
    loop
        execute format(
            'alter table %I.%I drop constraint %I',
            constraint_record.schema_name,
            constraint_record.table_name,
            constraint_record.constraint_name
        );
    end loop;
end
$$;

