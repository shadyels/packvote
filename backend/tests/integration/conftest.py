"""Integration-test fixtures.

Reuses the ``client``, ``db``, and ``engine`` fixtures from the root
conftest. Adds ``mock_email`` / ``mock_session_factory`` so integration
tests can exercise endpoints that fire off background tasks (trip
generation, invitation emails) without hitting real services.
"""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dependencies import get_email_service, get_session_factory
from app.main import app


class MockEmailService:
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
def mock_email() -> MockEmailService:
    svc = MockEmailService()
    app.dependency_overrides[get_email_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_email_service, None)


@pytest.fixture
def mock_session_factory(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app.dependency_overrides[get_session_factory] = lambda: factory
    yield factory
    app.dependency_overrides.pop(get_session_factory, None)
