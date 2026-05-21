# Temporal Cloud Bootstrap

## Required environment variables

- `TEMPORAL_TARGET_HOST`
- `TEMPORAL_NAMESPACE`
- `TEMPORAL_API_KEY`
- `TEMPORAL_TASK_QUEUE`

## Optional environment variables

- `TEMPORAL_USE_TLS`
- `TEMPORAL_IDENTITY`

## Connection model

The Python SDK enables TLS automatically when an API key is supplied.
This keeps the bootstrap small and avoids a second TLS code path unless a custom transport is required.

## Boot order

1. Provision namespace in Temporal Cloud
2. Create API key
3. Register the worker on the desired task queue
4. Deploy activities
5. Start the candidate workflows

## Migration policy

- keep n8n as a temporary adapter only where needed
- move each stable side effect into a Temporal activity
- keep all routing and state transitions in workflows
- remove legacy router logic after parity

