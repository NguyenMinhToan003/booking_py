import json
from datetime import UTC, datetime

from app.common.abstracts.cache_port import CachePort
from app.common.abstracts.session_store_port import AuthSessionStore, SessionRecord
from app.configs.settings import get_settings

SESSION_KEY_PREFIX = "auth:sess:"


def _session_key(session_id: str) -> str:
    return SESSION_KEY_PREFIX + session_id


def _subject_set_key(subject_id: str) -> str:
    return f"auth:user:{subject_id}:sessions"


def _serialize(record: SessionRecord) -> str:
    return json.dumps(
        {
            "id": record.id,
            "subject_id": record.subject_id,
            "created_at": record.created_at.isoformat(),
            "expires_at": record.expires_at.isoformat(),
            "absolute_expires_at": record.absolute_expires_at.isoformat(),
            "last_seen_at": record.last_seen_at.isoformat(),
            "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
            "replaced_by": record.replaced_by,
            "ip": record.ip,
            "user_agent": record.user_agent,
            "email": record.email,
        }
    )


def _deserialize(raw: str) -> SessionRecord:
    data = json.loads(raw)
    return SessionRecord(
        id=data["id"],
        subject_id=data["subject_id"],
        created_at=datetime.fromisoformat(data["created_at"]),
        expires_at=datetime.fromisoformat(data["expires_at"]),
        absolute_expires_at=datetime.fromisoformat(data["absolute_expires_at"]),
        last_seen_at=datetime.fromisoformat(data["last_seen_at"]),
        revoked_at=datetime.fromisoformat(data["revoked_at"]) if data["revoked_at"] else None,
        replaced_by=data["replaced_by"],
        ip=data["ip"],
        user_agent=data["user_agent"],
        email=data["email"],
    )


class CachedSessionStore(AuthSessionStore):
    """Read-through cache bọc 1 AuthSessionStore nguồn sự thật (thường là PostgresSessionStore,
    nhưng chỉ phụ thuộc port — có thể bọc bất kỳ implementation nào). Giao thức cache-aside:
    - Đường đọc (find_by_id) là nơi duy nhất SET, TTL = min(idle còn lại, cấu hình).
    - Mọi đường ghi: nguồn sự thật commit trước, sau đó chỉ DEL — không SET, tránh đè giá trị
      mới bằng giá trị cũ khi có đọc song song.
    - Cache port tự fallback None/no-op khi lỗi, không raise (xem CachePort)."""

    def __init__(self, inner: AuthSessionStore, cache: CachePort) -> None:
        self.inner = inner
        self._cache = cache
        self.settings = get_settings()

    async def create(self, record: SessionRecord) -> None:
        await self.inner.create(record)
        await self._cache.sadd(_subject_set_key(record.subject_id), record.id)

    async def find_by_id(self, session_id: str) -> SessionRecord | None:
        cached = await self._cache.get(_session_key(session_id))
        if cached:
            return _deserialize(cached)

        record = await self.inner.find_by_id(session_id)
        if record and record.revoked_at is None:
            ttl_seconds = min(
                int((record.expires_at - datetime.now(UTC)).total_seconds()),
                self.settings.SESSION_CACHE_TTL_SECONDS,
            )
            if ttl_seconds > 0:
                await self._cache.set_value(_session_key(session_id), _serialize(record), ex=ttl_seconds)
        return record

    async def touch(self, session_id: str, last_seen_at: datetime, expires_at: datetime) -> bool:
        touched = await self.inner.touch(session_id, last_seen_at, expires_at)
        if touched:
            await self._cache.delete(_session_key(session_id))
        return touched

    async def rotate(self, current_id: str, successor: SessionRecord) -> bool:
        rotated = await self.inner.rotate(current_id, successor)
        if rotated:
            await self._cache.delete(_session_key(current_id))
            await self._cache.sadd(_subject_set_key(successor.subject_id), successor.id)
        return rotated

    async def revoke(self, session_id: str, revoked_at: datetime) -> None:
        await self.inner.revoke(session_id, revoked_at)
        await self._cache.delete(_session_key(session_id))

    async def revoke_all(self, subject_id: str, revoked_at: datetime) -> None:
        await self.inner.revoke_all(subject_id, revoked_at)
        set_key = _subject_set_key(subject_id)
        ids = await self._cache.smembers(set_key)
        await self._cache.delete(*[_session_key(i) for i in ids], set_key)
