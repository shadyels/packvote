from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_RESET_MSG = "If that email is registered, a reset link has been sent."


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    try:
        user = await auth_service.register_user(db, payload)
    except auth_service.EmailTakenError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from err
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    user = await auth_service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(subject=user.id))


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/password-reset/request", response_model=MessageResponse, status_code=202)
async def request_password_reset(
    payload: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    created = await auth_service.create_reset_token(db, payload.email)
    if created is not None:
        user, token = created
        background_tasks.add_task(
            auth_service.send_reset_email, user.email, user.full_name, token
        )
    return MessageResponse(message=_RESET_MSG)


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    if not await auth_service.confirm_reset(db, payload.token, payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    return MessageResponse(message="Password updated successfully.")
