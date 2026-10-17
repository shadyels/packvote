"""Shared fixtures for unit tests."""

import secrets

import pytest
from httpx import AsyncClient

from tests.helpers import auth_headers as bearer
from tests.helpers import register_and_login


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register + login a fresh user, return bearer header dict."""
    email = f"user_{secrets.token_hex(4)}@test.com"
    return bearer(await register_and_login(client, email, "test1234"))
