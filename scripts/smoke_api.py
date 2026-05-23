from __future__ import annotations

import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = os.getenv("TICRM_API_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("TICRM_API_KEY") or os.getenv("TICRM_ADMIN_API_KEY")
TENANT_ID = os.getenv("TICRM_SMOKE_TENANT_ID") or os.getenv("NEXT_PUBLIC_DEFAULT_TENANT_ID") or "api-controlled-003"


def request_json(path: str, *, auth: bool = False) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    if auth and API_KEY:
        headers["X-API-Key"] = API_KEY
    req = Request(f"{API_URL}{path}", headers=headers)
    try:
        with urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body or "{}")
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            payload = {"detail": body}
        return exc.code, payload
    except URLError as exc:
        print(f"FAIL api_unreachable url={API_URL} reason={exc.reason}")
        sys.exit(2)


def assert_ok(name: str, status: int, payload: dict[str, Any]) -> None:
    if status >= 400 or payload.get("success") is False:
        print(f"FAIL {name} status={status} payload={json.dumps(payload, ensure_ascii=False)}")
        sys.exit(1)
    print(f"OK {name} status={status}")


def main() -> None:
    if not API_KEY:
        print("WARN missing_api_key set TICRM_API_KEY or TICRM_ADMIN_API_KEY for authenticated checks")

    status, payload = request_json("/health")
    assert_ok("health", status, payload)

    status, payload = request_json("/ready")
    if status != 200 or not payload.get("data", {}).get("postgres"):
        print(f"FAIL readiness status={status} payload={json.dumps(payload, ensure_ascii=False)}")
        sys.exit(1)
    print("OK readiness postgres=true")

    status, payload = request_json(f"/v1/tenants/{TENANT_ID}", auth=True)
    assert_ok("tenant", status, payload)

    status, payload = request_json(f"/v1/tenants/{TENANT_ID}/metrics", auth=True)
    assert_ok("metrics", status, payload)

    status, payload = request_json(f"/v1/tenants/{TENANT_ID}/candidates?page=1&limit=5", auth=True)
    assert_ok("candidates", status, payload)

    status, payload = request_json(f"/v1/tenants/{TENANT_ID}/interactions?page=1&limit=5", auth=True)
    assert_ok("interactions", status, payload)

    print(f"PASS smoke tenant={TENANT_ID} api={API_URL}")


if __name__ == "__main__":
    main()
