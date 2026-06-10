from __future__ import annotations

import json
import logging
import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from temporalio.exceptions import WorkflowAlreadyStartedError

from talent_intel_crm.auth import APIPrincipal, api_key_prefix, authorize_tenant, hash_api_key, new_tenant_api_key, require_admin, require_principal, require_tenant_admin
from talent_intel_crm.client import connect_temporal
from talent_intel_crm.config import TemporalConfig
from talent_intel_crm.db import (
    database_ready,
    append_audit_event,
    append_interaction_row,
    delete_tenant_membership,
    find_auth_user_by_email,
    get_candidate,
    get_interaction,
    find_linkedin_interaction_for_status,
    get_tenant,
    insert_tenant_api_key,
    list_candidate_interactions,
    list_tenants,
    list_tenant_api_keys,
    list_tenant_audit_events,
    list_tenant_expandi_interactions,
    list_tenant_candidates,
    list_tenant_interactions,
    list_tenant_memberships,
    list_tenant_workflow_runs,
    revoke_tenant_api_key,
    tenant_exists,
    tenant_metrics,
    update_candidate_state,
    update_interaction_status,
    update_tenant_metadata,
    upsert_candidate,
    upsert_tenant_membership,
)
from talent_intel_crm.domain import CandidateChannel, CandidateStage, TenantTier
from talent_intel_crm.support import env
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
    current_role: str = Field(default="", max_length=240)
    current_company: str = Field(default="", max_length=240)
    seniority: str = Field(default="", max_length=120)
    target_profile: str = Field(default="", max_length=240)
    state: str = Field(default="", max_length=80)


class TenantMembershipUpsertRequest(BaseModel):
    user_id: str = Field(default="", max_length=240)
    email: str = Field(default="", max_length=320)
    role: str = Field(default="viewer", pattern="^(owner|admin|recruiter|viewer)$")


class TenantAPIKeyCreateRequest(BaseModel):
    label: str = Field(default="default", min_length=1, max_length=120)


class InteractionStatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(draft|pending|approved|sent|replied|closed|paused|discarded)$")
    response_received: str = Field(default="", max_length=2000)


class InteractionReviewRequest(BaseModel):
    status: str = Field(default="approved", pattern="^(draft|pending|approved)$")
    message_sent: str = Field(min_length=1, max_length=4000)
    subject: str = Field(default="", max_length=500)
    decision_note: str = Field(default="", max_length=1000)


class ExpandiStatusSyncRequest(BaseModel):
    interaction_id: str = Field(default="", max_length=160)
    tenant_id: str = Field(default="", max_length=120)
    candidate_id: str = Field(default="", max_length=160)
    lead_id: str = Field(default="", max_length=240)
    message_id: str = Field(default="", max_length=240)
    messenger_id: str = Field(default="", max_length=240)
    provider_message_id: str = Field(default="", max_length=240)
    status: str = Field(default="", max_length=120)
    event: str = Field(default="", max_length=120)
    reason: str = Field(default="", max_length=1000)
    message: str = Field(default="", max_length=4000)
    response_received: str = Field(default="", max_length=4000)
    raw: Dict[str, Any] = Field(default_factory=dict)


class ExpandiPollSyncRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
    dry_run: bool = False


class CandidateDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(active|paused|discarded)$")
    decision_note: str = Field(default="", max_length=1000)


class TenantPreferencesRequest(BaseModel):
    target_roles: str = Field(default="", max_length=1000)
    seniority: str = Field(default="", max_length=500)
    locations: str = Field(default="", max_length=1000)
    keywords: str = Field(default="", max_length=1000)
    allowed_channels: List[str] = Field(default_factory=list)
    outreach_tone: str = Field(default="", max_length=500)
    daily_contact_limit: int = Field(default=20, ge=0, le=1000)
    max_attempts_per_candidate: int = Field(default=3, ge=0, le=20)
    follow_up_interval_days: int = Field(default=5, ge=0, le=60)
    require_manual_approval: bool = True
    linkedin_enabled: bool = True
    email_enabled: bool = True


class TenantMessageTemplatesRequest(BaseModel):
    email_initial_subject: str = Field(default="", max_length=500)
    email_initial_body: str = Field(default="", max_length=4000)
    email_follow_up_1_subject: str = Field(default="", max_length=500)
    email_follow_up_1_body: str = Field(default="", max_length=4000)
    email_follow_up_2_subject: str = Field(default="", max_length=500)
    email_follow_up_2_body: str = Field(default="", max_length=4000)
    email_follow_up_3_subject: str = Field(default="", max_length=500)
    email_follow_up_3_body: str = Field(default="", max_length=4000)
    linkedin_connection_note: str = Field(default="", max_length=1000)
    linkedin_initial_message: str = Field(default="", max_length=4000)
    linkedin_follow_up_message: str = Field(default="", max_length=4000)
    response_follow_up_message: str = Field(default="", max_length=4000)


class ApolloSearchRequest(BaseModel):
    target_roles: str = Field(default="", max_length=1000)
    locations: str = Field(default="", max_length=1000)
    seniority: str = Field(default="", max_length=500)
    keywords: str = Field(default="", max_length=1000)
    industries: str = Field(default="", max_length=1000)
    max_candidates: int = Field(default=10, ge=1, le=25)


class ApolloEnrichmentRequest(BaseModel):
    candidate_ids: List[str] = Field(default_factory=list, max_length=25)
    max_candidates: int = Field(default=10, ge=1, le=25)


class HunterEnrichmentRequest(BaseModel):
    candidate_ids: List[str] = Field(default_factory=list, max_length=25)
    max_candidates: int = Field(default=10, ge=1, le=25)


FOLLOW_UP_STEPS = ("follow_up_1", "follow_up_2", "follow_up_3")


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


def _split_values(value: str) -> List[str]:
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]


def _apollo_payload(payload: ApolloSearchRequest) -> Dict[str, Any]:
    roles = _split_values(payload.target_roles)
    locations = _split_values(payload.locations)
    keywords = " ".join(_split_values(payload.keywords))
    industries = _split_values(payload.industries)
    request_payload: Dict[str, Any] = {
        "page": 1,
        "per_page": payload.max_candidates,
    }
    if roles:
        request_payload["person_titles"] = roles
    if locations:
        request_payload["person_locations"] = locations
    if keywords:
        request_payload["q_keywords"] = keywords
    if industries:
        request_payload["organization_industry_tag_ids"] = industries
    return request_payload


