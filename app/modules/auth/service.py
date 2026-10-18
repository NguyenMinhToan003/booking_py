from app.common.exceptions.domain_exception import DomainException
from app.common.security.password_hasher import DUMMY_HASH, verify_password
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


class InvalidCredentialsError(DomainException):
    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="AUTH_INVALID_CREDENTIALS",
            message="Invalid email or password",
        )


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def authenticate_credentials(self, email: str, password: str) -> User:
        """Verify password; chạy dummy hash khi user không tồn tại để chống timing-attack
        (không lộ thông tin email có tồn tại hay không qua thời gian phản hồi)."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            verify_password(password, DUMMY_HASH)
            raise InvalidCredentialsError()

        verified, _new_hash = verify_password(password, user.hashed_password)
        if not verified:
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InvalidCredentialsError()

        return user
