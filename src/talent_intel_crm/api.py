from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from temporalio.exceptions import WorkflowAlreadyStartedError

from talent_intel_crm.auth import APIPrincipal, api_key_prefix, authorize_tenant, hash_api_key, new_tenant_api_key, require_admin, require_principal
from talent_intel_crm.client import connect_temporal
from talent_intel_crm.config import TemporalConfig
from talent_intel_crm.db import (
    database_ready,
    get_candidate,
    get_tenant,
    insert_tenant_api_key,
    list_candidate_interactions,
    list_tenant_api_keys,
    list_tenant_candidates,
    list_tenant_interactions,
    revoke_tenant_api_key,
    tenant_exists,
    tenant_metrics,
)
from talent_intel_crm.domain import CandidateChannel, CandidateStage, TenantTier
from talent_intel_crm.workflows import CandidateLifecycleWorkflow, TenantOnboardingWorkflow


app = FastAPI(
    title="Talent Intel CRM API",
    version="0.1.0",
    description="HTTP control plane for tenant onboarding and candidate lifecycle orchestration.",
)
logger = logging.getLogger("talent_intel_crm.api")


@app.middleware("http")
async def request_observability(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    started_at = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "http_request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
        },
    )
    return response


class TenantCreateRequest(BaseModel):
    tenant_id: str = Field(min_length=2, max_length=120)
    company_name: str = Field(min_length=2, max_length=240)
    tier: TenantTier = TenantTier.STARTER
    primary_domain: str = Field(default="", max_length=240)
    timezone: str = Field(default="America/Sao_Paulo", min_length=1, max_length=120)


class CandidateCreateRequest(BaseModel):
    tenant_id: str = Field(min_length=2, max_length=120)
    candidate_id: Optional[str] = Field(default=None, min_length=2, max_length=160)
    name: str = Field(min_length=2, max_length=240)
    city: str = Field(default="", max_length=160)
    email: str = Field(default="", max_length=320)
    linkedin_url: str = Field(default="", max_length=1000)
    channels: List[CandidateChannel] = Field(default_factory=list)
    source_page_id: Optional[str] = Field(default=None, max_length=240)


class TenantAPIKeyCreateRequest(BaseModel):
    label: str = Field(default="default", min_length=1, max_length=120)


def _success(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "data": data}


def _page(items: List[Dict[str, Any]], page: int, limit: int, total: int) -> Dict[str, Any]:
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
        },
    }


def _candidate_channels(payload: CandidateCreateRequest) -> List[str]:
    if payload.channels:
        return [channel.value for channel in payload.channels]

    channels: List[str] = []
    if payload.email:
        channels.append(CandidateChannel.EMAIL.value)
    if payload.linkedin_url:
        channels.append(CandidateChannel.LINKEDIN.value)
    return channels


@app.get("/health")
async def health() -> Dict[str, Any]:
    temporal = TemporalConfig()
    return _success(
        {
            "service": "talent-intel-crm-api",
            "temporal_namespace": temporal.namespace,
            "temporal_target_host": temporal.target_host,
        }
    )


@app.get("/ready")
async def readiness(response: Response) -> Dict[str, Any]:
    postgres_ready = database_ready()
    if not postgres_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return _success({"service": "talent-intel-crm-api", "postgres": postgres_ready})




