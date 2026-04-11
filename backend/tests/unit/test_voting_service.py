"""Unit tests for the voting service layer (DB interactions)."""

from __future__ import annotations

import json
import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip
from app.models.user import User
from app.models.vote import Vote
from app.models.vote_round import VoteRound
from app.services.voting.service import (
    get_or_compute_results,
    pick_winner,
    submit_admin_vote,
    submit_participant_vote,
    trigger_new_iteration,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(db: AsyncSession, **kwargs) -> User:
    defaults = dict(
        email=f"user_{secrets.token_hex(4)}@test.com",
        hashed_password="hashed",
        full_name=None,
    )
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    return user


def _make_trip(db: AsyncSession, creator: User, **kwargs) -> Trip:
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


def _make_participant(db: AsyncSession, trip: Trip, **kwargs) -> Participant:
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


def _make_itinerary(
    db: AsyncSession, trip: Trip, iteration: int = 1, **kwargs
) -> Itinerary:
    defaults = dict(
        trip_id=trip.id,
        iteration_number=iteration,
        destination_name="Test Destination",
        destination_description="A lovely place.",
        daily_itinerary_json=json.dumps([]),
        total_estimated_budget=1000.0,
        currency="USD",
        match_reasoning="Great match.",
        highlights=json.dumps(["highlight1"]),
    )
    defaults.update(kwargs)
    itin = Itinerary(**defaults)
    db.add(itin)
    return itin


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def voting_setup(db: AsyncSession):
    """Create a trip in VOTING status with 1 invitee participant, 1 creator participant, and 2 itineraries."""
    user = _make_user(db)
    db.add(user)
    await db.flush()

    trip = _make_trip(db, user)
    db.add(trip)
    await db.flush()

    participant = _make_participant(db, trip)
    db.add(participant)
    await db.flush()

    # Creator participant row — mirrors what create_trip now inserts
    creator_participant = _make_participant(
        db, trip, email=user.email, user_id=user.id, preferences_submitted=True
    )
    db.add(creator_participant)
    await db.flush()

    itin1 = _make_itinerary(db, trip, iteration=1)
    itin2 = _make_itinerary(db, trip, iteration=1)
    db.add(itin1)
    db.add(itin2)
    await db.flush()

    return {
        "user": user,
        "trip": trip,
        "participant": participant,
        "creator_participant": creator_participant,
        "itineraries": [itin1, itin2],
    }


# ---------------------------------------------------------------------------
# submit_participant_vote
# ---------------------------------------------------------------------------


class TestSubmitParticipantVote:
    async def test_success(self, db: AsyncSession, voting_setup) -> None:
        s = voting_setup
        itin_ids = [i.id for i in s["itineraries"]]
        vote = await submit_participant_vote(
            s["participant"].token, s["trip"].id, itin_ids, db
        )
        assert vote.participant_id == s["participant"].id
        assert vote.trip_id == s["trip"].id
        assert vote.iteration_number == 1
        assert json.loads(vote.rankings_json) == itin_ids

    async def test_invalid_token(self, db: AsyncSession, voting_setup) -> None:
        from fastapi import HTTPException

        s = voting_setup
        itin_ids = [i.id for i in s["itineraries"]]
        with pytest.raises(HTTPException) as exc:
            await submit_participant_vote("bad-token", s["trip"].id, itin_ids, db)
        assert exc.value.status_code == 404

    async def test_wrong_trip(self, db: AsyncSession, voting_setup) -> None:
        from fastapi import HTTPException

        s = voting_setup
        itin_ids = [i.id for i in s["itineraries"]]
        with pytest.raises(HTTPException) as exc:
            await submit_participant_vote(
                s["participant"].token, s["trip"].id + 999, itin_ids, db
            )
        # Participant exists but does not belong to that trip → 403
        assert exc.value.status_code == 403

    async def test_rejected_when_not_voting(
        self, db: AsyncSession, voting_setup
    ) -> None:
        from fastapi import HTTPException

        s = voting_setup
        s["trip"].status = "COLLECTING_PREFERENCES"
        await db.flush()
        itin_ids = [i.id for i in s["itineraries"]]
        with pytest.raises(HTTPException) as exc:
            await submit_participant_vote(
                s["participant"].token, s["trip"].id, itin_ids, db
            )
        assert exc.value.status_code == 409

    async def test_incomplete_rankings_rejected(
        self, db: AsyncSession, voting_setup
    ) -> None:
        from fastapi import HTTPException

        s = voting_setup
        # Only one of two required itinerary IDs
        with pytest.raises(HTTPException) as exc:
            await submit_participant_vote(
                s["participant"].token,
                s["trip"].id,
                [s["itineraries"][0].id],
                db,
            )
        assert exc.value.status_code == 422

    async def test_wrong_itinerary_ids_rejected(
        self, db: AsyncSession, voting_setup
    ) -> None:
        from fastapi import HTTPException

        s = voting_setup
        with pytest.raises(HTTPException) as exc:
            await submit_participant_vote(
                s["participant"].token, s["trip"].id, [9999, 8888], db
            )
        assert exc.value.status_code == 422

    async def test_revote_overwrites(self, db: AsyncSession, voting_setup) -> None:
        s = voting_setup
        itin_ids = [i.id for i in s["itineraries"]]
        reversed_ids = list(reversed(itin_ids))

        await submit_participant_vote(
            s["participant"].token, s["trip"].id, itin_ids, db
        )
        vote2 = await submit_participant_vote(
            s["participant"].token, s["trip"].id, reversed_ids, db
        )
        assert json.loads(vote2.rankings_json) == reversed_ids

        from sqlalchemy import func, select

        count = await db.execute(
            select(func.count(Vote.id)).where(
                Vote.participant_id == s["participant"].id,
                Vote.trip_id == s["trip"].id,
                Vote.iteration_number == 1,
            )
        )
        assert count.scalar_one() == 1


# ---------------------------------------------------------------------------
# submit_admin_vote
# ---------------------------------------------------------------------------


class TestSubmitAdminVote:
    async def test_success(self, db: AsyncSession, voting_setup) -> None:
        s = voting_setup
        itin_ids = [i.id for i in s["itineraries"]]
        vote = await submit_admin_vote(s["user"], s["trip"].id, itin_ids, db)
        assert vote.participant_id == s["creator_participant"].id
        assert vote.user_id is None

    async def test_non_creator_rejected(self, db: AsyncSession, voting_setup) -> None:
        from fastapi import HTTPException

        s = voting_setup
        other_user = _make_user(db)
        db.add(other_user)
        await db.flush()
        itin_ids = [i.id for i in s["itineraries"]]
        with pytest.raises(HTTPException) as exc:
            await submit_admin_vote(other_user, s["trip"].id, itin_ids, db)
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Auto-tally
# ---------------------------------------------------------------------------


class TestAutoTally:
    async def test_tally_runs_after_all_votes(
        self, db: AsyncSession, voting_setup
    ) -> None:
        s = voting_setup
        itin_ids = [i.id for i in s["itineraries"]]

        # Participant votes
        await submit_participant_vote(
            s["participant"].token, s["trip"].id, itin_ids, db
        )
        # Admin votes — this is the last eligible voter (1 participant + admin)
        await submit_admin_vote(s["user"], s["trip"].id, itin_ids, db)

        from sqlalchemy import select

        rounds = await db.execute(
            select(VoteRound).where(
                VoteRound.trip_id == s["trip"].id,
                VoteRound.iteration_number == 1,
            )
        )
        assert len(rounds.scalars().all()) > 0

    async def test_tally_does_not_run_before_all_votes(
        self, db: AsyncSession, voting_setup
    ) -> None:
        s = voting_setup
        itin_ids = [i.id for i in s["itineraries"]]

        # Only participant votes, admin has not voted yet
        await submit_participant_vote(
            s["participant"].token, s["trip"].id, itin_ids, db
        )

        from sqlalchemy import select

        rounds = await db.execute(
            select(VoteRound).where(
                VoteRound.trip_id == s["trip"].id,
                VoteRound.iteration_number == 1,
            )
        )
        assert len(rounds.scalars().all()) == 0


# ---------------------------------------------------------------------------
# get_or_compute_results
# ---------------------------------------------------------------------------


class TestGetOrComputeResults:
    async def test_computes_on_demand(self, db: AsyncSession, voting_setup) -> None:
        s = voting_setup
        itin_ids = [i.id for i in s["itineraries"]]

        # Submit both votes without triggering tally (directly insert to avoid auto-tally)
        db.add(
            Vote(
                participant_id=s["participant"].id,
                trip_id=s["trip"].id,
                iteration_number=1,
                rankings_json=json.dumps(itin_ids),
            )
        )
        db.add(
            Vote(
                user_id=s["user"].id,
                trip_id=s["trip"].id,
                iteration_number=1,
                rankings_json=json.dumps(itin_ids),
            )
        )
        await db.flush()

        results = await get_or_compute_results(s["trip"].id, None, db)
        assert results.trip_id == s["trip"].id
        assert results.is_complete is True
        assert results.winner_id is not None

    async def test_returns_stored_rounds_if_present(
        self, db: AsyncSession, voting_setup
    ) -> None:
        s = voting_setup
        itin_ids = [i.id for i in s["itineraries"]]

        # Pre-insert a stored round
        stored_round = VoteRound(
            trip_id=s["trip"].id,
            iteration_number=1,
            round_number=1,
            results_json=json.dumps({str(itin_ids[0]): 2, str(itin_ids[1]): 1}),
            winner_id=itin_ids[0],
            eliminated_option_id=None,
        )
        db.add(stored_round)
        await db.flush()

        results = await get_or_compute_results(s["trip"].id, None, db)
        assert results.winner_id == itin_ids[0]
        assert len(results.rounds) == 1


# ---------------------------------------------------------------------------
# pick_winner
# ---------------------------------------------------------------------------


class TestPickWinner:
    async def test_success(self, db: AsyncSession, voting_setup) -> None:
        s = voting_setup
        itin = s["itineraries"][0]
        trip = await pick_winner(s["user"], s["trip"].id, itin.id, db)
        assert trip.status == "FINALIZED"
        assert trip.winner_itinerary_id == itin.id

    async def test_non_creator_rejected(self, db: AsyncSession, voting_setup) -> None:
        from fastapi import HTTPException

        s = voting_setup
        other = _make_user(db)
        db.add(other)
        await db.flush()
        with pytest.raises(HTTPException) as exc:
            await pick_winner(other, s["trip"].id, s["itineraries"][0].id, db)
        assert exc.value.status_code == 403

    async def test_wrong_status_rejected(self, db: AsyncSession, voting_setup) -> None:
        from fastapi import HTTPException

        s = voting_setup
        s["trip"].status = "COLLECTING_PREFERENCES"
        await db.flush()
        with pytest.raises(HTTPException) as exc:
            await pick_winner(s["user"], s["trip"].id, s["itineraries"][0].id, db)
        assert exc.value.status_code == 409

    async def test_wrong_itinerary_rejected(
        self, db: AsyncSession, voting_setup
    ) -> None:
        from fastapi import HTTPException

        s = voting_setup
        with pytest.raises(HTTPException) as exc:
            await pick_winner(s["user"], s["trip"].id, 99999, db)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# trigger_new_iteration
# ---------------------------------------------------------------------------


class TestTriggerNewIteration:
    async def test_success(self, db: AsyncSession, voting_setup) -> None:
        from unittest.mock import MagicMock

        from sqlalchemy.ext.asyncio import async_sessionmaker

        s = voting_setup
        bg = MagicMock()
        bg.add_task = MagicMock()

        mock_factory = MagicMock(spec=async_sessionmaker)

        result = await trigger_new_iteration(
            s["user"], s["trip"].id, db, bg, mock_factory
        )

        assert result["status"] == "accepted"
        assert s["trip"].status == "GENERATING"
        bg.add_task.assert_called_once()

    async def test_non_creator_rejected(self, db: AsyncSession, voting_setup) -> None:
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        s = voting_setup
        other = _make_user(db)
        db.add(other)
        await db.flush()
        bg = MagicMock()
        mock_factory = MagicMock()
        with pytest.raises(HTTPException) as exc:
            await trigger_new_iteration(other, s["trip"].id, db, bg, mock_factory)
        assert exc.value.status_code == 403

    async def test_max_iterations_rejected(
        self, db: AsyncSession, voting_setup
    ) -> None:
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        s = voting_setup
        s["trip"].current_iteration = s["trip"].max_iterations
        await db.flush()
        bg = MagicMock()
        mock_factory = MagicMock()
        with pytest.raises(HTTPException) as exc:
            await trigger_new_iteration(s["user"], s["trip"].id, db, bg, mock_factory)
        assert exc.value.status_code == 409

    async def test_wrong_status_rejected(self, db: AsyncSession, voting_setup) -> None:
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        s = voting_setup
        s["trip"].status = "FINALIZED"
        await db.flush()
        bg = MagicMock()
        mock_factory = MagicMock()
        with pytest.raises(HTTPException) as exc:
            await trigger_new_iteration(s["user"], s["trip"].id, db, bg, mock_factory)
        assert exc.value.status_code == 409
