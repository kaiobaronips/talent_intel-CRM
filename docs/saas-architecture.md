# Talent Intel CRM SaaS Architecture

## Product shape

Talent Intel CRM is a multi-tenant recruitment SaaS. Each tenant gets isolated configuration, branding, message templates, routing policy and audit history.

## Control plane

- Tenant onboarding
- Billing / plan metadata
- Branding and messaging configuration
- Feature flags
- Compliance and access policy

## Candidate plane

- Ingest
- Enrichment
- Qualification
- Outreach by channel
- Follow-up cadence
- Closure and conversion

## Workflow split

### 1. CandidateIngestWorkflow

Responsibility:
- accept candidate intake from CRM, API or import batch
- normalize the record
- persist source traceability

### 2. CandidateEnrichmentWorkflow

Responsibility:
- fetch external profile data
- validate email and LinkedIn
- enrich company, role, city and seniority

### 3. CandidateQualificationWorkflow

Responsibility:
- score and classify the candidate
- produce routing metadata
- never block send decisions by score

### 4. CandidateOutreachWorkflow

Responsibility:
- determine eligible channels
- build outbound payloads
- route to email, LinkedIn or both

### 5. CandidateFollowUpWorkflow

Responsibility:
- own retry-safe cadences
- schedule follow-ups
- branch by channel and response state

### 6. CandidateClosureWorkflow

Responsibility:
- close completed, converted or exhausted candidates
- freeze the audit trail

### 7. TenantOnboardingWorkflow

Responsibility:
- create tenant defaults
- provision templates and routing rules
- seed branding and policies

## Recommended services

- `api`: public SaaS API
- `worker`: Temporal worker process
- `web`: admin dashboard
- `db`: Postgres
- `audit`: immutable event store
- `connectors`: Supabase Postgres, Gmail, LinkedIn, analytics

## Data model

- `tenant`
- `candidate`
- `interaction`
- `outreach_thread`
- `follow_up_event`
- `audit_event`

## Hard rules

- workflows are deterministic
- all external IO is done in activities
- LLMs can assist on text and classification, not on control flow
- idempotency keys are mandatory for all side effects
- every tenant has isolated config and audit history

## Runtime contract

- The main lifecycle workflow is the default production entrypoint for candidate orchestration.
- `CandidateIngestWorkflow`, `CandidateEnrichmentWorkflow`, `CandidateQualificationWorkflow`, `CandidateOutreachWorkflow`, `CandidateFollowUpWorkflow`, `CandidateClosureWorkflow` and `TenantOnboardingWorkflow` remain available as specialized execution units.
- Activities can run against real webhooks when configured, or fall back to `dry-run` for safe local validation.

## Implementation order

1. Introduce API and tenant model
2. Replace direct side effects with activities
3. Move candidate stages to the workflow split above
4. Add observability and replay-safe retry policies
5. Turn off fragile legacy routers only after parity
