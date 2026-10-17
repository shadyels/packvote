import asyncio
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.participant import Participant
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.email.brevo import EmailService

logger = logging.getLogger(__name__)

# Verified against on unknown email so login timing doesn't reveal account existence.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class EmailTakenError(Exception):
    pass


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def register_user(db: AsyncSession, payload: UserCreate) -> User:
    exists = await db.execute(select(User.id).where(User.email == payload.email))
    if exists.scalar_one_or_none() is not None:
        raise EmailTakenError
    user = User(
        email=payload.email,
        hashed_password=await asyncio.to_thread(hash_password, payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    try:
        await db.flush()
        # Keep in sync with create_trip's user_id lookup (see CLAUDE.md).
        await db.execute(
            update(Participant)
            .where(func.lower(Participant.email) == payload.email.lower())
            .values(user_id=user.id)
        )
        await db.commit()
    except IntegrityError as err:  # concurrent duplicate registration
        await db.rollback()
        raise EmailTakenError from err
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    hashed = user.hashed_password if user is not None else _DUMMY_HASH
    ok = await asyncio.to_thread(verify_password, password, hashed)
    return user if ok and user is not None else None


async def create_reset_token(db: AsyncSession, email: str) -> tuple[User, str] | None:
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None:
        return None
    token = secrets.token_urlsafe(32)
    user.reset_token_hash = hash_reset_token(token)
    user.reset_token_expires_at = datetime.now(UTC) + timedelta(
        minutes=get_settings().RESET_TOKEN_EXPIRE_MINUTES
    )
    await db.commit()
    return user, token


async def send_reset_email(to_email: str, full_name: str | None, token: str) -> None:
    """Background task; takes plain values, never ORM objects."""
    try:
        await EmailService.from_settings().send_password_reset(
            to_email=to_email, full_name=full_name, reset_token=token
        )
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)


async def confirm_reset(db: AsyncSession, token: str, new_password: str) -> bool:
    user = (
        await db.execute(
            select(User).where(
                User.reset_token_hash == hash_reset_token(token),
                User.reset_token_expires_at > datetime.now(UTC),
            )
        )
    ).scalar_one_or_none()
    if user is None:
        return False
    user.hashed_password = await asyncio.to_thread(hash_password, new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    user.password_changed_at = datetime.now(UTC)
    await db.commit()
    return True
