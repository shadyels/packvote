from datetime import datetime

from pydantic import BaseModel


class AICallLogResponse(BaseModel):
    id: int
    trip_id: int | None
    prompt_version_id: int | None
    model_used: str
    provider: str
    latency_ms: int | None
    token_count_input: int | None
    token_count_output: int | None
    response_valid: bool
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
