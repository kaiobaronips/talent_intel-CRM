"""Activity entrypoints for external IO."""

from .email import send_initial_email
from .linkedin import enqueue_linkedin_message
from .persistence import (
    append_interaction,
    record_audit_event,
    upsert_candidate_record,
    upsert_tenant_record,
)

__all__ = [
    "append_interaction",
    "enqueue_linkedin_message",
    "record_audit_event",
    "send_initial_email",
    "upsert_candidate_record",
    "upsert_tenant_record",
]
