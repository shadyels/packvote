from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.schemas._limits import NAME_MAX, PASSWORD_MAX, PASSWORD_MIN

LowerEmail = Annotated[EmailStr, AfterValidator(lambda v: v.strip().lower())]


def _check_bcrypt_bytes(v: str) -> str:
    # bcrypt 5 raises on >72 BYTES; PASSWORD_MAX only counts characters.
    if len(v.encode()) > PASSWORD_MAX:
        raise ValueError(f"password must be at most {PASSWORD_MAX} bytes")
    return v


Password = Annotated[str, AfterValidator(_check_bcrypt_bytes)]


class UserCreate(BaseModel):
    email: LowerEmail
    password: Password = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    full_name: str | None = Field(default=None, max_length=NAME_MAX)


class UserLogin(BaseModel):
    email: LowerEmail
    password: Password


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: LowerEmail


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: Password = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class MessageResponse(BaseModel):
    message: str
