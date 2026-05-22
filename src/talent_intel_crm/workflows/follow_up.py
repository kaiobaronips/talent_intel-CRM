from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.persistence import append_interaction, record_audit_event, record_workflow_run, upsert_candidate_record
    from talent_intel_crm.candidate_payload import candidate_from_input, candidate_record, candidate_result, interaction_record
    from talent_intel_crm.domain import CandidateStage


@workflow.defn
class CandidateFollowUpWorkflow:
    """Owns the retry-safe follow-up cadence."""

    @workflow.run
    async def run(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        candidate = candidate_from_input(candidate)
        workflow.logger.info("Scheduling follow-up", extra={"candidate_id": candidate.candidate_id})
        info = workflow.info()
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": candidate.tenant_id,
                "workflow_name": "CandidateFollowUp",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Running",
                "payload": {"stage": "follow_up"},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        candidate.stage = CandidateStage.FOLLOW_UP
        await workflow.execute_activity(
            upsert_candidate_record,
            candidate_record(candidate, candidate.stage, phase="follow_up"),
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        for channel in candidate.channels:
            await workflow.execute_activity(
                append_interaction,
                interaction_record(candidate, channel, "follow_up"),
                schedule_to_close_timeout=timedelta(seconds=30),
            )
        await workflow.execute_activity(
            record_audit_event,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "event_type": "candidate.follow_up_scheduled",
                "payload": {"stage": candidate.stage.value},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": candidate.tenant_id,
                "candidate_id": candidate.candidate_id,
                "workflow_name": "CandidateFollowUp",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Completed",
                "payload": {"stage": candidate.stage.value},
                "finished_at": workflow.now(),
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        return candidate_result(candidate)
