create table if not exists tenant_memberships (
    id uuid primary key default gen_random_uuid(),
    tenant_id text not null references tenants(id) on delete cascade,
    user_id text not null,
    email text not null default '',
    role text not null default 'viewer',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (tenant_id, user_id)
);

create index if not exists idx_tenant_memberships_user
    on tenant_memberships (user_id);

create index if not exists idx_tenant_memberships_tenant_role
    on tenant_memberships (tenant_id, role);
