from app.core.config import get_settings


class EmailService:
    """SendGrid email service.

    Free tier: 100 emails/day.
    All emails include: tokenized direct link + trip ID + PIN.
    """

    def __init__(self, api_key: str, frontend_url: str) -> None:
        self.api_key = api_key
        self.frontend_url = frontend_url

    @classmethod
    def from_settings(cls) -> "EmailService":
        settings = get_settings()
        return cls(api_key=settings.SENDGRID_API_KEY, frontend_url=settings.FRONTEND_URL)

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
        # TODO: implement in email integration step
        raise NotImplementedError

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
        # TODO: implement in email integration step
        raise NotImplementedError

    async def send_new_iteration_notification(
        self,
        to_email: str,
        participant_name: str | None,
        trip_title: str,
        trip_code: str,
        pin: str,
        token: str,
        survey_questions: list[str],
    ) -> bool:
        """Notify participant of a new iteration with follow-up survey."""
        # TODO: implement in email integration step
        raise NotImplementedError

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
        # TODO: implement in email integration step
        raise NotImplementedError
