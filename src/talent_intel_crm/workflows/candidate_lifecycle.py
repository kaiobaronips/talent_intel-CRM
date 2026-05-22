from datetime import timedelta
from typing import Any, Dict, Union

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.email import send_initial_email
    from talent_intel_crm.activities.linkedin import enqueue_linkedin_message
    from talent_intel_crm.activities.persistence import append_interaction, record_audit_event, record_workflow_run, upsert_candidate_record
    from talent_intel_crm.domain import CandidateChannel, CandidateEnvelope, CandidateStage


def _candidate_from_input(value: Union[Dict[str, Any], CandidateEnvelope]) -> CandidateEnvelope:
    if isinstance(value, CandidateEnvelope):
        return value
    if not isinstance(value, dict):
        raise TypeError("CandidateLifecycleWorkflow expects a dict payload or CandidateEnvelope")
    return CandidateEnvelope(
        candidate_id=str(value.get("candidate_id", "")),
        name=str(value.get("name", "")),
        tenant_id=str(value.get("tenant_id", "default")),
        city=str(value.get("city", "")),
        email=str(value.get("email", "")),
        linkedin_url=str(value.get("linkedin_url", "")),
        stage=_normalize_stage(value.get("stage")),
        channels=_normalize_channels(value.get("channels")),
        source_page_id=str(value.get("source_page_id")) if value.get("source_page_id") else None,
    )


def _normalize_stage(value: object) -> CandidateStage:
    if isinstance(value, CandidateStage):
        return value
    if isinstance(value, str):
        try:
            return CandidateStage(value)
        except ValueError:
            return CandidateStage.INGESTED
    return CandidateStage.INGESTED


def _normalize_channels(values: object) -> list[CandidateChannel]:
    if isinstance(values, (str, bytes)) or values is None:
        return []
    if not isinstance(values, (list, tuple, set)):
        try:
            values = list(values)
        except TypeError:
            return []
    result: list[CandidateChannel] = []
    for value in values:
        if isinstance(value, CandidateChannel):
            result.append(value)
            continue
        if isinstance(value, str):
            try:
                result.append(CandidateChannel(value))
            except ValueError:
                continue
    return result


def _stage_value(value: object) -> str:
    return _normalize_stage(value).value


def _candidate_record(candidate: CandidateEnvelope, stage: CandidateStage) -> dict[str, object]:
    return {
        "candidate_id": candidate.candidate_id,
        "tenant_id": candidate.tenant_id,
        "name": candidate.name,
        "city": candidate.city,
        "email": candidate.email,
        "linkedin_url": candidate.linkedin_url,
        "stage": stage.value,
        "channels": [channel.value for channel in candidate.channels],
        "source_page_id": candidate.source_page_id,
    }


def _interaction_record(candidate: CandidateEnvelope, channel: CandidateChannel, message_type: str) -> dict[str, object]:
    return {
        "candidate_id": candidate.candidate_id,
        "tenant_id": candidate.tenant_id,
        "name": candidate.name,
        "channel": channel.value,
        "message_type": message_type,
        "city": candidate.city,
        "email": candidate.email,
        "linkedin_url": candidate.linkedin_url,
        "stage": candidate.stage.value,
        "source_page_id": candidate.source_page_id,
    }


def _candidate_result(candidate: CandidateEnvelope) -> Dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "tenant_id": candidate.tenant_id,
        "name": candidate.name,
        "city": candidate.city,
        "email": candidate.email,
        "linkedin_url": candidate.linkedin_url,
        "stage": candidate.stage.value,
        "channels": [channel.value for channel in candidate.channels],
        "source_page_id": candidate.source_page_id,
    }


@workflow.defn
class CandidateLifecycleWorkflow:
    """Main candidate lifecycle orchestration."""

    @workflow.run
    async def run(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        candidate = _candidate_from_input(candidate)
        workflow.logger.info("Starting candidate lifecycle", extra={"candidate_id": candidate.candidate_id})
        candidate.stage = _normalize_stage(candidate.stage)
        candidate.channels = _normalize_channels(candidate.channels)
        info = workflow.info()
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": candidate.tenant_id,
                "workflow_name": "CandidateLifecycle",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Running",
                "payload": {"stage": _stage_value(candidate.stage)},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.INGESTED
        await workflow.execute_activity(
            upsert_candidate_record,
            _candidate_record(candidate, CandidateStage.INGESTED),
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.ENRICHED
        await workflow.execute_activity(
            upsert_candidate_record,
            _candidate_record(candidate, CandidateStage.ENRICHED),
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.QUALIFIED
        await workflow.execute_activity(
            upsert_candidate_record,
            _candidate_record(candidate, CandidateStage.QUALIFIED),
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.READY_TO_CONTACT
        await workflow.execute_activity(
            upsert_candidate_record,
            _candidate_record(candidate, CandidateStage.READY_TO_CONTACT),
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        if CandidateChannel.EMAIL in candidate.channels and candidate.email:
            await workflow.execute_activity(
                send_initial_email,
                {
                    "candidate_id": candidate.candidate_id,
                    "tenant_id": candidate.tenant_id,
                    "name": candidate.name,
                    "city": candidate.city,
                    "email": candidate.email,
                    "source_page_id": candidate.source_page_id,
                    "channel": CandidateChannel.EMAIL.value,
                    "message_type": "initial",
                },
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            await workflow.execute_activity(
                append_interaction,
                _interaction_record(candidate, CandidateChannel.EMAIL, "initial"),
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

        if CandidateChannel.LINKEDIN in candidate.channels and candidate.linkedin_url:
            await workflow.execute_activity(
                enqueue_linkedin_message,
                {
                    "candidate_id": candidate.candidate_id,
                    "tenant_id": candidate.tenant_id,
                    "name": candidate.name,
                    "city": candidate.city,
                    "linkedin_url": candidate.linkedin_url,
                    "source_page_id": candidate.source_page_id,
                    "channel": CandidateChannel.LINKEDIN.value,
                    "message_type": "initial",
                },
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            await workflow.execute_activity(
                append_interaction,
                _interaction_record(candidate, CandidateChannel.LINKEDIN, "initial"),
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

        if not candidate.channels:
            candidate.stage = CandidateStage.CLOSED
        else:
            candidate.stage = CandidateStage.CONTACTED

        await workflow.execute_activity(
            upsert_candidate_record,
            _candidate_record(candidate, candidate.stage),
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        await workflow.execute_activity(
            record_audit_event,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "event_type": "candidate.lifecycle_completed",
                "payload": {"stage": _stage_value(candidate.stage), "channels": [channel.value for channel in candidate.channels]},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "workflow_name": "CandidateLifecycle",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Completed",
                "payload": {"stage": candidate.stage.value, "channels": [channel.value for channel in candidate.channels]},
                "finished_at": workflow.now(),
            },
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        return _candidate_result(candidate)
