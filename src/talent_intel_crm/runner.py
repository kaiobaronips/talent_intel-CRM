from __future__ import annotations

import argparse
import asyncio
import uuid

from talent_intel_crm.client import connect_temporal
from talent_intel_crm.domain import CandidateChannel, CandidateStage, TenantTier
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


STEP_WORKFLOWS = {
    "ingest": CandidateIngestWorkflow,
    "enrichment": CandidateEnrichmentWorkflow,
    "qualification": CandidateQualificationWorkflow,
    "outreach": CandidateOutreachWorkflow,
    "follow-up": CandidateFollowUpWorkflow,
    "closure": CandidateClosureWorkflow,
}


def _stage_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _channel_values(values: object) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        return [str(values)]
    result = []
    for value in values:
        result.append(value.value if hasattr(value, "value") else str(value))
    return result


def _result_value(result: object, key: str) -> object:
    if isinstance(result, dict):
        return result.get(key, "")
    return getattr(result, key, "")


def _add_candidate_arguments(parser: argparse.ArgumentParser, include_stage: bool = False) -> None:
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--city", default="")
    parser.add_argument("--email", default="")
    parser.add_argument("--linkedin-url", default="")
    parser.add_argument("--channels", nargs="*", choices=[channel.value for channel in CandidateChannel], default=[])
    parser.add_argument("--source-page-id", default="")
    if include_stage:
        parser.add_argument("--stage", choices=[stage.value for stage in CandidateStage], default=CandidateStage.INGESTED.value)
        parser.add_argument("--follow-up-delay-seconds", nargs="*", type=int, default=[])


def _candidate_payload(args: argparse.Namespace) -> dict[str, object]:
    payload = {
        "candidate_id": args.candidate_id,
        "tenant_id": args.tenant_id,
        "name": args.name,
        "city": args.city,
        "email": args.email,
        "linkedin_url": args.linkedin_url,
        "channels": list(args.channels),
        "source_page_id": args.source_page_id or None,
    }
    if getattr(args, "stage", ""):
        payload["stage"] = args.stage
    if getattr(args, "follow_up_delay_seconds", []):
        payload["follow_up_delays_seconds"] = list(args.follow_up_delay_seconds)
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Controlled workflow runner for Talent Intel CRM")
    sub = parser.add_subparsers(dest="command", required=True)

    tenant = sub.add_parser("tenant-onboarding")
    tenant.add_argument("--tenant-id", required=True)
    tenant.add_argument("--company-name", required=True)
    tenant.add_argument("--tier", choices=[tier.value for tier in TenantTier], default=TenantTier.STARTER.value)
    tenant.add_argument("--primary-domain", default="")
    tenant.add_argument("--timezone", default="America/Sao_Paulo")

    candidate = sub.add_parser("candidate-lifecycle")
    _add_candidate_arguments(candidate)

    step = sub.add_parser("candidate-step")
    step.add_argument("--step", choices=sorted(STEP_WORKFLOWS), required=True)
    _add_candidate_arguments(step, include_stage=True)

    smoke = sub.add_parser("smoke")
    smoke.add_argument("--tenant-id", default="talent-intel-crm")
    smoke.add_argument("--company-name", default="Talent Intel CRM")
    smoke.add_argument("--candidate-id", default=f"candidate-{uuid.uuid4().hex[:10]}")
    smoke.add_argument("--name", default="Controlled Smoke Candidate")
    smoke.add_argument("--city", default="Sao Paulo")
    smoke.add_argument("--email", default="controlled-smoke@example.com")
    smoke.add_argument("--linkedin-url", default="https://www.linkedin.com/in/controlled-smoke-candidate")

    return parser


async def _run(args: argparse.Namespace) -> None:
    client = await connect_temporal()

    if args.command == "tenant-onboarding":
        handle = await client.start_workflow(
            TenantOnboardingWorkflow.run,
            {
                "tenant_id": args.tenant_id,
                "company_name": args.company_name,
                "tier": args.tier,
                "primary_domain": args.primary_domain,
                "timezone": args.timezone,
            },
            id=f"tenant-onboarding::{args.tenant_id}",
            task_queue="talent-intel-crm",
        )
        result = await handle.result()
        print({"workflow_id": handle.id, "run_id": handle.result_run_id, "tenant_id": _result_value(result, "tenant_id")})
        return

    if args.command == "candidate-lifecycle":
        payload = _candidate_payload(args)
        handle = await client.start_workflow(
            CandidateLifecycleWorkflow.run,
            payload,
            id=f"candidate-lifecycle::{args.tenant_id}::{args.candidate_id}",
            task_queue="talent-intel-crm",
        )
        result = await handle.result()
        print(
            {
                "workflow_id": handle.id,
                "run_id": handle.result_run_id,
                "candidate_id": _result_value(result, "candidate_id"),
                "stage": _stage_value(_result_value(result, "stage")),
                "channels": _channel_values(_result_value(result, "channels")),
            }
        )
        return

    if args.command == "candidate-step":
        workflow_type = STEP_WORKFLOWS[args.step]
        handle = await client.start_workflow(
            workflow_type.run,
            _candidate_payload(args),
            id=f"candidate-{args.step}::{args.tenant_id}::{args.candidate_id}::{uuid.uuid4().hex[:8]}",
            task_queue="talent-intel-crm",
        )
        result = await handle.result()
        print(
            {
                "workflow_id": handle.id,
                "run_id": handle.result_run_id,
                "step": args.step,
                "candidate_id": _result_value(result, "candidate_id"),
                "stage": _stage_value(_result_value(result, "stage")),
                "channels": _channel_values(_result_value(result, "channels")),
            }
        )
        return

    if args.command == "smoke":
        tenant_handle = await client.start_workflow(
            TenantOnboardingWorkflow.run,
            {
                "tenant_id": args.tenant_id,
                "company_name": args.company_name,
                "tier": TenantTier.STARTER.value,
                "primary_domain": "talentintelcrm.local",
            },
            id=f"tenant-onboarding::{args.tenant_id}",
            task_queue="talent-intel-crm",
        )
        await tenant_handle.result()

        candidate_handle = await client.start_workflow(
            CandidateLifecycleWorkflow.run,
            {
                "candidate_id": args.candidate_id,
                "tenant_id": args.tenant_id,
                "name": args.name,
                "city": args.city,
                "email": args.email,
                "linkedin_url": args.linkedin_url,
                "channels": [CandidateChannel.EMAIL.value, CandidateChannel.LINKEDIN.value],
            },
            id=f"candidate-lifecycle::{args.tenant_id}::{args.candidate_id}",
            task_queue="talent-intel-crm",
        )
        result = await candidate_handle.result()
        print(
            {
                "tenant_workflow_id": tenant_handle.id,
                "candidate_workflow_id": candidate_handle.id,
                "candidate_run_id": candidate_handle.result_run_id,
                "candidate_id": _result_value(result, "candidate_id"),
                "stage": _stage_value(_result_value(result, "stage")),
            }
        )


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
