from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.abstracts.session_store_port import AuthSessionStore, SessionRecord
from app.modules.auth.models import AuthSession


class PostgresSessionStore(AuthSessionStore):
    """Nguồn sự thật của stateful session. Implement AuthSessionStore port."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, record: SessionRecord) -> None:
        self.session.add(self._to_entity(record))
        await self.session.commit()

    async def find_by_id(self, session_id: str) -> SessionRecord | None:
        row = await self.session.get(AuthSession, session_id)
        return self._to_record(row) if row else None

    async def touch(
        self, session_id: str, last_seen_at: datetime, expires_at: datetime
    ) -> bool:
        stmt = (
            update(AuthSession)
            .where(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
            .values(last_seen_at=last_seen_at, expires_at=expires_at)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def rotate(self, current_id: str, successor: SessionRecord) -> bool:
        """Conditional UPDATE trên row hiện tại là điểm serialize: hai renew đồng thời
        chỉ một cái affected=1, cái còn lại False — không cần advisory lock."""
        async with self.session.begin():
            stmt = (
                update(AuthSession)
                .where(AuthSession.id == current_id, AuthSession.revoked_at.is_(None))
                .values(revoked_at=successor.created_at, replaced_by=successor.id)
            )
            result = await self.session.execute(stmt)
            if result.rowcount != 1:
                return False
            self.session.add(self._to_entity(successor))
        return True

    async def revoke(self, session_id: str, revoked_at: datetime) -> None:
        stmt = (
            update(AuthSession)
            .where(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def revoke_all(self, subject_id: str, revoked_at: datetime) -> None:
        stmt = (
            update(AuthSession)
            .where(
                AuthSession.subject_id == subject_id, AuthSession.revoked_at.is_(None)
            )
            .values(revoked_at=revoked_at)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    def _to_entity(self, record: SessionRecord) -> AuthSession:
        return AuthSession(
            id=record.id,
            subject_id=record.subject_id,
            created_at=record.created_at,
            expires_at=record.expires_at,
            absolute_expires_at=record.absolute_expires_at,
            last_seen_at=record.last_seen_at,
            revoked_at=record.revoked_at,
            replaced_by=None,
            ip=record.ip,
            user_agent=record.user_agent,
            data={"email": record.email} if record.email else None,
        )

    def _to_record(self, row: AuthSession) -> SessionRecord:
        return SessionRecord(
            id=row.id,
            subject_id=str(row.subject_id),
            created_at=row.created_at,
            expires_at=row.expires_at,
            absolute_expires_at=row.absolute_expires_at,
            last_seen_at=row.last_seen_at,
            revoked_at=row.revoked_at,
            replaced_by=row.replaced_by,
            ip=row.ip,
            user_agent=row.user_agent,
            email=(row.data or {}).get("email"),
        )
