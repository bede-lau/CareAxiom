from __future__ import annotations

from medical_desert.config.settings import Settings
from medical_desert.domain.models import Actor, IdentityMode, ProductRole


class ActorProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def resolve(
        self,
        forwarded_user: str | None,
        forwarded_email: str | None,
    ) -> Actor:
        if self.settings.identity_mode == IdentityMode.SINGLE_TEAM_DEMO:
            return Actor(
                actor_id=self.settings.demo_actor_id,
                display_name=self.settings.demo_actor_name,
                roles=[
                    ProductRole.PLANNER,
                    ProductRole.REVIEWER,
                    ProductRole.ADMINISTRATOR,
                ],
                identity_mode=IdentityMode.SINGLE_TEAM_DEMO,
            )
        actor_id = (forwarded_email or forwarded_user or "").strip().lower()
        if not actor_id:
            raise PermissionError("Trusted platform identity headers are required.")
        roles = self.settings.full_rbac_role_assignments.get(actor_id, [])
        if not roles:
            raise PermissionError("The authenticated actor has no assigned product roles.")
        return Actor(
            actor_id=actor_id,
            display_name=(forwarded_user or forwarded_email or actor_id).strip(),
            roles=roles,
            identity_mode=IdentityMode.FULL_RBAC,
        )
