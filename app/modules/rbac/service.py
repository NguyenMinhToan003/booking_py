import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.abstracts.cache_port import CachePort
from app.common.abstracts.deletable_repository import DeletableRepository
from app.common.exceptions.domain_exception import BadRequestError, NotFoundError
from app.configs.settings import get_settings
from app.modules.rbac.models import Permission, Role, role_permissions, user_roles
from app.modules.users.models import User

PERM_CACHE_PREFIX = "rbac:perms:"


class RbacService:
    def __init__(self, session: AsyncSession, cache: CachePort) -> None:
        self.session = session
        self._cache = cache
        self.settings = get_settings()
        self.deletable = DeletableRepository(session)

    async def get_user_permissions(self, user_id: str) -> set[str]:
        cache_key = PERM_CACHE_PREFIX + user_id
        cached = await self._cache.get(cache_key)
        if cached:
            return set(json.loads(cached))

        user = await self.session.get(User, user_id)
        permissions = {
            p.name
            for role in (user.roles if user else [])
            if role.deleted_at is None
            for p in role.permissions
        }
        await self._cache.set_value(
            cache_key, json.dumps(list(permissions)), ex=self.settings.PERMISSION_CACHE_TTL_SECONDS
        )
        return permissions

    async def list_roles(self) -> list[Role]:
        result = await self.session.execute(
            select(Role).where(Role.deleted_at.is_(None)).order_by(Role.name)
        )
        return list(result.scalars().all())

    async def list_permissions(self) -> list[Permission]:
        result = await self.session.execute(
            select(Permission).where(Permission.deleted_at.is_(None)).order_by(Permission.name)
        )
        return list(result.scalars().all())

    async def set_role_permissions(self, role_id: str, permission_names: list[str]) -> Role:
        async with self.session.begin():
            role = await self.session.get(Role, role_id, with_for_update=True)
            if role is None:
                raise NotFoundError("Role not found")

            result = await self.session.execute(
                select(Permission).where(Permission.name.in_(permission_names))
            )
            permissions = list(result.scalars().all())
            missing = set(permission_names) - {p.name for p in permissions}
            if missing:
                raise BadRequestError(
                    "Unknown permissions", code="RBAC_UNKNOWN_PERMISSION", details={"missing": list(missing)}
                )

            role.permissions = permissions

        await self._invalidate_all()
        return role

    async def set_user_roles(self, user_id: str, role_ids: list[str]) -> User:
        async with self.session.begin():
            user = await self.session.get(User, user_id, with_for_update=True)
            if user is None:
                raise NotFoundError("User not found")

            result = await self.session.execute(select(Role).where(Role.id.in_(role_ids)))
            roles = list(result.scalars().all())
            missing = set(role_ids) - {str(r.id) for r in roles}
            if missing:
                raise BadRequestError(
                    "Unknown roles", code="RBAC_UNKNOWN_ROLE", details={"missing": list(missing)}
                )

            user.roles = roles

        await self._invalidate_user(user_id)
        return user

    async def soft_remove_role(self, role_id: str) -> None:
        count_stmt = select(func.count()).select_from(user_roles).where(user_roles.c.role_id == role_id)
        in_use = (await self.session.execute(count_stmt)).scalar_one()
        if in_use > 0:
            raise BadRequestError(
                "Role is still assigned to users",
                code="RBAC_ROLE_IN_USE",
                details={"id": role_id, "userCount": in_use},
            )
        await self.deletable.soft_remove(Role, role_id)
        await self._invalidate_all()

    async def restore_role(self, role_id: str) -> None:
        await self.deletable.restore(Role, role_id)

    async def soft_remove_permission(self, permission_id: str) -> None:
        count_stmt = (
            select(func.count())
            .select_from(role_permissions)
            .where(role_permissions.c.permission_id == permission_id)
        )
        in_use = (await self.session.execute(count_stmt)).scalar_one()
        if in_use > 0:
            raise BadRequestError(
                "Permission is still assigned to roles",
                code="RBAC_PERMISSION_IN_USE",
                details={"id": permission_id, "roleCount": in_use},
            )
        await self.deletable.soft_remove(Permission, permission_id)

    async def restore_permission(self, permission_id: str) -> None:
        await self.deletable.restore(Permission, permission_id)

    async def _invalidate_user(self, user_id: str) -> None:
        await self._cache.delete(PERM_CACHE_PREFIX + user_id)

    async def _invalidate_all(self) -> None:
        keys = await self._cache.scan_keys(f"{PERM_CACHE_PREFIX}*")
        if keys:
            await self._cache.delete(*keys)
