from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.common.abstracts.auth_port import AuthContext, AuthPrincipal
from app.common.abstracts.session_store_port import AuthSessionStore, SessionRecord
from app.common.exceptions.domain_exception import DomainException
from app.configs.settings import get_settings
from app.modules.auth.session_authentication_adapter import SessionAuthenticationAdapter
from app.modules.auth.session_id import generate_session_id, hash_session_id, is_session_live, next_idle_expiry


@dataclass
class AuthResult:
    principal: AuthPrincipal
    raw_session_id: str
    expires_at: datetime


class InvalidSessionError(DomainException):
    def __init__(self, message: str = "Invalid or expired session") -> None:
        super().__init__(status_code=401, code="AUTH_INVALID_SESSION", message=message)


class SessionAlreadyRotatedError(DomainException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="AUTH_SESSION_ROTATED",
            message="Session already rotated",
        )


class SessionAuthStrategy:
    """Stateful session: cookie chỉ mang opaque ID; principal, expiry, revoke state nằm trong store.
    renew = rotate ID (giữ absolute expiry) — dùng sau khi đổi quyền theo khuyến nghị OWASP.
    Chỉ phụ thuộc AuthSessionStore port — không biết Postgres/Redis có cache hay không."""

    def __init__(self, store: AuthSessionStore, authentication: SessionAuthenticationAdapter) -> None:
        self.store = store
        self.authentication = authentication
        self.settings = get_settings()

    async def authenticate(
        self, raw_session_id: str, context: AuthContext
    ) -> AuthPrincipal | None:
        return await self.authentication.authenticate(raw_session_id, context)

    async def sign_in(
        self, subject_id: str, email: str | None, context: AuthContext
    ) -> AuthResult:
        now = datetime.now(UTC)
        absolute_expires_at = now + timedelta(
            days=self.settings.SESSION_ABSOLUTE_TTL_DAYS
        )
        raw, record = self._new_record(
            subject_id, now, absolute_expires_at, context, email
        )
        await self.store.create(record)
        return self._to_result(raw, record)

    async def renew(self, raw_session_id: str, context: AuthContext) -> AuthResult:
        current_id = hash_session_id(raw_session_id)
        current = await self.store.find_by_id(current_id)
        now = datetime.now(UTC)
        if not current or not is_session_live(current, now):
            raise InvalidSessionError()

        raw, record = self._new_record(
            current.subject_id, now, current.absolute_expires_at, context, current.email
        )
        rotated = await self.store.rotate(current_id, record)
        if not rotated:
            raise SessionAlreadyRotatedError()
        return self._to_result(raw, record)

    async def sign_out(self, raw_session_id: str) -> None:
        await self.store.revoke(hash_session_id(raw_session_id), datetime.now(UTC))

    async def revoke_all(self, subject_id: str) -> None:
        await self.store.revoke_all(subject_id, datetime.now(UTC))

    def _new_record(
        self,
        subject_id: str,
        now: datetime,
        absolute_expires_at: datetime,
        context: AuthContext,
        email: str | None,
    ) -> tuple[str, SessionRecord]:
        raw = generate_session_id()
        record = SessionRecord(
            id=hash_session_id(raw),
            subject_id=subject_id,
            created_at=now,
            expires_at=next_idle_expiry(
                now, self.settings.SESSION_IDLE_TTL_MINUTES * 60, absolute_expires_at
            ),
            absolute_expires_at=absolute_expires_at,
            last_seen_at=now,
            revoked_at=None,
            ip=context.ip,
            user_agent=context.user_agent,
            email=email,
        )
        return raw, record

    def _to_result(self, raw: str, record: SessionRecord) -> AuthResult:
        return AuthResult(
            principal=AuthPrincipal(
                subject_id=record.subject_id, session_id=record.id, email=record.email
            ),
            raw_session_id=raw,
            # Cookie sống tới absolute; idle do server quyết định, không phụ thuộc cookie expiry.
            expires_at=record.absolute_expires_at,
        )
