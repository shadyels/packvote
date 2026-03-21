"""Shared fixtures for unit tests.

Consolidates MockEmailService, auth_headers, mock_email, and
mock_session_factory so they don't have to be duplicated across every
test module.
"""

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dependencies import get_email_service, get_session_factory
from app.main import app

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"


class MockEmailService:
    """Superset mock for all four email methods.

    Tracks every call in ``self.sent`` so tests can assert on recipients,
    trip codes, PINs, and tokens without hitting SendGrid.
    """

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_invitation(
        self,
        to_email: str,
        participant_name: str | None,
        trip_title: str,
        trip_code: str,
        pin: str,
        token: str,
    ) -> bool:
        self.sent.append(
            {
                "type": "invitation",
                "to": to_email,
                "trip_code": trip_code,
                "pin": pin,
                "token": token,
            }
        )
        return True

    async def send_voting_notification(self, **kwargs: object) -> bool:
        self.sent.append({"type": "voting", **kwargs})
        return True

    async def send_new_iteration_notification(self, **kwargs: object) -> bool:
        self.sent.append({"type": "new_iteration", **kwargs})
        return True

    async def send_finalized_notification(self, **kwargs: object) -> bool:
        self.sent.append({"type": "finalized", **kwargs})
        return True


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register + login a fresh user, return bearer header dict."""
    email = f"user_{secrets.token_hex(4)}@test.com"
    await client.post(REGISTER_URL, json={"email": email, "password": "test1234"})
    resp = await client.post(LOGIN_URL, json={"email": email, "password": "test1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def mock_email() -> "MockEmailService":  # type: ignore[type-arg]
    """Override the email service dependency with MockEmailService."""
    svc = MockEmailService()
    app.dependency_overrides[get_email_service] = lambda: svc
    yield svc  # type: ignore[misc]
    app.dependency_overrides.pop(get_email_service, None)


@pytest.fixture
def mock_session_factory(engine):  # type: ignore[no-untyped-def]
    """Inject the test engine's session factory for background tasks."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app.dependency_overrides[get_session_factory] = lambda: factory
    yield factory
    app.dependency_overrides.pop(get_session_factory, None)
