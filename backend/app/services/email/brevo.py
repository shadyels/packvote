import logging
from typing import Literal

import httpx

from app.core.config import get_settings
from app.services.rate_limit import SlidingWindow

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
MAX_EPD = 300  # Brevo free tier: emails per day
_limiter = SlidingWindow(MAX_EPD, 86400)

logger = logging.getLogger(__name__)

EmailKind = Literal["invitation", "voting", "new_iteration", "finalized"]

# kind -> (subject, intro ending at the link label, link path); "{title}"/"{dest}" filled in.
TRIP_EMAILS: dict[EmailKind, tuple[str, str, str]] = {
    "invitation": (
        "You're invited to {title}",
        "You've been invited to join the trip: {title}\n\nJoin via link: ",
        "/join/{token}",
    ),
    "voting": (
        "Vote now: {title} itineraries are ready",
        "The itineraries for {title} are ready. Cast your vote!\n\nVote via link: ",
        "/trip/{token}/vote",
    ),
    "new_iteration": (
        "New options for {title} — vote again!",
        "A new round of itineraries has been generated for {title}.\n"
        "Check out the new options and cast your vote!\n\nVote via link: ",
        "/trip/{token}/vote",
    ),
    "finalized": (
        "Trip finalized: {title} — {dest}",
        "Your group has chosen: {dest}!\nThe trip {title} has been finalized.\n\n"
        "View the itinerary: ",
        "/trip/{token}",
    ),
}


class EmailService:
    """Brevo (formerly Sendinblue) transactional email service.

    Free tier: 300 emails/day.
    All emails include: tokenized direct link + trip code + PIN.
    """

    def __init__(self, api_key: str, frontend_url: str, from_email: str) -> None:
        self._api_key = api_key
        self._frontend_url = frontend_url
        self._from_email = from_email

    @classmethod
    def from_settings(cls) -> "EmailService":
        settings = get_settings()
        return cls(
            api_key=settings.BREVO_API_KEY,
            frontend_url=settings.FRONTEND_URL,
            from_email=settings.BREVO_FROM_EMAIL,
        )

    async def _send(self, to_email: str, subject: str, body: str) -> bool:
        if not self._api_key:
            logger.error("BREVO_API_KEY is not set — email not sent")
            return False
        if not _limiter.acquire():
            logger.warning(
                "Brevo daily rate limit reached (%d/day) — email dropped", MAX_EPD
            )
            return False
        payload = {
            "sender": {"email": self._from_email, "name": "PackVote"},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body,
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    BREVO_API_URL,
                    headers={
                        "api-key": self._api_key,
                        "content-type": "application/json",
                    },
                    json=payload,
                    timeout=10,
                )
            if resp.status_code not in (200, 201):
                logger.error("Brevo API error: status=%s", resp.status_code)
                return False
            return True
        except Exception:
            logger.exception("Unexpected error sending email")
            return False

    async def send_trip_email(
        self,
        kind: EmailKind,
        *,
        to_email: str,
        participant_name: str | None,
        trip_title: str,
        trip_code: str,
        pin: str,
        token: str,
        destination_name: str = "",
    ) -> bool:
        """Send one trip email (subject/intro/link path from ``TRIP_EMAILS``)."""
        subject, intro, path = TRIP_EMAILS[kind]
        fmt = {"title": trip_title, "dest": destination_name}
        return await self._send(
            to_email=to_email,
            subject=subject.format(**fmt),
            body=(
                f"Hi {participant_name or 'there'},\n\n"
                f"{intro.format(**fmt)}{self._frontend_url}{path.format(token=token)}\n"
                f"Or enter Trip Code: {trip_code}  PIN: {pin}\n"
            ),
        )

    async def send_password_reset(
        self,
        to_email: str,
        full_name: str | None,
        reset_token: str,
    ) -> bool:
        """Send password reset email with single-use link (expires in 60 min)."""
        return await self._send(
            to_email=to_email,
            subject="Reset your PackVote password",
            body=(
                f"Hi {full_name or 'there'},\n\n"
                f"We received a request to reset your PackVote password.\n\n"
                f"Reset your password: {self._frontend_url}/reset-password?token={reset_token}\n\n"
                f"This link expires in 60 minutes.\n\n"
                f"If you didn't request this, you can safely ignore this email.\n"
            ),
        )
