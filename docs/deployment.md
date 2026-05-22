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

- `TICRM_API_KEY`

Worker side effects:

- `EMAIL_SEND_WEBHOOK_URL`
- `LINKEDIN_SEND_WEBHOOK_URL`
- `NOTION_MIRROR_*`

## Production split

Deploy `api` and `worker` as separate services from the same image. Do not tie worker availability to HTTP autoscaling: Temporal backlog and activity latency control worker scaling, while request rate controls API scaling.
