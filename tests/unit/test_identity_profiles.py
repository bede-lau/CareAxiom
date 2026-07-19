from __future__ import annotations

import pytest

from medical_desert.config.settings import Settings
from medical_desert.domain.models import IdentityMode, ProductRole
from medical_desert.identity.actor import ActorProvider


def test_single_team_demo_uses_one_fixed_team_identity() -> None:
    provider = ActorProvider(
        Settings(identity_mode=IdentityMode.SINGLE_TEAM_DEMO, demo_actor_id="demo-planner")
    )
    resolved = provider.resolve("Other User", "other@example.com")
    assert resolved.actor_id == "demo-planner"
    assert resolved.roles == [
        ProductRole.PLANNER,
        ProductRole.REVIEWER,
        ProductRole.ADMINISTRATOR,
    ]


def test_full_rbac_requires_trusted_actor_headers() -> None:
    provider = ActorProvider(Settings(identity_mode=IdentityMode.FULL_RBAC))
    with pytest.raises(PermissionError, match="required"):
        provider.resolve(None, None)


def test_full_rbac_maps_server_side_product_roles() -> None:
    provider = ActorProvider(
        Settings(
            identity_mode=IdentityMode.FULL_RBAC,
            full_rbac_role_assignments={
                "reviewer@example.com": [ProductRole.REVIEWER, ProductRole.ADMINISTRATOR]
            },
        )
    )
    resolved = provider.resolve("Reviewer", "reviewer@example.com")
    assert resolved.roles == [ProductRole.REVIEWER, ProductRole.ADMINISTRATOR]


def test_full_rbac_rejects_authenticated_actor_without_role_assignment() -> None:
    provider = ActorProvider(Settings(identity_mode=IdentityMode.FULL_RBAC))
    with pytest.raises(PermissionError, match="no assigned product roles"):
        provider.resolve("Unassigned User", "unassigned@example.com")
