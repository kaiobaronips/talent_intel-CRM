from __future__ import annotations

from typing import Any

from talent_intel_crm.support import action_result, env, post_json


def send_initial_email(payload: dict[str, Any]) -> dict[str, Any]:
    """Send the first email contact through the approved mail provider."""
    endpoint = env("EMAIL_SEND_WEBHOOK_URL")
    if not endpoint:
        return action_result("email.send_initial_email", payload, executed=False)
    result = post_json(endpoint, payload)
    return action_result("email.send_initial_email", payload, endpoint, True, result)