@app.get("/v1/me")
async def read_current_principal(principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    return _success(
        {
            "role": principal.role,
            "tenant_id": principal.tenant_id,
            "api_key_id": principal.api_key_id,
            "is_admin": principal.is_admin,
        }
    )

@app.post("/v1/tenants", status_code=status.HTTP_202_ACCEPTED)
async def create_tenant(payload: TenantCreateRequest, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    require_admin(principal)
    client = await connect_temporal()
    try:
        handle = await client.start_workflow(
            TenantOnboardingWorkflow.run,
            {
                "tenant_id": payload.tenant_id,
                "company_name": payload.company_name,
                "tier": payload.tier.value,
                "primary_domain": payload.primary_domain,
                "timezone": payload.timezone,
            },
            id=f"tenant-onboarding::{payload.tenant_id}",
            task_queue=TemporalConfig().task_queue,
        )
    except WorkflowAlreadyStartedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant onboarding already started") from exc
    return _success({"workflow_id": handle.id, "run_id": handle.result_run_id, "tenant_id": payload.tenant_id})


@app.get("/v1/tenants/{tenant_id}")
async def read_tenant(tenant_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    authorize_tenant(principal, tenant["id"])
    return _success(tenant)


@app.post("/v1/tenants/{tenant_id}/api-keys", status_code=status.HTTP_201_CREATED)
async def create_tenant_api_key(
    tenant_id: str,
    payload: TenantAPIKeyCreateRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_admin(principal)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    raw_key = new_tenant_api_key()
    record = insert_tenant_api_key(
        {
            "tenant_id": tenant_id,
            "key_prefix": api_key_prefix(raw_key),
            "key_hash": hash_api_key(raw_key),
            "label": payload.label,
        }
    )
    return _success({"api_key": raw_key, "key": record})


@app.get("/v1/tenants/{tenant_id}/api-keys")
async def read_tenant_api_keys(tenant_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    require_admin(principal)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return _success({"tenant_id": tenant_id, "items": list_tenant_api_keys(tenant_id)})


@app.delete("/v1/tenants/{tenant_id}/api-keys/{api_key_id}")
async def delete_tenant_api_key(
    tenant_id: str,
    api_key_id: str,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_admin(principal)
    key = revoke_tenant_api_key(tenant_id, api_key_id)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active tenant API key not found")
    return _success({"tenant_id": tenant_id, "key": key})


@app.post("/v1/tenants/{tenant_id}/api-keys/{api_key_id}/rotate", status_code=status.HTTP_201_CREATED)
async def rotate_tenant_api_key(
    tenant_id: str,
    api_key_id: str,
    payload: TenantAPIKeyCreateRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_admin(principal)
    revoked_key = revoke_tenant_api_key(tenant_id, api_key_id)
    if not revoked_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active tenant API key not found")
    raw_key = new_tenant_api_key()
    created_key = insert_tenant_api_key(
        {
            "tenant_id": tenant_id,
            "key_prefix": api_key_prefix(raw_key),
            "key_hash": hash_api_key(raw_key),
            "label": payload.label,
        }
    )
    return _success({"api_key": raw_key, "revoked_key": revoked_key, "key": created_key})


@app.post("/v1/candidates", status_code=status.HTTP_202_ACCEPTED)
async def create_candidate(payload: CandidateCreateRequest, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    candidate_id = payload.candidate_id or f"candidate-{uuid4().hex}"
    channels = _candidate_channels(payload)
    if not channels:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one contact channel is required")
    if not tenant_exists(payload.tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    authorize_tenant(principal, payload.tenant_id)

    client = await connect_temporal()
    try:
        handle = await client.start_workflow(
            CandidateLifecycleWorkflow.run,
            {
                "candidate_id": candidate_id,
                "tenant_id": payload.tenant_id,
                "name": payload.name,
                "city": payload.city,
                "email": payload.email,
                "linkedin_url": payload.linkedin_url,
                "channels": channels,
                "source_page_id": payload.source_page_id,
                "stage": CandidateStage.INGESTED.value,
            },
            id=f"candidate-lifecycle::{payload.tenant_id}::{candidate_id}",
            task_queue=TemporalConfig().task_queue,
        )
    except WorkflowAlreadyStartedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate lifecycle already started") from exc
    return _success(
        {
            "workflow_id": handle.id,
            "run_id": handle.result_run_id,
            "candidate_id": candidate_id,
            "tenant_id": payload.tenant_id,
            "channels": channels,
        }
    )


@app.get("/v1/candidates/{candidate_id}")
async def read_candidate(candidate_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    authorize_tenant(principal, candidate["tenant_id"])
    return _success(candidate)


@app.get("/v1/tenants/{tenant_id}/candidates")
async def read_tenant_candidates(
    tenant_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    authorize_tenant(principal, tenant_id)
    result = list_tenant_candidates(tenant_id, page, limit)
    return _success({"tenant_id": tenant_id, **_page(result["items"], page, limit, result["total"])})


@app.get("/v1/candidates/{candidate_id}/interactions")
async def read_candidate_interactions(candidate_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    authorize_tenant(principal, candidate["tenant_id"])
    return _success(
        {
            "candidate_id": candidate_id,
            "items": list_candidate_interactions(candidate_id),
        }
    )


@app.get("/v1/tenants/{tenant_id}/interactions")
async def read_tenant_interactions(
    tenant_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    authorize_tenant(principal, tenant_id)
    result = list_tenant_interactions(tenant_id, page, limit)
    return _success({"tenant_id": tenant_id, **_page(result["items"], page, limit, result["total"])})


@app.get("/v1/tenants/{tenant_id}/metrics")
async def read_tenant_metrics(tenant_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    authorize_tenant(principal, tenant_id)
    return _success({"tenant_id": tenant_id, **tenant_metrics(tenant_id)})
