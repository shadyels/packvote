import logging

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip
from app.models.user import User
from app.models.vote import Vote
from app.schemas.vote import VotingResults
from app.services.voting.ranked_choice import tally

logger = logging.getLogger(__name__)


async def submit_participant_vote(
    token: str,
    trip_id: int,
    rankings: list[int],
    db: AsyncSession,
) -> Vote:
    """Submit or update a participant's ranked-choice vote."""
    participant_result = await db.execute(
        select(Participant).where(Participant.token == token)
    )
    participant = participant_result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found"
        )
    if participant.trip_id != trip_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Participant does not belong to this trip",
        )

    trip = await _get_voting_trip(trip_id, db)
    await _validate_rankings(rankings, trip_id, trip.current_iteration, db)

    vote = await _upsert_vote(
        db=db,
        trip_id=trip_id,
        iteration_number=trip.current_iteration,
        rankings=rankings,
        participant_id=participant.id,
    )
    await _maybe_auto_tally(trip, db)
    return vote


async def submit_admin_vote(
    user: User,
    trip_id: int,
    rankings: list[int],
    db: AsyncSession,
) -> Vote:
    """Submit or update the trip creator's ranked-choice vote."""
    trip = await _get_voting_trip(trip_id, db)
    if trip.creator_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    await _validate_rankings(rankings, trip_id, trip.current_iteration, db)

    creator_participant_result = await db.execute(
        select(Participant).where(
            Participant.trip_id == trip_id,
            Participant.user_id == user.id,
        )
    )
    creator_participant = creator_participant_result.scalar_one_or_none()
    if creator_participant is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Creator participant row missing for this trip",
        )

    vote = await _upsert_vote(
        db=db,
        trip_id=trip_id,
        iteration_number=trip.current_iteration,
        rankings=rankings,
        participant_id=creator_participant.id,
    )
    await _maybe_auto_tally(trip, db)
    return vote


async def compute_results(
    db: AsyncSession, trip: Trip, iteration: int | None = None
) -> VotingResults:
    """Compute voting results from the Vote rows on every read (nothing stored).

    For a FINALIZED trip viewed at its current iteration, the reported winner is
    ``trip.winner_itinerary_id`` (the admin may have overridden the tally).
    """
    iteration = trip.current_iteration if iteration is None else iteration
    ballots = list(
        (
            await db.execute(
                select(Vote.rankings).where(
                    Vote.trip_id == trip.id, Vote.iteration_number == iteration
                )
            )
        )
        .scalars()
        .all()
    )
    candidate_ids = list(
        (
            await db.execute(
                select(Itinerary.id).where(
                    Itinerary.trip_id == trip.id,
                    Itinerary.iteration_number == iteration,
                )
            )
        )
        .scalars()
        .all()
    )
    rounds, winner_id = tally(ballots, candidate_ids)
    if trip.status == "FINALIZED" and iteration == trip.current_iteration:
        winner_id = trip.winner_itinerary_id
    return VotingResults(
        trip_id=trip.id,
        iteration_number=iteration,
        rounds=rounds,
        winner_id=winner_id,
        is_complete=bool(ballots),
    )


async def pick_winner(
    user: User,
    trip_id: int,
    itinerary_id: int,
    db: AsyncSession,
) -> Trip:
    """Admin picks a winner, finalizing the trip."""
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )
    if trip.creator_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    if trip.status != "VOTING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot pick winner from status '{trip.status}'",
        )

    itin_result = await db.execute(
        select(Itinerary).where(
            Itinerary.id == itinerary_id, Itinerary.trip_id == trip_id
        )
    )
    if itin_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found for this trip",
        )

    trip.winner_itinerary_id = itinerary_id
    trip.status = "FINALIZED"
    await db.commit()
    await db.refresh(trip)

    await _send_finalized_emails(trip, itinerary_id, db)

    return trip


