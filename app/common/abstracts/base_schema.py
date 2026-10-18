import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_serializer


class BaseSchema(BaseModel):
    """Base DTO chung. from_attributes=True để convert trực tiếp từ SQLAlchemy model."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_datetime(self, value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=ZoneInfo("UTC"))
            return value.strftime("%Y-%m-%dT%H:%M:%S%z")
        return value


class RequestSchema(BaseSchema):
    """DTO cho input (create/update). Không có id/version/created_at/updated_at."""


class ResponseSchema(BaseSchema):
    """DTO cho output. Mọi response DTO kế thừa để có id/version/timestamps nhất quán."""

    id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime
