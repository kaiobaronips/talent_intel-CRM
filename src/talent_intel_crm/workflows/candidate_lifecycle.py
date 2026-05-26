from datetime import timedelta
from typing import Any, Dict, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.agents import classify_candidate_fit, enrich_candidate_profile, render_outreach_message
    from talent_intel_crm.activities.email import send_initial_email
    from talent_intel_crm.activities.linkedin import enqueue_linkedin_message
    from talent_intel_crm.activities.persistence import append_interaction, record_audit_event, record_workflow_run, upsert_candidate_record
    from talent_intel_crm.candidate_payload import candidate_from_input, candidate_record, candidate_result, interaction_record, normalize_channels, normalize_stage
    from talent_intel_crm.domain import CandidateChannel, CandidateStage


PERSISTENCE_TIMEOUT = timedelta(minutes=2)
AGENT_TIMEOUT = timedelta(minutes=2)


def _extract_activity_payload(result: dict[str, Any], key: str) -> dict[str, Any]:
    result_payload = result.get("result", {})
    if not isinstance(result_payload, dict):
        return {}

    response = result_payload.get("response")
    if isinstance(response, dict):
        value = response.get(key)
        if isinstance(value, dict):
            return value
        return response

    value = result_payload.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _candidate_agent_payload(candidate: Any, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = candidate_result(candidate)
    payload.update(candidate.metadata)
    if metadata:
        payload.update(metadata)
    return payload


@workflow.defn
class CandidateLifecycleWorkflow:
    """Main candidate lifecycle orchestration."""

    @workflow.run
    async def run(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        candidate = candidate_from_input(candidate)
        workflow.logger.info("Starting candidate lifecycle", extra={"candidate_id": candidate.candidate_id})
        candidate.stage = normalize_stage(candidate.stage)
        candidate.channels = normalize_channels(candidate.channels)
        info = workflow.info()
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": candidate.tenant_id,
                "workflow_name": "CandidateLifecycle",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Running",
                "payload": {"stage": candidate.stage.value},
            },
            schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.INGESTED
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, CandidateStage.INGESTED),
            schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.ENRICHED
        enrichment_result = await workflow.execute_activity(
            enrich_candidate_profile,
            _candidate_agent_payload(candidate),
            schedule_to_close_timeout=AGENT_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        enrichment = _extract_activity_payload(enrichment_result, "enrichment")
        agent_metadata: dict[str, Any] = {
            **enrichment,
            "enrichment": enrichment,
        }
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, CandidateStage.ENRICHED, **agent_metadata),
            schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.QUALIFIED
        classification_result = await workflow.execute_activity(
            classify_candidate_fit,
            _candidate_agent_payload(candidate, agent_metadata),
            schedule_to_close_timeout=AGENT_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        classification = _extract_activity_payload(classification_result, "classification")
        agent_metadata = {
            **agent_metadata,
            **classification,
            "classification_detail": classification,
        }
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, CandidateStage.QUALIFIED, **agent_metadata),
            schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.READY_TO_CONTACT
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, CandidateStage.READY_TO_CONTACT, **agent_metadata),
            schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        if CandidateChannel.EMAIL in candidate.channels and candidate.email:
            email_message_result = await workflow.execute_activity(
                render_outreach_message,
                _candidate_agent_payload(
                    candidate,
                    {
                        **agent_metadata,
                        "channel": CandidateChannel.EMAIL.value,
                        "message_type": "initial",
                    },
                ),
                schedule_to_close_timeout=AGENT_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            email_message = _extract_activity_payload(email_message_result, "message")
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
                    "message": email_message,
                },
                schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            email_interaction = interaction_record(candidate, CandidateChannel.EMAIL, "initial")
            email_interaction["message"] = email_message
            email_interaction["metadata"] = agent_metadata
            await workflow.execute_activity(
                append_interaction,
                email_interaction,
                schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

        if CandidateChannel.LINKEDIN in candidate.channels and candidate.linkedin_url:
            linkedin_message_result = await workflow.execute_activity(
                render_outreach_message,
                _candidate_agent_payload(
                    candidate,
                    {
                        **agent_metadata,
                        "channel": CandidateChannel.LINKEDIN.value,
                        "message_type": "initial",
                    },
                ),
                schedule_to_close_timeout=AGENT_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            linkedin_message = _extract_activity_payload(linkedin_message_result, "message")
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
                    "message": linkedin_message,
                },
                schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            linkedin_interaction = interaction_record(candidate, CandidateChannel.LINKEDIN, "initial")
            linkedin_interaction["message"] = linkedin_message
            linkedin_interaction["metadata"] = agent_metadata
            await workflow.execute_activity(
                append_interaction,
                linkedin_interaction,
                schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

        if not candidate.channels:
            candidate.stage = CandidateStage.CLOSED
        else:
            candidate.stage = CandidateStage.CONTACTED

        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, candidate.stage, **agent_metadata),
            schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        await workflow.execute_activity(
            record_audit_event,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "event_type": "candidate.lifecycle_completed",
                "payload": {"stage": candidate.stage.value, "channels": [channel.value for channel in candidate.channels]},
            },
            schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
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
            schedule_to_close_timeout=PERSISTENCE_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        return candidate_result(candidate)
