from fastapi import APIRouter, Depends

from app.modules.rbac.dependencies import get_rbac_service, require_permissions
from app.modules.rbac.schemas import (
    PermissionResponseDTO,
    RoleResponseDTO,
    SetRolePermissionsDTO,
    SetUserRolesDTO,
)
from app.modules.rbac.service import RbacService

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.get(
    "/roles",
    response_model=list[RoleResponseDTO],
    dependencies=[Depends(require_permissions("role:read"))],
)
async def list_roles(
    rbac: RbacService = Depends(get_rbac_service),
) -> list[RoleResponseDTO]:
    roles = await rbac.list_roles()
    return [RoleResponseDTO.model_validate(r) for r in roles]


@router.get(
    "/permissions",
    response_model=list[PermissionResponseDTO],
    dependencies=[Depends(require_permissions("role:read"))],
)
async def list_permissions(
    rbac: RbacService = Depends(get_rbac_service),
) -> list[PermissionResponseDTO]:
    permissions = await rbac.list_permissions()
    return [PermissionResponseDTO.model_validate(p) for p in permissions]


@router.put(
    "/roles/{role_id}/permissions",
    response_model=RoleResponseDTO,
    dependencies=[Depends(require_permissions("role:manage"))],
)
async def set_role_permissions(
    role_id: str,
    body: SetRolePermissionsDTO,
    rbac: RbacService = Depends(get_rbac_service),
) -> RoleResponseDTO:
    role = await rbac.set_role_permissions(role_id, body.permissions)
    return RoleResponseDTO.model_validate(role)


@router.put(
    "/users/{user_id}/roles",
    status_code=204,
    dependencies=[Depends(require_permissions("user:manage"))],
)
async def set_user_roles(
    user_id: str, body: SetUserRolesDTO, rbac: RbacService = Depends(get_rbac_service)
) -> None:
    await rbac.set_user_roles(user_id, body.role_ids)
