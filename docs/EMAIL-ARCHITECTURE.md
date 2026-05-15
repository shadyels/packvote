# Email Architecture — PackVote

## Overview

PackVote uses **Brevo** (formerly Sendinblue) for transactional email. The free tier provides 300 emails/day. This document describes the architecture, rate limiting strategy, and calling conventions.

---

## Service Layer

### `EmailService` (`backend/app/services/email/brevo.py`)

**Singleton:** Instantiated once in the app via `EmailService.from_settings()`.

**Methods:**
- `_send(to_email, subject, body) → bool` — Core transport. Async. Returns `False` if API key missing or rate limit exhausted.
- `send_invitation(...)` — Invitation to submit preferences
- `send_voting_notification(...)` — Voting round is open
- `send_new_iteration_notification(...)` — New voting iteration ready
- `send_password_reset(...)` — Password reset link (1-hour expiry)
- `send_finalized_notification(...)` — Final itinerary confirmed

All public methods call `_send()` internally. **Callers must handle `False` return gracefully** (they do; see below).

---

## Rate Limiting

### `BrevoRateLimiter` (`backend/app/services/email/rate_limiter.py`)

**Pattern:** Mirrors `UnsplashRateLimiter` — sliding-window deque + asyncio.Lock + module-level singleton.

**Window:** 24-hour sliding window (86400 seconds)  
**Capacity:** 300 emails/day (Brevo free tier)

**API:**
```python
async def try_consume() -> bool
```
Returns `True` if the email can be sent. Returns `False` if the 300/day limit is exhausted (within the current 24-hour window).

**Async-safe:** All calls protected by `asyncio.Lock`. Safe for concurrent `_send()` calls.

**Eviction:** Old timestamps are automatically evicted as time advances (sliding window maintains only the last 24 hours of records).

### Integration in `_send()`

```python
async def _send(self, to_email: str, subject: str, body: str) -> bool:
    if not self._api_key:
        logger.error("BREVO_API_KEY is not set — email to %s not sent", to_email)
        return False
    if not await get_brevo_limiter().try_consume():
        logger.warning(
            "Brevo daily rate limit reached (300/day) — email to %s dropped",
            to_email,
        )
        return False
    # ... HTTP request to Brevo API
```

**Behavior when exhausted:**
- `_send()` returns `False` immediately (no HTTP call made)
- Warning is logged with email address
- Callers see `False` and handle it gracefully (e.g., skip resend, accept the failure)

---

## Caller Conventions

All callers of `EmailService` methods (e.g., `send_invitation()`, `send_voting_notification()`) check the return value:

```python
success = await email_service.send_invitation(...)
if not success:
    logger.warning("Failed to send invitation to %s", participant_email)
    # Continue — don't retry, don't block
```

**No retry logic.** The rate limiter's return value is terminal; retrying the same call in the same minute will still fail. Callers must accept the failure gracefully.

---

## Environment Setup

**Required variables** (in `backend/.env` or Railway dashboard):
- `BREVO_API_KEY` — API key from Brevo account
- `BREVO_FROM_EMAIL` — Verified sender address (must be verified in Brevo dashboard under Settings → Senders)

---

## Testing

### Unit Tests (`backend/tests/unit/test_brevo_rate_limiter.py`)

**5 rate limiter tests:**
- Capacity test: 300 emails accepted, 301st rejected
- Sliding window eviction: old entries expelled after 24 hours
- Pre-expiry blocking: entries still block 1 second before expiry
- Concurrent safety: `asyncio.gather()` of 320 calls yields exactly 300 successes

**3 integration tests:**
- `_send()` returns `False` when limiter exhausted
- Warning logged when rate-limited
- `_send()` succeeds when limiter allows (with mocked HTTP)

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

**Log level:** `logging.WARNING` when limit is hit.

**Check rate limiter state** (dev only):
```python
from app.services.email.rate_limiter import get_brevo_limiter
limiter = get_brevo_limiter()
print(f"Emails sent in window: {len(limiter._emails)}")  # 0–300
```

**Manual test:**
```python
# Exhaust the limiter
from app.services.email.rate_limiter import get_brevo_limiter, MAX_EPD
import asyncio

async def test():
    limiter = get_brevo_limiter()
    for i in range(MAX_EPD):
        await limiter.try_consume()
    result = await limiter.try_consume()  # Should be False
    print(result)

asyncio.run(test())
```

---

## Future Enhancements

- **Distributed rate limiting:** If the app scales to multiple backend instances, move from in-process deque to a shared store (Redis, PostgreSQL) to enforce the limit across all instances.
- **Metrics:** Track successful sends, failed sends, rate-limit hits per day for monitoring dashboard (Phase 3).
- **Fallback provider:** If Brevo quotas need to grow, add a secondary provider (AWS SES, SendGrid) with logic to switch providers when one is exhausted.

---

## Related

- `app/services/email/brevo.py` — EmailService implementation
- `app/services/email/rate_limiter.py` — BrevoRateLimiter class
- `tests/unit/test_brevo_rate_limiter.py` — Test suite
- `CLAUDE.md` — Architecture quick reference
- `REQUIREMENTS.md` — F9 Email Notifications requirement
