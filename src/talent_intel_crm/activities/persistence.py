from __future__ import annotations

from typing import Any

from temporalio import activity

from talent_intel_crm.db import (
    append_audit_event,
    append_interaction_row,
    database_url,
    upsert_candidate,
    upsert_tenant,
    upsert_workflow_run,
)
from talent_intel_crm.activities.notion import (
    sync_audit_event_record,
    sync_candidate_record,
    sync_interaction_record,
    sync_tenant_record,
    sync_workflow_run_record,
)
from talent_intel_crm.support import action_result
from talent_intel_crm.telemetry import measure


@activity.defn
def upsert_tenant_record(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.upsert_tenant_record", payload, executed=False)
    result = measure("activity.postgres.upsert_tenant", lambda: upsert_tenant(payload), tenant_id=payload["tenant_id"])
    notion = measure("activity.notion.sync_tenant", lambda: sync_tenant_record(payload, result), tenant_id=payload["tenant_id"])
    return action_result("postgres.upsert_tenant_record", payload, "postgres", True, {"postgres": result, "notion": notion})


@activity.defn
def upsert_candidate_record(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.upsert_candidate_record", payload, executed=False)
    result = measure("activity.postgres.upsert_candidate", lambda: upsert_candidate(payload), tenant_id=payload["tenant_id"])
    notion = measure("activity.notion.sync_candidate", lambda: sync_candidate_record(payload, result), tenant_id=payload["tenant_id"])
    return action_result("postgres.upsert_candidate_record", payload, "postgres", True, {"postgres": result, "notion": notion})


@activity.defn
def append_interaction(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.append_interaction", payload, executed=False)
    result = measure(
        "activity.postgres.append_interaction",
        lambda: append_interaction_row(payload),
        tenant_id=payload["tenant_id"],
        channel=payload.get("channel", ""),
    )
    notion = measure(
        "activity.notion.sync_interaction",
        lambda: sync_interaction_record(payload, result),
        tenant_id=payload["tenant_id"],
        channel=payload.get("channel", ""),
    )
    return action_result("postgres.append_interaction", payload, "postgres", True, {"postgres": result, "notion": notion})


@activity.defn
def record_audit_event(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.record_audit_event", payload, executed=False)
    result = measure("activity.postgres.record_audit_event", lambda: append_audit_event(payload), tenant_id=payload["tenant_id"])
    notion = measure("activity.notion.sync_audit_event", lambda: sync_audit_event_record(payload, result), tenant_id=payload["tenant_id"])
    return action_result("postgres.record_audit_event", payload, "postgres", True, {"postgres": result, "notion": notion})


@activity.defn
def record_workflow_run(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.record_workflow_run", payload, executed=False)
    result = measure(
        "activity.postgres.record_workflow_run",
        lambda: upsert_workflow_run(payload),
        tenant_id=payload["tenant_id"],
        workflow_name=payload["workflow_name"],
        workflow_status=payload["status"],
    )
    notion = measure(
        "activity.notion.sync_workflow_run",
        lambda: sync_workflow_run_record(payload, result),
        tenant_id=payload["tenant_id"],
        workflow_name=payload["workflow_name"],
        workflow_status=payload["status"],
    )
    return action_result("postgres.record_workflow_run", payload, "postgres", True, {"postgres": result, "notion": notion})
