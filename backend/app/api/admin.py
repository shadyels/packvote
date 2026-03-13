from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ai-logs")
async def get_ai_logs() -> dict:
    # TODO: implement in Trip Creator Dashboard step
    raise NotImplementedError
