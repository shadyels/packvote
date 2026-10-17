from datetime import UTC
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import decode_access_token
from app.db.session import get_db
from app.db.session import get_session_factory as _get_session_factory
from app.models.participant import Participant
from app.models.trip import Trip
from app.models.user import User
from app.services.email.brevo import EmailService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    return await _user_from_token(token, db)


async def _user_from_token(token: str, db: AsyncSession) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (PyJWTError, ValueError) as err:
        raise credentials_exception from err

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if user.password_changed_at is not None:
        # iat is whole seconds; truncate the column to match so a token issued
        # in the same second right after a reset is accepted. Ceiling: a token
        # issued earlier in that same second as the reset is also accepted.
        changed = user.password_changed_at
        if changed.tzinfo is None:  # SQLite returns naive datetimes
            changed = changed.replace(tzinfo=UTC)
        if int(payload.get("iat", 0)) < int(changed.timestamp()):
            raise credentials_exception
    return user


async def get_results_trip(
    trip_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    jwt_token: Annotated[str | None, Depends(optional_oauth2_scheme)] = None,
    x_participant_token: Annotated[str | None, Header()] = None,
) -> Trip:
    """Trip for the results endpoint; caller must be a participant or creator.

    401 (no/invalid credentials) precedes 404 so anonymous callers cannot probe
    trip existence; 403 means valid credentials without access to this trip.
    """
    participant = None
    if x_participant_token is not None:
        participant = (
            await db.execute(
                select(Participant).where(Participant.token == x_participant_token)
            )
        ).scalar_one_or_none()
    if participant is not None and participant.trip_id == trip_id:
        # Participant token alone grants access; a stale bearer JWT must not
        # break it (the frontend sends both when both are stored).
        trip = await db.get(Trip, trip_id)
        if trip is not None:
            return trip
    user = None
    if jwt_token is not None:
        try:
            user = await _user_from_token(jwt_token, db)
        except HTTPException:
            if (
                participant is None
            ):  # an invalid JWT is "absent" next to a participant token
                raise
    if participant is None and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    trip = await db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    allowed = participant is not None and participant.trip_id == trip_id
    if not allowed and user is not None:
        allowed = (
            trip.creator_id == user.id
            or (
                await db.execute(
                    select(Participant.id).where(
                        Participant.trip_id == trip_id, Participant.user_id == user.id
                    )
                )
            ).first()
            is not None
        )
    if not allowed:
        raise HTTPException(status_code=403, detail="Not allowed to view results")
    return trip


CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]


def get_email_service() -> EmailService:
    return EmailService.from_settings()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return _get_session_factory()
