import json
import logging

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip
from app.models.user import User
from app.models.vote import Vote
from app.models.vote_round import VoteRound
from app.schemas.vote import VoteRoundResult, VotingResults
from app.services.voting.ranked_choice import run_instant_runoff

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
        user_id=None,
    )
    await _maybe_auto_tally(trip_id, trip.current_iteration, db)
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

    vote = await _upsert_vote(
        db=db,
        trip_id=trip_id,
        iteration_number=trip.current_iteration,
        rankings=rankings,
        participant_id=None,
        user_id=user.id,
    )
    await _maybe_auto_tally(trip_id, trip.current_iteration, db)
    return vote


async def get_or_compute_results(
    trip_id: int,
    iteration_number: int | None,
    db: AsyncSession,
) -> VotingResults:
    """Return stored round results or compute and persist them on demand."""
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )

    iteration = (
        iteration_number if iteration_number is not None else trip.current_iteration
    )

    stored = await _load_stored_rounds(trip_id, iteration, db)
    if stored is not None:
        return stored

    return await _compute_and_persist_results(trip_id, iteration, db)


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
    if trip.status not in ("VOTING", "ITERATING"):
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
    user_id: int | None,
) -> Vote:
    if participant_id is not None:
        existing_result = await db.execute(
            select(Vote).where(
                Vote.trip_id == trip_id,
                Vote.iteration_number == iteration_number,
                Vote.participant_id == participant_id,
            )
        )
    else:
        existing_result = await db.execute(
            select(Vote).where(
                Vote.trip_id == trip_id,
                Vote.iteration_number == iteration_number,
                Vote.user_id == user_id,
            )
        )

    vote = existing_result.scalar_one_or_none()
    rankings_json = json.dumps(rankings)

    if vote is None:
        vote = Vote(
            participant_id=participant_id,
            user_id=user_id,
            trip_id=trip_id,
            iteration_number=iteration_number,
            rankings_json=rankings_json,
        )
        db.add(vote)
    else:
        vote.rankings_json = rankings_json

    await db.commit()
    await db.refresh(vote)
    return vote


async def _maybe_auto_tally(
    trip_id: int,
    iteration_number: int,
    db: AsyncSession,
) -> None:
    """Run tally automatically if all eligible voters have submitted."""
    participant_count_result = await db.execute(
        select(func.count(Participant.id)).where(Participant.trip_id == trip_id)
    )
    participant_count = participant_count_result.scalar_one()

    # Eligible voters = all participants + 1 admin
    eligible = participant_count + 1

    vote_count_result = await db.execute(
        select(func.count(Vote.id)).where(
            Vote.trip_id == trip_id,
            Vote.iteration_number == iteration_number,
        )
    )
    vote_count = vote_count_result.scalar_one()

    if vote_count >= eligible:
        await _compute_and_persist_results(trip_id, iteration_number, db)


async def _load_stored_rounds(
    trip_id: int,
    iteration_number: int,
    db: AsyncSession,
) -> VotingResults | None:
    rounds_result = await db.execute(
        select(VoteRound)
        .where(
            VoteRound.trip_id == trip_id,
            VoteRound.iteration_number == iteration_number,
        )
        .order_by(VoteRound.round_number)
    )
    rows = rounds_result.scalars().all()
    if not rows:
        return None

    round_results = [
        VoteRoundResult(
            round_number=r.round_number,
            results={int(k): v for k, v in json.loads(r.results_json).items()},
            eliminated_option_id=r.eliminated_option_id,
            winner_id=r.winner_id,
        )
        for r in rows
    ]

    last = round_results[-1]
    winner_id = last.winner_id
    # A round with no eliminated and no winner means a tie; is_complete = True
    is_complete = winner_id is not None or last.eliminated_option_id is None

    return VotingResults(
        trip_id=trip_id,
        iteration_number=iteration_number,
        rounds=round_results,
        winner_id=winner_id,
        is_complete=is_complete,
    )


async def _compute_and_persist_results(
    trip_id: int,
    iteration_number: int,
    db: AsyncSession,
) -> VotingResults:
    votes_result = await db.execute(
        select(Vote).where(
            Vote.trip_id == trip_id,
            Vote.iteration_number == iteration_number,
        )
    )
    votes = votes_result.scalars().all()

    ballots = [json.loads(v.rankings_json) for v in votes]

    itin_result = await db.execute(
        select(Itinerary.id).where(
            Itinerary.trip_id == trip_id,
            Itinerary.iteration_number == iteration_number,
        )
    )
    candidate_ids = list(itin_result.scalars().all())

    results = run_instant_runoff(trip_id, iteration_number, ballots, candidate_ids)

    # Persist rounds (only if not already stored)
    existing_check = await db.execute(
        select(func.count(VoteRound.id)).where(
            VoteRound.trip_id == trip_id,
            VoteRound.iteration_number == iteration_number,
        )
    )
    if existing_check.scalar_one() == 0:
        for r in results.rounds:
            db.add(
                VoteRound(
                    trip_id=trip_id,
                    iteration_number=iteration_number,
                    round_number=r.round_number,
                    eliminated_option_id=r.eliminated_option_id,
                    results_json=json.dumps(r.results),
                    winner_id=r.winner_id,
                )
            )
        await db.commit()

    return results


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
