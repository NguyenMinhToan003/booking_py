from datetime import UTC, datetime
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.abstracts.base_model import BaseModel
from app.common.exceptions.domain_exception import NotFoundError

ModelT = TypeVar("ModelT", bound=BaseModel)


class DeletableRepository:
    """Mở khoá xoá mềm/khôi phục/xoá cứng. Entity không cần xoá (vd audit log) thì
    service của nó không import class này — không có nghĩa là lỗi, chỉ là không cần.
    Mọi SELECT trong codebase phải tự thêm .where(Model.deleted_at.is_(None)) khi cần
    loại bản ghi đã xoá mềm — không có global auto-filter, tránh query ẩn khó debug."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def soft_remove(self, model: type[ModelT], entity_id: object) -> None:
        entity = await self.session.get(model, entity_id)
        if entity is None or entity.deleted_at is not None:
            raise NotFoundError(f"{model.__name__} not found")
        entity.deleted_at = datetime.now(UTC)
        await self.session.commit()

    async def restore(self, model: type[ModelT], entity_id: object) -> None:
        entity = await self.session.get(model, entity_id)
        if entity is None or entity.deleted_at is None:
            raise NotFoundError(f"{model.__name__} not found")
        entity.deleted_at = None
        await self.session.commit()

    async def hard_remove(self, model: type[ModelT], entity_id: object) -> None:
        entity = await self.session.get(model, entity_id)
        if entity is None:
            raise NotFoundError(f"{model.__name__} not found")
        await self.session.delete(entity)
        await self.session.commit()
