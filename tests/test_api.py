from __future__ import annotations

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
        lambda candidate_id: [{"candidate_id": candidate_id, "channel": "email"}],
    )
    client = TestClient(api.app)

    tenant = client.get("/v1/tenants/tenant-001")
    candidate = client.get("/v1/candidates/candidate-001")
    interactions = client.get("/v1/candidates/candidate-001/interactions")

    assert tenant.status_code == 200
    assert candidate.json()["data"]["stage"] == "contacted"
    assert interactions.json()["data"]["items"] == [{"candidate_id": "candidate-001", "channel": "email"}]


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


def test_tenant_pagination_and_metrics_routes(monkeypatch) -> None:
    monkeypatch.setattr(api, "tenant_exists", lambda _tenant_id: True)
    monkeypatch.setattr(api, "list_tenant_candidates", lambda _tenant_id, _page, _limit: {"items": [{"id": "cand-1"}], "total": 11})
    monkeypatch.setattr(api, "list_tenant_interactions", lambda _tenant_id, _page, _limit: {"items": [{"id": "int-1"}], "total": 1})
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
    assert interactions.json()["data"]["items"] == [{"id": "int-1"}]
    assert workflows.json()["data"]["items"] == [{"id": "run-1"}]
    assert audit.json()["data"]["items"] == [{"id": "audit-1"}]
    assert metrics.json()["data"]["channel_backlog"] == [{"channel": "email", "pending": 1}]
