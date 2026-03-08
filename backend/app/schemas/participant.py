from datetime import datetime

from pydantic import BaseModel


class ParticipantResponse(BaseModel):
    id: int
    trip_id: int
    name: str | None
    preferences_submitted: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TripAccessByCode(BaseModel):
    trip_code: str
    pin: str
