from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.email import send_initial_email
    from talent_intel_crm.activities.linkedin import enqueue_linkedin_message
    from talent_intel_crm.activities.persistence import append_interaction, record_audit_event, upsert_candidate_record
    from talent_intel_crm.domain import CandidateChannel, CandidateEnvelope, CandidateStage


@workflow.defn
class CandidateOutreachWorkflow:
    """Routes outbound contact by available channel."""

    @workflow.run
    async def run(self, candidate: CandidateEnvelope) -> CandidateEnvelope:
        workflow.logger.info("Routing outreach", extra={"candidate_id": candidate.candidate_id})
        if candidate.stage == CandidateStage.CLOSED:
            return candidate

        candidate.stage = CandidateStage.READY_TO_CONTACT
        await workflow.execute_activity(
            upsert_candidate_record,
            {
                "candidate_id": candidate.candidate_id,
                "tenant_id": candidate.tenant_id,
                "name": candidate.name,
                "city": candidate.city,
                "email": candidate.email,
                "linkedin_url": candidate.linkedin_url,
                "stage": candidate.stage.value,
                "channels": [channel.value for channel in candidate.channels],
                "source_page_id": candidate.source_page_id,
                "phase": "outreach-routing",
            },
            schedule_to_close_timeout=timedelta(seconds=30),
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
            )
            await workflow.execute_activity(
                append_interaction,
                {
                    "candidate_id": candidate.candidate_id,
                    "tenant_id": candidate.tenant_id,
                    "name": candidate.name,
                    "channel": CandidateChannel.EMAIL.value,
                    "message_type": "initial",
                    "stage": candidate.stage.value,
                    "source_page_id": candidate.source_page_id,
                },
                schedule_to_close_timeout=timedelta(seconds=30),
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
            )
            await workflow.execute_activity(
                append_interaction,
                {
                    "candidate_id": candidate.candidate_id,
                    "tenant_id": candidate.tenant_id,
                    "name": candidate.name,
                    "channel": CandidateChannel.LINKEDIN.value,
                    "message_type": "initial",
                    "stage": candidate.stage.value,
                    "source_page_id": candidate.source_page_id,
                },
                schedule_to_close_timeout=timedelta(seconds=30),
            )
        await workflow.execute_activity(
            record_audit_event,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "event_type": "candidate.outreach_routed",
                "payload": {"stage": candidate.stage.value, "channels": [channel.value for channel in candidate.channels]},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        return candidate
