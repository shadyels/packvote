import pytest
from httpx import AsyncClient

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
ME_URL = "/auth/me"


# ── Password hashing ────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plain_text(self):
        assert hash_password("mysecret") != "mysecret"

    def test_verify_correct_password(self):
        assert verify_password("mysecret", hash_password("mysecret")) is True

    def test_verify_wrong_password(self):
        assert verify_password("wrong", hash_password("mysecret")) is False

    def test_same_password_produces_different_hashes(self):
        # bcrypt uses a random salt per hash
        assert hash_password("mysecret") != hash_password("mysecret")


# ── JWT ─────────────────────────────────────────────────────────────────────

class TestJWT:
    def test_create_and_decode_roundtrip(self):
        token = create_access_token(subject=42)
        payload = decode_access_token(token)
        assert payload["sub"] == "42"

    def test_token_is_string(self):
        assert isinstance(create_access_token(subject=1), str)

    def test_decode_invalid_token_raises(self):
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_access_token("not.a.valid.token")


# ── POST /auth/register ──────────────────────────────────────────────────────

class TestRegister:
    async def test_success_returns_201(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json={
            "email": "alice@example.com",
            "password": "password123",
            "full_name": "Alice",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "alice@example.com"
        assert data["full_name"] == "Alice"
        assert "id" in data
        assert "created_at" in data
        # Password must never appear in the response
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_full_name_is_optional(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json={
            "email": "bob@example.com",
            "password": "password123",
        })
        assert resp.status_code == 201
        assert resp.json()["full_name"] is None

    async def test_duplicate_email_returns_409(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "password": "password123"}
        await client.post(REGISTER_URL, json=payload)
        resp = await client.post(REGISTER_URL, json=payload)
        assert resp.status_code == 409

    async def test_invalid_email_returns_422(self, client: AsyncClient):
        resp = await client.post(REGISTER_URL, json={
            "email": "not-an-email",
            "password": "password123",
        })
        assert resp.status_code == 422


# ── POST /auth/login ─────────────────────────────────────────────────────────

class TestLogin:
    async def test_success_returns_token(self, client: AsyncClient):
        await client.post(REGISTER_URL, json={
            "email": "charlie@example.com",
            "password": "password123",
        })
        resp = await client.post(LOGIN_URL, json={
            "email": "charlie@example.com",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_wrong_password_returns_401(self, client: AsyncClient):
        await client.post(REGISTER_URL, json={
            "email": "dave@example.com",
            "password": "password123",
        })
        resp = await client.post(LOGIN_URL, json={
            "email": "dave@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    async def test_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post(LOGIN_URL, json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    async def test_wrong_and_unknown_return_same_message(self, client: AsyncClient):
        # Same error message for both cases — prevents user enumeration
        await client.post(REGISTER_URL, json={
            "email": "eve2@example.com",
            "password": "password123",
        })
        wrong_pw = await client.post(LOGIN_URL, json={
            "email": "eve2@example.com",
            "password": "wrong",
        })
        unknown = await client.post(LOGIN_URL, json={
            "email": "ghost@example.com",
            "password": "password123",
        })
        assert wrong_pw.json()["detail"] == unknown.json()["detail"]


# ── GET /auth/me ─────────────────────────────────────────────────────────────

class TestMe:
    async def test_returns_current_user(self, client: AsyncClient):
        await client.post(REGISTER_URL, json={
            "email": "eve@example.com",
            "password": "password123",
            "full_name": "Eve",
        })
        login_resp = await client.post(LOGIN_URL, json={
            "email": "eve@example.com",
            "password": "password123",
        })
        token = login_resp.json()["access_token"]

        resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "eve@example.com"
        assert data["full_name"] == "Eve"

    async def test_missing_token_returns_401(self, client: AsyncClient):
        resp = await client.get(ME_URL)
        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.get(ME_URL, headers={"Authorization": "Bearer garbage.token.here"})
        assert resp.status_code == 401
