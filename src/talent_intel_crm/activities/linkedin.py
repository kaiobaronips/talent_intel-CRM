from __future__ import annotations

from typing import Any

from temporalio import activity

from talent_intel_crm.support import action_result, env, post_json


@activity.defn
def enqueue_linkedin_message(payload: dict[str, Any]) -> dict[str, Any]:
    """Prepare a LinkedIn message dispatch using the approved channel."""
    endpoint = env("LINKEDIN_SEND_WEBHOOK_URL")
    if not endpoint:
        return action_result("linkedin.enqueue_linkedin_message", payload, executed=False)
    result = post_json(endpoint, payload)
    return action_result("linkedin.enqueue_linkedin_message", payload, endpoint, True, result)
