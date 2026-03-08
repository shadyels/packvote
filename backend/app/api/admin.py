from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics")
async def get_metrics() -> dict:
    # TODO: implement in monitoring step
    raise NotImplementedError


@router.get("/ai-logs")
async def get_ai_logs() -> dict:
    # TODO: implement in AI pipeline step
    raise NotImplementedError
