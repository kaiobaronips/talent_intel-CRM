import base64
import hashlib
import hmac
import json
import time

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from fastapi import HTTPException

from talent_intel_crm.auth import APIPrincipal, authorize_tenant, hash_api_key, require_admin, require_principal, require_tenant_admin


def _b64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _jwt(payload: dict[str, object], secret: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    body = _b64url(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), f"{header}.{body}".encode("ascii"), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url(signature)}"


def _es256_jwt(payload: dict[str, object], private_key: ec.EllipticCurvePrivateKey, kid: str) -> str:
    header = _b64url(json.dumps({"alg": "ES256", "typ": "JWT", "kid": kid}).encode("utf-8"))
    body = _b64url(json.dumps(payload).encode("utf-8"))
    der_signature = private_key.sign(f"{header}.{body}".encode("ascii"), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_signature)
    signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{header}.{body}.{_b64url(signature)}"


def _jwk(private_key: ec.EllipticCurvePrivateKey, kid: str) -> dict[str, object]:
    public_numbers = private_key.public_key().public_numbers()
    return {
        "keys": [
            {
                "x": _b64url(public_numbers.x.to_bytes(32, "big")),
                "y": _b64url(public_numbers.y.to_bytes(32, "big")),
                "alg": "ES256",
                "crv": "P-256",
                "kid": kid,
                "kty": "EC",
                "key_ops": ["verify"],
            }
        ]
    }


def test_hash_api_key_does_not_echo_raw_key() -> None:
    hashed = hash_api_key("ticrm-secret")

    assert hashed != "ticrm-secret"
    assert len(hashed) == 64


def test_tenant_principal_is_scoped_to_its_tenant() -> None:
    authorize_tenant(APIPrincipal(role="tenant", tenant_id="tenant-001"), "tenant-001")

    with pytest.raises(HTTPException) as exc:
        authorize_tenant(APIPrincipal(role="tenant", tenant_id="tenant-001"), "tenant-002")

    assert exc.value.status_code == 403


def test_only_admin_can_run_admin_action() -> None:
    require_admin(APIPrincipal(role="admin"))

    with pytest.raises(HTTPException) as exc:
        require_admin(APIPrincipal(role="tenant", tenant_id="tenant-001"))

    assert exc.value.status_code == 403


def test_tenant_admin_role_can_run_tenant_admin_action() -> None:
    require_tenant_admin(APIPrincipal(role="owner", tenant_id="tenant-001"), "tenant-001")

    with pytest.raises(HTTPException) as exc:
        require_tenant_admin(APIPrincipal(role="viewer", tenant_id="tenant-001"), "tenant-001")

    assert exc.value.status_code == 403


def test_bearer_token_resolves_membership_principal(monkeypatch) -> None:
    secret = "supabase-test-secret"
    token = _jwt({"sub": "user-001", "email": "user@example.com", "exp": int(time.time()) + 300}, secret)
    monkeypatch.setenv("TICRM_AUTH_JWT_SECRET", secret)
    monkeypatch.setattr(
        "talent_intel_crm.auth.find_tenant_membership_by_user",
        lambda user_id: {
            "tenant_id": "tenant-001",
            "user_id": user_id,
            "email": "user@example.com",
            "role": "recruiter",
        },
    )

    principal = require_principal(authorization=f"Bearer {token}")

    assert principal.role == "recruiter"
    assert principal.tenant_id == "tenant-001"
    assert principal.user_id == "user-001"
    assert principal.auth_method == "bearer"


def test_bearer_token_rejects_invalid_signature(monkeypatch) -> None:
    token = _jwt({"sub": "user-001", "exp": int(time.time()) + 300}, "right-secret")
    monkeypatch.setenv("TICRM_AUTH_JWT_SECRET", "wrong-secret")

    with pytest.raises(HTTPException) as exc:
        require_principal(authorization=f"Bearer {token}")

    assert exc.value.status_code == 401


def test_es256_bearer_token_resolves_membership_principal(monkeypatch) -> None:
    kid = "test-key"
    private_key = ec.generate_private_key(ec.SECP256R1())
    token = _es256_jwt({"sub": "user-001", "email": "user@example.com", "exp": int(time.time()) + 300}, private_key, kid)
    monkeypatch.setenv("SUPABASE_JWT_JWKS", json.dumps(_jwk(private_key, kid)))
    monkeypatch.delenv("TICRM_AUTH_JWT_SECRET", raising=False)
    monkeypatch.setattr(
        "talent_intel_crm.auth.find_tenant_membership_by_user",
        lambda user_id: {
            "tenant_id": "tenant-001",
            "user_id": user_id,
            "email": "user@example.com",
            "role": "owner",
        },
    )

    principal = require_principal(authorization=f"Bearer {token}")

    assert principal.role == "owner"
    assert principal.tenant_id == "tenant-001"
    assert principal.user_id == "user-001"
    assert principal.auth_method == "bearer"


def test_es256_bearer_token_rejects_unknown_key(monkeypatch) -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    token = _es256_jwt({"sub": "user-001", "exp": int(time.time()) + 300}, private_key, "wrong-key")
    monkeypatch.setenv("SUPABASE_JWT_JWKS", json.dumps(_jwk(private_key, "expected-key")))
    monkeypatch.delenv("TICRM_AUTH_JWT_SECRET", raising=False)

    with pytest.raises(HTTPException) as exc:
        require_principal(authorization=f"Bearer {token}")

    assert exc.value.status_code == 401
