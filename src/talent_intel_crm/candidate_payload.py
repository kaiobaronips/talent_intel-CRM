from __future__ import annotations

from typing import Any, Dict, Iterable, Union

from talent_intel_crm.domain import CandidateChannel, CandidateEnvelope, CandidateStage


def normalize_stage(value: object) -> CandidateStage:
    if isinstance(value, CandidateStage):
        return value
    if isinstance(value, str):
        try:
            return CandidateStage(value)
        except ValueError:
            pass
    return CandidateStage.INGESTED


def normalize_channels(values: object) -> list[CandidateChannel]:
    if values is None or isinstance(values, (str, bytes)):
        return []
    if not isinstance(values, Iterable):
        return []

    result: list[CandidateChannel] = []
    for value in values:
        if isinstance(value, CandidateChannel):
            channel = value
        elif isinstance(value, str):
            try:
                channel = CandidateChannel(value)
            except ValueError:
                continue
        else:
            continue
        if channel not in result:
            result.append(channel)
    return result


def candidate_from_input(value: Union[Dict[str, Any], CandidateEnvelope]) -> CandidateEnvelope:
    if isinstance(value, CandidateEnvelope):
        value.stage = normalize_stage(value.stage)
        value.channels = normalize_channels(value.channels)
        return value
    if not isinstance(value, dict):
        raise TypeError("Candidate workflow expects a dict payload or CandidateEnvelope")
    return CandidateEnvelope(
        candidate_id=str(value.get("candidate_id", "")),
        name=str(value.get("name", "")),
        tenant_id=str(value.get("tenant_id", "default")),
        city=str(value.get("city", "")),
        email=str(value.get("email", "")),
        linkedin_url=str(value.get("linkedin_url", "")),
        stage=normalize_stage(value.get("stage")),
        channels=normalize_channels(value.get("channels")),
        source_page_id=str(value.get("source_page_id")) if value.get("source_page_id") else None,
    )


def candidate_result(candidate: CandidateEnvelope) -> Dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "tenant_id": candidate.tenant_id,
        "name": candidate.name,
        "city": candidate.city,
        "email": candidate.email,
        "linkedin_url": candidate.linkedin_url,
        "stage": normalize_stage(candidate.stage).value,
        "channels": [channel.value for channel in normalize_channels(candidate.channels)],
        "source_page_id": candidate.source_page_id,
    }


def candidate_record(candidate: CandidateEnvelope, stage: CandidateStage, **metadata: object) -> Dict[str, Any]:
    record = candidate_result(candidate)
    record["stage"] = stage.value
    if metadata:
        record["metadata"] = metadata
    return record


def interaction_record(
    candidate: CandidateEnvelope,
    channel: CandidateChannel,
    message_type: str,
    cadence_step: str = "",
) -> Dict[str, Any]:
    suffix = cadence_step or message_type
    return {
        "candidate_id": candidate.candidate_id,
        "tenant_id": candidate.tenant_id,
        "name": candidate.name,
        "channel": channel.value,
        "message_type": message_type,
        "city": candidate.city,
        "email": candidate.email,
        "linkedin_url": candidate.linkedin_url,
        "stage": normalize_stage(candidate.stage).value,
        "source_page_id": candidate.source_page_id,
        "cadence_step": cadence_step,
        "idempotency_key": f"{candidate.candidate_id}:{channel.value}:{suffix}",
    }
