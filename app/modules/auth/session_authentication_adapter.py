import logging
from datetime import UTC, datetime

from app.common.abstracts.auth_port import AuthContext, AuthPrincipal
from app.common.abstracts.session_store_port import AuthSessionStore
from app.configs.settings import get_settings
from app.modules.auth.session_id import hash_session_id, is_session_live, next_idle_expiry

logger = logging.getLogger(__name__)


class SessionAuthenticationAdapter:
    """Xác thực mỗi request: 1 lần tra store (Redis hit, miss -> Postgres), không query user.
    Touch trượt idle expiry nhưng throttle để không ghi mỗi request.
    Chỉ phụ thuộc AuthSessionStore port."""

    def __init__(self, store: AuthSessionStore) -> None:
        self.store = store
        self.settings = get_settings()

    async def authenticate(
        self, raw_session_id: str, context: AuthContext
    ) -> AuthPrincipal | None:
        session_id = hash_session_id(raw_session_id)
        record = await self.store.find_by_id(session_id)
        now = datetime.now(UTC)
        if not record or not is_session_live(record, now):
            return None

        if (
            now - record.last_seen_at
        ).total_seconds() >= self.settings.SESSION_TOUCH_INTERVAL_SECONDS:
            expires_at = next_idle_expiry(
                now,
                self.settings.SESSION_IDLE_TTL_MINUTES * 60,
                record.absolute_expires_at,
            )
            try:
                await self.store.touch(session_id, now, expires_at)
            except Exception as exc:  # noqa: BLE001
                logger.warning("session touch failed: %s", exc)

        return AuthPrincipal(
            subject_id=record.subject_id, session_id=session_id, email=record.email
        )
