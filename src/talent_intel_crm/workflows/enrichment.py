from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.persistence import record_audit_event, upsert_candidate_record
    from talent_intel_crm.domain import CandidateEnvelope, CandidateStage


@workflow.defn
class CandidateEnrichmentWorkflow:
    """Coordinates enrichment through external providers and internal rules."""

    @workflow.run
    async def run(self, candidate: CandidateEnvelope) -> CandidateEnvelope:
        workflow.logger.info("Enriching candidate", extra={"candidate_id": candidate.candidate_id})
        candidate.stage = CandidateStage.ENRICHED
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
                "phase": "enrichment",
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            record_audit_event,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "event_type": "candidate.enriched",
                "payload": {"stage": candidate.stage.value},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        return candidate
