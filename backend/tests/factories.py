"""ORM seed builders shared across tests. Each ``make_*`` adds the row to ``db``."""

from __future__ import annotations

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip
from app.models.user import User


def make_user(db: AsyncSession, **kwargs) -> User:
    defaults = dict(
        email=f"user_{secrets.token_hex(4)}@test.com",
        hashed_password="hashed",
        full_name=None,
    )
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    return user


def make_trip(db: AsyncSession, creator: User, **kwargs) -> Trip:
    defaults = dict(
        trip_code=secrets.token_hex(4).upper()[:8],
        creator_id=creator.id,
        title="Test Trip",
        destination=None,
        num_options=2,
        status="VOTING",
        max_iterations=10,
        current_iteration=1,
        winner_itinerary_id=None,
    )
    defaults.update(kwargs)
    trip = Trip(**defaults)
    db.add(trip)
    return trip


def make_participant(db: AsyncSession, trip: Trip, **kwargs) -> Participant:
    defaults = dict(
        trip_id=trip.id,
        email=f"p_{secrets.token_hex(4)}@test.com",
        token=secrets.token_urlsafe(32),
        pin=secrets.token_hex(2)[:4],
        preferences_submitted=True,
    )
    defaults.update(kwargs)
    p = Participant(**defaults)
    db.add(p)
    return p


def make_itinerary(
    db: AsyncSession, trip: Trip | int, iteration: int = 1, **kwargs
) -> Itinerary:
    """``trip`` may be a Trip or a trip id."""
    defaults = dict(
        trip_id=trip if isinstance(trip, int) else trip.id,
        iteration_number=iteration,
        destination_name="Test Destination",
        destination_description="A lovely place.",
        daily_itinerary=[],
        total_estimated_budget=1000.0,
        currency="USD",
        match_reasoning="Great match.",
        highlights=["highlight1"],
    )
    defaults.update(kwargs)
    itin = Itinerary(**defaults)
    db.add(itin)
    return itin


async def seed_voting_trip(
    db: AsyncSession,
    *,
    creator_email: str | None = None,
    invitee_email: str | None = None,
    hashed_password: str = "hashed",
) -> dict:
    """VOTING trip: creator + creator participant, one invitee, 2 itineraries."""
    user = make_user(
        db,
        hashed_password=hashed_password,
        **({"email": creator_email} if creator_email else {}),
    )
    await db.flush()
    trip = make_trip(db, user)
    await db.flush()
    participant = make_participant(
        db, trip, **({"email": invitee_email} if invitee_email else {})
    )
    creator_participant = make_participant(db, trip, email=user.email, user_id=user.id)
    await db.flush()
    itineraries = [make_itinerary(db, trip), make_itinerary(db, trip)]
    await db.flush()
    return {
        "user": user,
        "trip": trip,
        "participant": participant,
        "creator_participant": creator_participant,
        "itineraries": itineraries,
    }
