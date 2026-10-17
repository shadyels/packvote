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
        from jwt import PyJWTError

        with pytest.raises(PyJWTError):
            decode_access_token("not.a.valid.token")


# ── POST /auth/register ──────────────────────────────────────────────────────


class TestRegister:
    async def test_success_returns_201(self, client: AsyncClient):
        resp = await client.post(
            REGISTER_URL,
            json={
                "email": "alice@example.com",
                "password": "password123",
                "full_name": "Alice",
            },
        )
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
        resp = await client.post(
            REGISTER_URL,
            json={
                "email": "bob@example.com",
                "password": "password123",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["full_name"] is None

    async def test_duplicate_email_returns_409(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "password": "password123"}
        await client.post(REGISTER_URL, json=payload)
        resp = await client.post(REGISTER_URL, json=payload)
        assert resp.status_code == 409

    async def test_invalid_email_returns_422(self, client: AsyncClient):
        resp = await client.post(
            REGISTER_URL,
            json={
                "email": "not-an-email",
                "password": "password123",
            },
        )
        assert resp.status_code == 422


# ── POST /auth/login ─────────────────────────────────────────────────────────


class TestLogin:
    async def test_success_returns_token(self, client: AsyncClient):
        await client.post(
            REGISTER_URL,
            json={
                "email": "charlie@example.com",
                "password": "password123",
            },
        )
        resp = await client.post(
            LOGIN_URL,
            json={
                "email": "charlie@example.com",
                "password": "password123",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_wrong_password_returns_401(self, client: AsyncClient):
        await client.post(
            REGISTER_URL,
            json={
                "email": "dave@example.com",
                "password": "password123",
            },
        )
        resp = await client.post(
            LOGIN_URL,
            json={
                "email": "dave@example.com",
                "password": "wrongpassword",
            },
        )
        assert resp.status_code == 401

    async def test_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post(
            LOGIN_URL,
            json={
                "email": "nobody@example.com",
                "password": "password123",
            },
        )
        assert resp.status_code == 401

    async def test_wrong_and_unknown_return_same_message(self, client: AsyncClient):
        # Same error message for both cases — prevents user enumeration
        await client.post(
            REGISTER_URL,
            json={
                "email": "eve2@example.com",
                "password": "password123",
            },
        )
        wrong_pw = await client.post(
            LOGIN_URL,
            json={
                "email": "eve2@example.com",
                "password": "wrong",
            },
        )
        unknown = await client.post(
            LOGIN_URL,
            json={
                "email": "ghost@example.com",
                "password": "password123",
            },
        )
        assert wrong_pw.json()["detail"] == unknown.json()["detail"]


# ── GET /auth/me ─────────────────────────────────────────────────────────────


class TestMe:
    async def test_returns_current_user(self, client: AsyncClient):
        await client.post(
            REGISTER_URL,
            json={
                "email": "eve@example.com",
                "password": "password123",
                "full_name": "Eve",
            },
        )
        login_resp = await client.post(
            LOGIN_URL,
            json={
                "email": "eve@example.com",
                "password": "password123",
            },
        )
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
        resp = await client.get(
            ME_URL, headers={"Authorization": "Bearer garbage.token.here"}
        )
        assert resp.status_code == 401


# ── Password reset ──────────────────────────────────────────────────────────

RESET_REQUEST_URL = "/auth/password-reset/request"
RESET_CONFIRM_URL = "/auth/password-reset/confirm"


class TestPasswordReset:
    @pytest.fixture
    def sent_resets(self):
        from unittest.mock import AsyncMock, patch

        svc = AsyncMock()
        with patch("app.services.auth.EmailService.from_settings", return_value=svc):
            yield svc.send_password_reset

    async def _register(self, client: AsyncClient, email: str = "r@test.com"):
        await client.post(REGISTER_URL, json={"email": email, "password": "oldpass12"})

    async def test_request_and_confirm_happy_path(
        self, client: AsyncClient, sent_resets
    ):
        await self._register(client)
        resp = await client.post(RESET_REQUEST_URL, json={"email": "r@test.com"})
        assert resp.status_code == 202
        token = sent_resets.call_args.kwargs["reset_token"]

        resp = await client.post(
            RESET_CONFIRM_URL, json={"token": token, "new_password": "newpass12"}
        )
        assert resp.status_code == 200
        login = lambda pw: client.post(  # noqa: E731
            LOGIN_URL, json={"email": "r@test.com", "password": pw}
        )
        assert (await login("newpass12")).status_code == 200
        assert (await login("oldpass12")).status_code == 401

        # token is single-use
        again = await client.post(
            RESET_CONFIRM_URL, json={"token": token, "new_password": "another12"}
        )
        assert again.status_code == 400

    async def test_unknown_email_does_not_leak(self, client: AsyncClient, sent_resets):
        await self._register(client)
        known = await client.post(RESET_REQUEST_URL, json={"email": "r@test.com"})
        unknown = await client.post(RESET_REQUEST_URL, json={"email": "no@test.com"})
        assert unknown.status_code == known.status_code == 202
        assert unknown.json() == known.json()
        assert sent_resets.await_count == 1

    async def test_invalid_token_returns_400(self, client: AsyncClient):
        resp = await client.post(
            RESET_CONFIRM_URL, json={"token": "bogus", "new_password": "newpass12"}
        )
        assert resp.status_code == 400

    async def test_expired_token_returns_400(
        self, client: AsyncClient, sent_resets, db
    ):
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import update

        from app.models.user import User

        await self._register(client)
        await client.post(RESET_REQUEST_URL, json={"email": "r@test.com"})
        token = sent_resets.call_args.kwargs["reset_token"]
        await db.execute(
            update(User).values(
                reset_token_expires_at=datetime.now(UTC) - timedelta(minutes=1)
            )
        )
        await db.commit()

        resp = await client.post(
            RESET_CONFIRM_URL, json={"token": token, "new_password": "newpass12"}
        )
        assert resp.status_code == 400


# ── Hardening ───────────────────────────────────────────────────────────────


class TestAuthHardening:
    async def test_duplicate_register_409(self, client: AsyncClient):
        body = {"email": "dup@test.com", "password": "password12"}
        assert (await client.post(REGISTER_URL, json=body)).status_code == 201
        resp = await client.post(REGISTER_URL, json=body)
        assert resp.status_code == 409
        assert resp.json()["detail"] == "Email already registered"

    async def test_register_race_integrity_error_409(self, client: AsyncClient):
        from unittest.mock import patch

        from sqlalchemy.exc import IntegrityError
        from sqlalchemy.ext.asyncio import AsyncSession

        with patch.object(
            AsyncSession, "flush", side_effect=IntegrityError("s", {}, Exception())
        ):
            resp = await client.post(
                REGISTER_URL, json={"email": "race@test.com", "password": "password12"}
            )
        assert resp.status_code == 409

    async def test_mixed_case_email(self, client: AsyncClient):
        await client.post(
            REGISTER_URL, json={"email": "MiXed@Test.com", "password": "password12"}
        )
        resp = await client.post(
            LOGIN_URL, json={"email": "mixed@TEST.com", "password": "password12"}
        )
        assert resp.status_code == 200
        dup = await client.post(
            REGISTER_URL, json={"email": "MIXED@test.com", "password": "password12"}
        )
        assert dup.status_code == 409

    async def test_unknown_user_login_401(self, client: AsyncClient):
        resp = await client.post(
            LOGIN_URL, json={"email": "nobody@test.com", "password": "password12"}
        )
        assert resp.status_code == 401

    async def test_token_revoked_after_reset(self, client: AsyncClient):
        import time
        from unittest.mock import AsyncMock, patch

        email = "rev@test.com"
        await client.post(REGISTER_URL, json={"email": email, "password": "oldpass12"})
        old = (
            await client.post(LOGIN_URL, json={"email": email, "password": "oldpass12"})
        ).json()["access_token"]
        svc = AsyncMock()
        with patch("app.services.auth.EmailService.from_settings", return_value=svc):
            await client.post(RESET_REQUEST_URL, json={"email": email})
        token = svc.send_password_reset.call_args.kwargs["reset_token"]
        time.sleep(1.1)  # iat has whole-second granularity
        await client.post(
            RESET_CONFIRM_URL, json={"token": token, "new_password": "newpass12"}
        )
        hdr = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731
        assert (await client.get(ME_URL, headers=hdr(old))).status_code == 401
        new = (
            await client.post(LOGIN_URL, json={"email": email, "password": "newpass12"})
        ).json()["access_token"]
        assert (await client.get(ME_URL, headers=hdr(new))).status_code == 200


class TestSecretKeyGuard:
    def test_default_key_rejected_outside_development(self):
        from pydantic import ValidationError

        from app.core.config import Settings

        with pytest.raises(ValidationError):
            Settings(ENVIRONMENT="production", SECRET_KEY="change-me-in-production")

    def test_default_key_ok_in_development(self):
        from app.core.config import Settings

        Settings(ENVIRONMENT="development", SECRET_KEY="change-me-in-production")

    def test_custom_key_ok_in_production(self):
        from app.core.config import Settings

        Settings(ENVIRONMENT="production", SECRET_KEY="x" * 32)
