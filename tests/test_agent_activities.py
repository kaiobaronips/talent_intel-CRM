from talent_intel_crm.activities.agents import (
    classify_candidate_fit,
    enrich_candidate_profile,
    render_outreach_message,
    search_linkedin_candidates,
)


def test_agent_activities_return_dry_run_payloads(monkeypatch) -> None:
    monkeypatch.delenv("LINKEDIN_SEARCH_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("CANDIDATE_ENRICHMENT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("CANDIDATE_CLASSIFICATION_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("OUTREACH_TEMPLATE_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    payload = {
        "candidate_id": "candidate-001",
        "tenant_id": "tenant-001",
        "name": "Candidate One",
        "city": "Sao Paulo",
        "email": "candidate@example.com",
        "linkedin_url": "https://www.linkedin.com/in/candidate-one",
        "current_role": "Account Executive",
    }

    search = search_linkedin_candidates({"tenant_id": "tenant-001", "query": "Account Executive"})
    enrichment = enrich_candidate_profile(payload)
    classification = classify_candidate_fit(payload)
    message = render_outreach_message({**payload, "channel": "email"})

    assert search["executed"] is False
    assert search["result"]["search_status"] == "dry_run"
    assert enrichment["result"]["enrichment"]["contactability"] == {"email": True, "linkedin": True}
    assert enrichment["result"]["enrichment"]["profile_summary"] == "Account Executive"
    assert classification["result"]["classification"]["classification"] == "A"
    assert "classification_reason" in classification["result"]["classification"]
    assert "recommended_action" in classification["result"]["classification"]
    assert message["result"]["message"]["subject"] == "Conversa sobre oportunidade para Candidate One"


def test_linkedin_template_uses_text_message(monkeypatch) -> None:
    monkeypatch.delenv("OUTREACH_TEMPLATE_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    result = render_outreach_message(
        {
            "candidate_id": "candidate-001",
            "tenant_id": "tenant-001",
            "name": "Candidate One",
            "channel": "linkedin",
            "current_role": "Assessor de Investimentos",
        }
    )

    assert result["executed"] is False
    assert "Candidate One" in result["result"]["message"]["text"]
    assert result["result"]["message"]["language"] == "pt-BR"


def test_openai_classification_is_used_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "talent_intel_crm.activities.agents._openai_chat_json",
        lambda _prompt, _payload: {
            "score_overall": 91,
            "classification": "A",
            "classification_reason": "Perfil aderente ao cargo alvo.",
            "recommended_action": "Aprovar abordagem consultiva.",
            "profile_summary": "Executivo comercial B2B.",
        },
    )
    monkeypatch.setattr("talent_intel_crm.activities.agents._tenant_metadata", lambda _payload: {"ideal_profile": {"target_roles": "Comercial"}})

    result = classify_candidate_fit({"candidate_id": "candidate-001", "tenant_id": "tenant-001", "name": "Candidate One"})

    assert result["executed"] is True
    assert result["endpoint"] == "openai"
    assert result["result"]["classification"]["classification_status"] == "openai"
    assert result["result"]["classification"]["score_overall"] == 91


def test_openrouter_classification_is_used_when_openai_fails(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-router-key")
    monkeypatch.setattr("talent_intel_crm.activities.agents._openai_chat_json", lambda _prompt, _payload: {})
    monkeypatch.setattr(
        "talent_intel_crm.activities.agents._openrouter_chat_json",
        lambda _prompt, _payload: {
            "score_overall": 84,
            "classification": "A",
            "classification_reason": "Perfil aderente com validação pendente.",
            "recommended_action": "Revisar e aprovar abordagem.",
            "profile_summary": "Executivo comercial.",
        },
    )
    monkeypatch.setattr("talent_intel_crm.activities.agents._tenant_metadata", lambda _payload: {"ideal_profile": {"target_roles": "Comercial"}})

    result = classify_candidate_fit({"candidate_id": "candidate-001", "tenant_id": "tenant-001", "name": "Candidate One"})

    assert result["executed"] is True
    assert result["endpoint"] == "openrouter"
    assert result["result"]["classification"]["classification_status"] == "openrouter"
    assert result["result"]["classification"]["score_overall"] == 84


def test_llm_provider_can_prioritize_openrouter(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-router-key")

    def openai(_prompt, _payload):
        calls.append("openai")
        return {}

    def openrouter(_prompt, _payload):
        calls.append("openrouter")
        return {
            "score_overall": 77,
            "classification": "B",
            "classification_reason": "Perfil parcialmente aderente.",
            "recommended_action": "Revisar antes do envio.",
            "profile_summary": "Executivo comercial.",
        }

    monkeypatch.setattr("talent_intel_crm.activities.agents._openai_chat_json", openai)
    monkeypatch.setattr("talent_intel_crm.activities.agents._openrouter_chat_json", openrouter)
    monkeypatch.setattr("talent_intel_crm.activities.agents._tenant_metadata", lambda _payload: {})

    result = classify_candidate_fit({"candidate_id": "candidate-001", "tenant_id": "tenant-001", "name": "Candidate One"})

    assert calls == ["openrouter"]
    assert result["endpoint"] == "openrouter"


def test_openai_message_is_used_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "talent_intel_crm.activities.agents._openai_chat_json",
        lambda _prompt, _payload: {
            "subject": "Conversa rápida",
            "body": "Olá Candidate One, podemos conversar?",
        },
    )
    monkeypatch.setattr("talent_intel_crm.activities.agents._tenant_metadata", lambda _payload: {"message_templates": {}})

    result = render_outreach_message({"candidate_id": "candidate-001", "tenant_id": "tenant-001", "name": "Candidate One", "channel": "email"})

    assert result["executed"] is True
    assert result["endpoint"] == "openai"
    assert result["result"]["message"]["template_status"] == "openai"
    assert result["result"]["message"]["subject"] == "Conversa rápida"
