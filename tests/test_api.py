from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from talent_intel_crm import api


@dataclass
class FakeHandle:
    id: str
    result_run_id: str = "run-001"


class FakeTemporalClient:
    async def start_workflow(self, _workflow, _payload, *, id, task_queue):
        assert task_queue == "talent-intel-crm"
        return FakeHandle(id=id)


def test_health_is_open() -> None:
    response = TestClient(api.app).get("/health")

    assert response.status_code == 200
    assert response.json()["success"] is True


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
