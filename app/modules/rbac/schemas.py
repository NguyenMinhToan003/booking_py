from app.common.abstracts.base_schema import RequestSchema, ResponseSchema


class RoleResponseDTO(ResponseSchema):
    name: str
    description: str | None = None


class PermissionResponseDTO(ResponseSchema):
    name: str


class SetRolePermissionsDTO(RequestSchema):
    permissions: list[str]


class SetUserRolesDTO(RequestSchema):
    role_ids: list[str]
