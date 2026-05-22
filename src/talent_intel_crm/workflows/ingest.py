from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.persistence import record_audit_event, record_workflow_run, upsert_candidate_record
    from talent_intel_crm.domain import CandidateEnvelope, CandidateStage


@workflow.defn
class CandidateIngestWorkflow:
    """Receives a candidate from the CRM ingestion layer."""

    @workflow.run
    async def run(self, candidate: CandidateEnvelope) -> CandidateEnvelope:
        workflow.logger.info("Ingested candidate", extra={"candidate_id": candidate.candidate_id})
        info = workflow.info()
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": candidate.tenant_id,
                "workflow_name": "CandidateIngest",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Running",
                "payload": {"stage": "ingested"},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        candidate.stage = CandidateStage.INGESTED
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
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            record_audit_event,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "event_type": "candidate.ingested",
                "payload": {"stage": candidate.stage.value},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "workflow_name": "CandidateIngest",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Completed",
                "payload": {"stage": candidate.stage.value},
                "finished_at": workflow.now(),
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        return candidate
