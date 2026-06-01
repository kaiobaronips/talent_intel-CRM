from __future__ import annotations

import json
from typing import Any
import urllib.error
import urllib.request

from temporalio import activity

from talent_intel_crm.db import get_tenant
from talent_intel_crm.support import action_result, env, post_json
from talent_intel_crm.telemetry import measure


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _candidate_sources(payload: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    if _clean_text(payload.get("linkedin_url")):
        sources.append("linkedin")
    if _clean_text(payload.get("email")):
        sources.append("email")
    if _clean_text(payload.get("source_page_id")):
        sources.append("source_page")
    return sources


def _tenant_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = _clean_text(payload.get("tenant_id"))
    if not tenant_id:
        return {}
    try:
        tenant = get_tenant(tenant_id)
    except Exception:
        return {}
    metadata = tenant.get("metadata_json") or {}
    return metadata if isinstance(metadata, dict) else {}


def _json_from_text(value: str) -> dict[str, Any]:
    raw = value.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            parsed = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _chat_json(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    response_format: bool = True,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not api_key or not model:
        return {}
    request_payload: dict[str, Any] = {
        "model": model,
        "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
    }
    if response_format:
        request_payload["response_format"] = {"type": "json_object"}
    body = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return {}
    choices = payload.get("choices") if isinstance(payload, dict) else []
    if not choices:
        return {}
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    return _json_from_text(content) if isinstance(content, str) else {}


def _openai_chat_json(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    return _chat_json(
        endpoint="https://api.openai.com/v1/chat/completions",
        api_key=env("OPENAI_API_KEY"),
        model=env("OPENAI_MODEL", "gpt-4.1-mini"),
        system_prompt=system_prompt,
        user_payload=user_payload,
    )


def _openrouter_chat_json(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    return _chat_json(
        endpoint="https://openrouter.ai/api/v1/chat/completions",
        api_key=env("OPENROUTER_API_KEY"),
        model=env("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash"),
        system_prompt=system_prompt,
        user_payload=user_payload,
        response_format=False,
        extra_headers={
            "HTTP-Referer": env("OPENROUTER_SITE_URL", "https://talent-intel-crm.vercel.app"),
            "X-Title": env("OPENROUTER_APP_TITLE", "Talent Intel CRM"),
        },
    )


def _llm_provider_order() -> tuple[tuple[str, Any], ...]:
    providers = {
        "openai": _openai_chat_json,
        "openrouter": _openrouter_chat_json,
    }
    preferred = env("LLM_PROVIDER").lower()
    if preferred in providers:
        fallback = "openrouter" if preferred == "openai" else "openai"
        return ((preferred, providers[preferred]), (fallback, providers[fallback]))
    return (("openai", _openai_chat_json), ("openrouter", _openrouter_chat_json))


def _llm_chat_json(system_prompt: str, user_payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for provider, chat in _llm_provider_order():
        for _ in range(2):
            result = chat(system_prompt, user_payload)
            if result:
                return provider, result
    return "", {}


def _dry_enrichment(payload: dict[str, Any]) -> dict[str, Any]:
    role = _clean_text(payload.get("current_role") or payload.get("role"))
    company = _clean_text(payload.get("current_company") or payload.get("company"))
    seniority = _clean_text(payload.get("seniority"))
    summary_parts = []
    if role:
        summary_parts.append(role)
    if company:
        summary_parts.append(f"atual em {company}")
    if seniority:
        summary_parts.append(f"senioridade {seniority}")

    return {
        "enrichment_status": "dry_run",
        "current_role": role,
        "current_company": company,
        "seniority": seniority,
        "profile_summary": ", ".join(summary_parts) if summary_parts else "Perfil aguardando enriquecimento externo.",
        "profile_sources": _candidate_sources(payload),
        "contactability": {
            "email": bool(_clean_text(payload.get("email"))),
            "linkedin": bool(_clean_text(payload.get("linkedin_url"))),
        },
    }


def _dry_classification(payload: dict[str, Any]) -> dict[str, Any]:
    score = 45
    if _clean_text(payload.get("linkedin_url")):
        score += 20
    if _clean_text(payload.get("email")):
        score += 15
    if _clean_text(payload.get("city")):
        score += 10
    if _clean_text(payload.get("current_role")):
        score += 10

    score = min(score, 100)
    if score >= 80:
        classification = "A"
    elif score >= 65:
        classification = "B"
    else:
        classification = "C"

    reasons = []
    if _clean_text(payload.get("linkedin_url")):
        reasons.append("perfil de LinkedIn disponível")
    if _clean_text(payload.get("email")):
        reasons.append("e-mail disponível")
    if _clean_text(payload.get("current_role")):
        reasons.append("cargo atual informado")
    if _clean_text(payload.get("target_profile")):
        reasons.append("perfil alvo informado")
    reason_text = "Aderência calculada com base em " + ", ".join(reasons) + "." if reasons else "Aderência inicial calculada com poucos dados disponíveis."

    return {
        "classification_status": "dry_run",
        "score_overall": score,
        "classification": classification,
        "classification_reason": reason_text,
        "recommended_action": "Priorizar abordagem consultiva e validar interesse em uma conversa curta.",
        "score_mode": "informational_only",
    }


def _openai_classification(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = _tenant_metadata(payload)
    provider, result = _llm_chat_json(
        (
            "Voce e um agente de recrutamento B2B para o Talent Intel CRM. "
            "Classifique o candidato em PT-BR usando apenas os dados fornecidos. "
            "Retorne JSON com: score_overall numero 0-100, classification A/B/C, "
            "classification_reason, recommended_action, profile_summary. "
            "Nao invente dados; quando faltar informacao, diga que precisa validacao."
        ),
        {
            "candidate": payload,
            "ideal_profile": metadata.get("ideal_profile", {}),
            "mvp_limits": metadata.get("mvp_limits", {}),
        },
    )
    if not result:
        return {}
    score = result.get("score_overall")
    try:
        score_value = max(0, min(100, int(score)))
    except (TypeError, ValueError):
        score_value = _dry_classification(payload)["score_overall"]
    classification = _clean_text(result.get("classification")).upper()
    if classification not in {"A", "B", "C"}:
        classification = "A" if score_value >= 80 else "B" if score_value >= 65 else "C"
    return {
        "classification_status": provider,
        "score_overall": score_value,
        "classification": classification,
        "classification_reason": _clean_text(result.get("classification_reason")) or _dry_classification(payload)["classification_reason"],
        "recommended_action": _clean_text(result.get("recommended_action")) or "Revisar o perfil e aprovar mensagem antes do envio.",
        "profile_summary": _clean_text(result.get("profile_summary")) or _dry_enrichment(payload)["profile_summary"],
        "score_mode": "ai_assisted_manual_approval",
    }


def _dry_message(payload: dict[str, Any]) -> dict[str, Any]:
    name = _clean_text(payload.get("name")) or "candidato"
    channel = _clean_text(payload.get("channel")) or "email"
    role = _clean_text(payload.get("current_role")) or "seu perfil"

    if channel == "linkedin":
        text = (
            f"Olá {name}, vi sua atuação como {role} e acredito que pode haver uma oportunidade aderente ao seu momento. "
            "Podemos conversar rapidamente esta semana?"
        )
        return {"text": text, "language": "pt-BR", "template_status": "dry_run"}

    subject = f"Conversa sobre oportunidade para {name}"
    body = (
        f"Olá {name},\n\n"
        f"Analisei sua atuação como {role} e gostaria de apresentar uma oportunidade que pode fazer sentido para você. "
        "Podemos agendar uma conversa rápida esta semana?\n\n"
        "Obrigado."
    )
    return {"subject": subject, "body": body, "language": "pt-BR", "template_status": "dry_run"}


def _openai_message(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = _tenant_metadata(payload)
    channel = _clean_text(payload.get("channel")) or "email"
    provider, result = _llm_chat_json(
        (
            "Voce escreve mensagens curtas de recrutamento em PT-BR. "
            "Use os templates como base, personalize com os dados do candidato e mantenha tom humano. "
            "Nao prometa salario, vaga ou entrevista. Retorne JSON. "
            'Para email, retorne exatamente: {"subject":"...", "body":"..."}. '
            'Para linkedin, retorne exatamente: {"text":"..."}. '
            "Sempre inclua language e template_status quando possivel."
        ),
        {
            "candidate": payload,
            "channel": channel,
            "message_type": payload.get("message_type", "initial"),
            "ideal_profile": metadata.get("ideal_profile", {}),
            "message_templates": metadata.get("message_templates", {}),
        },
    )
    if not result:
        return {}
    if channel == "linkedin":
        text = _clean_text(result.get("text"))
        if not text:
            return {}
        return {"text": text, "language": "pt-BR", "template_status": provider}
    subject = _clean_text(result.get("subject"))
    body = _clean_text(result.get("body"))
    if not subject or not body:
        return {}
    return {"subject": subject, "body": body, "language": "pt-BR", "template_status": provider}


@activity.defn
def search_linkedin_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    """Search external sources for candidate prospects."""
    endpoint = env("LINKEDIN_SEARCH_WEBHOOK_URL")
    if not endpoint:
        return action_result(
            "linkedin.search_candidates",
            payload,
            executed=False,
            result={"candidates": [], "search_status": "dry_run"},
        )
    result = measure(
        "activity.agent.linkedin_search",
        lambda: post_json(endpoint, payload),
        tenant_id=payload.get("tenant_id", ""),
    )
    return action_result("linkedin.search_candidates", payload, endpoint, True, result)


@activity.defn
def enrich_candidate_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Enrich a candidate profile through configured providers."""
    endpoint = env("CANDIDATE_ENRICHMENT_WEBHOOK_URL")
    if not endpoint:
        return action_result(
            "candidate.enrich_profile",
            payload,
            executed=False,
            result={"enrichment": _dry_enrichment(payload)},
        )
    result = measure(
        "activity.agent.enrichment",
        lambda: post_json(endpoint, payload),
        tenant_id=payload.get("tenant_id", ""),
        candidate_id=payload.get("candidate_id", ""),
    )
    return action_result("candidate.enrich_profile", payload, endpoint, True, result)


@activity.defn
def classify_candidate_fit(payload: dict[str, Any]) -> dict[str, Any]:
    """Classify candidate fit for prioritization and routing."""
    endpoint = env("CANDIDATE_CLASSIFICATION_WEBHOOK_URL")
    openai_result = measure(
        "activity.agent.classification_openai",
        lambda: _openai_classification(payload),
        tenant_id=payload.get("tenant_id", ""),
        candidate_id=payload.get("candidate_id", ""),
    )
    if openai_result:
        return action_result(
            "candidate.classify_fit",
            payload,
            endpoint=openai_result.get("classification_status", "llm"),
            executed=True,
            result={"classification": openai_result},
        )
    if not endpoint:
        return action_result(
            "candidate.classify_fit",
            payload,
            executed=False,
            result={"classification": _dry_classification(payload)},
        )
    result = measure(
        "activity.agent.classification",
        lambda: post_json(endpoint, payload),
        tenant_id=payload.get("tenant_id", ""),
        candidate_id=payload.get("candidate_id", ""),
    )
    return action_result("candidate.classify_fit", payload, endpoint, True, result)


@activity.defn
def render_outreach_message(payload: dict[str, Any]) -> dict[str, Any]:
    """Render channel-specific outreach copy before dispatch."""
    endpoint = env("OUTREACH_TEMPLATE_WEBHOOK_URL")
    openai_result = measure(
        "activity.agent.outreach_template_openai",
        lambda: _openai_message(payload),
        tenant_id=payload.get("tenant_id", ""),
        candidate_id=payload.get("candidate_id", ""),
        channel=payload.get("channel", ""),
    )
    if openai_result:
        return action_result(
            "outreach.render_message",
            payload,
            endpoint=openai_result.get("template_status", "llm"),
            executed=True,
            result={"message": openai_result},
        )
    if not endpoint:
        return action_result(
            "outreach.render_message",
            payload,
            executed=False,
            result={"message": _dry_message(payload)},
        )
    result = measure(
        "activity.agent.outreach_template",
        lambda: post_json(endpoint, payload),
        tenant_id=payload.get("tenant_id", ""),
        candidate_id=payload.get("candidate_id", ""),
        channel=payload.get("channel", ""),
    )
    return action_result("outreach.render_message", payload, endpoint, True, result)
