from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def post_json(url: str, payload: dict[str, Any], timeout: int = 20) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"raw": raw}
            return {
                "ok": True,
                "status": response.status,
                "response": data,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        return {
            "ok": False,
            "status": exc.code,
            "error": raw,
        }


def action_result(
    action: str,
    payload: dict[str, Any],
    endpoint: Optional[str] = None,
    executed: bool = False,
    result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "action": action,
        "executed": executed,
        "endpoint": endpoint or "",
        "payload": payload,
        "result": result or {},
    }

