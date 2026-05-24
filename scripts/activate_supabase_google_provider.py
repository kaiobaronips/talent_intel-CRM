from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

from talent_intel_crm.support import load_local_env


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def infer_project_ref() -> str:
    explicit = env("SUPABASE_PROJECT_REF")
    if explicit:
        return explicit

    for value in (env("SUPABASE_URL"), env("NEXT_PUBLIC_SUPABASE_URL"), env("SUPABASE_DB_URL")):
        match = re.search(r"(?:https://|db\.)([a-z0-9]{20})\.supabase\.co", value)
        if match:
            return match.group(1)
    return ""


def main() -> None:
    load_local_env()
    project_ref = infer_project_ref()
    access_token = env("SUPABASE_ACCESS_TOKEN")
    google_client_id = env("GOOGLE_OAUTH_CLIENT_ID")
    google_client_secret = env("GOOGLE_OAUTH_CLIENT_SECRET")

    missing = [
        name
        for name, value in {
            "SUPABASE_PROJECT_REF": project_ref,
            "SUPABASE_ACCESS_TOKEN": access_token,
            "GOOGLE_OAUTH_CLIENT_ID": google_client_id,
            "GOOGLE_OAUTH_CLIENT_SECRET": google_client_secret,
        }.items()
        if not value
    ]
    if missing:
        print(f"FAIL missing_required={','.join(missing)}")
        sys.exit(1)

    payload = json.dumps(
        {
            "external_google_enabled": True,
            "external_google_client_id": google_client_id,
            "external_google_secret": google_client_secret,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{project_ref}/config/auth",
        data=payload,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
            print(f"PASS google_provider_enabled project_ref={project_ref}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        print(f"FAIL supabase_management_api status={exc.code} response={raw}")
        sys.exit(1)


if __name__ == "__main__":
    main()
