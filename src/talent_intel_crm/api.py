from __future__ import annotations

from hmac import compare_digest
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from temporalio.exceptions import WorkflowAlreadyStartedError

from talent_intel_crm.client import connect_temporal
from talent_intel_crm.config import APIConfig, TemporalConfig
from talent_intel_crm.db import tenant_exists
from talent_intel_crm.domain import CandidateChannel, CandidateStage, TenantTier
from talent_intel_crm.workflows import CandidateLifecycleWorkflow, TenantOnboardingWorkflow


app = FastAPI(
    title="Talent Intel CRM API",
    version="0.1.0",
    description="HTTP control plane for tenant onboarding and candidate lifecycle orchestration.",
)


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


def _success(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "data": data}


def _candidate_channels(payload: CandidateCreateRequest) -> List[str]:
    if payload.channels:
        return [channel.value for channel in payload.channels]

    channels: List[str] = []
    if payload.email:
        channels.append(CandidateChannel.EMAIL.value)
    if payload.linkedin_url:
        channels.append(CandidateChannel.LINKEDIN.value)
    return channels


def _require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    configured_key = APIConfig().api_key
    if not configured_key:
        return
    if not x_api_key or not compare_digest(configured_key, x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


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


@app.post("/v1/tenants", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(_require_api_key)])
async def create_tenant(payload: TenantCreateRequest) -> Dict[str, Any]:
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


@app.post("/v1/candidates", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(_require_api_key)])
async def create_candidate(payload: CandidateCreateRequest) -> Dict[str, Any]:
    candidate_id = payload.candidate_id or f"candidate-{uuid4().hex}"
    channels = _candidate_channels(payload)
    if not channels:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one contact channel is required")
    if not tenant_exists(payload.tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

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
