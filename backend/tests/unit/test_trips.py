import re
import secrets

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
TRIPS_URL = "/trips/"


_TRIP_PAYLOAD = {
    "title": "Summer Adventure",
    "participant_emails": ["alice@example.com", "bob@example.com"],
}


class TestCreateTrip:
    async def test_success_returns_201(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Summer Adventure"
        assert "id" in data
        assert "trip_code" in data
        assert "pin" not in data
        assert "status" in data

    async def test_trip_code_is_8_char_uppercase_alphanum(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        trip_code = resp.json()["trip_code"]
        assert len(trip_code) == 8
        assert re.fullmatch(r"[A-Z0-9]{8}", trip_code)

    async def test_participant_pins_are_4_digits(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        import asyncio

        await asyncio.sleep(0)
        assert len(mock_email.sent) > 0
        for entry in mock_email.sent:
            pin = entry["pin"]
            assert len(pin) == 4
            assert re.fullmatch(r"\d{4}", pin)

    async def test_invitations_sent_per_participant(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        # Allow a moment for fire-and-forget gather
        import asyncio

        await asyncio.sleep(0)
        assert len(mock_email.sent) == 2
        sent_emails = {e["to"] for e in mock_email.sent}
        assert sent_emails == {"alice@example.com", "bob@example.com"}

    async def test_num_options_defaults_to_3(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["num_options"] == 3

    async def test_num_options_below_2_returns_422(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        payload = {**_TRIP_PAYLOAD, "num_options": 1}
        resp = await client.post(TRIPS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_num_options_above_5_returns_422(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        payload = {**_TRIP_PAYLOAD, "num_options": 6}
        resp = await client.post(TRIPS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_no_auth_returns_401(self, client: AsyncClient, mock_email):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD)
        assert resp.status_code == 401


class TestListTrips:
    async def test_empty_list(self, client: AsyncClient, auth_headers, mock_email):
        resp = await client.get(TRIPS_URL, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_only_callers_trips_returned(self, client: AsyncClient, mock_email):
        # Create two users, each creates a trip
        email_a = f"a_{secrets.token_hex(4)}@test.com"
        email_b = f"b_{secrets.token_hex(4)}@test.com"
        for email in (email_a, email_b):
            await client.post(
                REGISTER_URL, json={"email": email, "password": "test1234"}
            )

        async def login(email: str) -> dict:
            r = await client.post(
                LOGIN_URL, json={"email": email, "password": "test1234"}
            )
            return {"Authorization": f"Bearer {r.json()['access_token']}"}

        headers_a = await login(email_a)
        headers_b = await login(email_b)

        await client.post(
            TRIPS_URL, json={**_TRIP_PAYLOAD, "title": "Trip A"}, headers=headers_a
        )
        await client.post(
            TRIPS_URL, json={**_TRIP_PAYLOAD, "title": "Trip B"}, headers=headers_b
        )

        resp_a = await client.get(TRIPS_URL, headers=headers_a)
        assert resp_a.status_code == 200
        titles = [t["title"] for t in resp_a.json()]
        assert "Trip A" in titles
        assert "Trip B" not in titles

    async def test_participant_count_correct(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        payload = {
            **_TRIP_PAYLOAD,
            "participant_emails": ["p1@x.com", "p2@x.com", "p3@x.com"],
        }
        await client.post(TRIPS_URL, json=payload, headers=auth_headers)
        resp = await client.get(TRIPS_URL, headers=auth_headers)
        assert resp.status_code == 200
        trip = resp.json()[0]
        # 3 invitees + 1 creator participant row
        assert trip["participant_count"] == 4

    async def test_preferences_submitted_count(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        resp = await client.get(TRIPS_URL, headers=auth_headers)
        assert resp.status_code == 200
        # Creator row has preferences_submitted=True from day one
        assert resp.json()[0]["preferences_submitted_count"] == 1

    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.get(TRIPS_URL)
        assert resp.status_code == 401


class TestGetTrip:
    async def test_success(self, client: AsyncClient, auth_headers, mock_email):
        create_resp = await client.post(
            TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers
        )
        trip_id = create_resp.json()["id"]
        resp = await client.get(f"/trips/{trip_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == trip_id

    async def test_404_nonexistent(self, client: AsyncClient, auth_headers):
        resp = await client.get("/trips/999999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_403_when_not_creator(self, client: AsyncClient, mock_email):
        # User A creates trip
        email_a = f"a_{secrets.token_hex(4)}@test.com"
        email_b = f"b_{secrets.token_hex(4)}@test.com"
        for email in (email_a, email_b):
            await client.post(
                REGISTER_URL, json={"email": email, "password": "test1234"}
            )

        r_a = await client.post(
            LOGIN_URL, json={"email": email_a, "password": "test1234"}
        )
        headers_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}
        r_b = await client.post(
            LOGIN_URL, json={"email": email_b, "password": "test1234"}
        )
        headers_b = {"Authorization": f"Bearer {r_b.json()['access_token']}"}

        create_resp = await client.post(
            TRIPS_URL, json=_TRIP_PAYLOAD, headers=headers_a
        )
        trip_id = create_resp.json()["id"]

        resp = await client.get(f"/trips/{trip_id}", headers=headers_b)
        assert resp.status_code == 403

    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.get("/trips/1")
        assert resp.status_code == 401


class TestDeleteTrip:
    async def test_delete_returns_204(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        create_resp = await client.post(
            TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers
        )
        trip_id = create_resp.json()["id"]
        resp = await client.delete(f"/trips/{trip_id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_deleted_trip_not_in_list(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        create_resp = await client.post(
            TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers
        )
        trip_id = create_resp.json()["id"]
        await client.delete(f"/trips/{trip_id}", headers=auth_headers)
        resp = await client.get(TRIPS_URL, headers=auth_headers)
        assert resp.status_code == 200
        ids = [t["id"] for t in resp.json()]
        assert trip_id not in ids

    async def test_deleted_trip_returns_404(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        create_resp = await client.post(
            TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers
        )
        trip_id = create_resp.json()["id"]
        await client.delete(f"/trips/{trip_id}", headers=auth_headers)
        resp = await client.get(f"/trips/{trip_id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_nonexistent_returns_404(
        self, client: AsyncClient, auth_headers
    ):
        resp = await client.delete("/trips/999999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_not_creator_returns_403(
        self, client: AsyncClient, mock_email
    ):
        email_a = f"a_{secrets.token_hex(4)}@test.com"
        email_b = f"b_{secrets.token_hex(4)}@test.com"
        for email in (email_a, email_b):
            await client.post(
                REGISTER_URL, json={"email": email, "password": "test1234"}
            )

        r_a = await client.post(
            LOGIN_URL, json={"email": email_a, "password": "test1234"}
        )
        headers_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}
        r_b = await client.post(
            LOGIN_URL, json={"email": email_b, "password": "test1234"}
        )
        headers_b = {"Authorization": f"Bearer {r_b.json()['access_token']}"}

        create_resp = await client.post(
            TRIPS_URL, json=_TRIP_PAYLOAD, headers=headers_a
        )
        trip_id = create_resp.json()["id"]

        resp = await client.delete(f"/trips/{trip_id}", headers=headers_b)
        assert resp.status_code == 403

    async def test_delete_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.delete("/trips/1")
        assert resp.status_code == 401

    async def test_delete_generating_returns_409(
        self, client: AsyncClient, auth_headers, mock_email, db
    ):
        from sqlalchemy import select

        from app.models.trip import Trip

        create_resp = await client.post(
            TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers
        )
        trip_id = create_resp.json()["id"]

        # Manually set status to GENERATING in the DB
        result = await db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one()
        trip.status = "GENERATING"
        await db.commit()

        resp = await client.delete(f"/trips/{trip_id}", headers=auth_headers)
        assert resp.status_code == 409

    async def test_delete_with_participants(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        payload = {
            **_TRIP_PAYLOAD,
            "participant_emails": ["p1@x.com", "p2@x.com"],
        }
        create_resp = await client.post(TRIPS_URL, json=payload, headers=auth_headers)
        trip_id = create_resp.json()["id"]
        resp = await client.delete(f"/trips/{trip_id}", headers=auth_headers)
        assert resp.status_code == 204


class TestCreatorEmailDedup:
    async def test_creator_email_in_invite_list_is_deduped(
        self, client: AsyncClient, mock_email
    ):
        creator_email = f"creator_{secrets.token_hex(4)}@test.com"
        await client.post(
            REGISTER_URL, json={"email": creator_email, "password": "test1234"}
        )
        r = await client.post(
            LOGIN_URL, json={"email": creator_email, "password": "test1234"}
        )
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        payload = {
            "title": "Dedup Trip",
            # creator's own email plus two other invitees
            "participant_emails": [
                creator_email,
                "alice@example.com",
                "bob@example.com",
            ],
        }
        create_resp = await client.post(TRIPS_URL, json=payload, headers=headers)
        assert create_resp.status_code == 201
        trip_id = create_resp.json()["id"]

        resp = await client.get(f"/trips/{trip_id}/participants", headers=headers)
        assert resp.status_code == 200
        participants = resp.json()
        # 2 invitees + 1 creator row (not 4)
        assert len(participants) == 3
        creator_rows = [p for p in participants if p["email"] == creator_email]
        assert len(creator_rows) == 1

    async def test_creator_email_dedup_is_case_insensitive(
        self, client: AsyncClient, mock_email
    ):
        creator_email = f"creator_{secrets.token_hex(4)}@test.com"
        await client.post(
            REGISTER_URL, json={"email": creator_email, "password": "test1234"}
        )
        r = await client.post(
            LOGIN_URL, json={"email": creator_email, "password": "test1234"}
        )
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        payload = {
            "title": "Dedup Case Trip",
            # creator's email in uppercase — should still be deduped
            "participant_emails": [creator_email.upper(), "alice@example.com"],
        }
        create_resp = await client.post(TRIPS_URL, json=payload, headers=headers)
        assert create_resp.status_code == 201
        trip_id = create_resp.json()["id"]

        resp = await client.get(f"/trips/{trip_id}/participants", headers=headers)
        assert resp.status_code == 200
        participants = resp.json()
        # 1 invitee + 1 creator row (not 3)
        assert len(participants) == 2
        creator_rows = [
            p for p in participants if p["email"].lower() == creator_email.lower()
        ]
        assert len(creator_rows) == 1


class TestCreatorNotEmailed:
    async def test_creator_not_sent_invitation_email(
        self, client: AsyncClient, mock_email
    ):
        import asyncio

        creator_email = f"creator_{secrets.token_hex(4)}@test.com"
        await client.post(
            REGISTER_URL, json={"email": creator_email, "password": "test1234"}
        )
        r = await client.post(
            LOGIN_URL, json={"email": creator_email, "password": "test1234"}
        )
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        payload = {
            "title": "No Email Trip",
            "participant_emails": ["alice@example.com", "bob@example.com"],
        }
        await client.post(TRIPS_URL, json=payload, headers=headers)
        await asyncio.sleep(0)

        sent_emails = {e["to"] for e in mock_email.sent}
        assert creator_email not in sent_emails
        assert sent_emails == {"alice@example.com", "bob@example.com"}


class TestParticipantsEndpointVoteStatus:
    async def test_has_voted_current_iteration_reflects_vote_state(
        self,
        client: AsyncClient,
        auth_headers,
        mock_email,
        db: AsyncSession,
    ):
        """Admin participants list shows has_voted_current_iteration correctly for all rows."""
        from sqlalchemy import select

        from app.models.itinerary import Itinerary
        from app.models.participant import Participant
        from app.models.trip import Trip
        from app.models.vote import Vote

        # Create trip with 1 invitee
        create_resp = await client.post(
            TRIPS_URL,
            json={"title": "Vote Status Trip", "participant_emails": ["voter@x.com"]},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        trip_id = create_resp.json()["id"]

        # Put trip in VOTING status with 2 itineraries
        trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
        trip = trip_result.scalar_one()
        trip.status = "VOTING"
        trip.current_iteration = 1
        itin1 = Itinerary(
            trip_id=trip_id,
            iteration_number=1,
            destination_name="A",
            destination_description="Desc A",
            daily_itinerary_json="[]",
            total_estimated_budget=1000.0,
            currency="USD",
            match_reasoning="r",
            highlights='["h"]',
        )
        itin2 = Itinerary(
            trip_id=trip_id,
            iteration_number=1,
            destination_name="B",
            destination_description="Desc B",
            daily_itinerary_json="[]",
            total_estimated_budget=1200.0,
            currency="USD",
            match_reasoning="r",
            highlights='["h"]',
        )
        db.add(itin1)
        db.add(itin2)
        await db.flush()

        # Find the creator's participant row
        creator_p_result = await db.execute(
            select(Participant).where(
                Participant.trip_id == trip_id,
                Participant.user_id.is_not(None),
            )
        )
        creator_participant = creator_p_result.scalar_one()

        # Submit admin vote only (via direct DB insert to avoid going through HTTP auth complexity)
        db.add(
            Vote(
                participant_id=creator_participant.id,
                trip_id=trip_id,
                iteration_number=1,
                rankings_json=f"[{itin1.id},{itin2.id}]",
            )
        )
        await db.commit()

        # GET /trips/{id}/participants
        resp = await client.get(f"/trips/{trip_id}/participants", headers=auth_headers)
        assert resp.status_code == 200
        participants = resp.json()

        creator_rows = [p for p in participants if p["email"] == creator_participant.email]
        invitee_rows = [p for p in participants if p["email"] == "voter@x.com"]
        assert len(creator_rows) == 1
        assert len(invitee_rows) == 1
        assert creator_rows[0]["has_voted_current_iteration"] is True
        assert invitee_rows[0]["has_voted_current_iteration"] is False
