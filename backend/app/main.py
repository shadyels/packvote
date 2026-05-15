from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, participants, trips, unsplash, votes
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
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
    return {"status": "ok", "environment": settings.ENVIRONMENT}
