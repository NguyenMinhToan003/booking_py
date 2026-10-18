from datetime import date

from pydantic import EmailStr, Field

from app.common.abstracts.base_schema import RequestSchema, ResponseSchema


class UserCreateDTO(RequestSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str = Field(min_length=8, max_length=20)
    date_of_birth: date


class UserResponseDTO(ResponseSchema):
    email: EmailStr
    full_name: str
    phone_number: str
    date_of_birth: date
    is_active: bool
    # hashed_password KHÔNG được đưa vào đây — DTO output không lộ secret.
