"""Shared URL constants and HTTP helpers for endpoint tests."""

from __future__ import annotations

from httpx import AsyncClient

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
ME_URL = "/auth/me"
TRIPS_URL = "/trips/"
INVITED_URL = "/trips/invited"
ACCESS_BY_CODE_URL = "/participants/access-by-code"

PASSWORD = "password123"


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(client: AsyncClient, email: str, password: str = PASSWORD) -> None:
    resp = await client.post(REGISTER_URL, json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text


async def login(client: AsyncClient, email: str, password: str = PASSWORD) -> str:
    """Log in; returns the access token."""
    resp = await client.post(LOGIN_URL, json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def register_and_login(
    client: AsyncClient, email: str, password: str = PASSWORD
) -> str:
    await register(client, email, password)
    return await login(client, email, password)


async def create_trip(
    client: AsyncClient,
    token: str,
    emails: list[str] | None = None,
    **fields: object,
) -> dict:
    """POST /trips/ as ``token``'s user; asserts 201 and returns the body."""
    body = {
        "title": "Test Trip",
        "num_options": 2,
        "participant_emails": emails or ["p1@example.com"],
        **fields,
    }
    resp = await client.post(TRIPS_URL, json=body, headers=auth_headers(token))
    assert resp.status_code == 201, resp.text
    return resp.json()
