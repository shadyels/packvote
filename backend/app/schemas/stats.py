from datetime import date, datetime

from pydantic import BaseModel

from app.models.trip import TripStatus


class StatsTotals(BaseModel):
    trips: int
    users: int
    participants: int
    votes: int
    itineraries: int
    ai_attempts: int
    tokens_in: int
    tokens_out: int
    cost_usd: float  # list-price equivalent, priced models only


class StatusCount(BaseModel):
    status: TripStatus
    trips: int


class AttemptsPerRun(BaseModel):
    attempts: int
    runs: int


class FinishReasonCount(BaseModel):
    finish_reason: str | None
    attempts: int


class LatencyBucket(BaseModel):
    min_ms: int
    max_ms: int | None
    attempts: int


class LatencyStats(BaseModel):
    p50_ms: int | None
    p95_ms: int | None
    sample_size: int
    histogram: list[LatencyBucket]


class GenerationStats(BaseModel):
    attempts: int
    valid_attempts: int
    valid_rate: float | None
    runs: int
    runs_succeeded: int
    attempts_per_run: list[AttemptsPerRun]
    finish_reasons: list[FinishReasonCount]
    latency: LatencyStats
    orphaned_attempts: int


class ModelStats(BaseModel):
    provider: str
    model: str
    attempts: int
    valid_attempts: int
    tokens_in: int
    tokens_out: int
    cost_usd: float | None  # None: model has no price entry


class PromptVersionStats(BaseModel):
    prompt_version: str | None
    successful_generations: int
    itineraries: int
    attempts: int
    valid_rate: float | None
    latency_p50_ms: int | None
    latency_p95_ms: int | None
    tokens_per_itinerary: float | None
    cost_per_itinerary_usd: float | None


class DayActivity(BaseModel):
    date: date
    trips: int
    tokens_in: int
    tokens_out: int


class IterationsCount(BaseModel):
    iterations: int
    trips: int


class VotingStats(BaseModel):
    avg_participants_per_trip: float | None
    trips_reached_voting: int
    avg_votes_per_trip: float | None
    finalized_trips: int
    iterations_to_finalize: list[IterationsCount]
    cost_per_finalized_trip_usd: float | None


class StatsSampling(BaseModel):
    row_cap: int
    truncated: bool


class PricingInfo(BaseModel):
    as_of: str
    unpriced_models: list[str]


class CheckRate(BaseModel):
    check: str
    pass_rate: float
    cases: int
    gating: bool  # False: informational, not in all_checks_pass_rate


class JudgeScore(BaseModel):
    criterion: str
    mean: float | None


class PromptQualityVersion(BaseModel):
    prompt_version: str
    cases: int  # paired: both versions answered
    judged_cases: int
    all_checks_pass_rate: float
    checks: list[CheckRate]
    judge: list[JudgeScore]
    judge_overall: float | None


class PromptQuality(BaseModel):
    run_date: str
    model: str
    judge_model: str
    cases: int
    versions: list[PromptQualityVersion]


class PlatformStats(BaseModel):
    generated_at: datetime
    totals: StatsTotals
    funnel: list[StatusCount]
    generation: GenerationStats
    by_model: list[ModelStats]
    by_prompt_version: list[PromptVersionStats]
    activity: list[DayActivity]
    voting: VotingStats
    sampling: StatsSampling
    pricing: PricingInfo
    prompt_quality: PromptQuality | None
