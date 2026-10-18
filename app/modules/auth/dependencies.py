from fastapi import Cookie, Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.abstracts.auth_port import AuthContext, AuthPrincipal
from app.common.cache.redis_cache import RedisCache
from app.common.cache.redis_client import get_redis
from app.common.exceptions.domain_exception import DomainException
from app.configs.settings import get_settings
from app.database.session import get_db
from app.modules.auth.auth_strategy import SessionAuthStrategy
from app.modules.auth.cached_session_store import CachedSessionStore
from app.modules.auth.postgres_session_store import PostgresSessionStore
from app.modules.auth.service import AuthService
from app.modules.auth.session_authentication_adapter import SessionAuthenticationAdapter
from app.modules.users.repository import UserRepository

SESSION_COOKIE_NAME = "session_id"


class MissingSessionError(DomainException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401, code="AUTH_MISSING_SESSION", message="Missing session"
        )


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(user_repo)


def get_session_strategy(
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SessionAuthStrategy:
    postgres_store = PostgresSessionStore(session)
    cached_store = CachedSessionStore(postgres_store, RedisCache(redis))
    adapter = SessionAuthenticationAdapter(cached_store)
    return SessionAuthStrategy(cached_store, adapter)


def get_auth_context(request: Request) -> AuthContext:
    return AuthContext(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


async def get_current_user(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    strategy: SessionAuthStrategy = Depends(get_session_strategy),
    context: AuthContext = Depends(get_auth_context),
) -> AuthPrincipal:
    if not session_id:
        raise MissingSessionError()
    principal = await strategy.authenticate(session_id, context)
    if principal is None:
        raise MissingSessionError()
    return principal


settings = get_settings()
