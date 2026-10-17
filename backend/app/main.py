import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, participants, trips, unsplash, votes
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.generation import recover_stuck_generations

settings = get_settings()

# Scoped to "app" rather than root (basicConfig): a root handler would double
# SQLAlchemy echo output and surface httpx's per-request INFO lines.
_log_handler = logging.StreamHandler(sys.stdout)
_log_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
)
logging.getLogger("app").addHandler(_log_handler)
logging.getLogger("app").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await recover_stuck_generations(get_session_factory())
    yield


app = FastAPI(
    lifespan=lifespan,
    title="PackVote API",
    description="AI-powered group travel planning",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(participants.router)
app.include_router(votes.router)
app.include_router(admin.router)
app.include_router(unsplash.router)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
