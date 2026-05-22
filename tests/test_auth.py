import pytest
from fastapi import HTTPException

from talent_intel_crm.auth import APIPrincipal, authorize_tenant, hash_api_key, require_admin


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
