import functools
import os

# Set before app imports (settings are cached); >=32 bytes avoids PyJWT warnings.
os.environ["SECRET_KEY"] = "test-secret-key-0123456789-abcdefghijkl"

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_email_service, get_session_factory
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services import participants
from app.services.ai import rate_limiter as ai_rate_limiter
from app.services.email import brevo
from app.services.rate_limit import SlidingWindow

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def _fast_bcrypt(monkeypatch):
    """Cost factor 4 (bcrypt minimum) keeps hashing-heavy tests fast."""
    monkeypatch.setattr(bcrypt, "gensalt", functools.partial(bcrypt.gensalt, rounds=4))


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Reset process-global caches/limiters so tests can't leak into each other."""
    brevo._limiter = SlidingWindow(brevo.MAX_EPD, 86400)
    ai_rate_limiter._limiter = None
    participants._pin_windows.clear()
    yield
    brevo._limiter = SlidingWindow(brevo.MAX_EPD, 86400)
    ai_rate_limiter._limiter = None
    participants._pin_windows.clear()


@pytest.fixture
async def engine():
    """Fresh in-memory DB per test (StaticPool keeps one shared connection)."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db: AsyncSession):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


class MockEmailService:
    """Records every ``send_trip_email`` call in ``self.sent`` (no Brevo)."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_trip_email(
        self, kind: str, *, to_email: str, **kwargs: object
    ) -> bool:
        self.sent.append({"type": kind, "to": to_email, "to_email": to_email, **kwargs})
        return True


@pytest.fixture
def mock_email():
    """Override the email service dependency with MockEmailService."""
    svc = MockEmailService()
    app.dependency_overrides[get_email_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_email_service, None)


@pytest.fixture
def mock_session_factory(engine):
    """Inject the test engine's session factory for background tasks."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app.dependency_overrides[get_session_factory] = lambda: factory
    yield factory
    app.dependency_overrides.pop(get_session_factory, None)