async def trigger_new_iteration(
    user: User,
    trip_id: int,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    session_factory: async_sessionmaker[AsyncSession],
) -> dict:
    """Admin triggers a new iteration of AI generation + voting."""
    from app.services.generation import run_generation  # avoid circular import

    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )
    if trip.creator_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    if trip.status != "VOTING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start new iteration from status '{trip.status}'",
        )
    if trip.current_iteration >= trip.max_iterations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Maximum iterations ({trip.max_iterations}) reached",
        )

    trip.status = "GENERATING"
    await db.commit()

    background_tasks.add_task(run_generation, trip_id, session_factory)
    return {"status": "accepted", "trip_id": trip_id}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_voting_trip(trip_id: int, db: AsyncSession) -> Trip:
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )
    if trip.status != "VOTING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Trip is not in VOTING status (current: '{trip.status}')",
        )
    return trip


async def _validate_rankings(
    rankings: list[int],
    trip_id: int,
    iteration_number: int,
    db: AsyncSession,
) -> None:
    itin_result = await db.execute(
        select(Itinerary.id).where(
            Itinerary.trip_id == trip_id,
            Itinerary.iteration_number == iteration_number,
        )
    )
    valid_ids = set(itin_result.scalars().all())
    if not valid_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No itineraries found for this trip and iteration",
        )
    if set(rankings) != valid_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Rankings must contain exactly all itinerary IDs for this iteration",
        )


async def _upsert_vote(
    db: AsyncSession,
    trip_id: int,
    iteration_number: int,
    rankings: list[int],
    participant_id: int | None,
) -> Vote:
    existing_result = await db.execute(
        select(Vote).where(
            Vote.trip_id == trip_id,
            Vote.iteration_number == iteration_number,
            Vote.participant_id == participant_id,
        )
    )

    vote = existing_result.scalar_one_or_none()

    if vote is None:
        vote = Vote(
            participant_id=participant_id,
            trip_id=trip_id,
            iteration_number=iteration_number,
            rankings=rankings,
        )
        db.add(vote)
    else:
        vote.rankings = rankings

    await db.commit()
    await db.refresh(vote)
    return vote


async def _maybe_auto_tally(trip: Trip, db: AsyncSession) -> None:
    """Run tally automatically if all eligible voters have submitted.

    Callers guarantee ``trip`` is in VOTING (via ``_get_voting_trip``), and a
    VOTING trip never has a winner set, so it is always finalizable here.
    """
    participant_count_result = await db.execute(
        select(func.count(Participant.id)).where(Participant.trip_id == trip.id)
    )
    participant_count = participant_count_result.scalar_one()

    vote_count_result = await db.execute(
        select(func.count(Vote.id)).where(
            Vote.trip_id == trip.id,
            Vote.iteration_number == trip.current_iteration,
        )
    )
    vote_count = vote_count_result.scalar_one()

    if vote_count < participant_count:
        return

    results = await compute_results(db, trip)

    if results.winner_id is not None:
        trip.winner_itinerary_id = results.winner_id
        trip.status = "FINALIZED"
        await db.commit()
        await db.refresh(trip)
        await _send_finalized_emails(trip, results.winner_id, db)


async def _send_finalized_emails(
    trip: Trip, itinerary_id: int, db: AsyncSession
) -> None:
    """Send finalized notification to all participants (best-effort)."""
    from app.services.email.brevo import EmailService

    itin_result = await db.execute(
        select(Itinerary).where(Itinerary.id == itinerary_id)
    )
    itinerary = itin_result.scalar_one_or_none()
    if itinerary is None:
        return

    participants_result = await db.execute(
        select(Participant).where(Participant.trip_id == trip.id)
    )
    participants = participants_result.scalars().all()

    email_service = EmailService.from_settings()
    for p in participants:
        try:  # noqa: SIM105
            await email_service.send_finalized_notification(
                to_email=p.email,
                participant_name=p.name,
                trip_title=trip.title,
                trip_code=trip.trip_code,
                pin=p.pin,
                token=p.token,
                destination_name=itinerary.destination_name,
            )
        except Exception:
            logger.warning(
                "Failed to send finalized email to %s for trip %d", p.email, trip.id
            )
