from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from talent_intel_crm.support import env


logger = logging.getLogger("talent_intel_crm.db")


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


def database_ready() -> bool:
    try:
        with get_connection() as connection:
            with connection.cursor() as cur:
                cur.execute("select 1 as ready")
                return bool(cur.fetchone())
    except Exception as exc:
        logger.warning("database_ready_failed: %s: %s", type(exc).__name__, exc)
        return False


def list_tenants(page: int, limit: int) -> dict[str, Any]:
    offset = (page - 1) * limit
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select count(*) as total from tenants")
            total = int(cur.fetchone()["total"])
            cur.execute(
                """
                select id, slug, company_name, tier, primary_domain, timezone, metadata_json, created_at, updated_at
                from tenants
                order by created_at desc, id desc
                limit %s offset %s
                """,
                (limit, offset),
            )
            return {"items": [dict(row) for row in cur.fetchall()], "total": total}


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


def update_tenant_metadata(tenant_id: str, metadata_updates: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select metadata_json from tenants where id = %s", (tenant_id,))
            existing = cur.fetchone()
            if not existing:
                return {}
            metadata = existing.get("metadata_json") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            metadata.update(metadata_updates)
            cur.execute(
                """
                update tenants
                set metadata_json = %s::jsonb,
                    updated_at = now()
                where id = %s
                returning id, slug, company_name, tier, primary_domain, timezone, metadata_json, created_at, updated_at
                """,
                (json.dumps(metadata, ensure_ascii=False), tenant_id),
            )
            return dict(cur.fetchone() or {})


def upsert_tenant_membership(payload: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                insert into tenant_memberships (tenant_id, user_id, email, role)
                values (%(tenant_id)s, %(user_id)s, %(email)s, %(role)s)
                on conflict (tenant_id, user_id) do update set
                    email = excluded.email,
                    role = excluded.role,
                    updated_at = now()
                returning id, tenant_id, user_id, email, role, created_at, updated_at
                """,
                payload,
            )
            return dict(cur.fetchone() or {})


def list_tenant_memberships(tenant_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select id, tenant_id, user_id, email, role, created_at, updated_at
                from tenant_memberships
                where tenant_id = %s
                order by created_at desc, id desc
                """,
                (tenant_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def find_tenant_membership_by_user(user_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select id, tenant_id, user_id, email, role, created_at, updated_at
                from tenant_memberships
                where user_id = %s
                order by
                    case role
                        when 'owner' then 1
                        when 'admin' then 2
                        when 'recruiter' then 3
                        else 4
                    end,
                    created_at desc
                limit 1
                """,
                (user_id,),
            )
            return dict(cur.fetchone() or {})


def find_auth_user_by_email(email: str) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select id::text as id, email
                from auth.users
                where lower(email) = lower(%s)
                limit 1
                """,
                (email,),
            )
            return dict(cur.fetchone() or {})


def delete_tenant_membership(tenant_id: str, membership_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                delete from tenant_memberships
                where tenant_id = %s and id::text = %s
                returning id, tenant_id, user_id, email, role, created_at, updated_at
                """,
                (tenant_id, membership_id),
            )
            return dict(cur.fetchone() or {})


def insert_tenant_api_key(payload: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                insert into tenant_api_keys (tenant_id, key_prefix, key_hash, label)
                values (%(tenant_id)s, %(key_prefix)s, %(key_hash)s, %(label)s)
                returning id, tenant_id, key_prefix, label, is_active, created_at
                """,
                payload,
            )
            return dict(cur.fetchone() or {})


def find_tenant_api_key(key_hash: str) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                update tenant_api_keys
                set last_used_at = %s
                where key_hash = %s and is_active = true and revoked_at is null
                returning id, tenant_id, key_prefix, label, is_active
                """,
                (datetime.now(timezone.utc), key_hash),
            )
            return dict(cur.fetchone() or {})


def list_tenant_api_keys(tenant_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select id, tenant_id, key_prefix, label, is_active, last_used_at, created_at, revoked_at
                from tenant_api_keys
                where tenant_id = %s
                order by created_at desc
                """,
                (tenant_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def revoke_tenant_api_key(tenant_id: str, api_key_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                update tenant_api_keys
                set is_active = false, revoked_at = now()
                where tenant_id = %s and id::text = %s and is_active = true
                returning id, tenant_id, key_prefix, label, is_active, last_used_at, created_at, revoked_at
                """,
                (tenant_id, api_key_id),
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


def update_candidate_state(candidate_id: str, stage: str, metadata_updates: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata_updates = metadata_updates or {}
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select metadata_json from candidates where id = %s", (candidate_id,))
            existing = cur.fetchone()
            if not existing:
                return {}
            metadata = existing.get("metadata_json") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            metadata.update(metadata_updates)
            cur.execute(
                """
                update candidates
                set stage = %s,
                    metadata_json = %s::jsonb,
                    updated_at = now()
                where id = %s
                returning id, tenant_id, external_id, name, city, email, linkedin_url, stage, source_page_id,
                    metadata_json, created_at, updated_at
                """,
                (stage, json.dumps(metadata, ensure_ascii=False), candidate_id),
            )
            return dict(cur.fetchone() or {})


def list_tenant_candidates(tenant_id: str, page: int, limit: int) -> dict[str, Any]:
    offset = (page - 1) * limit
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select count(*) as total from candidates where tenant_id = %s", (tenant_id,))
            total = int(cur.fetchone()["total"])
            cur.execute(
                """
                select id, tenant_id, external_id, name, city, email, linkedin_url, stage, source_page_id,
                    metadata_json, created_at, updated_at
                from candidates
                where tenant_id = %s
                order by created_at desc, id desc
                limit %s offset %s
                """,
                (tenant_id, limit, offset),
            )
            return {"items": [dict(row) for row in cur.fetchall()], "total": total}


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


def list_tenant_interactions(tenant_id: str, page: int, limit: int) -> dict[str, Any]:
    offset = (page - 1) * limit
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select count(*) as total from interactions where tenant_id = %s", (tenant_id,))
            total = int(cur.fetchone()["total"])
            cur.execute(
                """
                select id, tenant_id, candidate_id, channel, message_type, status, provider_message_id,
                    provider_thread_id, idempotency_key, payload_json, created_at
                from interactions
                where tenant_id = %s
                order by created_at desc, id desc
                limit %s offset %s
                """,
                (tenant_id, limit, offset),
            )
            return {"items": [dict(row) for row in cur.fetchall()], "total": total}


def list_tenant_expandi_interactions(tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select id, tenant_id, candidate_id, channel, message_type, status, provider_message_id,
                    provider_thread_id, idempotency_key, payload_json, created_at
                from interactions
                where tenant_id = %s
                  and channel = 'linkedin'
                  and (
                    payload_json->>'linkedin_provider' = 'expandi'
                    or payload_json->>'provider_target' = 'expandi'
                  )
                order by created_at desc, id desc
                limit %s
                """,
                (tenant_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]


def get_interaction(interaction_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select id, tenant_id, candidate_id, channel, message_type, status, provider_message_id,
                    provider_thread_id, idempotency_key, payload_json, created_at
                from interactions
                where id::text = %s
                """,
                (interaction_id,),
            )
            return dict(cur.fetchone() or {})


def find_linkedin_interaction_for_status(payload: dict[str, Any]) -> dict[str, Any]:
    interaction_id = str(payload.get("interaction_id") or "").strip()
    provider_message_id = str(payload.get("provider_message_id") or payload.get("lead_id") or payload.get("message_id") or payload.get("messenger_id") or "").strip()
    tenant_id = str(payload.get("tenant_id") or "").strip()
    candidate_id = str(payload.get("candidate_id") or payload.get("external_id") or "").strip()

    with get_connection() as connection:
        with connection.cursor() as cur:
            if interaction_id:
                cur.execute(
                    """
                    select id, tenant_id, candidate_id, channel, message_type, status, provider_message_id,
                        provider_thread_id, idempotency_key, payload_json, created_at
                    from interactions
                    where id::text = %s and channel = 'linkedin'
                    """,
                    (interaction_id,),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)

            if provider_message_id:
                cur.execute(
                    """
                    select id, tenant_id, candidate_id, channel, message_type, status, provider_message_id,
                        provider_thread_id, idempotency_key, payload_json, created_at
                    from interactions
                    where channel = 'linkedin'
                      and (
                        provider_message_id = %s
                        or payload_json->>'provider_message_id' = %s
                        or payload_json->>'lead_id' = %s
                        or payload_json->>'messenger_id' = %s
                      )
                    order by created_at desc
                    limit 1
                    """,
                    (provider_message_id, provider_message_id, provider_message_id, provider_message_id),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)

            if tenant_id and candidate_id:
                cur.execute(
                    """
                    select id, tenant_id, candidate_id, channel, message_type, status, provider_message_id,
                        provider_thread_id, idempotency_key, payload_json, created_at
                    from interactions
                    where tenant_id = %s and candidate_id = %s and channel = 'linkedin'
                    order by created_at desc
                    limit 1
                    """,
                    (tenant_id, candidate_id),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)

    return {}


def update_interaction_status(interaction_id: str, status: str, payload_updates: dict[str, Any] | None = None) -> dict[str, Any]:
    payload_updates = payload_updates or {}
    provider_message_id = payload_updates.get("provider_message_id")
    provider_thread_id = payload_updates.get("provider_thread_id")
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select payload_json from interactions where id::text = %s", (interaction_id,))
            existing = cur.fetchone()
            if not existing:
                return {}
            payload = existing.get("payload_json") or {}
            if not isinstance(payload, dict):
                payload = {}
            payload.update(payload_updates)
            payload["status"] = status
            cur.execute(
                """
                update interactions
                set status = %s,
                    provider_message_id = coalesce(%s, provider_message_id),
                    provider_thread_id = coalesce(%s, provider_thread_id),
                    payload_json = %s::jsonb
                where id::text = %s
                returning id, tenant_id, candidate_id, channel, message_type, status, provider_message_id,
                    provider_thread_id, idempotency_key, payload_json, created_at
                """,
                (status, provider_message_id, provider_thread_id, json.dumps(payload, ensure_ascii=False), interaction_id),
            )
            return dict(cur.fetchone() or {})


def tenant_metrics(tenant_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute(
                """
                select
                    count(*) filter (where status = 'Completed') as completed,
                    count(*) filter (where status = 'Running') as running,
                    count(*) filter (where status not in ('Completed', 'Running')) as other
                from workflow_runs
                where tenant_id = %s
                """,
                (tenant_id,),
            )
            workflow_runs = dict(cur.fetchone() or {})
            cur.execute(
                """
                select channel, status, count(*) as total
                from interactions
                where tenant_id = %s
                group by channel, status
                order by channel, status
                """,
                (tenant_id,),
            )
            interaction_counts = [dict(row) for row in cur.fetchall()]
            cur.execute(
                """
                select channel, count(*) as pending
                from interactions
                where tenant_id = %s and status = 'pending'
                group by channel
                order by channel
                """,
                (tenant_id,),
            )
            channel_backlog = [dict(row) for row in cur.fetchall()]
            return {
                "workflow_runs": workflow_runs,
                "interaction_counts": interaction_counts,
                "channel_backlog": channel_backlog,
            }

def list_tenant_workflow_runs(tenant_id: str, page: int, limit: int) -> dict[str, Any]:
    offset = (page - 1) * limit
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select count(*) as total from workflow_runs where tenant_id = %s", (tenant_id,))
            total = int(cur.fetchone()["total"])
            cur.execute(
                """
                select id, tenant_id, candidate_id, workflow_name, workflow_id, run_id, status, payload_json, started_at, finished_at
                from workflow_runs
                where tenant_id = %s
                order by started_at desc, id desc
                limit %s offset %s
                """,
                (tenant_id, limit, offset),
            )
            return {"items": [dict(row) for row in cur.fetchall()], "total": total}


def list_tenant_audit_events(tenant_id: str, page: int, limit: int) -> dict[str, Any]:
    offset = (page - 1) * limit
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select count(*) as total from audit_events where tenant_id = %s", (tenant_id,))
            total = int(cur.fetchone()["total"])
            cur.execute(
                """
                select id, tenant_id, candidate_id, event_type, actor_type, actor_id, payload_json, created_at
                from audit_events
                where tenant_id = %s
                order by created_at desc
                limit %s offset %s
                """,
                (tenant_id, limit, offset),
            )
            return {"items": [dict(row) for row in cur.fetchall()], "total": total}


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
