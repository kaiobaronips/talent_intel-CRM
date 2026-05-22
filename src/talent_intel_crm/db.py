from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from talent_intel_crm.support import env


def database_url() -> str:
    return env("SUPABASE_DB_URL") or env("DATABASE_URL")


@contextmanager
def get_connection() -> Iterator[psycopg.Connection[Any]]:
    db_url = database_url()
    if not db_url:
        raise RuntimeError("SUPABASE_DB_URL or DATABASE_URL is required")
    connection = psycopg.connect(db_url, row_factory=dict_row)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def upsert_tenant(payload: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                insert into tenants (
                    id, slug, company_name, tier, primary_domain, timezone, metadata_json
                ) values (
                    %(tenant_id)s, %(slug)s, %(company_name)s, %(tier)s, %(primary_domain)s, %(timezone)s, %(metadata_json)s::jsonb
                )
                on conflict (id) do update set
                    slug = excluded.slug,
                    company_name = excluded.company_name,
                    tier = excluded.tier,
                    primary_domain = excluded.primary_domain,
                    timezone = excluded.timezone,
                    metadata_json = excluded.metadata_json,
                    updated_at = now()
                returning id, slug, company_name, tier, primary_domain, timezone, created_at, updated_at
                """,
                {
                    "tenant_id": payload["tenant_id"],
                    "slug": payload.get("slug") or payload["tenant_id"],
                    "company_name": payload["company_name"],
                    "tier": payload.get("tier", "starter"),
                    "primary_domain": payload.get("primary_domain", ""),
                    "timezone": payload.get("timezone", "America/Sao_Paulo"),
                    "metadata_json": json.dumps(payload.get("metadata", {}), ensure_ascii=False),
                },
            )
            return dict(cur.fetchone() or {})


def tenant_exists(tenant_id: str) -> bool:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select 1 from tenants where id = %s", (tenant_id,))
            return cur.fetchone() is not None


def get_tenant(tenant_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select id, slug, company_name, tier, primary_domain, timezone, metadata_json, created_at, updated_at
                from tenants
                where id = %s
                """,
                (tenant_id,),
            )
            return dict(cur.fetchone() or {})


def upsert_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                insert into candidates (
                    id, tenant_id, external_id, name, city, email, linkedin_url, stage, source_page_id, metadata_json
                ) values (
                    %(candidate_id)s, %(tenant_id)s, %(external_id)s, %(name)s, %(city)s, %(email)s, %(linkedin_url)s, %(stage)s, %(source_page_id)s, %(metadata_json)s::jsonb
                )
                on conflict (id) do update set
                    tenant_id = excluded.tenant_id,
                    external_id = excluded.external_id,
                    name = excluded.name,
                    city = excluded.city,
                    email = excluded.email,
                    linkedin_url = excluded.linkedin_url,
                    stage = excluded.stage,
                    source_page_id = excluded.source_page_id,
                    metadata_json = excluded.metadata_json,
                    updated_at = now()
                returning id, tenant_id, external_id, name, city, email, linkedin_url, stage, created_at, updated_at
                """,
                {
                    "candidate_id": payload["candidate_id"],
                    "tenant_id": payload["tenant_id"],
                    "external_id": payload.get("external_id") or payload["candidate_id"],
                    "name": payload["name"],
                    "city": payload.get("city", ""),
                    "email": payload.get("email", ""),
                    "linkedin_url": payload.get("linkedin_url", ""),
                    "stage": payload["stage"],
                    "source_page_id": payload.get("source_page_id"),
                    "metadata_json": json.dumps(payload.get("metadata", {}), ensure_ascii=False),
                },
            )
            return dict(cur.fetchone() or {})


def get_candidate(candidate_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select id, tenant_id, external_id, name, city, email, linkedin_url, stage, source_page_id, metadata_json, created_at, updated_at
                from candidates
                where id = %s
                """,
                (candidate_id,),
            )
            return dict(cur.fetchone() or {})


