"""End-to-end integration smoke tests.

Exercises the real HTTP endpoints against an in-memory SQLite database
to ensure the router → service → ORM wiring is intact. These are
broad coverage checks — unit tests cover edge cases.
"""

from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from tests.factories import seed_voting_trip
from tests.helpers import (
    LOGIN_URL,
    ME_URL,
    PASSWORD,
    auth_headers,
    register_and_login,
)


class TestAuthFlow:
    async def test_register_login_me_roundtrip(self, client: AsyncClient):
        token = await register_and_login(client, "creator@test.com")
        resp = await client.get(ME_URL, headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["email"] == "creator@test.com"


VOTE_URL = "/votes/trips/{trip_id}/vote/{token}"
ADMIN_VOTE_URL = "/votes/trips/{trip_id}/admin-vote"
TRIP_DETAIL_URL = "/trips/{trip_id}"


async def _seed(db: AsyncSession, creator_email: str, invitee_email: str) -> dict:
    s = await seed_voting_trip(
        db,
        creator_email=creator_email,
        invitee_email=invitee_email,
        hashed_password=hash_password(PASSWORD),
    )
    await db.commit()
    return s


class TestVotingLifecycle:
    async def test_all_votes_auto_finalize_trip(
        self, client: AsyncClient, db: AsyncSession, mock_email, monkeypatch
    ) -> None:
        mock_svc = MagicMock()
        mock_svc.send_trip_email = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.services.email.brevo.EmailService.from_settings",
            lambda: mock_svc,
        )

        s = await _seed(db, "vote_creator@test.com", "vote_invitee@test.com")
        trip_id = s["trip"].id
        itin_ids = [i.id for i in s["itineraries"]]
        invitee_token = s["participant"].token

        # Login creator (user seeded with hashed password) for JWT
        login = await client.post(
            LOGIN_URL,
            json={"email": "vote_creator@test.com", "password": "password123"},
        )
        assert login.status_code == 200, login.text
        jwt = login.json()["access_token"]

        # Invitee votes
        resp = await client.post(
            VOTE_URL.format(trip_id=trip_id, token=invitee_token),
            json={"rankings": itin_ids},
        )
        assert resp.status_code == 201, resp.text

        # Verify trip still VOTING (not yet finalized)
        resp = await client.get(
            TRIP_DETAIL_URL.format(trip_id=trip_id),
            headers=auth_headers(jwt),
        )
        assert resp.json()["status"] == "VOTING"

        # Creator (admin) votes — triggers auto-finalize
        resp = await client.post(
            ADMIN_VOTE_URL.format(trip_id=trip_id),
            json={"rankings": itin_ids},
            headers=auth_headers(jwt),
        )
        assert resp.status_code == 201, resp.text

        # Trip must now be FINALIZED
        resp = await client.get(
            TRIP_DETAIL_URL.format(trip_id=trip_id),
            headers=auth_headers(jwt),
        )
        data = resp.json()
        assert data["status"] == "FINALIZED"
        assert data["winner_itinerary_id"] is not None

    async def test_tie_does_not_auto_finalize(
        self, client: AsyncClient, db: AsyncSession, mock_email, monkeypatch
    ) -> None:
        mock_svc = MagicMock()
        mock_svc.send_trip_email = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.services.email.brevo.EmailService.from_settings",
            lambda: mock_svc,
        )

        s = await _seed(db, "tie_creator@test.com", "tie_invitee@test.com")
        trip_id = s["trip"].id
        itin_ids = [i.id for i in s["itineraries"]]
        invitee_token = s["participant"].token

        login = await client.post(
            LOGIN_URL,
            json={"email": "tie_creator@test.com", "password": "password123"},
        )
        jwt = login.json()["access_token"]

        # Opposing rankings → tie
        await client.post(
            VOTE_URL.format(trip_id=trip_id, token=invitee_token),
            json={"rankings": itin_ids},
        )
        await client.post(
            ADMIN_VOTE_URL.format(trip_id=trip_id),
            json={"rankings": list(reversed(itin_ids))},
            headers=auth_headers(jwt),
        )

        resp = await client.get(
            TRIP_DETAIL_URL.format(trip_id=trip_id),
            headers=auth_headers(jwt),
        )
        data = resp.json()
        assert data["status"] == "VOTING"
        assert data["winner_itinerary_id"] is None
        mock_svc.send_trip_email.assert_not_called()
