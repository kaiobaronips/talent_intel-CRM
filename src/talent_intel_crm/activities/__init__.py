"""Activity entrypoints for external IO."""

from .agents import classify_candidate_fit, enrich_candidate_profile, render_outreach_message, search_linkedin_candidates
from .email import send_initial_email
from .linkedin import enqueue_linkedin_message
from .persistence import (
    append_interaction,
    record_audit_event,
    record_workflow_run,
    upsert_candidate_record,
    upsert_tenant_record,
)

__all__ = [
    "append_interaction",
    "classify_candidate_fit",
    "enrich_candidate_profile",
    "enqueue_linkedin_message",
    "record_audit_event",
    "record_workflow_run",
    "render_outreach_message",
    "search_linkedin_candidates",
    "send_initial_email",
    "upsert_candidate_record",
    "upsert_tenant_record",
]
