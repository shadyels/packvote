import anyio
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import get_settings


class EmailService:
    """SendGrid email service.

    Free tier: 100 emails/day.
    All emails include: tokenized direct link + trip ID + PIN.
    """

    def __init__(self, api_key: str, frontend_url: str, from_email: str) -> None:
        self._api_key = api_key
        self._frontend_url = frontend_url
        self._from_email = from_email

    @classmethod
    def from_settings(cls) -> "EmailService":
        settings = get_settings()
        return cls(
            api_key=settings.SENDGRID_API_KEY,
            frontend_url=settings.FRONTEND_URL,
            from_email=settings.SENDGRID_FROM_EMAIL,
        )

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
        mail = Mail(
            from_email=self._from_email,
            to_emails=to_email,
            subject=f"You're invited to {trip_title}",
            plain_text_content=(
                f"Hi {participant_name or 'there'},\n\n"
                f"You've been invited to join the trip: {trip_title}\n\n"
                f"Join via link: {self._frontend_url}/join/{token}\n"
                f"Or enter Trip Code: {trip_code}  PIN: {pin}\n"
            ),
        )
        try:
            sg = SendGridAPIClient(self._api_key)
            resp = await anyio.to_thread.run_sync(
                lambda: sg.client.mail.send.post(request_body=mail.get())
            )
            return resp.status_code in (200, 202)
        except Exception:
            return False

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
        mail = Mail(
            from_email=self._from_email,
            to_emails=to_email,
            subject=f"Vote now: {trip_title} itineraries are ready",
            plain_text_content=(
                f"Hi {participant_name or 'there'},\n\n"
                f"The itineraries for {trip_title} are ready. Cast your vote!\n\n"
                f"Vote via link: {self._frontend_url}/trip/{token}/vote\n"
                f"Or enter Trip Code: {trip_code}  PIN: {pin}\n"
            ),
        )
        try:
            sg = SendGridAPIClient(self._api_key)
            resp = await anyio.to_thread.run_sync(
                lambda: sg.client.mail.send.post(request_body=mail.get())
            )
            return resp.status_code in (200, 202)
        except Exception:
            return False

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
        mail = Mail(
            from_email=self._from_email,
            to_emails=to_email,
            subject=f"New options for {trip_title} — vote again!",
            plain_text_content=(
                f"Hi {participant_name or 'there'},\n\n"
                f"A new round of itineraries has been generated for {trip_title}.\n"
                f"Check out the new options and cast your vote!\n\n"
                f"Vote via link: {self._frontend_url}/trip/{token}/vote\n"
                f"Or enter Trip Code: {trip_code}  PIN: {pin}\n"
            ),
        )
        try:
            sg = SendGridAPIClient(self._api_key)
            resp = await anyio.to_thread.run_sync(
                lambda: sg.client.mail.send.post(request_body=mail.get())
            )
            return resp.status_code in (200, 202)
        except Exception:
            return False

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
        mail = Mail(
            from_email=self._from_email,
            to_emails=to_email,
            subject=f"Trip finalized: {trip_title} — {destination_name}",
            plain_text_content=(
                f"Hi {participant_name or 'there'},\n\n"
                f"Your group has chosen: {destination_name}!\n"
                f"The trip {trip_title} has been finalized.\n\n"
                f"View the itinerary: {self._frontend_url}/trip/{token}\n"
                f"Or enter Trip Code: {trip_code}  PIN: {pin}\n"
            ),
        )
        try:
            sg = SendGridAPIClient(self._api_key)
            resp = await anyio.to_thread.run_sync(
                lambda: sg.client.mail.send.post(request_body=mail.get())
            )
            return resp.status_code in (200, 202)
        except Exception:
            return False
