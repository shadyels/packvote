from fastapi import APIRouter

from app.core.dependencies import DB
from app.schemas.stats import PlatformStats
from app.services.stats import get_platform_stats

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=PlatformStats)
async def platform_stats(db: DB) -> PlatformStats:
    return await get_platform_stats(db)
