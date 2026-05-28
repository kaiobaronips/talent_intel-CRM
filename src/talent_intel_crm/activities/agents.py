from __future__ import annotations

from typing import Any

from temporalio import activity

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
