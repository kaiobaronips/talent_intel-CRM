from datetime import timedelta
from typing import Any, Dict, Union

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from talent_intel_crm.activities.persistence import record_audit_event, record_workflow_run, upsert_tenant_record
    from talent_intel_crm.domain import TenantEnvelope, TenantTier


def _tenant_from_input(value: Union[Dict[str, Any], TenantEnvelope]) -> TenantEnvelope:
    if isinstance(value, TenantEnvelope):
        return value
    if not isinstance(value, dict):
        raise TypeError("TenantOnboardingWorkflow expects a dict payload or TenantEnvelope")
    return TenantEnvelope(
        tenant_id=str(value.get("tenant_id", "")),
        company_name=str(value.get("company_name", "")),
        tier=_normalize_tier(value.get("tier")),
        primary_domain=str(value.get("primary_domain", "")),
        timezone=str(value.get("timezone", "America/Sao_Paulo")),
    )


def _normalize_tier(value: object) -> TenantTier:
    if isinstance(value, TenantTier):
        return value
    if isinstance(value, str):
        try:
            return TenantTier(value)
        except ValueError:
            return TenantTier.STARTER
    return TenantTier.STARTER


def _tenant_result(tenant: TenantEnvelope) -> Dict[str, Any]:
    return {
        "tenant_id": tenant.tenant_id,
        "company_name": tenant.company_name,
        "tier": tenant.tier.value,
        "primary_domain": tenant.primary_domain,
        "timezone": tenant.timezone,
    }


@workflow.defn
class TenantOnboardingWorkflow:
    """Bootstraps a new tenant in the SaaS control plane."""

    @workflow.run
    async def run(self, tenant: Dict[str, Any]) -> Dict[str, Any]:
        tenant = _tenant_from_input(tenant)
        workflow.logger.info("Onboarding tenant", extra={"tenant_id": tenant.tenant_id})
        tenant.tier = _normalize_tier(tenant.tier)
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
        return _tenant_result(tenant)
