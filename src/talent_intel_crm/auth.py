from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from hmac import compare_digest
from time import time
from typing import Any, Optional

from fastapi import Header, HTTPException, status

from talent_intel_crm.config import APIConfig
from talent_intel_crm.db import find_tenant_api_key, find_tenant_membership_by_user


@dataclass(frozen=True)
class APIPrincipal:
    role: str
    tenant_id: str = ""
    api_key_id: str = ""
    user_id: str = ""
    email: str = ""
    auth_method: str = "api_key"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_tenant_admin(self) -> bool:
        return self.role in {"owner", "admin"}


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def new_tenant_api_key() -> str:
    return f"ticrm_{secrets.token_urlsafe(32)}"


def api_key_prefix(api_key: str) -> str:
    return api_key[:14]


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _decode_and_verify_jwt(token: str, secret: str) -> dict[str, Any]:
    try:
        header_raw, payload_raw, signature_raw = token.split(".")
        header = json.loads(_b64url_decode(header_raw))
        if header.get("alg") != "HS256":
            raise ValueError("Unsupported JWT algorithm")
        signed = f"{header_raw}.{payload_raw}".encode("ascii")
        expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).digest()
        actual = _b64url_decode(signature_raw)
        if not compare_digest(expected, actual):
            raise ValueError("Invalid JWT signature")
        payload = json.loads(_b64url_decode(payload_raw))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and exp < time():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired bearer token")
    return payload


def _principal_from_bearer_token(token: str, config: APIConfig) -> APIPrincipal:
    if not config.auth_jwt_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT auth is not configured")

    payload = _decode_and_verify_jwt(token, config.auth_jwt_secret)
    user_id = str(payload.get("sub") or "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token missing user subject")

    membership = find_tenant_membership_by_user(user_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not linked to a tenant")

    return APIPrincipal(
        role=str(membership["role"]),
        tenant_id=str(membership["tenant_id"]),
        user_id=user_id,
        email=str(membership.get("email") or payload.get("email") or ""),
        auth_method="bearer",
    )


def require_principal(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> APIPrincipal:
    config = APIConfig()
    admin_key = config.admin_api_key

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return _principal_from_bearer_token(token, config)

    if admin_key and x_api_key and compare_digest(admin_key, x_api_key):
        return APIPrincipal(role="admin", auth_method="api_key")

    if x_api_key:
        record = find_tenant_api_key(hash_api_key(x_api_key))
        if record:
            return APIPrincipal(role="tenant", tenant_id=record["tenant_id"], api_key_id=str(record["id"]), auth_method="api_key")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if config.allow_insecure_development_auth:
        return APIPrincipal(role="admin", auth_method="dev")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def require_admin(principal: APIPrincipal) -> None:
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin API key required")


def require_tenant_admin(principal: APIPrincipal, tenant_id: str) -> None:
    authorize_tenant(principal, tenant_id)
    if principal.is_admin or principal.is_tenant_admin:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant admin role required")


def authorize_tenant(principal: APIPrincipal, tenant_id: str) -> None:
    if principal.is_admin or principal.tenant_id == tenant_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")
