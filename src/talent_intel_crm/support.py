from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional


_LOCAL_ENV_LOADED = False


def load_local_env(path: Optional[Path] = None) -> None:
    """Load a local env file without overriding variables exported by the shell."""
    global _LOCAL_ENV_LOADED
    if path is None and _LOCAL_ENV_LOADED:
        return

    env_file = path or Path.cwd() / ".env"
    if not env_file.is_file():
        if path is None:
            _LOCAL_ENV_LOADED = True
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or name in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[name] = value
    if path is None:
        _LOCAL_ENV_LOADED = True


def env(name: str, default: str = "") -> str:
    load_local_env()
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
