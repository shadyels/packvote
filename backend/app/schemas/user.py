from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas._limits import NAME_MAX, PASSWORD_MAX, PASSWORD_MIN


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    full_name: str | None = Field(default=None, max_length=NAME_MAX)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


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
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class MessageResponse(BaseModel):
    message: str
