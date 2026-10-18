import warnings
from functools import lru_cache
from typing import Self

from pydantic import PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    PROJECT_NAME: str = "booking-system"
    API_V1_STR: str = "/api/v1"
    ENV: str = "development"

    DATABASE_URL: PostgresDsn
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_asyncpg_driver(cls, value: str | PostgresDsn) -> str:
        database_url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if database_url.startswith(scheme):
                return database_url.replace(scheme, "postgresql+asyncpg://", 1)
        return database_url

    REDIS_URL: str = "redis://localhost:6379/0"

    SESSION_IDLE_TTL_MINUTES: int = 30
    SESSION_ABSOLUTE_TTL_DAYS: int = 14
    SESSION_TOUCH_INTERVAL_SECONDS: int = 60
    SESSION_CACHE_TTL_SECONDS: int = 300

    # Tách riêng khỏi SESSION_CACHE_TTL_SECONDS: 2 cache khác domain (session vs rbac permission),
    # trùng giá trị default không có nghĩa phải đổi cùng nhau.
    PERMISSION_CACHE_TTL_SECONDS: int = 300

    TRANSACTION_LOCK_TIMEOUT_MS: int = 5000

    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = f'{var_name} is "changethis", change it before deploying.'
            if self.ENV == "development":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        for host in self.DATABASE_URL.hosts():
            self._check_default_secret("DATABASE_URL password", host.get("password"))
        self._check_default_secret("FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
