from abc import ABC, abstractmethod

from app.schemas.itinerary import AIGenerationResponse


class AIProvider(ABC):
    """Abstract interface for AI inference providers.

    All providers must implement these methods so the AIService can
    swap between Cerebras or any future provider transparently.
    """

    @abstractmethod
    async def generate_itineraries(
        self,
        prompt: str,
        num_options: int,
        model: str,
    ) -> tuple[AIGenerationResponse, str]:
        """Generate N itinerary options from the rendered prompt.

        Returns (response, provider_name) where provider_name is e.g. "cerebras".
        """
        ...

    @abstractmethod
    async def generate_followup_survey(
        self,
        prompt: str,
        model: str,
    ) -> list[str]:
        """Generate follow-up survey questions for a new iteration."""
        ...

    @abstractmethod
    async def organize_preferences(
        self,
        prompt: str,
        model: str,
    ) -> dict:
        """Organize and summarize raw participant preferences."""
        ...
