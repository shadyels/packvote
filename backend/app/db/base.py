from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.ENVIRONMENT == "development",
    )
