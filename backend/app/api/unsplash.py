from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.unsplash import fetch_destination_images

router = APIRouter(prefix="/unsplash", tags=["unsplash"])


class UnsplashResponse(BaseModel):
    images: list[str]


@router.get("/photo", response_model=UnsplashResponse)
async def get_destination_photos(
    destination: str,
    count: int = Query(1, ge=1, le=10),
) -> UnsplashResponse:
    images = await fetch_destination_images(destination, count)
    return UnsplashResponse(images=images)
