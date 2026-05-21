# Temporal Architecture for Talent Intel CRM

## Goal

Replace ad hoc orchestration with durable workflow execution.

## Core layers

- Domain models: candidate, channel, stage, interaction
- Workflows: lifecycle orchestration and cadence control
- Activities: IO to Supabase Postgres, Gmail, LinkedIn, webhooks and analytics
- Worker: long-running process that executes workflow tasks
- Storage: Supabase Postgres as system-of-record

## Mapping from current stack

- n8n router workflows -> Temporal workflows
- Python scripts -> Temporal activities or support utilities
- manual handoffs -> audit events + persisted execution history
- retry logic in scripts -> built-in Temporal retry policies

## Recommended workflow split

1. `CandidateIngestWorkflow`
2. `CandidateEnrichmentWorkflow`
3. `CandidateQualificationWorkflow`
4. `CandidateOutreachWorkflow`
5. `CandidateFollowUpWorkflow`
6. `CandidateClosureWorkflow`

## Operational rules

- LLMs can draft text and classify data
- deterministic code controls execution, retries and idempotency
- every external side effect must live inside an activity
- no direct side effects from workflow code

## Migration order

1. Define domain model and state machine
2. Port enrichment and outreach side effects to activities
3. Wrap the current n8n-triggered flows behind a Temporal adapter
4. Move schedule and follow-up control into Temporal
5. Decommission fragile workflow logic from scripts once parity is achieved
