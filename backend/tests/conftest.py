import functools

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services import unsplash
from app.services.ai import rate_limiter as ai_rate_limiter
from app.services.email import rate_limiter as brevo_rate_limiter

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def _fast_bcrypt(monkeypatch):
    """Cost factor 4 (bcrypt minimum) keeps hashing-heavy tests fast."""
    monkeypatch.setattr(bcrypt, "gensalt", functools.partial(bcrypt.gensalt, rounds=4))


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Reset process-global caches/limiters so tests can't leak into each other."""
    unsplash._cache.clear()
    unsplash._limiter = None
    brevo_rate_limiter._limiter = None
    ai_rate_limiter._limiter = None
    yield
    unsplash._cache.clear()
    unsplash._limiter = None
    brevo_rate_limiter._limiter = None
    ai_rate_limiter._limiter = None


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

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
