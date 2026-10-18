from dataclasses import dataclass
from typing import Protocol


@dataclass
class AuthContext:
    ip: str | None = None
    user_agent: str | None = None


@dataclass
class AuthPrincipal:
    subject_id: str
    session_id: str
    email: str | None = None


class AuthenticationPort(Protocol):
    """Port trung lập: credential (session id) -> AuthPrincipal mỗi request.
    Router/dependency chỉ phụ thuộc port này, không biết session hay JWT nằm bên dưới."""

    async def authenticate(self, raw_session_id: str, context: AuthContext) -> AuthPrincipal | None: ...
