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
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `RESEND_REPLY_TO_EMAIL`
- `LINKEDIN_SEND_WEBHOOK_URL`
- `LINKEDIN_SEARCH_WEBHOOK_URL`
- `APOLLO_API_KEY`
- `HUNTER_API_KEY`
- `CANDIDATE_ENRICHMENT_WEBHOOK_URL`
- `CANDIDATE_CLASSIFICATION_WEBHOOK_URL`
- `OUTREACH_TEMPLATE_WEBHOOK_URL`
- `LLM_PROVIDER`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
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

## Railway Worker MVP

For MVP, the Temporal worker can run as a dedicated Railway service using the root `Dockerfile` and `railway.toml`.

Start command:

```bash
python -m talent_intel_crm.worker
```

Required Railway variables:

- `SUPABASE_DB_URL`
- `TEMPORAL_TARGET_HOST`
- `TEMPORAL_NAMESPACE`
- `TEMPORAL_API_KEY`
- `TEMPORAL_TASK_QUEUE=talent-intel-crm`
- `TEMPORAL_USE_TLS=true`
- `APOLLO_API_KEY`
- `HUNTER_API_KEY`
- `LLM_PROVIDER=openrouter`
- `OPENAI_API_KEY`
- `OPENAI_MODEL=gpt-4.1-mini`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL=deepseek/deepseek-v4-flash`

Do not configure `NOTION_MIRROR_*` in Railway for the MVP worker unless rate limiting has been handled. Supabase Postgres remains the operational source of truth.

## API keys

- `TICRM_ADMIN_API_KEY` is environment-scoped and required for tenant onboarding and tenant key creation in production.
- Tenant API keys are stored only as SHA-256 hashes in Postgres.
- The raw tenant key is returned only once from `POST /v1/tenants/{tenant_id}/api-keys`.
- Rotate a tenant key with `POST /v1/tenants/{tenant_id}/api-keys/{api_key_id}/rotate`; the old key is revoked before the new raw key is returned.
- Revoke a tenant key with `DELETE /v1/tenants/{tenant_id}/api-keys/{api_key_id}`.
- Tenant keys can only access candidates, interactions and tenant details owned by that tenant.

## Metrics

- Request logs include `X-Request-ID`, path, status and duration.
- Worker activity logs emit structured metric events with `outcome`, duration and relevant tenant/channel/workflow fields.
- `GET /v1/tenants/{tenant_id}/metrics` returns workflow run outcome counts, interaction counts and pending backlog grouped by channel from Postgres.

## Smoke Checks

Use the smoke helper after deploy or before a release cut:

```bash
make smoke-api
```

It verifies:

- `/health`
- `/ready`
- tenant read access
- `metrics`
- `memberships`
- `audit-events`
- `candidates`
- `interactions`

## Web Container

A UI Next.js possui imagem separada em `web/Dockerfile`.

Build local:

```bash
docker build -t talent-intel-crm-web:local ./web
```

Compose local com API, worker e UI:

```bash
docker compose -f deploy/compose.yml up --build api worker web
```

Compose producao espera duas imagens:

- `TICRM_IMAGE`: API/worker Python
- `TICRM_WEB_IMAGE`: UI Next.js

A UI precisa das variaveis:

- `NEXT_PUBLIC_TICRM_API_URL`
- `NEXT_PUBLIC_DEFAULT_TENANT_ID`
- `TICRM_WEB_API_KEY`, repassada como `TICRM_API_KEY` apenas no servidor Next.js
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_SITE_URL`

Para login humano funcionar em producao, o service `web` precisa receber as variaveis publicas do Supabase e a URL publica do app no mesmo ambiente do container, nao apenas via env local de desenvolvimento.
