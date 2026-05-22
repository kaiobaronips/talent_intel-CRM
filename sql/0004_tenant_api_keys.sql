create table if not exists tenant_api_keys (
    id uuid primary key default gen_random_uuid(),
    tenant_id text not null references tenants(id) on delete cascade,
    key_prefix text not null,
    key_hash text not null unique,
    label text not null default 'default',
    is_active boolean not null default true,
    last_used_at timestamptz,
    created_at timestamptz not null default now(),
    revoked_at timestamptz
);

create index if not exists idx_tenant_api_keys_tenant_active
    on tenant_api_keys (tenant_id, is_active);