def _apollo_people_search(payload: ApolloSearchRequest) -> Dict[str, Any]:
    api_key = env("APOLLO_API_KEY")
    if not api_key:
        return {
            "configured": False,
            "people": [],
            "message": "APOLLO_API_KEY ainda não está configurada no serviço da API.",
        }
    body = json.dumps(_apollo_payload(payload), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        "https://api.apollo.io/api/v1/mixed_people/api_search",
        data=body,
        method="POST",
        headers={
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Apollo retornou HTTP {exc.code}: {raw[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Falha ao consultar Apollo.io") from exc

    people = data.get("people") or data.get("contacts") or []
    if not isinstance(people, list):
        people = []
    return {"configured": True, "people": [person for person in people if isinstance(person, dict)], "raw_count": len(people)}


def _apollo_people_match(apollo_person_id: str) -> Dict[str, Any]:
    api_key = env("APOLLO_API_KEY")
    if not api_key:
        return {
            "configured": False,
            "person": {},
            "message": "APOLLO_API_KEY ainda não está configurada no serviço da API.",
        }
    body = json.dumps(
        {
            "id": apollo_person_id,
            "reveal_personal_emails": False,
            "reveal_phone_number": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.apollo.io/api/v1/people/match",
        data=body,
        method="POST",
        headers={
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        if exc.code == 404:
            return {"configured": True, "person": {}, "status": "not_found", "message": "Apollo não encontrou dados adicionais para este candidato."}
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Apollo retornou HTTP {exc.code}: {raw[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Falha ao consultar Apollo.io") from exc

    person = data.get("person") or data.get("contact") or data.get("data") or {}
    if not isinstance(person, dict):
        person = {}
    return {"configured": True, "person": person, "status": "found" if person else "not_found"}


def _apollo_person_company(person: Dict[str, Any]) -> Dict[str, str]:
    organization = person.get("organization") if isinstance(person.get("organization"), dict) else {}
    account = person.get("account") if isinstance(person.get("account"), dict) else {}
    return {
        "name": str(organization.get("name") or account.get("name") or person.get("organization_name") or "").strip(),
        "domain": str(organization.get("website_url") or organization.get("primary_domain") or account.get("website_url") or account.get("domain") or "").strip(),
    }


def _professional_email(value: Any) -> str:
    email = str(value or "").strip()
    return email if email and "email_not_unlocked" not in email else ""


def _hunter_get(path: str, params: Dict[str, str]) -> Dict[str, Any]:
    api_key = env("HUNTER_API_KEY")
    if not api_key:
        return {
            "configured": False,
            "data": {},
            "message": "HUNTER_API_KEY ainda não está configurada no serviço da API.",
        }
    query = urllib.parse.urlencode({**params, "api_key": api_key})
    request = urllib.request.Request(
        f"https://api.hunter.io/v2/{path}?{query}",
        method="GET",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        if exc.code == 404:
            return {"configured": True, "data": {}, "not_found": True}
        if exc.code in {401, 403}:
            return {
                "configured": True,
                "data": {},
                "provider_error": True,
                "message": "Hunter recusou a consulta neste momento. Verifique permissão da chave, plano ou bloqueio temporário do provedor.",
            }
        if exc.code == 451:
            return {"configured": True, "data": {}, "blocked": True, "message": "Hunter bloqueou o processamento deste contato por solicitação do titular."}
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Hunter.io retornou HTTP {exc.code}: {raw[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Falha ao consultar Hunter.io") from exc
    return {"configured": True, "data": data.get("data") if isinstance(data, dict) else {}}


def _linkedin_handle(linkedin_url: str) -> str:
    value = linkedin_url.strip().strip("/")
    if not value:
        return ""
    if "linkedin.com/in/" in value:
        return value.rsplit("/in/", 1)[-1].split("/", 1)[0].strip()
    if value.startswith("in/"):
        return value.split("/", 1)[-1].strip()
    return value if "/" not in value and "." not in value else ""


def _candidate_person_name(name: str) -> str:
    clean_name = " ".join(name.strip().split())
    if not clean_name or clean_name.lower().startswith("apollo - "):
        return ""
    return clean_name if len(clean_name.split()) >= 2 else ""


def _candidate_company_domain(candidate: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    domain = str(metadata.get("company_domain") or metadata.get("domain") or metadata.get("organization_domain") or "").strip()
    if domain:
        normalized = domain.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
        return normalized[4:] if normalized.startswith("www.") else normalized
    return ""


def _hunter_email_finder(candidate: Dict[str, Any]) -> Dict[str, Any]:
    metadata = candidate.get("metadata_json") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}

    linkedin_handle = _linkedin_handle(str(candidate.get("linkedin_url") or ""))
    full_name = _candidate_person_name(str(candidate.get("name") or ""))
    company = str(metadata.get("current_company") or "").strip()
    domain = _candidate_company_domain(candidate, metadata)

    params: Dict[str, str] = {"max_duration": "10"}
    if full_name and (domain or company):
        params["full_name"] = full_name
        if domain:
            params["domain"] = domain
        else:
            params["company"] = company
    elif linkedin_handle:
        params["linkedin_handle"] = linkedin_handle
    else:
        return {
            "configured": True,
            "status": "insufficient_data",
            "message": "Hunter precisa de nome completo com domínio/empresa, ou handle do LinkedIn.",
        }

    result = _hunter_get("email-finder", params)
    if not result.get("configured"):
        return result
    if result.get("provider_error"):
        return {"configured": True, "status": "provider_error", "message": result.get("message", "")}
    if result.get("blocked"):
        return {"configured": True, "status": "blocked", "message": result.get("message", "")}
    data = result.get("data") or {}
    if not isinstance(data, dict) or not data.get("email"):
        return {"configured": True, "status": "not_found", "message": "Hunter não encontrou e-mail profissional para este candidato."}

    verification = data.get("verification") if isinstance(data.get("verification"), dict) else {}
    return {
        "configured": True,
        "status": "found",
        "email": str(data.get("email") or "").strip(),
        "score": data.get("score"),
        "domain": str(data.get("domain") or domain).strip(),
        "company": str(data.get("company") or company).strip(),
        "position": str(data.get("position") or "").strip(),
        "linkedin_url": str(data.get("linkedin_url") or candidate.get("linkedin_url") or "").strip(),
        "verification_status": str(verification.get("status") or "").strip(),
    }


def _apollo_candidate_id(tenant_id: str, person: Dict[str, Any]) -> str:
    stable = str(person.get("linkedin_url") or person.get("id") or person.get("email") or person.get("name") or uuid4().hex)
    digest = hashlib.sha1(f"{tenant_id}:{stable}".encode("utf-8")).hexdigest()[:14]
    return f"apollo-{digest}"


def _candidate_from_apollo_person(tenant_id: str, person: Dict[str, Any], source_payload: ApolloSearchRequest) -> Dict[str, Any]:
    organization = person.get("organization") if isinstance(person.get("organization"), dict) else {}
    account = person.get("account") if isinstance(person.get("account"), dict) else {}
    title = str(person.get("title") or "").strip()
    current_company = str(organization.get("name") or account.get("name") or person.get("organization_name") or "").strip()
    name = str(person.get("name") or "").strip()
    if not name:
        name = f"Apollo - {current_company}" if current_company else f"Apollo - {title[:80]}" if title else "Candidato Apollo"
    email = str(person.get("email") or "").strip()
    linkedin_url = str(person.get("linkedin_url") or person.get("linkedin_url_normalized") or person.get("linkedin") or "").strip()
    return {
        "candidate_id": _apollo_candidate_id(tenant_id, person),
        "tenant_id": tenant_id,
        "name": name,
        "city": str(person.get("city") or person.get("person_city") or "").strip(),
        "email": email if "email_not_unlocked" not in email else "",
        "linkedin_url": linkedin_url,
        "channels": [channel for channel, value in ((CandidateChannel.EMAIL.value, email), (CandidateChannel.LINKEDIN.value, linkedin_url)) if value],
        "source_page_id": str(person.get("id") or ""),
        "stage": CandidateStage.INGESTED.value,
        "metadata": {
            "state": str(person.get("state") or person.get("country") or "").strip(),
            "current_role": title,
            "current_company": current_company,
            "seniority": source_payload.seniority,
            "target_profile": source_payload.target_roles or source_payload.keywords,
            "source": "apollo",
            "apollo_person_id": str(person.get("id") or ""),
            "needs_contact_enrichment": not bool(email or linkedin_url),
        },
    }


def _candidate_projection(candidate: Dict[str, Any]) -> Dict[str, Any]:
    metadata = candidate.get("metadata_json") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}

    projected = {**metadata, **candidate}
    projected["metadata_json"] = metadata
    projected["metadata"] = metadata
    return projected


def _tenant_metadata(tenant_id: str) -> Dict[str, Any]:
    tenant = get_tenant(tenant_id)
    metadata = tenant.get("metadata_json") if tenant else {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return metadata if isinstance(metadata, dict) else {}


def _render_outreach_template(template: str, candidate: Dict[str, Any]) -> str:
    projected = _candidate_projection(candidate)
    metadata = projected.get("metadata_json") or {}
    values = {
        "nome": projected.get("name") or "talento",
        "cargo": projected.get("current_role") or metadata.get("current_role") or "sua área de atuação",
        "empresa": projected.get("current_company") or metadata.get("current_company") or "sua empresa atual",
        "cidade": projected.get("city") or "sua região",
        "senioridade": projected.get("seniority") or metadata.get("seniority") or "seu nível de experiência",
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered.strip()


def _follow_up_message(candidate: Dict[str, Any], tenant_id: str, step: str) -> Dict[str, str]:
    metadata = _tenant_metadata(tenant_id)
    templates = metadata.get("message_templates") if isinstance(metadata.get("message_templates"), dict) else {}
    defaults = {
        "follow_up_1": {
            "subject": "Retomando meu contato",
            "body": "Olá {{nome}}, passando para retomar meu contato anterior. Se fizer sentido para você, posso compartilhar mais contexto sobre a oportunidade.",
        },
        "follow_up_2": {
            "subject": "Ainda faz sentido conversarmos?",
            "body": "Olá {{nome}}, sei que a agenda pode estar corrida. Caso este tema faça sentido, posso te enviar um resumo objetivo da oportunidade.",
        },
        "follow_up_3": {
            "subject": "Encerrando meu contato por enquanto",
            "body": "Olá {{nome}}, este será meu último contato por enquanto. Se a conversa fizer sentido no futuro, fico à disposição para retomarmos. Obrigado.",
        },
    }
    subject = templates.get(f"email_{step}_subject") or defaults[step]["subject"]
    body = templates.get(f"email_{step}_body") or defaults[step]["body"]
    return {
        "subject": _render_outreach_template(str(subject), candidate),
        "body": _render_outreach_template(str(body), candidate),
        "language": "pt-BR",
        "template_status": "tenant_template",
    }


def _linkedin_follow_up_message(candidate: Dict[str, Any], tenant_id: str, step: str) -> Dict[str, str]:
    metadata = _tenant_metadata(tenant_id)
    templates = metadata.get("message_templates") if isinstance(metadata.get("message_templates"), dict) else {}
    template = templates.get("linkedin_follow_up_message") or "Olá {{nome}}, passando só para retomar minha mensagem. Se preferir, posso enviar um resumo da oportunidade por aqui."
    return {
        "text": _render_outreach_template(str(template), candidate),
        "language": "pt-BR",
        "template_status": "tenant_template",
        "cadence_step": step,
    }


def _sent_today_count(tenant_id: str) -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    result = list_tenant_interactions(tenant_id, 1, 100)
    count = 0
    for interaction in result.get("items", []):
        payload = interaction.get("payload_json") if isinstance(interaction.get("payload_json"), dict) else {}
        sent_at = str(payload.get("sent_at") or interaction.get("created_at") or "")
        if interaction.get("channel") == CandidateChannel.EMAIL.value and interaction.get("status") == "sent" and sent_at.startswith(today):
            count += 1
    return count


def _next_follow_up_step(interactions: List[Dict[str, Any]], channel: CandidateChannel) -> tuple[str, Optional[Dict[str, Any]]]:
    follow_ups = [
        interaction
        for interaction in interactions
        if interaction.get("channel") == channel.value and interaction.get("message_type") == "follow_up"
    ]
    for interaction in follow_ups:
        if interaction.get("status") in {"draft", "pending", "approved"}:
            return "", interaction
    completed_steps = {
        str((interaction.get("payload_json") or {}).get("cadence_step") or "")
        for interaction in follow_ups
        if interaction.get("status") in {"sent", "replied", "closed"}
    }
    for step in FOLLOW_UP_STEPS:
        if step not in completed_steps:
            return step, None
    return "", None


def _message_preview(message: Any) -> str:
    if isinstance(message, str):
        return message.strip()
    if not isinstance(message, dict):
        return ""
    text = message.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    body = message.get("body")
    if isinstance(body, str) and body.strip():
        return body.strip()
    subject = message.get("subject")
    if isinstance(subject, str):
        return subject.strip()
    return ""


def _resend_message_fields(interaction: Dict[str, Any]) -> Dict[str, str]:
    payload = interaction.get("payload_json") or {}
    if not isinstance(payload, dict):
        payload = {}
    message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    email = str(payload.get("email") or payload.get("candidate_email") or "").strip()
    subject = str(message.get("subject") or payload.get("subject") or "Contato sobre oportunidade profissional").strip()
    body = _message_preview(payload.get("message_sent")) or _message_preview(message)
    if not body:
        body = str(payload.get("message_sent") or "").strip()
    return {"to": email, "subject": subject, "text": body}


def _send_resend_email(interaction: Dict[str, Any]) -> Dict[str, Any]:
    api_key = env("RESEND_API_KEY")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RESEND_API_KEY ainda não está configurada no serviço da API.")
    from_email = env("RESEND_FROM_EMAIL", "Talent Intel CRM <onboarding@resend.dev>")
    reply_to = env("RESEND_REPLY_TO_EMAIL")
    fields = _resend_message_fields(interaction)
    if not fields["to"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta interação não tem e-mail do candidato.")
    if not fields["text"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta interação não tem mensagem revisada para envio.")

    request_payload: Dict[str, Any] = {
        "from": from_email,
        "to": [fields["to"]],
        "subject": fields["subject"],
        "text": fields["text"],
    }
    if reply_to:
        request_payload["reply_to"] = reply_to
    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TalentIntelCRM/1.0 (+https://talent-intel-crm.vercel.app)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Resend retornou HTTP {exc.code}: {raw[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Falha ao enviar e-mail pelo Resend.") from exc
    resend_id = str(data.get("id") or "").strip() if isinstance(data, dict) else ""
    return {"provider": "resend", "provider_message_id": resend_id, "to": fields["to"], "subject": fields["subject"]}


def _send_expandi_linkedin_message(interaction: Dict[str, Any]) -> Dict[str, Any]:
    webhook_url = env("EXPANDI_REVERSED_WEBHOOK_URL") or env("LINKEDIN_SEND_WEBHOOK_URL")
    if not webhook_url:
        return {"provider": "manual", "provider_message_id": "", "executed": False}

    payload = interaction.get("payload_json") or {}
    if not isinstance(payload, dict):
        payload = {}
    message = _message_preview(payload.get("message_sent")) or _message_preview(payload.get("message"))
    linkedin_url = str(payload.get("linkedin_url") or "").strip()
    if not linkedin_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta interação não tem URL do LinkedIn.")
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta interação não tem mensagem revisada para LinkedIn.")

    request_payload: Dict[str, Any] = {
        "interaction_id": str(interaction.get("id") or ""),
        "profile_link": linkedin_url,
        "candidate_id": str(interaction.get("candidate_id") or payload.get("candidate_id") or ""),
        "tenant_id": str(interaction.get("tenant_id") or payload.get("tenant_id") or ""),
        "name": str(payload.get("name") or ""),
        "email": str(payload.get("email") or ""),
        "linkedin_url": linkedin_url,
        "message": message,
        "message_type": str(interaction.get("message_type") or payload.get("message_type") or ""),
        "cadence_step": str(payload.get("cadence_step") or ""),
        "source": "talent-intel-crm",
    }
    campaign_id = env("EXPANDI_CAMPAIGN_ID")
    if campaign_id:
        request_payload["campaign_id"] = campaign_id

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "TalentIntelCRM/1.0 (+https://talent-intel-crm.vercel.app)",
    }
    if not env("EXPANDI_REVERSED_WEBHOOK_URL"):
        api_key = env("EXPANDI_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key
        api_secret = env("EXPANDI_API_SECRET")
        if api_secret:
            headers["X-API-Secret"] = api_secret
            headers["X-Expandi-API-Secret"] = api_secret

    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Expandi retornou HTTP {exc.code}: {raw[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Falha ao enviar mensagem LinkedIn para o Expandi.") from exc

    provider_id = ""
    if isinstance(data, dict):
        provider_id = str(data.get("id") or data.get("lead_id") or data.get("message_id") or data.get("request_id") or "").strip()
    return {"provider": "expandi", "provider_message_id": provider_id, "executed": True}


def _normalize_expandi_status(raw_status: str, raw_event: str = "") -> Dict[str, str]:
    raw = f"{raw_status} {raw_event}".strip().lower()
    raw = raw.replace("-", "_").replace(" ", "_")

    if any(token in raw for token in ("reply", "replied", "response", "responded", "message_received")):
        return {"provider_status": "replied", "interaction_status": "replied", "label": "Resposta recebida"}
    if any(token in raw for token in ("connected", "accepted", "connection_accepted")):
        return {"provider_status": "connected", "interaction_status": "sent", "label": "Conectado"}
    if any(token in raw for token in ("invitation_sent", "invite_sent", "connection_sent", "request_sent", "message_sent", "sent")):
        return {"provider_status": "invitation_sent", "interaction_status": "sent", "label": "Convite enviado"}
    if any(token in raw for token in ("failed", "error", "bounced", "blocked", "not_found", "invalid")):
        return {"provider_status": "failed", "interaction_status": "failed", "label": "Falhou no Expandi"}
    if any(token in raw for token in ("paused", "stopped", "limit", "restricted", "throttled")):
        return {"provider_status": "paused", "interaction_status": "paused", "label": "Pausado por limite"}
    if any(token in raw for token in ("queued", "queue", "imported", "running", "scheduled", "pending", "processing")):
        return {"provider_status": "queued", "interaction_status": "sent", "label": "Na fila do LinkedIn"}

    return {"provider_status": "synced", "interaction_status": "sent", "label": "Status sincronizado"}


def _expandi_status_payload(payload: ExpandiStatusSyncRequest) -> Dict[str, Any]:
    raw_payload = payload.model_dump(exclude_none=True)
    raw = payload.raw if isinstance(payload.raw, dict) else {}
    provider_message_id = (
        payload.provider_message_id
        or payload.lead_id
        or payload.message_id
        or payload.messenger_id
        or str(raw.get("provider_message_id") or raw.get("lead_id") or raw.get("message_id") or raw.get("messenger_id") or "")
    ).strip()
    raw_status = payload.status or str(raw.get("status") or raw.get("running_status") or raw.get("campaign_running_status") or "")
    raw_event = payload.event or str(raw.get("event") or raw.get("type") or raw.get("event_type") or "")
    normalized = _normalize_expandi_status(raw_status, raw_event)
    response_received = payload.response_received or payload.message or str(raw.get("response_received") or raw.get("message") or "")

    updates: Dict[str, Any] = {
        "linkedin_provider": "expandi",
        "provider_executed": True,
        "provider_status": normalized["provider_status"],
        "provider_status_label": normalized["label"],
        "provider_status_raw": raw_status or raw_event or "unknown",
        "provider_event_type": raw_event,
        "provider_status_synced_at": datetime.now(timezone.utc).isoformat(),
        "provider_payload": raw_payload,
        "manual_approval_status": normalized["interaction_status"],
    }
    if provider_message_id:
        updates["provider_message_id"] = provider_message_id
        updates["lead_id"] = provider_message_id
    if payload.reason:
        updates["provider_status_reason"] = payload.reason
    if response_received and normalized["provider_status"] == "replied":
        updates["response_received"] = response_received
    if normalized["provider_status"] == "invitation_sent":
        updates["linkedin_sent_at"] = datetime.now(timezone.utc).isoformat()

    return {"interaction_status": normalized["interaction_status"], "updates": updates}


def _expandi_api_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "TalentIntelCRM/1.0 (+https://talent-intel-crm.vercel.app)",
    }
    api_key = env("EXPANDI_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    api_secret = env("EXPANDI_API_SECRET")
    if api_secret:
        headers["X-API-Secret"] = api_secret
        headers["X-Expandi-API-Secret"] = api_secret
    return headers


def _expandi_status_poll_url(limit: int) -> str:
    configured_url = env("EXPANDI_STATUS_POLL_URL")
    if configured_url:
        return configured_url.format(limit=limit, campaign_id=urllib.parse.quote(env("EXPANDI_CAMPAIGN_ID", "")))

    campaign_id = env("EXPANDI_CAMPAIGN_ID")
    if not campaign_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="EXPANDI_CAMPAIGN_ID precisa estar configurado para polling.")

    query: Dict[str, str] = {
        "contact__campaigninstance[]": campaign_id,
        "page": "1",
        "page_size": str(limit),
    }
    linkedin_account_id = env("EXPANDI_LINKEDIN_ACCOUNT_ID")
    if linkedin_account_id:
        query["li_account_id"] = linkedin_account_id
    api_key = env("EXPANDI_API_KEY")
    api_secret = env("EXPANDI_API_SECRET")
    if api_key and api_secret:
        query["key"] = api_key
        query["secret"] = api_secret
    return f"https://api.liaufa.com/api/v1/linkedin/messenger/?{urllib.parse.urlencode(query)}"


def _expandi_response_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("results", "items", "data", "contacts", "messengers"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _expandi_response_items(value)
            if nested:
                return nested
    return [payload] if payload else []


def _nested_value(data: Dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _string_from_item(item: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value: Any = item
        for part in key.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if value is not None and value != "":
            return str(value).strip()
    return ""


def _expandi_item_to_status_request(item: Dict[str, Any], fallback: Dict[str, Any] | None = None) -> ExpandiStatusSyncRequest:
    fallback = fallback or {}
    custom_fields = item.get("custom_fields") if isinstance(item.get("custom_fields"), dict) else {}
    placeholders = item.get("placeholders") if isinstance(item.get("placeholders"), dict) else {}
    custom_placeholders = item.get("custom_placeholders") if isinstance(item.get("custom_placeholders"), dict) else {}
    merged = {**custom_fields, **placeholders, **custom_placeholders, **item}

    provider_message_id = _string_from_item(
        merged,
        "provider_message_id",
        "lead_id",
        "messenger_id",
        "message_id",
        "campaign_contact_id",
        "id",
        "contact.id",
    )
    raw_status = _string_from_item(
        merged,
        "status",
        "running_status",
        "campaign_running_status",
        "state",
        "current_status",
        "status_name",
        "step_status",
    )
    if raw_status.isdigit():
        status_map = {
            "1": "queued",
            "2": "running",
            "3": "queued",
            "4": "sent",
            "5": "connected",
            "6": "failed",
        }
        raw_status = status_map.get(raw_status, raw_status)

    response = _string_from_item(merged, "response_received", "last_message", "message", "reply.text")
    candidate_id = _string_from_item(merged, "candidate_id", "external_id") or str(fallback.get("candidate_id") or "")
    interaction_id = _string_from_item(merged, "interaction_id") or str(fallback.get("id") or "")

    return ExpandiStatusSyncRequest(
        interaction_id=interaction_id,
        tenant_id=str(fallback.get("tenant_id") or _string_from_item(merged, "tenant_id")),
        candidate_id=candidate_id,
        lead_id=provider_message_id,
        provider_message_id=provider_message_id,
        status=raw_status or "synced",
        event=_string_from_item(merged, "event", "event_type", "type"),
        reason=_string_from_item(merged, "reason", "reason_failed", "error", "error_message"),
        response_received=response,
        raw=item,
    )


def _fetch_expandi_status_items(limit: int) -> List[Dict[str, Any]]:
    poll_url = _expandi_status_poll_url(limit)
    request = urllib.request.Request(poll_url, method="GET", headers=_expandi_api_headers())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Expandi retornou HTTP {exc.code}: {raw[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Falha ao consultar status no Expandi.") from exc
    return _expandi_response_items(payload)


def _interaction_lookup_key(interaction: Dict[str, Any]) -> tuple[str, str, str]:
    payload = interaction.get("payload_json") if isinstance(interaction.get("payload_json"), dict) else {}
    provider_id = str(interaction.get("provider_message_id") or payload.get("provider_message_id") or payload.get("lead_id") or "").strip()
    return (str(interaction.get("id") or ""), str(interaction.get("candidate_id") or ""), provider_id)


def _apply_expandi_status(interaction: Dict[str, Any], payload: ExpandiStatusSyncRequest, principal: APIPrincipal) -> Dict[str, Any]:
    status_payload = _expandi_status_payload(payload)
    updated = update_interaction_status(str(interaction["id"]), status_payload["interaction_status"], status_payload["updates"])
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")

    _record_audit_event(
        tenant_id=interaction["tenant_id"],
        candidate_id=interaction["candidate_id"],
        event_type="interaction.expandi_status_synced",
        principal=principal,
        payload={
            "interaction_id": str(interaction["id"]),
            "provider_status": status_payload["updates"].get("provider_status"),
            "provider_status_label": status_payload["updates"].get("provider_status_label"),
            "provider_status_raw": status_payload["updates"].get("provider_status_raw"),
        },
    )
    return updated


def _interaction_projection(interaction: Dict[str, Any]) -> Dict[str, Any]:
    payload = interaction.get("payload_json") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}

    message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    status_value = interaction.get("status") or payload.get("status") or "pending"
    candidate_name = payload.get("name") or interaction.get("candidate_name")
    message_sent = _message_preview(payload.get("message_sent")) or _message_preview(message)
    next_action = payload.get("next_action")
    if not next_action:
        channel = interaction.get("channel")
        next_action = "Enviar mensagem pelo LinkedIn" if channel == "linkedin" else "Enviar e-mail inicial"

    projected = {**payload, **interaction}
    if projected.get("id") is not None:
        projected["id"] = str(projected["id"])
    if projected.get("created_at") is not None:
        created_at = projected["created_at"]
        projected["created_at"] = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
    projected["payload_json"] = payload
    projected["candidate_name"] = candidate_name
    projected["interaction_status"] = status_value
    projected["status"] = status_value
    projected["message_sent"] = message_sent
    projected["response_received"] = payload.get("response_received") or interaction.get("response_received")
    projected["next_action"] = next_action
    projected["provider_message_id"] = interaction.get("provider_message_id") or payload.get("provider_message_id")
    projected["provider_thread_id"] = interaction.get("provider_thread_id") or payload.get("provider_thread_id")
    projected["email_subject"] = payload.get("email_subject") or message.get("subject")
    return projected


def _record_audit_event(
    *,
    tenant_id: str,
    event_type: str,
    principal: APIPrincipal,
    payload: Dict[str, Any],
    candidate_id: Optional[str] = None,
) -> None:
    append_audit_event(
        {
            "tenant_id": tenant_id,
            "candidate_id": candidate_id,
            "event_type": event_type,
            "actor_type": principal.auth_method or principal.role or "system",
            "actor_id": principal.user_id or principal.api_key_id or principal.tenant_id or principal.role,
            "payload": payload,
        }
    )


def _metadata_from_record(record: Dict[str, Any]) -> Dict[str, Any]:
    metadata = record.get("metadata_json") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    return metadata if isinstance(metadata, dict) else {}


def _connector_item(
    *,
    key: str,
    name: str,
    configured: bool,
    status_value: str,
    summary: str,
    last_result: str,
    next_action: str,
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "configured": configured,
        "status": status_value,
        "summary": summary,
        "last_result": last_result,
        "next_action": next_action,
        "metrics": metrics,
    }


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


@app.get("/v1/tenants/{tenant_id}/connector-status")
async def read_connector_status(tenant_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    candidates = list_tenant_candidates(tenant_id, 1, 100).get("items", [])
    apollo_candidates = []
    hunter_counts = {"found": 0, "provider_error": 0, "not_found": 0, "insufficient_data": 0, "blocked": 0}
    ready_for_hunter = 0
    apollo_enriched = 0
    apollo_staged = 0
    with_contact_channel = 0

    for candidate in candidates:
        metadata = _metadata_from_record(candidate)
        if candidate.get("email") or candidate.get("linkedin_url"):
            with_contact_channel += 1
        if metadata.get("source") == "apollo":
            apollo_candidates.append(candidate)
            if metadata.get("apollo_enrichment_status") == "found" or metadata.get("apollo_status") == "enriched":
                apollo_enriched += 1
            if metadata.get("apollo_status") == "discovered_without_contact_channel":
                apollo_staged += 1
            if metadata.get("ready_for_hunter"):
                ready_for_hunter += 1
        hunter_status = str(metadata.get("hunter_status") or "")
        if hunter_status in hunter_counts:
            hunter_counts[hunter_status] += 1

    apollo_configured = bool(env("APOLLO_API_KEY"))
    hunter_configured = bool(env("HUNTER_API_KEY"))
    openai_configured = bool(env("OPENAI_API_KEY"))
    openrouter_configured = bool(env("OPENROUTER_API_KEY"))
    expandi_webhook_configured = bool(env("EXPANDI_REVERSED_WEBHOOK_URL") or env("LINKEDIN_SEND_WEBHOOK_URL"))
    expandi_api_key_configured = bool(env("EXPANDI_API_KEY"))
    expandi_api_secret_configured = bool(env("EXPANDI_API_SECRET"))
    expandi_campaign_configured = bool(env("EXPANDI_CAMPAIGN_ID"))
    expandi_credentials_configured = expandi_api_key_configured and expandi_api_secret_configured
    expandi_status = "active" if expandi_webhook_configured else "pending" if expandi_credentials_configured else "offline"
    expandi_last_result = "Credenciais e webhook ainda não configurados."
    expandi_next_action = "Configurar EXPANDI_API_KEY, EXPANDI_API_SECRET e campanha do Expandi."
    if expandi_webhook_configured:
        expandi_last_result = "Webhook configurado para receber leads e mensagens."
        expandi_next_action = "Enviar mensagens LinkedIn aprovadas pelo painel."
    elif expandi_credentials_configured and expandi_campaign_configured:
        expandi_last_result = "Credenciais e campanha configuradas; falta a URL de webhook ou endpoint de envio."
        expandi_next_action = "Configurar EXPANDI_REVERSED_WEBHOOK_URL ou implementar envio direto pela API oficial do Expandi."
    elif expandi_credentials_configured:
        expandi_last_result = "Credenciais configuradas; falta vincular a campanha do Expandi."
        expandi_next_action = "Configurar EXPANDI_CAMPAIGN_ID e depois a URL de webhook da campanha."
    llm_provider = (env("LLM_PROVIDER", "openai") or "openai").lower()
    temporal = TemporalConfig()

    apollo_status = "offline"
    apollo_last_result = "Chave não configurada."
    apollo_next_action = "Configurar APOLLO_API_KEY no serviço da API."
    if apollo_configured:
        apollo_status = "active" if apollo_enriched or apollo_candidates else "pending"
        apollo_last_result = f"{len(apollo_candidates)} candidato(s) importado(s), {apollo_enriched} perfil(is) completo(s)."
        apollo_next_action = "Buscar candidatos no Apollo e depois completar dados do Apollo."

    hunter_status_value = "offline"
    hunter_last_result = "Chave não configurada."
    hunter_next_action = "Configurar HUNTER_API_KEY no serviço da API."
    if hunter_configured:
        if hunter_counts["provider_error"]:
            hunter_status_value = "degraded"
            hunter_last_result = f"{hunter_counts['provider_error']} erro(s) do provedor; {hunter_counts['found']} e-mail(s) encontrado(s)."
            hunter_next_action = "Verificar plano, crédito ou permissão da chave Hunter. Tentar novamente após ajuste no provedor."
        elif hunter_counts["found"]:
            hunter_status_value = "active"
            hunter_last_result = f"{hunter_counts['found']} e-mail(s) encontrado(s) pela Hunter."
            hunter_next_action = "Revisar candidatos enriquecidos e contatos gerados pelos agentes."
        elif ready_for_hunter:
            hunter_status_value = "pending"
            hunter_last_result = f"{ready_for_hunter} candidato(s) pronto(s) para consulta Hunter."
            hunter_next_action = "Rodar Hunter para buscar e validar e-mails profissionais."
        else:
            hunter_status_value = "active"
            hunter_last_result = "Configurado, sem pendências novas para consultar."
            hunter_next_action = "Completar dados do Apollo antes de rodar Hunter."

    llm_configured = openai_configured or openrouter_configured
    llm_status = "active" if llm_configured else "offline"
    selected_llm_ready = (llm_provider == "openrouter" and openrouter_configured) or (llm_provider == "openai" and openai_configured)
    if llm_configured and not selected_llm_ready:
        llm_status = "degraded"

    items = [
        _connector_item(
            key="api",
            name="API Talent Intel CRM",
            configured=True,
            status_value="active",
            summary="Serviço central que autentica, consulta o banco e inicia fluxos.",
            last_result="API respondeu a esta consulta com sucesso.",
            next_action="Manter monitoramento de health e readiness.",
            metrics={"with_contact_channel": with_contact_channel, "total_candidates": len(candidates)},
        ),
        _connector_item(
            key="apollo",
            name="Apollo.io",
            configured=apollo_configured,
            status_value=apollo_status,
            summary="Busca candidatos e completa nome, LinkedIn, empresa e domínio.",
            last_result=apollo_last_result,
            next_action=apollo_next_action,
            metrics={"imported": len(apollo_candidates), "enriched": apollo_enriched, "staged": apollo_staged, "ready_for_hunter": ready_for_hunter},
        ),
        _connector_item(
            key="hunter",
            name="Hunter.io",
            configured=hunter_configured,
            status_value=hunter_status_value,
            summary="Busca e valida e-mails profissionais antes da abordagem.",
            last_result=hunter_last_result,
            next_action=hunter_next_action,
            metrics=hunter_counts,
        ),
        _connector_item(
            key="llm",
            name="OpenAI / OpenRouter",
            configured=llm_configured,
            status_value=llm_status,
            summary="Classifica candidatos, justifica o score e gera mensagens.",
            last_result=f"Provider preferido: {llm_provider}. OpenAI: {'configurado' if openai_configured else 'pendente'}. OpenRouter: {'configurado' if openrouter_configured else 'pendente'}.",
            next_action="Manter pelo menos um provedor LLM configurado para classificação e copy.",
            metrics={"openai_configured": openai_configured, "openrouter_configured": openrouter_configured, "provider": llm_provider},
        ),
        _connector_item(
            key="expandi",
            name="Expandi",
            configured=expandi_credentials_configured or expandi_webhook_configured,
            status_value=expandi_status,
            summary="Executa mensagens aprovadas do LinkedIn por webhook de campanha.",
            last_result=expandi_last_result,
            next_action=expandi_next_action,
            metrics={
                "api_key_configured": expandi_api_key_configured,
                "api_secret_configured": expandi_api_secret_configured,
                "webhook_configured": expandi_webhook_configured,
                "campaign_configured": expandi_campaign_configured,
            },
        ),
        _connector_item(
            key="temporal",
            name="Temporal",
            configured=bool(temporal.target_host and temporal.target_host != "unknown"),
            status_value="active" if temporal.target_host and temporal.target_host != "unknown" else "offline",
            summary="Orquestra retries, etapas dos agentes e auditoria operacional.",
            last_result=f"Namespace: {temporal.namespace}. Task queue: {temporal.task_queue}.",
            next_action="Acompanhar execuções em Fluxos e logs do worker.",
            metrics={"namespace": temporal.namespace, "task_queue": temporal.task_queue},
        ),
    ]

    return _success({"tenant_id": tenant_id, "items": items})




@app.get("/v1/me")
async def read_current_principal(principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    return _success(
        {
            "role": principal.role,
            "tenant_id": principal.tenant_id,
            "api_key_id": principal.api_key_id,
            "is_admin": principal.is_admin,
            "user_id": principal.user_id,
            "email": principal.email,
            "auth_method": principal.auth_method,
        }
    )

@app.get("/v1/tenants")
async def read_tenants(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_admin(principal)
    result = list_tenants(page, limit)
    return _success(_page(result["items"], page, limit, result["total"]))


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
    _record_audit_event(
        tenant_id=payload.tenant_id,
        event_type="tenant.create_requested",
        principal=principal,
        payload={
            "tenant_id": payload.tenant_id,
            "company_name": payload.company_name,
            "tier": payload.tier.value,
            "primary_domain": payload.primary_domain,
            "timezone": payload.timezone,
            "workflow_id": handle.id,
            "run_id": handle.result_run_id,
        },
    )
    return _success({"workflow_id": handle.id, "run_id": handle.result_run_id, "tenant_id": payload.tenant_id})


@app.get("/v1/tenants/{tenant_id}")
async def read_tenant(tenant_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    authorize_tenant(principal, tenant["id"])
    return _success(tenant)


@app.post("/v1/tenants/{tenant_id}/preferences")
async def update_tenant_preferences(
    tenant_id: str,
    payload: TenantPreferencesRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant = update_tenant_metadata(
        tenant_id,
        {
            "ideal_profile": {
                "target_roles": payload.target_roles,
                "seniority": payload.seniority,
                "locations": payload.locations,
                "keywords": payload.keywords,
                "allowed_channels": payload.allowed_channels,
                "outreach_tone": payload.outreach_tone,
            },
            "mvp_limits": {
                "daily_contact_limit": payload.daily_contact_limit,
                "max_attempts_per_candidate": payload.max_attempts_per_candidate,
                "follow_up_interval_days": payload.follow_up_interval_days,
                "require_manual_approval": payload.require_manual_approval,
                "linkedin_enabled": payload.linkedin_enabled,
                "email_enabled": payload.email_enabled,
            },
        },
    )
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    _record_audit_event(
        tenant_id=tenant_id,
        event_type="tenant.preferences_updated",
        principal=principal,
        payload={"ideal_profile": tenant.get("metadata_json", {}).get("ideal_profile", {}), "mvp_limits": tenant.get("metadata_json", {}).get("mvp_limits", {})},
    )
    return _success({"tenant_id": tenant_id, "tenant": tenant})


@app.post("/v1/tenants/{tenant_id}/message-templates")
async def update_tenant_message_templates(
    tenant_id: str,
    payload: TenantMessageTemplatesRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    message_templates = {
        "email_initial_subject": payload.email_initial_subject,
        "email_initial_body": payload.email_initial_body,
        "email_follow_up_1_subject": payload.email_follow_up_1_subject,
        "email_follow_up_1_body": payload.email_follow_up_1_body,
        "email_follow_up_2_subject": payload.email_follow_up_2_subject,
        "email_follow_up_2_body": payload.email_follow_up_2_body,
        "email_follow_up_3_subject": payload.email_follow_up_3_subject,
        "email_follow_up_3_body": payload.email_follow_up_3_body,
        "linkedin_connection_note": payload.linkedin_connection_note,
        "linkedin_initial_message": payload.linkedin_initial_message,
        "linkedin_follow_up_message": payload.linkedin_follow_up_message,
        "response_follow_up_message": payload.response_follow_up_message,
    }
    tenant = update_tenant_metadata(tenant_id, {"message_templates": message_templates})
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    _record_audit_event(
        tenant_id=tenant_id,
        event_type="tenant.message_templates_updated",
        principal=principal,
        payload={"template_keys": list(message_templates.keys())},
    )
    return _success({"tenant_id": tenant_id, "tenant": tenant})


@app.post("/v1/tenants/{tenant_id}/sourcing/apollo/search", status_code=status.HTTP_202_ACCEPTED)
async def search_apollo_candidates(
    tenant_id: str,
    payload: ApolloSearchRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    apollo_result = _apollo_people_search(payload)
    if not apollo_result["configured"]:
        _record_audit_event(
            tenant_id=tenant_id,
            event_type="sourcing.apollo_configuration_missing",
            principal=principal,
            payload={"criteria": payload.model_dump(), "provider": "apollo"},
        )
        return _success(
            {
                "tenant_id": tenant_id,
                "provider": "apollo",
                "configured": False,
                "created": [],
                "duplicates": [],
                "message": apollo_result["message"],
            }
        )

    client = await connect_temporal()
    created: List[Dict[str, Any]] = []
    duplicates: List[str] = []
    staged: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []

    for person in apollo_result["people"][: payload.max_candidates]:
        candidate_payload = _candidate_from_apollo_person(tenant_id, person, payload)
        candidate_id = str(candidate_payload["candidate_id"])
        if not candidate_payload["channels"]:
            existing = get_candidate(candidate_id)
            if existing:
                duplicates.append(candidate_id)
                continue
            upsert_candidate(
                {
                    **candidate_payload,
                    "external_id": candidate_id,
                    "metadata": {
                        **candidate_payload["metadata"],
                            "apollo_status": "discovered_without_contact_channel",
                            "recommended_next_step": "Completar dados no Apollo antes de chamar Hunter.io.",
                    },
                }
            )
            staged.append(
                {
                    "candidate_id": candidate_id,
                    "name": candidate_payload["name"],
                    "stage": CandidateStage.INGESTED.value,
                    "reason": "Apollo retornou o perfil sem e-mail ou LinkedIn completo.",
                }
            )
            continue
        try:
            handle = await client.start_workflow(
                CandidateLifecycleWorkflow.run,
                candidate_payload,
                id=f"candidate-lifecycle::{tenant_id}::{candidate_id}",
                task_queue=TemporalConfig().task_queue,
            )
        except WorkflowAlreadyStartedError:
            duplicates.append(candidate_id)
            continue
        created.append(
            {
                "candidate_id": candidate_id,
                "name": candidate_payload["name"],
                "channels": candidate_payload["channels"],
                "workflow_id": handle.id,
                "run_id": handle.result_run_id,
            }
        )

    _record_audit_event(
        tenant_id=tenant_id,
        event_type="sourcing.apollo_search_requested",
        principal=principal,
        payload={
            "criteria": payload.model_dump(),
            "created": len(created),
            "staged": len(staged),
            "duplicates": len(duplicates),
            "skipped": len(skipped),
        },
    )
    return _success(
        {
            "tenant_id": tenant_id,
            "provider": "apollo",
            "configured": True,
            "created": created,
            "staged": staged,
            "duplicates": duplicates,
            "skipped": skipped,
            "message": f"{len(created)} candidato(s) enviados para análise dos agentes e {len(staged)} salvo(s) para enriquecimento de contato.",
        }
    )


@app.post("/v1/tenants/{tenant_id}/sourcing/apollo/enrich", status_code=status.HTTP_202_ACCEPTED)
async def enrich_apollo_candidates(
    tenant_id: str,
    payload: ApolloEnrichmentRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if payload.candidate_ids:
        candidates = [candidate for candidate_id in payload.candidate_ids if (candidate := get_candidate(candidate_id))]
    else:
        result = list_tenant_candidates(tenant_id, 1, payload.max_candidates)
        candidates = result.get("items", [])

    if not env("APOLLO_API_KEY"):
        _record_audit_event(
            tenant_id=tenant_id,
            event_type="sourcing.apollo_enrichment_configuration_missing",
            principal=principal,
            payload={"candidate_ids": [candidate.get("id") for candidate in candidates], "provider": "apollo"},
        )
        return _success(
            {
                "tenant_id": tenant_id,
                "provider": "apollo",
                "configured": False,
                "enriched": [],
                "started": [],
                "pending": [],
                "duplicates": [],
                "message": "APOLLO_API_KEY ainda não está configurada no serviço da API.",
            }
        )

    temporal_client = None
    enriched: List[Dict[str, Any]] = []
    started: List[Dict[str, str]] = []
    pending: List[Dict[str, str]] = []
    duplicates: List[str] = []

    for raw_candidate in candidates[: payload.max_candidates]:
        candidate = _candidate_projection(raw_candidate)
        candidate_id = str(candidate.get("id") or "")
        if not candidate_id:
            continue
        metadata = candidate.get("metadata_json") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        if metadata.get("source") != "apollo":
            pending.append({"candidate_id": candidate_id, "status": "not_apollo", "reason": "Candidato não veio do Apollo."})
            continue

        apollo_person_id = str(metadata.get("apollo_person_id") or candidate.get("source_page_id") or "").strip()
        if not apollo_person_id:
            update_candidate_state(
                candidate_id,
                str(candidate.get("stage") or CandidateStage.INGESTED.value),
                {"apollo_enrichment_status": "missing_person_id", "apollo_enrichment_reason": "Candidato não tem apollo_person_id."},
            )
            pending.append({"candidate_id": candidate_id, "status": "missing_person_id", "reason": "Candidato não tem apollo_person_id."})
            continue

        match = _apollo_people_match(apollo_person_id)
        if match.get("configured") is False:
            return _success(
                {
                    "tenant_id": tenant_id,
                    "provider": "apollo",
                    "configured": False,
                    "enriched": enriched,
                    "started": started,
                    "pending": pending,
                    "duplicates": duplicates,
                    "message": match.get("message", "APOLLO_API_KEY ainda não está configurada no serviço da API."),
                }
            )
        person = match.get("person") if isinstance(match.get("person"), dict) else {}
        if not person:
            update_candidate_state(
                candidate_id,
                str(candidate.get("stage") or CandidateStage.INGESTED.value),
                {
                    "apollo_enrichment_status": "not_found",
                    "apollo_enrichment_reason": match.get("message", "Apollo não encontrou dados adicionais."),
                    "needs_contact_enrichment": True,
                },
            )
            pending.append({"candidate_id": candidate_id, "status": "not_found", "reason": "Apollo não encontrou dados adicionais."})
            continue

        company = _apollo_person_company(person)
        name = str(person.get("name") or candidate.get("name") or "").strip()
        current_company = company["name"] or str(metadata.get("current_company") or "").strip()
        current_role = str(person.get("title") or metadata.get("current_role") or "").strip()
        email = _professional_email(person.get("email") or candidate.get("email"))
        linkedin_url = str(person.get("linkedin_url") or person.get("linkedin_url_normalized") or candidate.get("linkedin_url") or "").strip()
        company_domain = company["domain"].removeprefix("https://").removeprefix("http://").split("/", 1)[0]
        channels = [channel for channel, value in ((CandidateChannel.EMAIL.value, email), (CandidateChannel.LINKEDIN.value, linkedin_url)) if value]
        full_name = _candidate_person_name(name)
        ready_for_hunter = bool(full_name and (company_domain or current_company or linkedin_url))
        updated_metadata = {
            **metadata,
            "apollo_status": "enriched",
            "apollo_enrichment_status": "found",
            "apollo_person_id": apollo_person_id,
            "apollo_first_name": str(person.get("first_name") or "").strip(),
            "apollo_last_name": str(person.get("last_name") or "").strip(),
            "current_role": current_role,
            "current_company": current_company,
            "company_domain": company_domain,
            "needs_contact_enrichment": not bool(channels),
            "ready_for_hunter": ready_for_hunter and not bool(email),
            "recommended_next_step": "Rodar Hunter.io para encontrar e validar e-mail profissional." if ready_for_hunter and not channels else "",
        }
        upsert_candidate(
            {
                "candidate_id": candidate_id,
                "tenant_id": tenant_id,
                "external_id": candidate.get("external_id") or candidate_id,
                "name": name or candidate_id,
                "city": str(person.get("city") or candidate.get("city") or "").strip(),
                "email": email,
                "linkedin_url": linkedin_url,
                "source_page_id": candidate.get("source_page_id") or apollo_person_id,
                "stage": str(candidate.get("stage") or CandidateStage.INGESTED.value),
                "metadata": updated_metadata,
            }
        )
        enriched.append({"candidate_id": candidate_id, "name": name or candidate_id, "channels": channels, "ready_for_hunter": ready_for_hunter})

        if not channels:
            pending.append(
                {
                    "candidate_id": candidate_id,
                    "status": "ready_for_hunter" if ready_for_hunter else "still_missing_contact",
                    "reason": "Dados suficientes para Hunter." if ready_for_hunter else "Apollo completou o perfil, mas ainda falta canal e dados suficientes.",
                }
            )
            continue

        workflow_payload = {
            "candidate_id": candidate_id,
            "tenant_id": tenant_id,
            "name": name or candidate_id,
            "city": str(person.get("city") or candidate.get("city") or "").strip(),
            "email": email,
            "linkedin_url": linkedin_url,
            "channels": channels,
            "source_page_id": candidate.get("source_page_id") or apollo_person_id,
            "stage": CandidateStage.INGESTED.value,
            "metadata": updated_metadata,
        }
        try:
            if temporal_client is None:
                temporal_client = await connect_temporal()
            handle = await temporal_client.start_workflow(
                CandidateLifecycleWorkflow.run,
                workflow_payload,
                id=f"candidate-lifecycle::{tenant_id}::{candidate_id}",
                task_queue=TemporalConfig().task_queue,
            )
        except WorkflowAlreadyStartedError:
            duplicates.append(candidate_id)
        else:
            started.append({"candidate_id": candidate_id, "workflow_id": handle.id, "run_id": handle.result_run_id})

    _record_audit_event(
        tenant_id=tenant_id,
        event_type="sourcing.apollo_enrichment_requested",
        principal=principal,
        payload={
            "candidate_ids": [candidate.get("id") for candidate in candidates],
            "enriched": len(enriched),
            "started": len(started),
            "pending": len(pending),
            "duplicates": len(duplicates),
        },
    )
    return _success(
        {
            "tenant_id": tenant_id,
            "provider": "apollo",
            "configured": True,
            "enriched": enriched,
            "started": started,
            "pending": pending,
            "duplicates": duplicates,
            "message": f"Apollo completou {len(enriched)} candidato(s), iniciou {len(started)} fluxo(s) e deixou {len(pending)} pendente(s).",
        }
    )


@app.post("/v1/tenants/{tenant_id}/enrichment/hunter/run", status_code=status.HTTP_202_ACCEPTED)
async def run_hunter_enrichment(
    tenant_id: str,
    payload: HunterEnrichmentRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if payload.candidate_ids:
        candidates = [candidate for candidate_id in payload.candidate_ids if (candidate := get_candidate(candidate_id))]
    else:
        result = list_tenant_candidates(tenant_id, 1, payload.max_candidates)
        candidates = result.get("items", [])

    if not env("HUNTER_API_KEY"):
        _record_audit_event(
            tenant_id=tenant_id,
            event_type="enrichment.hunter_configuration_missing",
            principal=principal,
            payload={"candidate_ids": [candidate.get("id") for candidate in candidates], "provider": "hunter"},
        )
        return _success(
            {
                "tenant_id": tenant_id,
                "provider": "hunter",
                "configured": False,
                "enriched": [],
                "started": [],
                "pending": [],
                "message": "HUNTER_API_KEY ainda não está configurada no serviço da API.",
            }
        )

    temporal_client = None
    enriched: List[Dict[str, Any]] = []
    started: List[Dict[str, str]] = []
    pending: List[Dict[str, str]] = []
    duplicates: List[str] = []
    already_ready = 0
    insufficient_data = 0
    provider_error = 0
    not_found = 0
    blocked = 0

    for raw_candidate in candidates[: payload.max_candidates]:
        candidate = _candidate_projection(raw_candidate)
        candidate_id = str(candidate.get("id") or "")
        if not candidate_id:
            continue
        metadata = candidate.get("metadata_json") or {}
        if not isinstance(metadata, dict):
            metadata = {}

        if candidate.get("email") and not metadata.get("needs_contact_enrichment"):
            already_ready += 1
            pending.append({"candidate_id": candidate_id, "status": "already_ready", "reason": "Candidato já possui e-mail operacional."})
            continue

        hunter_result = _hunter_email_finder(candidate)
        if hunter_result.get("configured") is False:
            return _success(
                {
                    "tenant_id": tenant_id,
                    "provider": "hunter",
                    "configured": False,
                    "enriched": enriched,
                    "started": started,
                    "pending": pending,
                    "message": hunter_result.get("message", "HUNTER_API_KEY ainda não está configurada no serviço da API."),
                }
            )

        if hunter_result.get("status") != "found" or not hunter_result.get("email"):
            hunter_status = str(hunter_result.get("status") or "not_found")
            if hunter_status == "insufficient_data":
                insufficient_data += 1
            elif hunter_status == "provider_error":
                provider_error += 1
            elif hunter_status == "blocked":
                blocked += 1
            elif hunter_status == "not_found":
                not_found += 1
            update_candidate_state(
                candidate_id,
                str(candidate.get("stage") or CandidateStage.INGESTED.value),
                {
                    "hunter_status": hunter_status,
                    "hunter_reason": hunter_result.get("message", ""),
                    "needs_contact_enrichment": True,
                },
            )
            pending.append(
                {
                    "candidate_id": candidate_id,
                    "status": hunter_status,
                    "reason": str(hunter_result.get("message") or "Hunter não encontrou e-mail profissional."),
                }
            )
            continue

        email = str(hunter_result["email"])
        linkedin_url = str(hunter_result.get("linkedin_url") or candidate.get("linkedin_url") or "")
        updated_metadata = {
            **metadata,
            "hunter_status": "found",
            "hunter_email": email,
            "hunter_score": hunter_result.get("score"),
            "hunter_domain": hunter_result.get("domain", ""),
            "hunter_company": hunter_result.get("company", ""),
            "hunter_position": hunter_result.get("position", ""),
            "hunter_verification_status": hunter_result.get("verification_status", ""),
            "needs_contact_enrichment": False,
        }
        upsert_candidate(
            {
                "candidate_id": candidate_id,
                "tenant_id": tenant_id,
                "external_id": candidate.get("external_id") or candidate_id,
                "name": candidate.get("name") or email,
                "city": candidate.get("city") or "",
                "email": email,
                "linkedin_url": linkedin_url,
                "source_page_id": candidate.get("source_page_id"),
                "stage": str(candidate.get("stage") or CandidateStage.INGESTED.value),
                "metadata": updated_metadata,
            }
        )
        channels = [CandidateChannel.EMAIL.value]
        if linkedin_url:
            channels.append(CandidateChannel.LINKEDIN.value)
        workflow_payload = {
            "candidate_id": candidate_id,
            "tenant_id": tenant_id,
            "name": candidate.get("name") or email,
            "city": candidate.get("city") or "",
            "email": email,
            "linkedin_url": linkedin_url,
            "channels": channels,
            "source_page_id": candidate.get("source_page_id"),
            "stage": CandidateStage.INGESTED.value,
            "metadata": updated_metadata,
        }
        try:
            if temporal_client is None:
                temporal_client = await connect_temporal()
            handle = await temporal_client.start_workflow(
                CandidateLifecycleWorkflow.run,
                workflow_payload,
                id=f"candidate-lifecycle::{tenant_id}::{candidate_id}",
                task_queue=TemporalConfig().task_queue,
            )
        except WorkflowAlreadyStartedError:
            duplicates.append(candidate_id)
        else:
            started.append({"candidate_id": candidate_id, "workflow_id": handle.id, "run_id": handle.result_run_id})
        enriched.append({"candidate_id": candidate_id, "email": email, "score": hunter_result.get("score")})

    _record_audit_event(
        tenant_id=tenant_id,
        event_type="enrichment.hunter_run_requested",
        principal=principal,
        payload={
            "candidate_ids": [candidate.get("id") for candidate in candidates],
            "enriched": len(enriched),
            "started": len(started),
            "pending": len(pending),
            "duplicates": len(duplicates),
        },
    )
    return _success(
        {
            "tenant_id": tenant_id,
            "provider": "hunter",
            "configured": True,
            "enriched": enriched,
            "started": started,
            "pending": pending,
            "duplicates": duplicates,
            "already_ready": already_ready,
            "insufficient_data": insufficient_data,
            "provider_error": provider_error,
            "not_found": not_found,
            "blocked": blocked,
            "message": f"Hunter enriqueceu {len(enriched)} candidato(s), iniciou {len(started)} fluxo(s), encontrou {already_ready} já pronto(s), teve {provider_error} erro(s) do provedor, não encontrou e-mail para {not_found} e manteve {insufficient_data} sem dados suficientes.",
        }
    )


@app.get("/v1/tenants/{tenant_id}/memberships")
async def read_tenant_memberships(tenant_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return _success({"tenant_id": tenant_id, "items": list_tenant_memberships(tenant_id)})


@app.post("/v1/tenants/{tenant_id}/memberships", status_code=status.HTTP_201_CREATED)
async def upsert_membership(
    tenant_id: str,
    payload: TenantMembershipUpsertRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    user_id = payload.user_id.strip()
    email = payload.email.strip()
    if not user_id and not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID or e-mail is required")
    if not user_id:
        auth_user = find_auth_user_by_email(email)
        if not auth_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supabase Auth user not found for e-mail")
        user_id = str(auth_user["id"])
        email = str(auth_user.get("email") or email)
    membership = upsert_tenant_membership(
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "email": email,
            "role": payload.role,
        }
    )
    _record_audit_event(
        tenant_id=tenant_id,
        event_type="tenant_membership.upserted",
        principal=principal,
        payload={
            "membership_id": membership.get("id"),
            "user_id": membership.get("user_id", user_id),
            "email": membership.get("email", email),
            "role": membership.get("role", payload.role),
        },
    )
    return _success({"tenant_id": tenant_id, "membership": membership})


@app.delete("/v1/tenants/{tenant_id}/memberships/{membership_id}")
async def remove_tenant_membership(
    tenant_id: str,
    membership_id: str,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    membership = delete_tenant_membership(tenant_id, membership_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant membership not found")
    _record_audit_event(
        tenant_id=tenant_id,
        event_type="tenant_membership.deleted",
        principal=principal,
        payload={
            "membership_id": membership.get("id"),
            "user_id": membership.get("user_id", ""),
            "email": membership.get("email", ""),
            "role": membership.get("role", ""),
        },
    )
    return _success({"tenant_id": tenant_id, "membership": membership})


@app.post("/v1/tenants/{tenant_id}/api-keys", status_code=status.HTTP_201_CREATED)
async def create_tenant_api_key(
    tenant_id: str,
    payload: TenantAPIKeyCreateRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
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
    _record_audit_event(
        tenant_id=tenant_id,
        event_type="tenant_api_key.created",
        principal=principal,
        payload={
            "key_id": record.get("id"),
            "label": payload.label,
            "key_prefix": record.get("key_prefix"),
        },
    )
    return _success({"api_key": raw_key, "key": record})


@app.get("/v1/tenants/{tenant_id}/api-keys")
async def read_tenant_api_keys(tenant_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return _success({"tenant_id": tenant_id, "items": list_tenant_api_keys(tenant_id)})


@app.delete("/v1/tenants/{tenant_id}/api-keys/{api_key_id}")
async def delete_tenant_api_key(
    tenant_id: str,
    api_key_id: str,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    key = revoke_tenant_api_key(tenant_id, api_key_id)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active tenant API key not found")
    _record_audit_event(
        tenant_id=tenant_id,
        event_type="tenant_api_key.revoked",
        principal=principal,
        payload={
            "key_id": key.get("id"),
            "key_prefix": key.get("key_prefix"),
            "label": key.get("label"),
        },
    )
    return _success({"tenant_id": tenant_id, "key": key})


@app.post("/v1/tenants/{tenant_id}/api-keys/{api_key_id}/rotate", status_code=status.HTTP_201_CREATED)
async def rotate_tenant_api_key(
    tenant_id: str,
    api_key_id: str,
    payload: TenantAPIKeyCreateRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
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
    _record_audit_event(
        tenant_id=tenant_id,
        event_type="tenant_api_key.rotated",
        principal=principal,
        payload={
            "revoked_key_id": revoked_key.get("id"),
            "created_key_id": created_key.get("id"),
            "label": payload.label,
        },
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
                "metadata": {
                    "current_role": payload.current_role,
                    "current_company": payload.current_company,
                    "seniority": payload.seniority,
                    "target_profile": payload.target_profile,
                    "state": payload.state,
                },
            },
            id=f"candidate-lifecycle::{payload.tenant_id}::{candidate_id}",
            task_queue=TemporalConfig().task_queue,
        )
    except WorkflowAlreadyStartedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate lifecycle already started") from exc
    _record_audit_event(
        tenant_id=payload.tenant_id,
        event_type="candidate.create_requested",
        principal=principal,
        payload={
            "candidate_id": candidate_id,
            "name": payload.name,
            "city": payload.city,
            "email": payload.email,
            "linkedin_url": payload.linkedin_url,
            "channels": channels,
            "current_role": payload.current_role,
            "current_company": payload.current_company,
            "seniority": payload.seniority,
            "target_profile": payload.target_profile,
            "state": payload.state,
            "workflow_id": handle.id,
            "run_id": handle.result_run_id,
        },
    )
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
    return _success(_candidate_projection(candidate))


@app.post("/v1/candidates/{candidate_id}/decision")
async def update_candidate_decision(
    candidate_id: str,
    payload: CandidateDecisionRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    authorize_tenant(principal, candidate["tenant_id"])
    stage = "paused" if payload.decision == "paused" else "discarded" if payload.decision == "discarded" else "qualified"
    updated = update_candidate_state(
        candidate_id,
        stage,
        {
            "manual_decision": payload.decision,
            "manual_decision_note": payload.decision_note,
        },
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    _record_audit_event(
        tenant_id=candidate["tenant_id"],
        candidate_id=candidate_id,
        event_type="candidate.decision_updated",
        principal=principal,
        payload={"decision": payload.decision, "decision_note": payload.decision_note, "stage": stage},
    )
    return _success({"candidate": _candidate_projection(updated)})


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
    items = [_candidate_projection(candidate) for candidate in result["items"]]
    return _success({"tenant_id": tenant_id, **_page(items, page, limit, result["total"])})


@app.get("/v1/candidates/{candidate_id}/interactions")
async def read_candidate_interactions(candidate_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    authorize_tenant(principal, candidate["tenant_id"])
    return _success(
        {
            "candidate_id": candidate_id,
            "items": [_interaction_projection(interaction) for interaction in list_candidate_interactions(candidate_id)],
        }
    )


@app.post("/v1/candidates/{candidate_id}/email-follow-up", status_code=status.HTTP_201_CREATED)
async def prepare_candidate_email_follow_up(candidate_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    tenant_id = candidate["tenant_id"]
    authorize_tenant(principal, tenant_id)
    if not str(candidate.get("email") or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O candidato não tem e-mail para follow-up.")

    metadata = _tenant_metadata(tenant_id)
    limits = metadata.get("mvp_limits") if isinstance(metadata.get("mvp_limits"), dict) else {}
    if limits.get("email_enabled") is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail está desabilitado nas preferências do MVP.")
    daily_limit = int(limits.get("daily_contact_limit") or 20)
    if daily_limit > 0 and _sent_today_count(tenant_id) >= daily_limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Limite diário de e-mails atingido para esta empresa.")

    interactions = list_candidate_interactions(candidate_id)
    email_interactions = [interaction for interaction in interactions if interaction.get("channel") == CandidateChannel.EMAIL.value]
    has_sent_email = any(interaction.get("status") in {"sent", "replied", "closed"} for interaction in email_interactions)
    if not has_sent_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envie o e-mail inicial antes de preparar follow-up.")
    if any(interaction.get("status") == "replied" for interaction in email_interactions):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O candidato já respondeu. Use o acompanhamento manual da resposta.")

    step, existing = _next_follow_up_step(interactions, CandidateChannel.EMAIL)
    if existing:
        return _success({"interaction": _interaction_projection(existing), "already_prepared": True})
    max_follow_ups = max(0, min(int(limits.get("max_attempts_per_candidate") or len(FOLLOW_UP_STEPS)), len(FOLLOW_UP_STEPS)))
    if not step or FOLLOW_UP_STEPS.index(step) >= max_follow_ups:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não há novos follow-ups disponíveis para este candidato.")

    message = _follow_up_message(candidate, tenant_id, step)
    payload = {
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "name": candidate.get("name", ""),
        "email": candidate.get("email", ""),
        "city": candidate.get("city", ""),
        "linkedin_url": candidate.get("linkedin_url", ""),
        "channel": CandidateChannel.EMAIL.value,
        "message_type": "follow_up",
        "cadence_step": step,
        "status": "pending",
        "manual_approval_status": "pending",
        "message": message,
        "message_sent": message["body"],
        "next_action": "Revisar e aprovar follow-up por e-mail",
        "idempotency_key": f"{candidate_id}:email:{step}",
        "scheduled_after_days": int(limits.get("follow_up_interval_days") or 5),
    }
    created = append_interaction_row(payload)
    interaction = get_interaction(str(created.get("id"))) if created.get("id") else created
    _record_audit_event(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        event_type="interaction.email_follow_up_prepared",
        principal=principal,
        payload={"interaction_id": created.get("id"), "cadence_step": step, "scheduled_after_days": payload["scheduled_after_days"]},
    )
    return _success({"interaction": _interaction_projection(interaction), "already_prepared": False})


@app.post("/v1/candidates/{candidate_id}/linkedin-follow-up", status_code=status.HTTP_201_CREATED)
async def prepare_candidate_linkedin_follow_up(candidate_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    tenant_id = candidate["tenant_id"]
    authorize_tenant(principal, tenant_id)
    if not str(candidate.get("linkedin_url") or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O candidato não tem LinkedIn para follow-up.")

    metadata = _tenant_metadata(tenant_id)
    limits = metadata.get("mvp_limits") if isinstance(metadata.get("mvp_limits"), dict) else {}
    if limits.get("linkedin_enabled") is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LinkedIn está desabilitado nas preferências do MVP.")

    interactions = list_candidate_interactions(candidate_id)
    linkedin_interactions = [interaction for interaction in interactions if interaction.get("channel") == CandidateChannel.LINKEDIN.value]
    has_sent_linkedin = any(interaction.get("status") in {"sent", "replied", "closed"} for interaction in linkedin_interactions)
    if not has_sent_linkedin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Marque a mensagem inicial do LinkedIn como enviada antes de preparar follow-up.")
    if any(interaction.get("status") == "replied" for interaction in linkedin_interactions):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O candidato já respondeu no LinkedIn. Use o acompanhamento manual da resposta.")

    step, existing = _next_follow_up_step(interactions, CandidateChannel.LINKEDIN)
    if existing:
        return _success({"interaction": _interaction_projection(existing), "already_prepared": True})
    max_follow_ups = max(0, min(int(limits.get("max_attempts_per_candidate") or len(FOLLOW_UP_STEPS)), len(FOLLOW_UP_STEPS)))
    if not step or FOLLOW_UP_STEPS.index(step) >= max_follow_ups:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não há novos follow-ups de LinkedIn disponíveis para este candidato.")

    message = _linkedin_follow_up_message(candidate, tenant_id, step)
    payload = {
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "name": candidate.get("name", ""),
        "email": candidate.get("email", ""),
        "city": candidate.get("city", ""),
        "linkedin_url": candidate.get("linkedin_url", ""),
        "channel": CandidateChannel.LINKEDIN.value,
        "message_type": "follow_up",
        "cadence_step": step,
        "status": "pending",
        "manual_approval_status": "pending",
        "message": message,
        "message_sent": message["text"],
        "next_action": "Revisar e aprovar follow-up no LinkedIn",
        "idempotency_key": f"{candidate_id}:linkedin:{step}",
        "scheduled_after_days": int(limits.get("follow_up_interval_days") or 5),
        "provider_target": "expandi",
    }
    created = append_interaction_row(payload)
    interaction = get_interaction(str(created.get("id"))) if created.get("id") else created
    _record_audit_event(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        event_type="interaction.linkedin_follow_up_prepared",
        principal=principal,
        payload={"interaction_id": created.get("id"), "cadence_step": step, "provider_target": "expandi", "scheduled_after_days": payload["scheduled_after_days"]},
    )
    return _success({"interaction": _interaction_projection(interaction), "already_prepared": False})


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
    items = [_interaction_projection(interaction) for interaction in result["items"]]
    return _success({"tenant_id": tenant_id, **_page(items, page, limit, result["total"])})


@app.post("/v1/interactions/{interaction_id}/status")
async def update_interaction_status_route(
    interaction_id: str,
    payload: InteractionStatusUpdateRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    interaction = get_interaction(interaction_id)
    if not interaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
    authorize_tenant(principal, interaction["tenant_id"])

    payload_updates: Dict[str, Any] = {}
    interaction_payload = interaction.get("payload_json") or {}
    if not isinstance(interaction_payload, dict):
        interaction_payload = {}
    if payload.status == "sent" and interaction.get("status") != "approved" and interaction_payload.get("manual_approval_status") != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message must be approved before send")
    if payload.response_received:
        payload_updates["response_received"] = payload.response_received
    if payload.status == "sent":
        if interaction.get("channel") == CandidateChannel.EMAIL.value:
            resend_result = _send_resend_email(interaction)
            payload_updates["email_provider"] = "resend"
            payload_updates["provider_message_id"] = resend_result.get("provider_message_id", "")
            payload_updates["email_sent_to"] = resend_result.get("to", "")
            payload_updates["email_subject"] = resend_result.get("subject", "")
            payload_updates["sent_at"] = datetime.now(timezone.utc).isoformat()
        elif interaction.get("channel") == CandidateChannel.LINKEDIN.value:
            expandi_result = _send_expandi_linkedin_message(interaction)
            payload_updates["linkedin_provider"] = expandi_result.get("provider", "manual")
            payload_updates["provider_message_id"] = expandi_result.get("provider_message_id", "")
            payload_updates["provider_executed"] = bool(expandi_result.get("executed"))
            payload_updates["sent_at"] = datetime.now(timezone.utc).isoformat()
        payload_updates["manual_approval_status"] = "sent"
    if payload.status == "replied":
        payload_updates["manual_approval_status"] = "replied"
    updated = update_interaction_status(interaction_id, payload.status, payload_updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
    if payload.status == "sent":
        _record_audit_event(
            tenant_id=interaction["tenant_id"],
            candidate_id=interaction["candidate_id"],
            event_type="interaction.email_sent" if interaction.get("channel") == CandidateChannel.EMAIL.value else "interaction.marked_sent",
            principal=principal,
            payload={"interaction_id": interaction_id, "channel": interaction.get("channel"), "provider": payload_updates.get("email_provider", "manual")},
        )
    return _success({"interaction": _interaction_projection(updated)})


@app.post("/v1/providers/expandi/status")
async def sync_expandi_status(
    payload: ExpandiStatusSyncRequest,
    request: Request,
) -> Dict[str, Any]:
    webhook_secret = env("EXPANDI_STATUS_WEBHOOK_SECRET")
    provided_secret = request.headers.get("X-Expandi-Webhook-Secret", "")
    if webhook_secret and provided_secret == webhook_secret:
        principal = APIPrincipal(role="admin", auth_method="expandi_webhook")
    else:
        if webhook_secret and provided_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Expandi webhook secret")
        principal = require_principal(
            authorization=request.headers.get("Authorization"),
            x_api_key=request.headers.get("X-API-Key"),
        )

    lookup_payload = dict(payload.raw or {})
    for key, value in payload.model_dump().items():
        if value not in ("", {}, None):
            lookup_payload[key] = value
    interaction = find_linkedin_interaction_for_status(lookup_payload)
    if not interaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LinkedIn interaction not found for Expandi status")
    authorize_tenant(principal, interaction["tenant_id"])

    updated = _apply_expandi_status(interaction, payload, principal)
    return _success({"interaction": _interaction_projection(updated)})


@app.post("/v1/tenants/{tenant_id}/providers/expandi/poll")
async def poll_expandi_status(
    tenant_id: str,
    payload: ExpandiPollSyncRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    require_tenant_admin(principal, tenant_id)
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    interactions = list_tenant_expandi_interactions(tenant_id, payload.limit)
    interactions_by_interaction_id = {str(interaction.get("id")): interaction for interaction in interactions}
    interactions_by_candidate_id = {str(interaction.get("candidate_id")): interaction for interaction in interactions}
    interactions_by_provider_id = {}
    for interaction in interactions:
        _interaction_id, _candidate_id, provider_id = _interaction_lookup_key(interaction)
        if provider_id:
            interactions_by_provider_id[provider_id] = interaction

    items = _fetch_expandi_status_items(payload.limit)
    synced: List[Dict[str, Any]] = []
    unmatched: List[Dict[str, Any]] = []
    for item in items:
        status_request = _expandi_item_to_status_request(item)
        match = (
            interactions_by_interaction_id.get(status_request.interaction_id)
            or interactions_by_provider_id.get(status_request.provider_message_id or status_request.lead_id)
            or interactions_by_candidate_id.get(status_request.candidate_id)
        )
        if not match:
            unmatched.append(
                {
                    "provider_message_id": status_request.provider_message_id or status_request.lead_id,
                    "candidate_id": status_request.candidate_id,
                    "status": status_request.status,
                }
            )
            continue

        status_request = _expandi_item_to_status_request(item, match)
        if payload.dry_run:
            normalized = _normalize_expandi_status(status_request.status, status_request.event)
            synced.append(
                {
                    "interaction_id": str(match.get("id")),
                    "candidate_id": str(match.get("candidate_id")),
                    "provider_status": normalized["provider_status"],
                    "provider_status_label": normalized["label"],
                    "dry_run": True,
                }
            )
            continue

        updated = _apply_expandi_status(match, status_request, principal)
        projected = _interaction_projection(updated)
        synced.append(
            {
                "interaction_id": projected["id"],
                "candidate_id": projected["candidate_id"],
                "provider_status": projected.get("provider_status"),
                "provider_status_label": projected.get("provider_status_label"),
            }
        )

    return _success(
        {
            "tenant_id": tenant_id,
            "checked": len(items),
            "synced": synced,
            "unmatched": unmatched,
            "dry_run": payload.dry_run,
        }
    )


@app.post("/v1/interactions/{interaction_id}/review")
async def review_interaction_message(
    interaction_id: str,
    payload: InteractionReviewRequest,
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    interaction = get_interaction(interaction_id)
    if not interaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
    authorize_tenant(principal, interaction["tenant_id"])

    interaction_payload = interaction.get("payload_json") or {}
    if not isinstance(interaction_payload, dict):
        interaction_payload = {}
    message = interaction_payload.get("message") if isinstance(interaction_payload.get("message"), dict) else {}
    reviewed_message = {**message, "body": payload.message_sent}
    if payload.subject:
        reviewed_message["subject"] = payload.subject

    updated = update_interaction_status(
        interaction_id,
        payload.status,
        {
            "message": reviewed_message,
            "message_sent": payload.message_sent,
            "email_subject": reviewed_message.get("subject", ""),
            "manual_approval_status": payload.status,
            "manual_decision_note": payload.decision_note,
        },
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
    _record_audit_event(
        tenant_id=interaction["tenant_id"],
        candidate_id=interaction["candidate_id"],
        event_type="interaction.message_reviewed",
        principal=principal,
        payload={"interaction_id": interaction_id, "status": payload.status, "decision_note": payload.decision_note},
    )
    return _success({"interaction": _interaction_projection(updated)})


@app.get("/v1/tenants/{tenant_id}/workflow-runs")
async def read_tenant_workflow_runs(
    tenant_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    authorize_tenant(principal, tenant_id)
    result = list_tenant_workflow_runs(tenant_id, page, limit)
    return _success({"tenant_id": tenant_id, **_page(result["items"], page, limit, result["total"])})


@app.get("/v1/tenants/{tenant_id}/audit-events")
async def read_tenant_audit_events(
    tenant_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: APIPrincipal = Depends(require_principal),
) -> Dict[str, Any]:
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    authorize_tenant(principal, tenant_id)
    result = list_tenant_audit_events(tenant_id, page, limit)
    return _success({"tenant_id": tenant_id, **_page(result["items"], page, limit, result["total"])})


@app.get("/v1/tenants/{tenant_id}/metrics")
async def read_tenant_metrics(tenant_id: str, principal: APIPrincipal = Depends(require_principal)) -> Dict[str, Any]:
    if not tenant_exists(tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    authorize_tenant(principal, tenant_id)
    return _success({"tenant_id": tenant_id, **tenant_metrics(tenant_id)})
