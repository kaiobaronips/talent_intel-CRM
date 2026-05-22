alter table interactions
    add column if not exists idempotency_key text not null default '';

create unique index if not exists idx_interactions_tenant_idempotency
    on interactions (tenant_id, idempotency_key)
    where idempotency_key <> '';
