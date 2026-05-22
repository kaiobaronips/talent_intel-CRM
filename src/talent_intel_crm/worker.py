"""Temporal worker bootstrap for Talent Intel CRM."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.worker import Worker

from talent_intel_crm.client import connect_temporal
from talent_intel_crm.activities.email import send_initial_email
from talent_intel_crm.activities.linkedin import enqueue_linkedin_message
from talent_intel_crm.activities.persistence import (
    append_interaction,
    record_audit_event,
    record_workflow_run,
    upsert_candidate_record,
    upsert_tenant_record,
)
from talent_intel_crm.config import TemporalConfig
from talent_intel_crm.workflows import (
    CandidateClosureWorkflow,
    CandidateEnrichmentWorkflow,
    CandidateFollowUpWorkflow,
    CandidateIngestWorkflow,
    CandidateLifecycleWorkflow,
    CandidateOutreachWorkflow,
    CandidateQualificationWorkflow,
    TenantOnboardingWorkflow,
)


async def main() -> None:
    config = TemporalConfig()
    client = await connect_temporal()
    activity_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ticrm-activity")
    worker = Worker(
        client,
        task_queue=config.task_queue,
        activity_executor=activity_executor,
        activities=[
            upsert_tenant_record,
            upsert_candidate_record,
            append_interaction,
            record_audit_event,
            record_workflow_run,
            send_initial_email,
            enqueue_linkedin_message,
        ],
        workflows=[
            CandidateIngestWorkflow,
            CandidateEnrichmentWorkflow,
            CandidateQualificationWorkflow,
            CandidateOutreachWorkflow,
            CandidateFollowUpWorkflow,
            CandidateClosureWorkflow,
            TenantOnboardingWorkflow,
            CandidateLifecycleWorkflow,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
