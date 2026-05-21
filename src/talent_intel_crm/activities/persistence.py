from __future__ import annotations

from typing import Any

from talent_intel_crm.db import (
    append_audit_event,
    append_interaction_row,
    database_url,
    upsert_candidate,
    upsert_tenant,
)
from talent_intel_crm.support import action_result


def upsert_tenant_record(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.upsert_tenant_record", payload, executed=False)
    result = upsert_tenant(payload)
    return action_result("postgres.upsert_tenant_record", payload, "postgres", True, result)


def upsert_candidate_record(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.upsert_candidate_record", payload, executed=False)
    result = upsert_candidate(payload)
    return action_result("postgres.upsert_candidate_record", payload, "postgres", True, result)


def append_interaction(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.append_interaction", payload, executed=False)
    result = append_interaction_row(payload)
    return action_result("postgres.append_interaction", payload, "postgres", True, result)


def record_audit_event(payload: dict[str, Any]) -> dict[str, Any]:
    if not database_url():
        return action_result("postgres.record_audit_event", payload, executed=False)
    result = append_audit_event(payload)
    return action_result("postgres.record_audit_event", payload, "postgres", True, result)
