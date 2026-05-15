"""Integration test for /unsplash/photo endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unsplash_photo_returns_images(client: AsyncClient) -> None:
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.json.return_value = {
        "results": [
            {"urls": {"regular": "https://images.unsplash.com/photo1.jpg"}},
            {"urls": {"regular": "https://images.unsplash.com/photo2.jpg"}},
        ]
    }

    with (
        patch("app.services.unsplash.get_settings") as mock_settings,
        patch("app.services.unsplash.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_settings.return_value.UNSPLASH_ACCESS_KEY = "test-key"
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        import app.services.unsplash as svc_module

        svc_module._cache.pop("paris", None)

        response = await client.get("/unsplash/photo?destination=Paris&count=2")

    assert response.status_code == 200
    body = response.json()
    assert "images" in body
    assert len(body["images"]) == 2


@pytest.mark.asyncio
async def test_unsplash_photo_no_key_returns_empty(client: AsyncClient) -> None:
    with patch("app.services.unsplash.get_settings") as mock_settings:
        mock_settings.return_value.UNSPLASH_ACCESS_KEY = ""
        response = await client.get("/unsplash/photo?destination=Berlin&count=1")

    assert response.status_code == 200
    assert response.json() == {"images": []}


@pytest.mark.asyncio
async def test_unsplash_photo_count_clamped(client: AsyncClient) -> None:
    response = await client.get("/unsplash/photo?destination=Rome&count=99")
    assert response.status_code == 422  # FastAPI validation rejects count > 10
