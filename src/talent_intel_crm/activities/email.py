from __future__ import annotations

from typing import Any

from temporalio import activity

from talent_intel_crm.support import action_result, env, post_json
from talent_intel_crm.telemetry import measure


@activity.defn
def send_initial_email(payload: dict[str, Any]) -> dict[str, Any]:
    """Send the first email contact through the approved mail provider."""
    endpoint = env("EMAIL_SEND_WEBHOOK_URL")
    if not endpoint:
        return action_result("email.send_initial_email", payload, executed=False)
    result = measure(
        "activity.channel.email",
        lambda: post_json(endpoint, payload),
        tenant_id=payload.get("tenant_id", ""),
        message_type=payload.get("message_type", ""),
    )
    return action_result("email.send_initial_email", payload, endpoint, True, result)
