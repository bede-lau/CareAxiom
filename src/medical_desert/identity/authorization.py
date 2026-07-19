from medical_desert.domain.models import Actor, ProductRole, Scenario


def require_role(actor: Actor, *roles: ProductRole) -> None:
    if not any(role in actor.roles for role in roles):
        raise PermissionError(
            f"One of these roles is required: {', '.join(role.value for role in roles)}"
        )


def require_scenario_access(actor: Actor, scenario: Scenario, *, write: bool = False) -> None:
    if ProductRole.ADMINISTRATOR in actor.roles:
        return
    if scenario.owner_id == actor.actor_id or actor.actor_id in scenario.collaborators:
        return
    action = "update" if write else "read"
    raise PermissionError(f"Actor is not allowed to {action} this scenario.")
