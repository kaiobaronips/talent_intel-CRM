from __future__ import annotations

import json
from dataclasses import dataclass

from fastapi.testclient import TestClient
import pytest

from talent_intel_crm import api
from talent_intel_crm.auth import APIPrincipal


@dataclass
class FakeHandle:
    id: str
    result_run_id: str = "run-001"


class FakeTemporalClient:
    async def start_workflow(self, _workflow, _payload, *, id, task_queue):
        assert task_queue == "talent-intel-crm"
        return FakeHandle(id=id)


@pytest.fixture(autouse=True)
def admin_principal_override():
    api.app.dependency_overrides[api.require_principal] = lambda: APIPrincipal(role="admin")
    yield
    api.app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def audit_event_stub(monkeypatch):
    monkeypatch.setattr(api, "append_audit_event", lambda payload: {"id": "audit-stub", **payload})
    yield


def test_read_current_principal() -> None:
    response = TestClient(api.app).get("/v1/me")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "role": "admin",
        "tenant_id": "",
        "api_key_id": "",
        "is_admin": True,
        "user_id": "",
        "email": "",
        "auth_method": "api_key",
    }


def test_health_is_open() -> None:
    response = TestClient(api.app).get("/health")

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_readiness_reports_database_state(monkeypatch) -> None:
    monkeypatch.setattr(api, "database_ready", lambda: False)

    response = TestClient(api.app).get("/ready")

    assert response.status_code == 503
    assert response.json()["data"]["postgres"] is False


