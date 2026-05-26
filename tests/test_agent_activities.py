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
    assert classification["result"]["classification"]["classification"] == "A"
    assert message["result"]["message"]["subject"] == "Conversa sobre oportunidade para Candidate One"


def test_linkedin_template_uses_text_message(monkeypatch) -> None:
    monkeypatch.delenv("OUTREACH_TEMPLATE_WEBHOOK_URL", raising=False)

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
