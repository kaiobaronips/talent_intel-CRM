from __future__ import annotations

import os
import sys
import json
import urllib.error
import urllib.request

from talent_intel_crm.db import get_connection, get_tenant, upsert_tenant_membership
from talent_intel_crm.support import load_local_env


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def find_auth_user_id(email: str) -> str:
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute("select id::text as id from auth.users where lower(email) = lower(%s) limit 1", (email,))
            row = cur.fetchone()
            return str(row["id"]) if row else ""


def create_auth_user(email: str, password: str) -> str:
    supabase_url = env("SUPABASE_URL", env("NEXT_PUBLIC_SUPABASE_URL")).rstrip("/")
    service_role_key = env("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_role_key:
        return ""

    payload = json.dumps({"email": email, "password": password, "email_confirm": True}).encode("utf-8")
    request = urllib.request.Request(
        f"{supabase_url}/auth/v1/admin/users",
        data=payload,
        method="POST",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
            return str(data.get("id") or "")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        print(f"FAIL auth_user_create_failed status={exc.code} response={raw}")
        sys.exit(1)


def main() -> None:
    load_local_env()
    tenant_id = env("TICRM_BOOTSTRAP_TENANT_ID", env("NEXT_PUBLIC_DEFAULT_TENANT_ID", "api-controlled-003"))
    email = env("TICRM_BOOTSTRAP_USER_EMAIL")
    explicit_user_id = env("TICRM_BOOTSTRAP_USER_ID")
    password = env("TICRM_BOOTSTRAP_USER_PASSWORD")
    role = env("TICRM_BOOTSTRAP_ROLE", "owner")

    if role not in {"owner", "admin", "recruiter", "viewer"}:
        print("FAIL invalid_role expected one of owner,admin,recruiter,viewer")
        sys.exit(1)

    if not tenant_id:
        print("FAIL missing_tenant_id set TICRM_BOOTSTRAP_TENANT_ID")
        sys.exit(1)

    tenant = get_tenant(tenant_id)
    if not tenant:
        print(f"FAIL tenant_not_found tenant={tenant_id}")
        sys.exit(1)

    user_id = explicit_user_id
    if not user_id:
        if not email:
            print("FAIL missing_user set TICRM_BOOTSTRAP_USER_EMAIL or TICRM_BOOTSTRAP_USER_ID")
            sys.exit(1)
        user_id = find_auth_user_id(email)
        if not user_id and password:
            user_id = create_auth_user(email, password)

    if not user_id:
        print(f"FAIL auth_user_not_found email={email} set TICRM_BOOTSTRAP_USER_PASSWORD and SUPABASE_SERVICE_ROLE_KEY to create it automatically")
        sys.exit(1)

    membership = upsert_tenant_membership(
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "email": email,
            "role": role,
        }
    )

    print(
        "PASS tenant_member_bootstrapped "
        f"tenant={membership['tenant_id']} user_id={membership['user_id']} role={membership['role']}"
    )


if __name__ == "__main__":
    main()
