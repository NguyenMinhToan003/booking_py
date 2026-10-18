from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.abstracts.auth_port import AuthPrincipal
from app.common.cache.redis_cache import RedisCache
from app.common.cache.redis_client import get_redis
from app.common.exceptions.domain_exception import ForbiddenError
from app.database.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.rbac.service import RbacService


def get_rbac_service(
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> RbacService:
    return RbacService(session, RedisCache(redis))


def require_permissions(*required: str):
    """Dependency factory. required rỗng -> chỉ cần đã xác thực (không check permission gì thêm)."""

    async def checker(
        current_user: AuthPrincipal = Depends(get_current_user),
        rbac: RbacService = Depends(get_rbac_service),
    ) -> AuthPrincipal:
        if not required:
            return current_user
        granted = await rbac.get_user_permissions(current_user.subject_id)
        missing = set(required) - granted
        if missing:
            raise ForbiddenError(f"Missing permissions: {', '.join(sorted(missing))}")
        return current_user

    return checker
