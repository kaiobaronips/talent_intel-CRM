from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ENV = ROOT / "web" / ".env.local"

api_url = os.getenv("NEXT_PUBLIC_TICRM_API_URL") or os.getenv("TICRM_API_URL") or "http://localhost:8000"
api_key = os.getenv("TICRM_API_KEY") or os.getenv("TICRM_ADMIN_API_KEY") or ""
tenant_id = os.getenv("NEXT_PUBLIC_DEFAULT_TENANT_ID") or os.getenv("TICRM_SMOKE_TENANT_ID") or "api-controlled-003"
supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL") or ""
supabase_anon_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""
site_url = os.getenv("NEXT_PUBLIC_SITE_URL") or "http://localhost:3000"

if not api_key:
    raise SystemExit("Missing TICRM_API_KEY or TICRM_ADMIN_API_KEY. Refusing to write web/.env.local without a real server-side key.")

WEB_ENV.write_text(
    "\n".join(
        [
            f"NEXT_PUBLIC_TICRM_API_URL={api_url}",
            f"TICRM_API_KEY={api_key}",
            f"NEXT_PUBLIC_DEFAULT_TENANT_ID={tenant_id}",
            f"NEXT_PUBLIC_SUPABASE_URL={supabase_url}",
            f"NEXT_PUBLIC_SUPABASE_ANON_KEY={supabase_anon_key}",
            f"NEXT_PUBLIC_SITE_URL={site_url}",
            "",
        ]
    )
)
print(f"Wrote {WEB_ENV} for tenant {tenant_id}. Secret value was not printed.")
