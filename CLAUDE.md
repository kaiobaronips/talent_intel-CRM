# Talent Intel CRM

Multi-tenant recruitment CRM. Next.js 16 (App Router) frontend + Python FastAPI backend + Supabase Auth/PostgreSQL.

## Before starting

Read `HANDOFF.md` in the project root for current state, pending tasks, and context from the last session.

## Key paths

- Frontend: `web/`
- Backend: `src/talent_intel_crm/`
- Scripts: `scripts/`
- Migrations: `migrations/`

## Conventions

- Language: pt-BR for UI, English for code/commits.
- Auth: Supabase Auth (email + Google OAuth). Session via httpOnly cookie.
- API: JWT validated with `SUPABASE_JWT_SECRET`. Multi-tenant via `tenant_memberships`.
- Env files: `.env` (backend), `web/.env.local` (frontend) — both gitignored.
