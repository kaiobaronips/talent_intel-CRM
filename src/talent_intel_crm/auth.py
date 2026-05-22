from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from hmac import compare_digest
from typing import Optional

from fastapi import Header, HTTPException, status

from talent_intel_crm.config import APIConfig
from talent_intel_crm.db import find_tenant_api_key


@dataclass(frozen=True)
class APIPrincipal:
    role: str
    tenant_id: str = ""
    api_key_id: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def new_tenant_api_key() -> str:
    return f"ticrm_{secrets.token_urlsafe(32)}"


def api_key_prefix(api_key: str) -> str:
    return api_key[:14]


def require_principal(x_api_key: Optional[str] = Header(default=None)) -> APIPrincipal:
    config = APIConfig()
    admin_key = config.admin_api_key

    if admin_key and x_api_key and compare_digest(admin_key, x_api_key):
        return APIPrincipal(role="admin")

    if x_api_key:
        record = find_tenant_api_key(hash_api_key(x_api_key))
        if record:
            return APIPrincipal(role="tenant", tenant_id=record["tenant_id"], api_key_id=str(record["id"]))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if config.allow_insecure_development_auth:
        return APIPrincipal(role="admin")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")


def require_admin(principal: APIPrincipal) -> None:
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin API key required")


def authorize_tenant(principal: APIPrincipal, tenant_id: str) -> None:
    if principal.is_admin or principal.tenant_id == tenant_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")
