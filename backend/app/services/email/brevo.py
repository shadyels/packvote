import logging

import httpx

from app.core.config import get_settings

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

logger = logging.getLogger(__name__)


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
            logger.error("BREVO_API_KEY is not set — email to %s not sent", to_email)
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
                    headers={"api-key": self._api_key, "content-type": "application/json"},
                    json=payload,
                    timeout=10,
                )
            if resp.status_code not in (200, 201):
                logger.error(
                    "Brevo API error sending to %s: status=%s body=%s",
                    to_email,
                    resp.status_code,
                    resp.text,
                )
                return False
            return True
        except Exception as exc:
            logger.exception("Unexpected error sending email to %s: %s", to_email, exc)
            return False

    async def send_invitation(
        self,
        to_email: str,
        participant_name: str | None,
        trip_title: str,
        trip_code: str,
        pin: str,
        token: str,
    ) -> bool:
        """Send trip invitation with preference form link."""
        return await self._send(
            to_email=to_email,
            subject=f"You're invited to {trip_title}",
            body=(
                f"Hi {participant_name or 'there'},\n\n"
                f"You've been invited to join the trip: {trip_title}\n\n"
                f"Join via link: {self._frontend_url}/join/{token}\n"
                f"Or enter Trip Code: {trip_code}  PIN: {pin}\n"
            ),
        )

    async def send_voting_notification(
        self,
        to_email: str,
        participant_name: str | None,
        trip_title: str,
        trip_code: str,
        pin: str,
        token: str,
    ) -> bool:
        """Notify participant that itineraries are ready to vote on."""
        return await self._send(
            to_email=to_email,
            subject=f"Vote now: {trip_title} itineraries are ready",
            body=(
                f"Hi {participant_name or 'there'},\n\n"
                f"The itineraries for {trip_title} are ready. Cast your vote!\n\n"
                f"Vote via link: {self._frontend_url}/trip/{token}/vote\n"
                f"Or enter Trip Code: {trip_code}  PIN: {pin}\n"
            ),
        )

    async def send_new_iteration_notification(
        self,
        to_email: str,
        participant_name: str | None,
        trip_title: str,
        trip_code: str,
        pin: str,
        token: str,
    ) -> bool:
        """Notify participant that new itinerary options are ready for voting."""
        return await self._send(
            to_email=to_email,
            subject=f"New options for {trip_title} — vote again!",
            body=(
                f"Hi {participant_name or 'there'},\n\n"
                f"A new round of itineraries has been generated for {trip_title}.\n"
                f"Check out the new options and cast your vote!\n\n"
                f"Vote via link: {self._frontend_url}/trip/{token}/vote\n"
                f"Or enter Trip Code: {trip_code}  PIN: {pin}\n"
            ),
        )

    async def send_finalized_notification(
        self,
        to_email: str,
        participant_name: str | None,
        trip_title: str,
        trip_code: str,
        pin: str,
        token: str,
        destination_name: str,
    ) -> bool:
        """Notify participant that the trip has been finalized."""
        return await self._send(
            to_email=to_email,
            subject=f"Trip finalized: {trip_title} — {destination_name}",
            body=(
                f"Hi {participant_name or 'there'},\n\n"
                f"Your group has chosen: {destination_name}!\n"
                f"The trip {trip_title} has been finalized.\n\n"
                f"View the itinerary: {self._frontend_url}/trip/{token}\n"
                f"Or enter Trip Code: {trip_code}  PIN: {pin}\n"
            ),
        )
