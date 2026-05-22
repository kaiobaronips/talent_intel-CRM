from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, datetime
from typing import Any

from talent_intel_crm.config import NotionMirrorConfig
from talent_intel_crm.support import action_result


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


def _rich_text(value: str) -> dict[str, Any]:
    return {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": value[:2000]},
            }
        ]
    }


def _title(value: str) -> dict[str, Any]:
    return {
        "title": [
            {
                "type": "text",
                "text": {"content": value[:2000]},
            }
        ]
    }


def _date(value: Any) -> dict[str, Any]:
    iso = _iso(value)
    return {"date": {"start": iso}} if iso else {"date": None}


def _email(value: str) -> dict[str, Any]:
    return {"email": value or None}


def _phone(value: str) -> dict[str, Any]:
    return {"phone_number": value or None}


def _url(value: str) -> dict[str, Any]:
    return {"url": value or None}


def _select(value: str) -> dict[str, Any]:
    return {"select": {"name": value}} if value else {"select": None}


def _status(value: str) -> dict[str, Any]:
    return {"status": {"name": value}} if value else {"status": None}


def _multi_select(values: list[str]) -> dict[str, Any]:
    options = [{"name": item} for item in values if item]
    return {"multi_select": options}


def _request(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    config = NotionMirrorConfig()
    if not config.api_token:
        raise RuntimeError("NOTION_MIRROR_API_TOKEN or NOTION_API_TOKEN is required")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"https://api.notion.com{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {config.api_token}",
            "Content-Type": "application/json",
            "Notion-Version": config.api_version,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        raise RuntimeError(f"Notion API {method} {path} failed: {exc.code} {raw}") from exc


def _find_page_id(data_source_id: str, property_name: str, property_value: str) -> str:
    payload = {
        "filter": {
            "property": property_name,
            "rich_text": {"equals": property_value},
        },
        "page_size": 1,
    }
    result = _request(f"/v1/data_sources/{data_source_id}/query", "POST", payload)
    rows = result.get("results", [])
    return rows[0]["id"] if rows else ""


def _upsert_page(
    *,
    data_source_id: str,
    external_property_name: str,
    external_property_value: str,
    properties: dict[str, Any],
) -> dict[str, Any]:
    page_id = _find_page_id(data_source_id, external_property_name, external_property_value)
    payload = {"properties": properties}
    if page_id:
        return _request(f"/v1/pages/{page_id}", "PATCH", payload)
    payload["parent"] = {"data_source_id": data_source_id}
    return _request("/v1/pages", "POST", payload)


def sync_tenant_record(payload: dict[str, Any], postgres_result: dict[str, Any]) -> dict[str, Any]:
    config = NotionMirrorConfig()
    if not config.enabled:
        return action_result("notion.sync_tenant_record", payload, executed=False)
    properties = {
        "Name": _title(payload["company_name"]),
        "Tenant ID": _rich_text(payload["tenant_id"]),
        "Status": _status("Active"),
        "Primary Contact": _rich_text(payload.get("primary_contact", "")),
        "Contact Email": _email(payload.get("contact_email", "")),
        "Plan": _select((payload.get("tier") or "starter").capitalize()),
        "Created At": _date(postgres_result.get("created_at")),
        "Updated At": _date(postgres_result.get("updated_at")),
        "Mirror Status": _status("Synced"),
    }
    result = _upsert_page(
        data_source_id=config.tenants_data_source_id,
        external_property_name="Tenant ID",
        external_property_value=payload["tenant_id"],
        properties=properties,
    )
    return action_result("notion.sync_tenant_record", payload, "notion", True, result)


def sync_candidate_record(payload: dict[str, Any], postgres_result: dict[str, Any]) -> dict[str, Any]:
    config = NotionMirrorConfig()
    if not config.enabled:
        return action_result("notion.sync_candidate_record", payload, executed=False)
    metadata = payload.get("metadata", {})
    properties = {
        "Name": _title(payload["name"]),
        "Tenant ID": _rich_text(payload["tenant_id"]),
        "Primary Email": _email(payload.get("email", "")),
        "Primary Phone": _phone(metadata.get("phone", "")),
        "LinkedIn URL": _url(payload.get("linkedin_url", "")),
        "City": _rich_text(payload.get("city", "")),
        "State": _rich_text(metadata.get("state", "")),
        "Current Role": _rich_text(metadata.get("current_role", "")),
        "Current Company": _rich_text(metadata.get("current_company", "")),
        "Target Profile": _select(metadata.get("target_profile", "Other")),
        "Seniority": _select(metadata.get("seniority", "")),
        "Certifications": _multi_select(metadata.get("certifications", [])),
        "Score Overall": {"number": metadata.get("score_overall")},
        "Classification": _select(metadata.get("classification", "")),
        "Created At": _date(postgres_result.get("created_at")),
        "Updated At": _date(postgres_result.get("updated_at")),
        "Mirror Status": _status("Synced"),
    }
    result = _upsert_page(
        data_source_id=config.candidates_data_source_id,
        external_property_name="Tenant ID",
        external_property_value=payload["tenant_id"],
        properties={
            **properties,
            "Tenant ID": _rich_text(f'{payload["tenant_id"]}:{payload["candidate_id"]}'),
        },
    )
    return action_result("notion.sync_candidate_record", payload, "notion", True, result)


def sync_interaction_record(payload: dict[str, Any], postgres_result: dict[str, Any]) -> dict[str, Any]:
    config = NotionMirrorConfig()
    if not config.enabled:
        return action_result("notion.sync_interaction_record", payload, executed=False)
    properties = {
        "Name": _title(f'{payload.get("name", payload["candidate_id"])} - {payload.get("channel", "").title()}'),
        "Tenant ID": _rich_text(payload["tenant_id"]),
        "Candidate ID": _rich_text(payload["candidate_id"]),
        "Channel": _select((payload.get("channel") or "").capitalize()),
        "Interaction": _select(payload.get("interaction", "Queued")),
        "Next Action": _select(payload.get("next_action", "Awaiting execution")),
        "Status": _status(payload.get("status", "Pending").capitalize()),
        "Message Sent": _rich_text(payload.get("message_sent", "")),
        "Response": _rich_text(payload.get("response", "")),
        "Occurred At": _date(postgres_result.get("created_at")),
        "Mirror Status": _status("Synced"),
    }
    result = _upsert_page(
        data_source_id=config.interactions_data_source_id,
        external_property_name="Candidate ID",
        external_property_value=f'{payload["candidate_id"]}:{postgres_result.get("id", "")}',
        properties={
            **properties,
            "Candidate ID": _rich_text(f'{payload["candidate_id"]}:{postgres_result.get("id", "")}'),
        },
    )
    return action_result("notion.sync_interaction_record", payload, "notion", True, result)


def sync_workflow_run_record(payload: dict[str, Any], postgres_result: dict[str, Any]) -> dict[str, Any]:
    config = NotionMirrorConfig()
    if not config.enabled:
        return action_result("notion.sync_workflow_run_record", payload, executed=False)
    properties = {
        "Name": _title(payload["workflow_name"]),
        "Tenant ID": _rich_text(payload["tenant_id"]),
        "Workflow": _select(payload["workflow_name"]),
        "Run ID": _rich_text(payload["run_id"]),
        "Status": _status(payload["status"]),
        "Started At": _date(postgres_result.get("started_at")),
        "Finished At": _date(postgres_result.get("finished_at")),
        "Error": _rich_text(payload.get("error", "")),
        "Mirror Status": _status("Synced"),
    }
    result = _upsert_page(
        data_source_id=config.workflow_runs_data_source_id,
        external_property_name="Run ID",
        external_property_value=payload["run_id"],
        properties=properties,
    )
    return action_result("notion.sync_workflow_run_record", payload, "notion", True, result)


def sync_audit_event_record(payload: dict[str, Any], postgres_result: dict[str, Any]) -> dict[str, Any]:
    config = NotionMirrorConfig()
    if not config.enabled:
        return action_result("notion.sync_audit_event_record", payload, executed=False)
    properties = {
        "Name": _title(payload["event_type"]),
        "Tenant ID": _rich_text(payload["tenant_id"]),
        "Entity Type": _select(payload.get("entity_type", "System")),
        "Entity ID": _rich_text(payload.get("entity_id") or payload.get("candidate_id", "")),
        "Event Type": _rich_text(payload["event_type"]),
        "Severity": _select(payload.get("severity", "Info")),
        "Occurred At": _date(postgres_result.get("created_at")),
        "Payload Summary": _rich_text(json.dumps(payload.get("payload", {}), ensure_ascii=False)[:2000]),
        "Mirror Status": _status("Synced"),
    }
    result = _upsert_page(
        data_source_id=config.audit_events_data_source_id,
        external_property_name="Entity ID",
        external_property_value=f'{payload.get("event_type")}:{postgres_result.get("id", "")}',
        properties={
            **properties,
            "Entity ID": _rich_text(f'{payload.get("event_type")}:{postgres_result.get("id", "")}'),
        },
    )
    return action_result("notion.sync_audit_event_record", payload, "notion", True, result)