def list_candidate_interactions(candidate_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select id, tenant_id, candidate_id, channel, message_type, status, provider_message_id,
                    provider_thread_id, idempotency_key, payload_json, created_at
                from interactions
                where candidate_id = %s
                order by created_at desc
                """,
                (candidate_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def append_interaction_row(payload: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                insert into interactions (
                    tenant_id, candidate_id, channel, message_type, status, provider_message_id, provider_thread_id, idempotency_key, payload_json
                ) values (
                    %(tenant_id)s, %(candidate_id)s, %(channel)s, %(message_type)s, %(status)s, %(provider_message_id)s, %(provider_thread_id)s, %(idempotency_key)s, %(payload_json)s::jsonb
                )
                on conflict (tenant_id, idempotency_key) where idempotency_key <> '' do update set
                    status = excluded.status,
                    provider_message_id = coalesce(excluded.provider_message_id, interactions.provider_message_id),
                    provider_thread_id = coalesce(excluded.provider_thread_id, interactions.provider_thread_id),
                    payload_json = excluded.payload_json
                returning id, tenant_id, candidate_id, channel, message_type, status, idempotency_key, created_at
                """,
                {
                    "tenant_id": payload["tenant_id"],
                    "candidate_id": payload["candidate_id"],
                    "channel": payload.get("channel", ""),
                    "message_type": payload.get("message_type", ""),
                    "status": payload.get("status", "pending"),
                    "provider_message_id": payload.get("provider_message_id"),
                    "provider_thread_id": payload.get("provider_thread_id"),
                    "idempotency_key": payload.get("idempotency_key", ""),
                    "payload_json": json.dumps(payload, ensure_ascii=False),
                },
            )
            return dict(cur.fetchone() or {})


def append_audit_event(payload: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                insert into audit_events (
                    tenant_id, candidate_id, event_type, actor_type, actor_id, payload_json
                ) values (
                    %(tenant_id)s, %(candidate_id)s, %(event_type)s, %(actor_type)s, %(actor_id)s, %(payload_json)s::jsonb
                )
                returning id, tenant_id, candidate_id, event_type, actor_type, actor_id, created_at
                """,
                {
                    "tenant_id": payload["tenant_id"],
                    "candidate_id": payload.get("candidate_id"),
                    "event_type": payload["event_type"],
                    "actor_type": payload.get("actor_type", "system"),
                    "actor_id": payload.get("actor_id", "temporal-worker"),
                    "payload_json": json.dumps(payload.get("payload", {}), ensure_ascii=False),
                },
            )
            return dict(cur.fetchone() or {})


def upsert_workflow_run(payload: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("create unique index if not exists idx_workflow_runs_run_id on workflow_runs (run_id)")
            candidate_id = payload.get("candidate_id")
            if candidate_id:
                cur.execute("select 1 from candidates where id = %s", (candidate_id,))
                if cur.fetchone() is None:
                    candidate_id = None
            cur.execute(
                """
                insert into workflow_runs (
                    tenant_id, candidate_id, workflow_name, workflow_id, run_id, status, payload_json, finished_at
                ) values (
                    %(tenant_id)s, %(candidate_id)s, %(workflow_name)s, %(workflow_id)s, %(run_id)s, %(status)s, %(payload_json)s::jsonb, %(finished_at)s
                )
                on conflict (run_id) do update set
                    tenant_id = excluded.tenant_id,
                    candidate_id = excluded.candidate_id,
                    workflow_name = excluded.workflow_name,
                    workflow_id = excluded.workflow_id,
                    status = excluded.status,
                    payload_json = excluded.payload_json,
                    finished_at = excluded.finished_at
                returning id, tenant_id, candidate_id, workflow_name, workflow_id, run_id, status, started_at, finished_at
                """,
                {
                    "tenant_id": payload["tenant_id"],
                    "candidate_id": candidate_id,
                    "workflow_name": payload["workflow_name"],
                    "workflow_id": payload["workflow_id"],
                    "run_id": payload["run_id"],
                    "status": payload["status"],
                    "payload_json": json.dumps(payload.get("payload", {}), ensure_ascii=False),
                    "finished_at": payload.get("finished_at"),
                },
            )
            return dict(cur.fetchone() or {})
