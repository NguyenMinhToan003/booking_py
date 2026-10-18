from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.abstracts.base_model import BaseModel

T = TypeVar("T")
ModelT = TypeVar("ModelT", bound=BaseModel)


class OptimisticConcurrencyError(Exception):
    def __init__(
        self, entity_name: str, entity_id: object, expected_version: int
    ) -> None:
        self.entity_name = entity_name
        self.entity_id = entity_id
        self.expected_version = expected_version
        super().__init__(
            f"{entity_name} {entity_id} is no longer at version {expected_version}"
        )


async def acquire_transaction_advisory_lock(
    session: AsyncSession, namespace: int, key: str
) -> None:
    """PostgreSQL transaction-scoped lock. namespace tách domain lock, tránh đụng nhau giữa các module.
    Tự giải phóng khi transaction commit/rollback — phải gọi trong session.begin()."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:ns, hashtext(:key))"),
        {"ns": namespace, "key": key},
    )


async def run_in_transaction(
    session: AsyncSession,
    work: Callable[[], Awaitable[T]],
    lock_timeout_ms: int | None = None,
) -> T:
    async with session.begin():
        if lock_timeout_ms is not None:
            await session.execute(
                text("SELECT set_config('lock_timeout', :timeout, true)"),
                {"timeout": f"{lock_timeout_ms}ms"},
            )
        return await work()


async def update_with_version(
    session: AsyncSession,
    model: type[ModelT],
    entity_id: object,
    expected_version: int,
    changes: dict,
) -> None:
    """Compare-and-swap: UPDATE chỉ thành công nếu version khớp. Dùng cho optimistic lock
    khi client gửi version cùng payload update (vd đổi trạng thái booking)."""
    if expected_version < 1:
        raise ValueError("expected_version must be a positive integer")

    safe_changes = {
        k: v
        for k, v in changes.items()
        if k not in ("id", "version", "created_at", "updated_at")
    }

    stmt = (
        update(model)
        .where(model.id == entity_id, model.version == expected_version)
        .values(**safe_changes, version=model.version + 1)
    )
    result = await session.execute(stmt)
    if result.rowcount != 1:
        raise OptimisticConcurrencyError(model.__name__, entity_id, expected_version)
