# Deployment

Talent Intel CRM runs as two long-lived application processes over shared configuration.

## Processes

### API

Responsibilities:

- accept HTTP control-plane requests
- validate API payloads
- start Temporal workflows
- read projections from Supabase Postgres

Command:

```bash
uvicorn talent_intel_crm.api:app --host 0.0.0.0 --port 8000
```

### Worker

Responsibilities:

- poll the Temporal task queue
- run workflows and activities
- persist state in Supabase Postgres
- mirror operational views into Notion when configured

Command:

```bash
python -m talent_intel_crm.worker
```

## Local container split

Build both process types from the same image:

```bash
docker compose -f deploy/compose.yml up --build
```

Scale workers independently from API capacity:

```bash
docker compose -f deploy/compose.yml up --build --scale worker=2
```

## Runtime variables

Both process types need Temporal connection variables. API reads also need the Supabase DSN.

- `TEMPORAL_TARGET_HOST`
- `TEMPORAL_NAMESPACE`
- `TEMPORAL_API_KEY`
- `TEMPORAL_TASK_QUEUE`
- `SUPABASE_DB_URL`

API protection:

- `TICRM_ADMIN_API_KEY`
- `TICRM_ALLOW_INSECURE_DEV_AUTH=false`

Worker side effects:

- `EMAIL_SEND_WEBHOOK_URL`
- `LINKEDIN_SEND_WEBHOOK_URL`
- `NOTION_MIRROR_*`

## Production split

Deploy `api` and `worker` as separate services from the same image. Do not tie worker availability to HTTP autoscaling: Temporal backlog and activity latency control worker scaling, while request rate controls API scaling.

Run migrations before API/worker rollout:

```bash
ticrm-migrate status
ticrm-migrate apply
```

Container example:

```bash
docker compose --profile ops -f deploy/compose.production.yml run --rm migrate
docker compose -f deploy/compose.production.yml up -d api worker
```

Inject production variables from the platform secrets manager. Use `deploy/production.env.example` only as the variable contract, not as secret storage.

## API keys

- `TICRM_ADMIN_API_KEY` is environment-scoped and required for tenant onboarding and tenant key creation in production.
- Tenant API keys are stored only as SHA-256 hashes in Postgres.
- The raw tenant key is returned only once from `POST /v1/tenants/{tenant_id}/api-keys`.
- Tenant keys can only access candidates, interactions and tenant details owned by that tenant.
