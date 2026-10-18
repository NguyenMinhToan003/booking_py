from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class SessionRecord:
    """Domain type trung lập — không riêng Postgres hay Redis, cả 2 implementation
    của AuthSessionStore đều đọc/trả về type này."""

    id: str
    subject_id: str
    created_at: datetime
    expires_at: datetime
    absolute_expires_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None
    replaced_by: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    email: str | None = None


class AuthSessionStore(Protocol):
    """Port trung lập: nguồn sự thật của stateful session, bất kể Postgres thuần
    hay Postgres+Redis cache đứng sau. SessionAuthStrategy chỉ phụ thuộc port này —
    đổi implementation (vd InMemorySessionStore cho test) không đụng domain logic."""

    async def create(self, record: SessionRecord) -> None: ...

    async def find_by_id(self, session_id: str) -> SessionRecord | None: ...

    async def touch(self, session_id: str, last_seen_at: datetime, expires_at: datetime) -> bool: ...

    async def rotate(self, current_id: str, successor: SessionRecord) -> bool: ...

    async def revoke(self, session_id: str, revoked_at: datetime) -> None: ...

    async def revoke_all(self, subject_id: str, revoked_at: datetime) -> None: ...
