from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.email import send_initial_email
    from talent_intel_crm.activities.linkedin import enqueue_linkedin_message
    from talent_intel_crm.activities.persistence import append_interaction, record_audit_event, record_workflow_run, upsert_candidate_record
    from talent_intel_crm.candidate_payload import candidate_from_input, candidate_record, candidate_result, interaction_record, normalize_channels, normalize_stage
    from talent_intel_crm.domain import CandidateChannel, CandidateStage


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
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.INGESTED
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, CandidateStage.INGESTED),
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.ENRICHED
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, CandidateStage.ENRICHED),
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.QUALIFIED
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, CandidateStage.QUALIFIED),
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        candidate.stage = CandidateStage.READY_TO_CONTACT
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, CandidateStage.READY_TO_CONTACT),
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
                interaction_record(candidate, CandidateChannel.EMAIL, "initial"),
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
                interaction_record(candidate, CandidateChannel.LINKEDIN, "initial"),
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

        if not candidate.channels:
            candidate.stage = CandidateStage.CLOSED
        else:
            candidate.stage = CandidateStage.CONTACTED

        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, candidate.stage),
            schedule_to_close_timeout=timedelta(seconds=30),
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

        return candidate_result(candidate)
