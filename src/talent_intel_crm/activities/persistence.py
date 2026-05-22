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


@activity.defn
def upsert_tenant_record(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.upsert_tenant_record", payload, executed=False)
    result = upsert_tenant(payload)
    notion = sync_tenant_record(payload, result)
    return action_result("postgres.upsert_tenant_record", payload, "postgres", True, {"postgres": result, "notion": notion})


@activity.defn
def upsert_candidate_record(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.upsert_candidate_record", payload, executed=False)
    result = upsert_candidate(payload)
    notion = sync_candidate_record(payload, result)
    return action_result("postgres.upsert_candidate_record", payload, "postgres", True, {"postgres": result, "notion": notion})


@activity.defn
def append_interaction(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.append_interaction", payload, executed=False)
    result = append_interaction_row(payload)
    notion = sync_interaction_record(payload, result)
    return action_result("postgres.append_interaction", payload, "postgres", True, {"postgres": result, "notion": notion})


@activity.defn
def record_audit_event(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.record_audit_event", payload, executed=False)
    result = append_audit_event(payload)
    notion = sync_audit_event_record(payload, result)
    return action_result("postgres.record_audit_event", payload, "postgres", True, {"postgres": result, "notion": notion})


@activity.defn
def record_workflow_run(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.record_workflow_run", payload, executed=False)
    result = upsert_workflow_run(payload)
    notion = sync_workflow_run_record(payload, result)
    return action_result("postgres.record_workflow_run", payload, "postgres", True, {"postgres": result, "notion": notion})
