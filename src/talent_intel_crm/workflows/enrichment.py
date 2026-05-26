from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.agents import enrich_candidate_profile
    from talent_intel_crm.activities.persistence import record_audit_event, record_workflow_run, upsert_candidate_record
    from talent_intel_crm.candidate_payload import candidate_from_input, candidate_record, candidate_result
    from talent_intel_crm.domain import CandidateStage


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


@workflow.defn
class CandidateEnrichmentWorkflow:
    """Coordinates enrichment through external providers and internal rules."""

    @workflow.run
    async def run(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        candidate = candidate_from_input(candidate)
        workflow.logger.info("Enriching candidate", extra={"candidate_id": candidate.candidate_id})
        info = workflow.info()
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": candidate.tenant_id,
                "workflow_name": "CandidateEnrichment",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Running",
                "payload": {"stage": "enriched"},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        candidate.stage = CandidateStage.ENRICHED
        enrichment_result = await workflow.execute_activity(
            enrich_candidate_profile,
            candidate_result(candidate),
            schedule_to_close_timeout=timedelta(minutes=2),
        )
        enrichment = _extract_activity_payload(enrichment_result, "enrichment")
        metadata = {
            "phase": "enrichment",
            **enrichment,
            "enrichment": enrichment,
        }
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, candidate.stage, **metadata),
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
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "workflow_name": "CandidateEnrichment",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Completed",
                "payload": {"stage": candidate.stage.value},
                "finished_at": workflow.now(),
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        return candidate_result(candidate)
