"""Project-level authorization helpers."""

from dataclasses import dataclass

from fastapi import HTTPException, Depends

from packages.platform.auth.firebase import get_current_user, CurrentUser
from packages.platform.store.projects import find_project_for_user

ROLE_HIERARCHY = {"viewer": 0, "editor": 1, "admin": 2}


@dataclass
class ProjectAccess:
    """Result of a successful authorization check."""
    user: CurrentUser
    project: dict
    owner_uid: str


def _check_role(actual_role: str, min_role: str) -> bool:
    """Return True if actual_role >= min_role in the hierarchy."""
    return ROLE_HIERARCHY.get(actual_role, -1) >= ROLE_HIERARCHY.get(min_role, 99)


def require_project_access(min_role: str = "viewer"):
    """FastAPI dependency factory that checks the user has at least `min_role` on the project.

    Extracts project_ref_id from the path parameter. Checks:
    1. User is the project owner (tenant_id matches) -> always allowed
    2. User is a collaborator with role >= min_role
    3. User is_admin flag -> always allowed

    Role hierarchy: viewer < editor < admin

    Returns ProjectAccess(user, project_doc, owner_uid).
    Raises 404 if the project doesn't exist or user has no access (avoids leaking existence).
    """

    async def _dependency(
        project_ref_id: str,
        user: CurrentUser = Depends(get_current_user),
    ) -> ProjectAccess:
        # Find the project for this user (owned or shared)
        project, owner_uid = find_project_for_user(user.tenant_id, project_ref_id)

        if not project or not owner_uid:
            # If user is a global admin, try a broader lookup isn't feasible
            # without knowing the owner. Return 404.
            raise HTTPException(status_code=404, detail="Project not found")

        # Owner always has full access
        if user.tenant_id == owner_uid:
            return ProjectAccess(user=user, project=project, owner_uid=owner_uid)

        # Global admin always has full access
        if user.is_admin:
            return ProjectAccess(user=user, project=project, owner_uid=owner_uid)

        # Check collaborator role
        collabs = project.get("collaborators", {})
        if isinstance(collabs, dict) and user.tenant_id in collabs:
            collab_role = collabs[user.tenant_id].get("role", "viewer")
            if _check_role(collab_role, min_role):
                return ProjectAccess(user=user, project=project, owner_uid=owner_uid)

        # Insufficient permissions — return 404 to avoid leaking existence
        raise HTTPException(status_code=404, detail="Project not found")

    return _dependency
