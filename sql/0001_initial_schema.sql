create extension if not exists pgcrypto;

create table if not exists tenants (
    id text primary key,
    slug text not null unique,
    company_name text not null,
    tier text not null default 'starter',
    primary_domain text not null default '',
    timezone text not null default 'America/Sao_Paulo',
    metadata_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists candidates (
    id text primary key,
    tenant_id text not null references tenants(id) on delete cascade,
    external_id text not null,
    name text not null,
    city text not null default '',
    email text not null default '',
    linkedin_url text not null default '',
    stage text not null default 'ingested',
    source_page_id text,
    metadata_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (tenant_id, external_id)
);

create table if not exists candidate_channels (
    id uuid primary key default gen_random_uuid(),
    candidate_id text not null references candidates(id) on delete cascade,
    channel_type text not null,
    channel_value text not null,
    is_primary boolean not null default false,
    is_valid boolean not null default true,
    created_at timestamptz not null default now(),
    unique (candidate_id, channel_type, channel_value)
);

create table if not exists interactions (
    id uuid primary key default gen_random_uuid(),
    tenant_id text not null references tenants(id) on delete cascade,
    candidate_id text not null references candidates(id) on delete cascade,
    channel text not null,
    message_type text not null,
    status text not null default 'pending',
    provider_message_id text,
    provider_thread_id text,
    payload_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists outreach_threads (
    id uuid primary key default gen_random_uuid(),
    tenant_id text not null references tenants(id) on delete cascade,
    candidate_id text not null references candidates(id) on delete cascade,
    channel text not null,
    external_thread_id text,
    last_message_at timestamptz,
    created_at timestamptz not null default now(),
    unique (tenant_id, candidate_id, channel)
);

create table if not exists workflow_runs (
    id uuid primary key default gen_random_uuid(),
    tenant_id text not null references tenants(id) on delete cascade,
    candidate_id text references candidates(id) on delete set null,
    workflow_name text not null,
    workflow_id text not null,
    run_id text not null,
    status text not null,
    payload_json jsonb not null default '{}'::jsonb,
    started_at timestamptz not null default now(),
    finished_at timestamptz
);

create table if not exists audit_events (
    id uuid primary key default gen_random_uuid(),
    tenant_id text not null references tenants(id) on delete cascade,
    candidate_id text references candidates(id) on delete set null,
    event_type text not null,
    actor_type text not null default 'system',
    actor_id text not null default 'temporal-worker',
    payload_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_candidates_tenant_stage on candidates (tenant_id, stage);
create index if not exists idx_candidates_email on candidates (tenant_id, email);
create index if not exists idx_candidates_linkedin on candidates (tenant_id, linkedin_url);
create index if not exists idx_interactions_candidate_created on interactions (candidate_id, created_at desc);
create index if not exists idx_audit_events_tenant_created on audit_events (tenant_id, created_at desc);
create index if not exists idx_workflow_runs_candidate on workflow_runs (candidate_id, started_at desc);
