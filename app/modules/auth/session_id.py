import hashlib
import secrets
from datetime import datetime, timedelta

from app.common.abstracts.session_store_port import SessionRecord

__all__ = ["SessionRecord", "generate_session_id", "hash_session_id", "is_session_live", "next_idle_expiry"]


def generate_session_id() -> str:
    """256-bit random, vượt xa mức tối thiểu 64-bit entropy OWASP khuyến nghị."""
    return secrets.token_hex(32)


def hash_session_id(raw: str) -> str:
    """Store chỉ giữ hash — dump Redis/Postgres không dùng được làm credential."""
    return hashlib.sha256(raw.encode()).hexdigest()


def is_session_live(record: SessionRecord, now: datetime) -> bool:
    return (
        record.revoked_at is None
        and record.expires_at > now
        and record.absolute_expires_at > now
    )


def next_idle_expiry(now: datetime, idle_ttl_seconds: int, absolute_expires_at: datetime) -> datetime:
    candidate = now + timedelta(seconds=idle_ttl_seconds)
    return min(candidate, absolute_expires_at)
