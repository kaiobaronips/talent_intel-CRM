from __future__ import annotations

import os
import sys

REQUIRED = [
    "SUPABASE_DB_URL",
    "TEMPORAL_TARGET_HOST",
    "TEMPORAL_NAMESPACE",
    "TEMPORAL_API_KEY",
    "TEMPORAL_TASK_QUEUE",
    "TICRM_ADMIN_API_KEY",
]

RECOMMENDED = [
    "TEMPORAL_USE_TLS",
    "NEXT_PUBLIC_TICRM_API_URL",
    "NEXT_PUBLIC_DEFAULT_TENANT_ID",
]


def masked_state(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        return "missing"
    return f"set(len={len(value)})"


def main() -> None:
    missing = [name for name in REQUIRED if not os.getenv(name)]
    for name in REQUIRED:
        print(f"{name}: {masked_state(name)}")
    for name in RECOMMENDED:
        print(f"{name}: {masked_state(name)}")

    if os.getenv("TICRM_ALLOW_INSECURE_DEV_AUTH", "").lower() in {"1", "true", "yes"}:
        print("FAIL TICRM_ALLOW_INSECURE_DEV_AUTH must be false/unset for production")
        sys.exit(1)

    if os.getenv("TEMPORAL_USE_TLS", "").lower() not in {"1", "true", "yes"}:
        print("WARN TEMPORAL_USE_TLS is not enabled")

    if missing:
        print(f"FAIL missing_required={','.join(missing)}")
        sys.exit(1)

    print("PASS production_readiness_config")


if __name__ == "__main__":
    main()
