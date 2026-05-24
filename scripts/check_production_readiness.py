from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from talent_intel_crm.support import load_local_env  # noqa: E402

REQUIRED = [
    "SUPABASE_DB_URL",
    "TEMPORAL_TARGET_HOST",
    "TEMPORAL_NAMESPACE",
    "TEMPORAL_API_KEY",
    "TEMPORAL_TASK_QUEUE",
    "TICRM_ADMIN_API_KEY",
    "SUPABASE_JWT_SECRET",
]

RECOMMENDED = [
    "TEMPORAL_USE_TLS",
    "NEXT_PUBLIC_TICRM_API_URL",
    "NEXT_PUBLIC_DEFAULT_TENANT_ID",
    "NEXT_PUBLIC_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    "NEXT_PUBLIC_SITE_URL",
]


def masked_state(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        return "missing"
    return f"set(len={len(value)})"


def main() -> None:
    load_local_env()
    load_local_env(ROOT / "web" / ".env.local")
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

    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    if supabase_url and urlparse(supabase_url).scheme != "https":
        print("FAIL NEXT_PUBLIC_SUPABASE_URL must use https")
        sys.exit(1)

    site_url = os.getenv("NEXT_PUBLIC_SITE_URL", "")
    if site_url:
        parsed_site_url = urlparse(site_url)
        if parsed_site_url.scheme not in {"http", "https"} or not parsed_site_url.netloc:
            print("FAIL NEXT_PUBLIC_SITE_URL must be an absolute URL")
            sys.exit(1)
        if "localhost" not in parsed_site_url.netloc and parsed_site_url.scheme != "https":
            print("FAIL NEXT_PUBLIC_SITE_URL must use https outside localhost")
            sys.exit(1)

    if missing:
        print(f"FAIL missing_required={','.join(missing)}")
        sys.exit(1)

    print("PASS production_readiness_config")


if __name__ == "__main__":
    main()
