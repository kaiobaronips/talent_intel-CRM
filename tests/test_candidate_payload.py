from talent_intel_crm.candidate_payload import candidate_from_input, candidate_record, candidate_result, interaction_record, normalize_channels
from talent_intel_crm.domain import CandidateChannel, CandidateStage


def test_candidate_payload_normalizes_channels_and_stage() -> None:
    candidate = candidate_from_input(
        {
            "candidate_id": "candidate-001",
            "name": "Candidate One",
            "tenant_id": "tenant-001",
            "stage": "contacted",
            "channels": ["email", "email", "linkedin", "invalid"],
        }
    )

    assert candidate.stage == CandidateStage.CONTACTED
    assert normalize_channels(candidate.channels) == [CandidateChannel.EMAIL, CandidateChannel.LINKEDIN]
    assert candidate_result(candidate)["channels"] == ["email", "linkedin"]


def test_interaction_record_builds_stable_cadence_key() -> None:
    candidate = candidate_from_input(
        {
            "candidate_id": "candidate-001",
            "name": "Candidate One",
            "tenant_id": "tenant-001",
            "channels": ["linkedin"],
        }
    )

    record = interaction_record(candidate, CandidateChannel.LINKEDIN, "follow_up", cadence_step="d7")

    assert record["idempotency_key"] == "candidate-001:linkedin:d7"
    assert record["cadence_step"] == "d7"


def test_candidate_record_preserves_input_metadata() -> None:
    candidate = candidate_from_input(
        {
            "candidate_id": "candidate-001",
            "name": "Candidate One",
            "tenant_id": "tenant-001",
            "metadata": {
                "current_role": "Account Executive",
                "current_company": "Acme",
            },
        }
    )

    record = candidate_record(candidate, CandidateStage.ENRICHED, enrichment_status="dry_run")

    assert record["metadata"]["current_role"] == "Account Executive"
    assert record["metadata"]["current_company"] == "Acme"
    assert record["metadata"]["enrichment_status"] == "dry_run"
