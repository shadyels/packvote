# Email Architecture — PackVote

## Overview

PackVote uses **Brevo** (formerly Sendinblue) for transactional email. The free tier provides 300 emails/day. This document describes the architecture, rate limiting strategy, and calling conventions.

---

## Service Layer

### `EmailService` (`backend/app/services/email/brevo.py`)

**Construction:** `EmailService.from_settings()` reads `BREVO_API_KEY`, `FRONTEND_URL` and `BREVO_FROM_EMAIL` via `get_settings()`. Route handlers get one from the `get_email_service` dependency (`app/core/dependencies.py`); background tasks call `from_settings()` directly. Tests override the dependency with the `mock_email` fixture.

**Methods:**
- `send_trip_email(kind, *, to_email, participant_name, trip_title, trip_code, pin, token, destination_name="") → bool` — the single method for all trip emails. `kind` is looked up in `TRIP_EMAILS`, which holds each kind's subject, intro and link path.
- `send_password_reset(to_email, full_name, reset_token) → bool` — separate from `TRIP_EMAILS`. Link is `/reset-password?token=…`; the body says it expires in 60 minutes.
- `_send(to_email, subject, body) → bool` — core transport. Returns `False` if the API key is missing, the daily cap is used up, or the Brevo call fails.

**Trip email kinds (`TRIP_EMAILS`):**

| Kind | Link path | Sent when |
|---|---|---|
| `invitation` | `/join/{token}` | Trip created; admin resend for CREATED, COLLECTING_PREFERENCES, GENERATING, GENERATION_FAILED |
| `voting` | `/trip/{token}/vote` | Generation completes for iteration 1 |
| `new_iteration` | `/trip/{token}/vote` | Generation completes for iteration 2+; admin resend for VOTING after iteration 1 |
| `finalized` | `/trip/{token}` | Trip finalised; admin resend for FINALIZED |

Every trip email body has the same shape: greeting, intro, link, then `Or enter Trip Code: … PIN: …`. Golden tests pin subjects, bodies and links per kind.

**Where sends happen:**
- Invitations, finalized emails and password-reset emails run as FastAPI `BackgroundTasks`. They take plain values, never ORM objects, because the request session is closed by then.
- Voting and new-iteration emails are sent at the end of `run_generation`, which is itself a background task.
- Admin resend awaits its sends inline and returns `{sent, failed}`.
- Recipients are sent concurrently with `asyncio.gather(..., return_exceptions=True)`.

**Logging:** no recipient addresses and no Brevo response bodies are logged. A non-2xx response logs the HTTP status only. Caller logs use trip or participant IDs.

---

## Rate Limiting

### Shared `SlidingWindow` (`backend/app/services/rate_limit.py`)

**Pattern:** `SlidingWindow(max_events, window_s)` is a synchronous class with `allowed()`, `hit()` and `acquire()`. The methods do no I/O and no `await`, so each call is atomic on the single-threaded event loop. `acquire()` checks and records in one step; when full it returns `False` and records nothing. Use `acquire()` unless the check and the record are separated by no `await`.

**Brevo instance:** module-level `_limiter = SlidingWindow(MAX_EPD, 86400)` in `brevo.py`.

**Window:** 24-hour sliding window (86400 seconds)
**Capacity:** `MAX_EPD = 300` emails/day (Brevo free tier)

### Integration in `_send()`

```python
async def _send(self, to_email: str, subject: str, body: str) -> bool:
    if not self._api_key:
        logger.error("BREVO_API_KEY is not set — email not sent")
        return False
    if not _limiter.acquire():
        logger.warning(
            "Brevo daily rate limit reached (%d/day) — email dropped", MAX_EPD
        )
        return False
    # ... HTTP request to Brevo API
```

**Behavior when exhausted:**
- `_send()` returns `False` immediately (no HTTP call made)
- A warning is logged (no recipient address)
- The caller sees `False`

---

## Caller Conventions

Callers of `send_trip_email()` and `send_password_reset()` treat a `False` return as a failed send:
- Admin resend counts it in `failed`.
- Background senders (invitations, finalized, voting, password reset) log only raised exceptions, so a `False` return is not logged by the caller.

```python
sent = await email_service.send_trip_email(
    "invitation",
    to_email=participant.email,
    participant_name=participant.name,
    trip_title=trip.title,
    trip_code=trip.trip_code,
    pin=participant.pin,
    token=participant.token,
)
```

**No retry logic.** The rate limiter's return value is terminal; retrying the same call in the same minute will still fail. Callers must accept the failure gracefully.

---

## Environment Setup

**Required variables** (in `backend/.env` or Railway dashboard):
- `BREVO_API_KEY` — API key from Brevo account
- `BREVO_FROM_EMAIL` — Verified sender address (must be verified in Brevo dashboard under Settings → Senders)

---

## Testing

### Unit Tests

- `backend/tests/unit/test_brevo_rate_limiter.py` — `_send()` returns `False` when the limiter is exhausted, logs a warning, and succeeds when the limiter allows (mocked HTTP).
- `backend/tests/unit/test_sliding_window.py` — `SlidingWindow` acquire/allowed/hit semantics and expiry.
- `backend/tests/unit/test_email_golden.py` — subject, body and link per `TRIP_EMAILS` kind.
- `backend/tests/unit/test_email_service.py` — `EmailService` behaviour.
- `backend/tests/unit/test_email_resend.py` — status → kind mapping for the resend endpoints.

### Running Tests

```bash
cd backend
uv run pytest tests/unit/test_brevo_rate_limiter.py -v
```

All email-related tests:
```bash
uv run pytest tests/unit/ -k "email or brevo" -v
```

---

## Monitoring & Debugging

**Log level:** `logging.WARNING` when the daily cap is hit.

**Check the limiter state** (from `backend/`):
```python
from app.services.email import brevo

print(brevo._limiter.allowed())  # False once MAX_EPD sends are in the last 24h
```

**Manual test** (from `backend/`; affects only the current process):
```python
from app.services.email import brevo

for _ in range(brevo.MAX_EPD):
    brevo._limiter.acquire()
print(brevo._limiter.acquire())  # False
```

---

## Future Enhancements

- **Distributed rate limiting:** undecided. The limiter is in-process per worker; behaviour across multiple backend instances is not designed.
- **Metrics:** Track successful sends, failed sends, rate-limit hits per day for monitoring dashboard (Phase 3).
- **Fallback provider:** If Brevo quotas need to grow, add a secondary provider (AWS SES, SendGrid) with logic to switch providers when one is exhausted.

---

## Related

- `app/services/email/brevo.py` — EmailService, `TRIP_EMAILS`, Brevo transport
- `app/services/rate_limit.py` — SlidingWindow
- `app/services/email_resend.py` — status → email kind mapping for admin resend
- `tests/unit/test_brevo_rate_limiter.py` — Test suite
- `CLAUDE.md` — Architecture quick reference
- `REQUIREMENTS.md` — F9 Email Notifications requirement
