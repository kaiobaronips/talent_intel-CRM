from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.persistence import record_audit_event, record_workflow_run, upsert_tenant_record
    from talent_intel_crm.domain import TenantEnvelope


@workflow.defn
class TenantOnboardingWorkflow:
    """Bootstraps a new tenant in the SaaS control plane."""

    @workflow.run
    async def run(self, tenant: TenantEnvelope) -> TenantEnvelope:
        workflow.logger.info("Onboarding tenant", extra={"tenant_id": tenant.tenant_id})
        info = workflow.info()
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": tenant.tenant_id,
                "workflow_name": "TenantOnboarding",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Running",
                "payload": {"company_name": tenant.company_name},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            upsert_tenant_record,
            {
                "tenant_id": tenant.tenant_id,
                "slug": tenant.tenant_id,
                "company_name": tenant.company_name,
                "tier": tenant.tier.value,
                "primary_domain": tenant.primary_domain,
                "timezone": tenant.timezone,
                "metadata": {"phase": "tenant_onboarding"},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            record_audit_event,
            {
                "tenant_id": tenant.tenant_id,
                "event_type": "tenant.onboarded",
                "payload": {"company_name": tenant.company_name, "tier": tenant.tier.value},
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            record_workflow_run,
            {
                "tenant_id": tenant.tenant_id,
                "workflow_name": "TenantOnboarding",
                "workflow_id": info.workflow_id,
                "run_id": info.run_id,
                "status": "Completed",
                "payload": {"company_name": tenant.company_name},
                "finished_at": workflow.now(),
            },
            schedule_to_close_timeout=timedelta(seconds=30),
        )
        return tenant