def test_create_candidate_rejects_missing_channel() -> None:
    response = TestClient(api.app).post(
        "/v1/candidates",
        json={"tenant_id": "tenant-001", "name": "Missing Channel"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "At least one contact channel is required"


def test_create_candidate_infers_channels(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)

    async def connect():
        return FakeTemporalClient()

    monkeypatch.setattr(api, "connect_temporal", connect)
    response = TestClient(api.app).post(
        "/v1/candidates",
        json={
            "tenant_id": "tenant-001",
            "candidate_id": "candidate-001",
            "name": "Candidate One",
            "email": "candidate@example.com",
            "linkedin_url": "https://www.linkedin.com/in/candidate-one",
        },
    )

    assert response.status_code == 202
    assert response.json()["data"]["channels"] == ["email", "linkedin"]
    assert response.json()["data"]["workflow_id"] == "candidate-lifecycle::tenant-001::candidate-001"


def test_list_tenants_route(monkeypatch) -> None:
    monkeypatch.setattr(api, "list_tenants", lambda _page, _limit: {"items": [{"id": "tenant-001"}], "total": 1})

    response = TestClient(api.app).get("/v1/tenants?page=1&limit=10")

    assert response.status_code == 200
    assert response.json()["data"]["items"] == [{"id": "tenant-001"}]
    assert response.json()["data"]["pagination"] == {"page": 1, "limit": 10, "total": 1, "pages": 1}


def test_read_routes_return_projected_records(monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "get_tenant",
        lambda tenant_id: {"id": tenant_id, "company_name": "Tenant One"},
    )
    monkeypatch.setattr(
        api,
        "get_candidate",
        lambda candidate_id: {"id": candidate_id, "tenant_id": "tenant-001", "stage": "contacted"},
    )
    monkeypatch.setattr(
        api,
        "list_candidate_interactions",
        lambda candidate_id: [
            {
                "candidate_id": candidate_id,
                "channel": "email",
                "status": "pending",
                "payload_json": {"name": "Candidate One", "message": {"body": "Mensagem preparada"}},
            }
        ],
    )
    client = TestClient(api.app)

    tenant = client.get("/v1/tenants/tenant-001")
    candidate = client.get("/v1/candidates/candidate-001")
    interactions = client.get("/v1/candidates/candidate-001/interactions")

    assert tenant.status_code == 200
    assert candidate.json()["data"]["stage"] == "contacted"
    interaction = interactions.json()["data"]["items"][0]
    assert interaction["candidate_id"] == "candidate-001"
    assert interaction["candidate_name"] == "Candidate One"
    assert interaction["interaction_status"] == "pending"
    assert interaction["message_sent"] == "Mensagem preparada"


def test_candidate_routes_flatten_agent_metadata(monkeypatch) -> None:
    candidate = {
        "id": "candidate-001",
        "tenant_id": "tenant-001",
        "name": "Candidate One",
        "stage": "qualified",
        "metadata_json": {
            "current_role": "Assessor de Investimentos",
            "score_overall": 86,
            "classification": "A",
        },
    }
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "get_candidate", lambda _candidate_id: candidate)
    monkeypatch.setattr(api, "list_tenant_candidates", lambda _tenant_id, _page, _limit: {"items": [candidate], "total": 1})
    client = TestClient(api.app)

    single = client.get("/v1/candidates/candidate-001")
    listed = client.get("/v1/tenants/tenant-001/candidates")

    assert single.json()["data"]["current_role"] == "Assessor de Investimentos"
    assert single.json()["data"]["score_overall"] == 86
    assert single.json()["data"]["classification"] == "A"
    assert single.json()["data"]["metadata"]["classification"] == "A"
    assert listed.json()["data"]["items"][0]["current_role"] == "Assessor de Investimentos"


def test_read_routes_return_not_found(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_tenant", lambda _tenant_id: {})
    monkeypatch.setattr(api, "get_candidate", lambda _candidate_id: {})
    client = TestClient(api.app)

    assert client.get("/v1/tenants/missing").status_code == 404
    assert client.get("/v1/candidates/missing").status_code == 404
    assert client.get("/v1/candidates/missing/interactions").status_code == 404


def test_create_tenant_key_returns_raw_key_once(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "new_tenant_api_key", lambda: "ticrm_raw-tenant-key")
    monkeypatch.setattr(
        api,
        "insert_tenant_api_key",
        lambda payload: {
            "id": "key-001",
            "tenant_id": payload["tenant_id"],
            "key_prefix": payload["key_prefix"],
            "label": payload["label"],
        },
    )
    client = TestClient(api.app)

    response = client.post("/v1/tenants/tenant-001/api-keys", json={"label": "primary"})

    assert response.status_code == 201
    assert response.json()["data"]["api_key"] == "ticrm_raw-tenant-key"
    assert "key_hash" not in response.json()["data"]["key"]


def test_tenant_membership_routes(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "list_tenant_memberships", lambda _tenant_id: [{"id": "member-001", "role": "admin"}])
    monkeypatch.setattr(api, "upsert_tenant_membership", lambda payload: {"id": "member-001", **payload})
    monkeypatch.setattr(api, "delete_tenant_membership", lambda _tenant_id, membership_id: {"id": membership_id, "role": "viewer"})
    client = TestClient(api.app)

    listed = client.get("/v1/tenants/tenant-001/memberships")
    created = client.post(
        "/v1/tenants/tenant-001/memberships",
        json={"user_id": "user-001", "email": "user@example.com", "role": "recruiter"},
    )
    deleted = client.delete("/v1/tenants/tenant-001/memberships/member-001")

    assert listed.json()["data"]["items"] == [{"id": "member-001", "role": "admin"}]
    assert created.status_code == 201
    assert created.json()["data"]["membership"]["role"] == "recruiter"
    assert deleted.json()["data"]["membership"]["id"] == "member-001"


def test_tenant_membership_resolves_user_by_email(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "find_auth_user_by_email", lambda email: {"id": "user-from-email", "email": email})
    monkeypatch.setattr(api, "upsert_tenant_membership", lambda payload: {"id": "member-001", **payload})

    response = TestClient(api.app).post(
        "/v1/tenants/tenant-001/memberships",
        json={"email": "user@example.com", "role": "viewer"},
    )

    assert response.status_code == 201
    assert response.json()["data"]["membership"]["user_id"] == "user-from-email"
    assert response.json()["data"]["membership"]["email"] == "user@example.com"


def test_tenant_membership_requires_user_or_email(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)

    response = TestClient(api.app).post(
        "/v1/tenants/tenant-001/memberships",
        json={"role": "viewer"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "User ID or e-mail is required"


def test_tenant_membership_email_not_found(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "find_auth_user_by_email", lambda _email: {})

    response = TestClient(api.app).post(
        "/v1/tenants/tenant-001/memberships",
        json={"email": "missing@example.com", "role": "viewer"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Supabase Auth user not found for e-mail"


def test_tenant_membership_delete_not_found(monkeypatch) -> None:
    monkeypatch.setattr(api, "delete_tenant_membership", lambda _tenant_id, _membership_id: {})

    response = TestClient(api.app).delete("/v1/tenants/tenant-001/memberships/missing")

    assert response.status_code == 404


def test_tenant_key_lifecycle_routes(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "list_tenant_api_keys", lambda _tenant_id: [{"id": "key-001", "is_active": True}])
    monkeypatch.setattr(api, "revoke_tenant_api_key", lambda _tenant_id, key_id: {"id": key_id, "is_active": False})
    monkeypatch.setattr(api, "new_tenant_api_key", lambda: "ticrm_rotated-key")
    monkeypatch.setattr(api, "insert_tenant_api_key", lambda payload: {"id": "key-002", "key_prefix": payload["key_prefix"]})
    client = TestClient(api.app)

    listed = client.get("/v1/tenants/tenant-001/api-keys")
    revoked = client.delete("/v1/tenants/tenant-001/api-keys/key-001")
    rotated = client.post("/v1/tenants/tenant-001/api-keys/key-001/rotate", json={"label": "rotated"})

    assert listed.json()["data"]["items"][0]["id"] == "key-001"
    assert revoked.json()["data"]["key"]["is_active"] is False
    assert rotated.status_code == 201
    assert rotated.json()["data"]["api_key"] == "ticrm_rotated-key"


def test_mutating_routes_append_audit_events(monkeypatch) -> None:
    events: list[dict[str, object]] = []

    def capture_audit(payload: dict[str, object]) -> dict[str, object]:
        events.append(payload)
        return {"id": f"audit-{len(events)}", **payload}

    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "append_audit_event", capture_audit)
    monkeypatch.setattr(api, "find_auth_user_by_email", lambda email: {"id": "user-from-email", "email": email})
    monkeypatch.setattr(api, "upsert_tenant_membership", lambda payload: {"id": "member-001", **payload})
    monkeypatch.setattr(api, "new_tenant_api_key", lambda: "ticrm_new-key")
    monkeypatch.setattr(api, "insert_tenant_api_key", lambda payload: {"id": "key-002", "key_prefix": payload["key_prefix"], "label": payload["label"]})
    monkeypatch.setattr(api, "revoke_tenant_api_key", lambda _tenant_id, key_id: {"id": key_id, "key_prefix": "ticrm_old", "label": "old", "is_active": False})

    async def connect():
        return FakeTemporalClient()

    monkeypatch.setattr(api, "connect_temporal", connect)
    client = TestClient(api.app)

    membership = client.post(
        "/v1/tenants/tenant-001/memberships",
        json={"email": "user@example.com", "role": "recruiter"},
    )
    key = client.post("/v1/tenants/tenant-001/api-keys", json={"label": "primary"})
    candidate = client.post(
        "/v1/candidates",
        json={
            "tenant_id": "tenant-001",
            "name": "Candidate One",
            "email": "candidate@example.com",
            "linkedin_url": "https://linkedin.com/in/candidate-one",
        },
    )

    assert membership.status_code == 201
    assert key.status_code == 201
    assert candidate.status_code == 202
    assert [event["event_type"] for event in events] == [
        "tenant_membership.upserted",
        "tenant_api_key.created",
        "candidate.create_requested",
    ]
    assert events[-1]["candidate_id"] is None
    assert events[-1]["payload"]["candidate_id"] == candidate.json()["data"]["candidate_id"]
    assert all("access_token" not in json.dumps(event) and "refresh_token" not in json.dumps(event) for event in events)


def test_tenant_pagination_and_metrics_routes(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "list_tenant_candidates", lambda _tenant_id, _page, _limit: {"items": [{"id": "cand-1"}], "total": 11})
    monkeypatch.setattr(
        api,
        "list_tenant_interactions",
        lambda _tenant_id, _page, _limit: {
            "items": [{"id": "int-1", "channel": "linkedin", "payload_json": {"name": "Candidate One", "message": {"text": "Convite preparado"}}}],
            "total": 1,
        },
    )
    monkeypatch.setattr(api, "list_tenant_audit_events", lambda _tenant_id, _page, _limit: {"items": [{"id": "audit-1"}], "total": 1})
    monkeypatch.setattr(api, "list_tenant_workflow_runs", lambda _tenant_id, _page, _limit: {"items": [{"id": "run-1"}], "total": 1})
    monkeypatch.setattr(
        api,
        "tenant_metrics",
        lambda _tenant_id: {
            "workflow_runs": {"completed": 2, "running": 1, "other": 0},
            "interaction_counts": [{"channel": "email", "status": "pending", "total": 1}],
            "channel_backlog": [{"channel": "email", "pending": 1}],
        },
    )
    client = TestClient(api.app)

    candidates = client.get("/v1/tenants/tenant-001/candidates?page=2&limit=10")
    interactions = client.get("/v1/tenants/tenant-001/interactions?page=1&limit=5")
    workflows = client.get("/v1/tenants/tenant-001/workflow-runs?page=1&limit=5")
    audit = client.get("/v1/tenants/tenant-001/audit-events?page=1&limit=5")
    metrics = client.get("/v1/tenants/tenant-001/metrics")

    assert candidates.json()["data"]["pagination"] == {"page": 2, "limit": 10, "total": 11, "pages": 2}
    assert interactions.json()["data"]["items"][0]["candidate_name"] == "Candidate One"
    assert interactions.json()["data"]["items"][0]["message_sent"] == "Convite preparado"
    assert workflows.json()["data"]["items"] == [{"id": "run-1"}]
    assert audit.json()["data"]["items"] == [{"id": "audit-1"}]
    assert metrics.json()["data"]["channel_backlog"] == [{"channel": "email", "pending": 1}]


def test_update_interaction_status_route(monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "get_interaction",
        lambda interaction_id: {
            "id": interaction_id,
            "tenant_id": "tenant-001",
            "candidate_id": "candidate-001",
            "channel": "email",
            "status": "pending",
            "payload_json": {"name": "Candidate One"},
        },
    )

    def update(interaction_id, status, payload_updates):
        return {
            "id": interaction_id,
            "tenant_id": "tenant-001",
            "candidate_id": "candidate-001",
            "channel": "email",
            "status": status,
            "payload_json": {"name": "Candidate One", **payload_updates},
        }

    monkeypatch.setattr(api, "update_interaction_status", update)
    client = TestClient(api.app)

    response = client.post(
        "/v1/interactions/interaction-001/status",
        json={"status": "replied", "response_received": "Tenho interesse."},
    )

    assert response.status_code == 200
    interaction = response.json()["data"]["interaction"]
    assert interaction["status"] == "replied"
    assert interaction["interaction_status"] == "replied"
    assert interaction["response_received"] == "Tenho interesse."


def test_review_interaction_message_route(monkeypatch) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr(api, "append_audit_event", lambda payload: events.append(payload) or {"id": "audit-1", **payload})
    monkeypatch.setattr(
        api,
        "get_interaction",
        lambda interaction_id: {
            "id": interaction_id,
            "tenant_id": "tenant-001",
            "candidate_id": "candidate-001",
            "channel": "linkedin",
            "status": "pending",
            "payload_json": {"name": "Candidate One"},
        },
    )
    monkeypatch.setattr(
        api,
        "update_interaction_status",
        lambda interaction_id, status, payload_updates: {
            "id": interaction_id,
            "tenant_id": "tenant-001",
            "candidate_id": "candidate-001",
            "channel": "linkedin",
            "status": status,
            "payload_json": {"name": "Candidate One", **payload_updates},
        },
    )

    response = TestClient(api.app).post(
        "/v1/interactions/interaction-001/review",
        json={"status": "approved", "message_sent": "Mensagem revisada.", "decision_note": "Aprovado."},
    )

    assert response.status_code == 200
    interaction = response.json()["data"]["interaction"]
    assert interaction["status"] == "approved"
    assert interaction["message_sent"] == "Mensagem revisada."
    assert events[0]["event_type"] == "interaction.message_reviewed"


def test_sent_interaction_requires_approval(monkeypatch) -> None:
    monkeypatch.setattr(
        api,
        "get_interaction",
        lambda interaction_id: {
            "id": interaction_id,
            "tenant_id": "tenant-001",
            "candidate_id": "candidate-001",
            "channel": "email",
            "status": "pending",
            "payload_json": {},
        },
    )

    response = TestClient(api.app).post("/v1/interactions/interaction-001/status", json={"status": "sent"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Message must be approved before send"


def test_candidate_decision_route(monkeypatch) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr(api, "append_audit_event", lambda payload: events.append(payload) or {"id": "audit-1", **payload})
    monkeypatch.setattr(
        api,
        "get_candidate",
        lambda candidate_id: {
            "id": candidate_id,
            "tenant_id": "tenant-001",
            "name": "Candidate One",
            "stage": "qualified",
            "metadata_json": {},
        },
    )
    monkeypatch.setattr(
        api,
        "update_candidate_state",
        lambda candidate_id, stage, metadata_updates: {
            "id": candidate_id,
            "tenant_id": "tenant-001",
            "name": "Candidate One",
            "stage": stage,
            "metadata_json": metadata_updates,
        },
    )

    response = TestClient(api.app).post(
        "/v1/candidates/candidate-001/decision",
        json={"decision": "paused", "decision_note": "Aguardar novo momento."},
    )

    assert response.status_code == 200
    assert response.json()["data"]["candidate"]["stage"] == "paused"
    assert response.json()["data"]["candidate"]["manual_decision"] == "paused"
    assert events[0]["event_type"] == "candidate.decision_updated"


def test_tenant_preferences_route(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(
        api,
        "update_tenant_metadata",
        lambda tenant_id, metadata_updates: {
            "id": tenant_id,
            "company_name": "Tenant One",
            "metadata_json": metadata_updates,
        },
    )

    response = TestClient(api.app).post(
        "/v1/tenants/tenant-001/preferences",
        json={
            "target_roles": "Executivo de contas",
            "seniority": "Senior",
            "locations": "São Paulo",
            "keywords": "B2B, SaaS",
            "allowed_channels": ["email", "linkedin"],
            "outreach_tone": "Consultivo",
            "daily_contact_limit": 15,
            "max_attempts_per_candidate": 3,
            "follow_up_interval_days": 5,
            "require_manual_approval": True,
            "linkedin_enabled": True,
            "email_enabled": True,
        },
    )

    assert response.status_code == 200
    metadata = response.json()["data"]["tenant"]["metadata_json"]
    assert metadata["ideal_profile"]["target_roles"] == "Executivo de contas"
    assert metadata["mvp_limits"]["daily_contact_limit"] == 15


def test_tenant_message_templates_route(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(
        api,
        "update_tenant_metadata",
        lambda tenant_id, metadata_updates: {
            "id": tenant_id,
            "company_name": "Tenant One",
            "metadata_json": metadata_updates,
        },
    )

    response = TestClient(api.app).post(
        "/v1/tenants/tenant-001/message-templates",
        json={
            "email_initial_subject": "Convite rápido",
            "email_initial_body": "Olá {{nome}}.",
            "email_follow_up_1_subject": "Retomando 1",
            "email_follow_up_1_body": "Retomando meu contato.",
            "email_follow_up_2_subject": "Retomando 2",
            "email_follow_up_2_body": "Segundo follow-up.",
            "email_follow_up_3_subject": "Encerrando contato",
            "email_follow_up_3_body": "Último contato por enquanto.",
            "linkedin_connection_note": "Vamos conectar?",
            "linkedin_initial_message": "Obrigado por conectar.",
            "linkedin_follow_up_message": "Retomando por aqui.",
            "response_follow_up_message": "Obrigado pelo retorno.",
        },
    )

    assert response.status_code == 200
    templates = response.json()["data"]["tenant"]["metadata_json"]["message_templates"]
    assert templates["email_initial_subject"] == "Convite rápido"
    assert templates["email_follow_up_3_subject"] == "Encerrando contato"
    assert templates["linkedin_initial_message"] == "Obrigado por conectar."


def test_apollo_search_reports_missing_configuration(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(
        api,
        "_apollo_people_search",
        lambda _payload: {"configured": False, "people": [], "message": "APOLLO_API_KEY ainda não está configurada no serviço da API."},
    )

    response = TestClient(api.app).post(
        "/v1/tenants/tenant-001/sourcing/apollo/search",
        json={"target_roles": "Executivo de contas", "locations": "São Paulo", "max_candidates": 5},
    )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["configured"] is False
    assert data["created"] == []
    assert "APOLLO_API_KEY" in data["message"]


def test_apollo_search_starts_candidate_lifecycles(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "get_candidate", lambda _candidate_id: {})
    monkeypatch.setattr(
        api,
        "_apollo_people_search",
        lambda _payload: {
            "configured": True,
            "people": [
                {
                    "id": "person-001",
                    "name": "Apollo Candidate",
                    "title": "Account Executive",
                    "city": "São Paulo",
                    "linkedin_url": "https://linkedin.com/in/apollo-candidate",
                    "organization": {"name": "Apollo Corp"},
                }
            ],
        },
    )

    async def connect():
        return FakeTemporalClient()

    monkeypatch.setattr(api, "connect_temporal", connect)

    response = TestClient(api.app).post(
        "/v1/tenants/tenant-001/sourcing/apollo/search",
        json={"target_roles": "Account Executive", "locations": "São Paulo", "seniority": "Senior", "max_candidates": 5},
    )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["configured"] is True
    assert len(data["created"]) == 1
    assert data["created"][0]["channels"] == ["linkedin"]
    assert data["created"][0]["workflow_id"].startswith("candidate-lifecycle::tenant-001::apollo-")


def test_apollo_search_stages_profiles_without_contact_channel(monkeypatch) -> None:
    staged_payloads: list[dict[str, object]] = []
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "get_candidate", lambda _candidate_id: {})
    monkeypatch.setattr(api, "upsert_candidate", lambda payload: staged_payloads.append(payload) or {"id": payload["candidate_id"]})
    monkeypatch.setattr(
        api,
        "_apollo_people_search",
        lambda _payload: {
            "configured": True,
            "people": [
                {
                    "id": "person-002",
                    "title": "Sales Executive",
                    "city": "São Paulo",
                    "organization": {"name": "Preview Corp"},
                }
            ],
        },
    )

    async def connect():
        return FakeTemporalClient()

    monkeypatch.setattr(api, "connect_temporal", connect)

    response = TestClient(api.app).post(
        "/v1/tenants/tenant-001/sourcing/apollo/search",
        json={"target_roles": "Sales Executive", "locations": "São Paulo", "max_candidates": 3},
    )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["created"] == []
    assert len(data["staged"]) == 1
    assert data["staged"][0]["name"] == "Apollo - Preview Corp"
    assert staged_payloads[0]["metadata"]["needs_contact_enrichment"] is True
    assert staged_payloads[0]["metadata"]["recommended_next_step"] == "Conectar Hunter.io para encontrar e validar e-mail profissional."
