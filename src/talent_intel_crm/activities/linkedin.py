from __future__ import annotations

from typing import Any

from temporalio import activity

from talent_intel_crm.support import action_result, env, post_json
from talent_intel_crm.telemetry import measure


@activity.defn
def enqueue_linkedin_message(payload: dict[str, Any]) -> dict[str, Any]:
    """Prepare a LinkedIn message dispatch using the approved channel."""
    endpoint = env("LINKEDIN_SEND_WEBHOOK_URL")
    if not endpoint:
        return action_result("linkedin.enqueue_linkedin_message", payload, executed=False)
    result = measure(
        "activity.channel.linkedin",
        lambda: post_json(endpoint, payload),
        tenant_id=payload.get("tenant_id", ""),
        message_type=payload.get("message_type", ""),
    )
    return action_result("linkedin.enqueue_linkedin_message", payload, endpoint, True, result)
