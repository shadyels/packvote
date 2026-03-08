from fastapi import APIRouter

from app.schemas.participant import ParticipantResponse, TripAccessByCode
from app.schemas.preference import PreferenceCreate, PreferenceResponse

router = APIRouter(prefix="/participants", tags=["participants"])


@router.post("/access-by-code", response_model=ParticipantResponse)
async def access_by_code(payload: TripAccessByCode) -> ParticipantResponse:
    # TODO: implement in participant flow step
    raise NotImplementedError


@router.get("/{token}", response_model=ParticipantResponse)
async def get_participant_by_token(token: str) -> ParticipantResponse:
    # TODO: implement in participant flow step
    raise NotImplementedError


@router.post("/{token}/preferences", response_model=PreferenceResponse)
async def submit_preferences(
    token: str, payload: PreferenceCreate
) -> PreferenceResponse:
    # TODO: implement in participant flow step
    raise NotImplementedError
