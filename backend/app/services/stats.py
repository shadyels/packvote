import asyncio
import logging
import math
import time
from bisect import bisect_right
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai_call_log import AICallLog
from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip, TripStatus
from app.models.user import User
from app.models.vote import Vote
from app.schemas.stats import (
    AttemptsPerRun,
    DayActivity,
    FinishReasonCount,
    GenerationStats,
    IterationsCount,
    LatencyBucket,
    LatencyStats,
    ModelStats,
    PlatformStats,
    PricingInfo,
    PromptQuality,
    PromptVersionStats,
    StatsSampling,
    StatsTotals,
    StatusCount,
    VotingStats,
)
from app.services.rate_limit import SlidingWindow

logger = logging.getLogger(__name__)

CACHE_TTL_S = 60
REQUEST_CAP = 120
COMPUTE_TIMEOUT_S = 10
FAILURE_BACKOFF_S = 10
ROW_CAP = 100_000
ACTIVITY_DAYS = 30
LATENCY_EDGES_MS = [0, 5000, 10000, 20000, 30000, 60000, 120000]
# Written by `python -m evals.run`, committed, shipped with the backend.
PROMPT_QUALITY_PATH = Path(__file__).resolve().parents[2] / "evals" / "results.json"
# Thinking tokens are billed as output; total - input captures them, which
# token_count_output alone does not. Fall back to output when total is missing.
_BILLABLE_OUT = func.coalesce(
    AICallLog.token_count_total - AICallLog.token_count_input,
    AICallLog.token_count_output,
    0,
)

# ponytail: one global cap for all callers, not per-IP. Upgrade: a per-IP limiter
# keyed on a trusted X-Forwarded-For if one client can starve the rest.
_limiter = SlidingWindow(REQUEST_CAP, 60)
_cache: tuple[float, PlatformStats] | None = None
_lock = asyncio.Lock()
_failed_until = 0.0


def _fresh() -> PlatformStats | None:
    if _cache is not None and time.monotonic() < _cache[0]:
        return _cache[1]
    return None


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Stats are temporarily unavailable. Try again shortly.",
    )


async def get_platform_stats(db: AsyncSession) -> PlatformStats:
    global _cache, _failed_until
    # No await before this: the cap must be checked before any work.
    if not _limiter.acquire():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again in a minute.",
        )
    if (hit := _fresh()) is not None:
        return hit
    async with _lock:
        if (hit := _fresh()) is not None:
            return hit
        if time.monotonic() < _failed_until:
            raise _unavailable()
        try:
            result = await asyncio.wait_for(_compute(db), COMPUTE_TIMEOUT_S)
        except Exception:
            logger.exception("platform stats compute failed")
            _failed_until = time.monotonic() + FAILURE_BACKOFF_S
            raise _unavailable() from None
        _cache = (time.monotonic() + CACHE_TTL_S, result)
        return result


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def _cost(model: str, tokens_in: int, billable_out: int) -> float | None:
    """List-price-equivalent USD; None when the model has no price entry."""
    price = get_settings().AI_PRICES_USD_PER_1M.get(model.removeprefix("models/"))
    if price is None:
        return None
    return (tokens_in * price[0] + billable_out * price[1]) / 1_000_000


@lru_cache(maxsize=1)
def load_prompt_quality() -> PromptQuality | None:
    """Offline eval results, or None when absent/unreadable (the file is static)."""
    try:
        return PromptQuality.model_validate_json(PROMPT_QUALITY_PATH.read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValidationError):
        logger.warning("prompt quality results unreadable; omitting", exc_info=True)
        return None


def _percentile(sorted_vals: list[int], q: float) -> int | None:
    """Nearest-rank percentile."""
    if not sorted_vals:
        return None
    return sorted_vals[math.ceil(q * len(sorted_vals)) - 1]


def _histogram(values: list[int]) -> list[LatencyBucket]:
    counts = [0] * len(LATENCY_EDGES_MS)
    for v in values:
        counts[max(0, bisect_right(LATENCY_EDGES_MS, v) - 1)] += 1
    edges = [*LATENCY_EDGES_MS[1:], None]
    return [
        LatencyBucket(min_ms=lo, max_ms=hi, attempts=n)
        for lo, hi, n in zip(LATENCY_EDGES_MS, edges, counts, strict=True)
    ]


def _utc_date(dt: datetime) -> date:
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(UTC).date()


async def _totals(db: AsyncSession, by_model: list[ModelStats]) -> StatsTotals:
    ai = (
        await db.execute(
            select(
                func.count(),
                func.coalesce(func.sum(AICallLog.token_count_input), 0),
                func.coalesce(func.sum(AICallLog.token_count_output), 0),
            )
        )
    ).one()
    return StatsTotals(
        trips=await db.scalar(select(func.count(Trip.id))) or 0,
        users=await db.scalar(select(func.count(User.id))) or 0,
        participants=await db.scalar(select(func.count(Participant.id))) or 0,
        votes=await db.scalar(select(func.count(Vote.id))) or 0,
        itineraries=await db.scalar(select(func.count(Itinerary.id))) or 0,
        ai_attempts=ai[0],
        tokens_in=int(ai[1]),
        tokens_out=int(ai[2]),
        cost_usd=sum(m.cost_usd or 0.0 for m in by_model),
    )


async def _funnel(db: AsyncSession) -> list[StatusCount]:
    rows = (
        await db.execute(select(Trip.status, func.count()).group_by(Trip.status))
    ).all()
    by_status = {s: n for s, n in rows}
    return [StatusCount(status=s, trips=by_status.get(s, 0)) for s in TripStatus]


async def _generation(
    db: AsyncSession,
) -> tuple[GenerationStats, bool, dict[str | None, list[int]]]:
    attempts, valid = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(AICallLog.response_valid.is_(True)),
            )
        )
    ).one()

    # C(k) = runs with >= k attempts (one row per attempt number per run).
    cum = dict(
        (
            await db.execute(
                select(AICallLog.attempt, func.count())
                .where(AICallLog.attempt.is_not(None))
                .group_by(AICallLog.attempt)
            )
        )
        .tuples()
        .all()
    )
    top = max(cum, default=0)
    per_run = [
        AttemptsPerRun(attempts=k, runs=cum.get(k, 0) - cum.get(k + 1, 0))
        for k in range(1, top + 1)
    ]

    reasons = (
        await db.execute(
            select(AICallLog.finish_reason, func.count())
            .group_by(AICallLog.finish_reason)
            .order_by(func.count().desc())
        )
    ).all()

    orphaned = await db.scalar(select(func.count()).where(AICallLog.trip_id.is_(None)))

    # ponytail: percentiles computed in Python over the newest ROW_CAP rows
    # (ceiling ~100k rows). Upgrade: percentile_cont on Postgres or a rollup table.
    lat_rows = (
        await db.execute(
            select(AICallLog.latency_ms, AICallLog.prompt_version)
            .where(AICallLog.latency_ms.is_not(None))
            .order_by(AICallLog.id.desc())
            .limit(ROW_CAP + 1)
        )
    ).all()
    truncated = len(lat_rows) > ROW_CAP
    kept = lat_rows[:ROW_CAP]
    lat = sorted(ms for ms, _ in kept)
    lat_by_version: dict[str | None, list[int]] = {}
    for ms, pv in kept:
        lat_by_version.setdefault(pv, []).append(ms)
    for vals in lat_by_version.values():
        vals.sort()

    return (
        GenerationStats(
            attempts=attempts,
            valid_attempts=valid,
            valid_rate=_ratio(valid, attempts),
            runs=cum.get(1, 0),
            runs_succeeded=valid,
            attempts_per_run=per_run,
            finish_reasons=[
                FinishReasonCount(finish_reason=r, attempts=n) for r, n in reasons
            ],
            latency=LatencyStats(
                p50_ms=_percentile(lat, 0.5),
                p95_ms=_percentile(lat, 0.95),
                sample_size=len(lat),
                histogram=_histogram(lat),
            ),
            orphaned_attempts=orphaned or 0,
        ),
        truncated,
        lat_by_version,
    )


async def _by_model(db: AsyncSession) -> list[ModelStats]:
    rows = await db.execute(
        select(
            AICallLog.provider,
            AICallLog.model_used,
            func.count(),
            func.count().filter(AICallLog.response_valid.is_(True)),
            func.coalesce(func.sum(AICallLog.token_count_input), 0),
            func.coalesce(func.sum(AICallLog.token_count_output), 0),
            func.coalesce(func.sum(_BILLABLE_OUT), 0),
        )
        .group_by(AICallLog.provider, AICallLog.model_used)
        .order_by(func.count().desc())
    )
    return [
        ModelStats(
            provider=p,
            model=m,
            attempts=a,
            valid_attempts=v,
            tokens_in=int(ti),
            tokens_out=int(to),
            cost_usd=_cost(m, int(ti), int(bo)),
        )
        for p, m, a, v, ti, to, bo in rows
    ]


async def _by_prompt_version(
    db: AsyncSession, lat_by_version: dict[str | None, list[int]]
) -> list[PromptVersionStats]:
    # One generation = one (trip, iteration) per prompt version.
    gen = (
        select(
            Itinerary.prompt_version.label("pv"),
            func.max(Itinerary.created_at).label("ts"),
        )
        .group_by(
            Itinerary.prompt_version, Itinerary.trip_id, Itinerary.iteration_number
        )
        .subquery()
    )
    gens = (
        await db.execute(
            select(gen.c.pv, func.count())
            .group_by(gen.c.pv)
            .order_by(func.max(gen.c.ts).desc())
        )
    ).all()
    itins = dict(
        (
            await db.execute(
                select(Itinerary.prompt_version, func.count()).group_by(
                    Itinerary.prompt_version
                )
            )
        )
        .tuples()
        .all()
    )
    n_gens = dict(gens)

    # Attempts per version, every model: [attempts, valid, tokens, cost, priced].
    usage: dict[str | None, list] = {}
    rows = (
        await db.execute(
            select(
                AICallLog.prompt_version,
                AICallLog.model_used,
                func.count(),
                func.count().filter(AICallLog.response_valid.is_(True)),
                func.coalesce(func.sum(AICallLog.token_count_input), 0),
                func.coalesce(func.sum(_BILLABLE_OUT), 0),
            ).group_by(AICallLog.prompt_version, AICallLog.model_used)
        )
    ).all()
    for pv, model, a, v, ti, bo in rows:
        u = usage.setdefault(pv, [0, 0, 0, 0.0, True])
        cost = _cost(model, int(ti), int(bo))
        u[0] += a
        u[1] += v
        u[2] += int(ti) + int(bo)
        u[3] += cost or 0.0
        u[4] = u[4] and cost is not None

    # Versions with itineraries (newest first), then log-only ones (None last).
    order = [pv for pv, _ in gens]
    order += sorted(
        (pv for pv in usage if pv not in n_gens), key=lambda v: (v is None, v or "")
    )
    out = []
    for pv in order:
        attempts, valid, tokens, cost, priced = usage.get(pv, [0, 0, 0, 0.0, True])
        n_itin = itins.get(pv, 0)
        lat = lat_by_version.get(pv, [])
        out.append(
            PromptVersionStats(
                prompt_version=pv,
                successful_generations=n_gens.get(pv, 0),
                itineraries=n_itin,
                attempts=attempts,
                valid_rate=_ratio(valid, attempts),
                latency_p50_ms=_percentile(lat, 0.5),
                latency_p95_ms=_percentile(lat, 0.95),
                tokens_per_itinerary=tokens / n_itin if n_itin and attempts else None,
                cost_per_itinerary_usd=(
                    cost / n_itin if n_itin and attempts and priced else None
                ),
            )
        )
    return out


async def _activity(db: AsyncSession) -> tuple[list[DayActivity], bool]:
    today = datetime.now(UTC).date()
    days = [today - timedelta(days=i) for i in range(ACTIVITY_DAYS - 1, -1, -1)]
    start = datetime(days[0].year, days[0].month, days[0].day, tzinfo=UTC)

    trip_dates = (
        await db.scalars(
            select(Trip.created_at)
            .where(Trip.created_at >= start)
            .order_by(Trip.id.desc())
            .limit(ROW_CAP + 1)
        )
    ).all()
    calls = (
        await db.execute(
            select(
                AICallLog.created_at,
                AICallLog.token_count_input,
                AICallLog.token_count_output,
            )
            .where(AICallLog.created_at >= start)
            .order_by(AICallLog.id.desc())
            .limit(ROW_CAP + 1)
        )
    ).all()
    truncated = len(trip_dates) > ROW_CAP or len(calls) > ROW_CAP

    trips = dict.fromkeys(days, 0)
    tin = dict.fromkeys(days, 0)
    tout = dict.fromkeys(days, 0)
    for created in trip_dates[:ROW_CAP]:
        if (d := _utc_date(created)) in trips:
            trips[d] += 1
    for created, ti, to in calls[:ROW_CAP]:
        if (d := _utc_date(created)) in tin:
            tin[d] += ti or 0
            tout[d] += to or 0
    return (
        [
            DayActivity(date=d, trips=trips[d], tokens_in=tin[d], tokens_out=tout[d])
            for d in days
        ],
        truncated,
    )


async def _voting(db: AsyncSession, totals: StatsTotals) -> VotingStats:
    reached = (
        await db.scalar(select(func.count()).where(Trip.current_iteration >= 1)) or 0
    )
    finalized = dict(
        (
            await db.execute(
                select(Trip.current_iteration, func.count())
                .where(Trip.status == TripStatus.FINALIZED)
                .group_by(Trip.current_iteration)
            )
        )
        .tuples()
        .all()
    )
    top = max(finalized, default=0)
    n_finalized = sum(finalized.values())
    # Cost of every attempt on a FINALIZED trip (failed ones included).
    spend = (
        await db.execute(
            select(
                AICallLog.model_used,
                func.coalesce(func.sum(AICallLog.token_count_input), 0),
                func.coalesce(func.sum(_BILLABLE_OUT), 0),
            )
            .join(Trip, Trip.id == AICallLog.trip_id)
            .where(Trip.status == TripStatus.FINALIZED)
            .group_by(AICallLog.model_used)
        )
    ).all()
    costs = [_cost(m, int(ti), int(bo)) for m, ti, bo in spend]
    return VotingStats(
        avg_participants_per_trip=_ratio(totals.participants, totals.trips),
        trips_reached_voting=reached,
        avg_votes_per_trip=_ratio(totals.votes, reached),
        # ponytail: the key-0 bucket is unreachable (FINALIZED requires VOTING,
        # which requires current_iteration >= 1), so this equals the rows' sum.
        finalized_trips=n_finalized,
        iterations_to_finalize=[
            IterationsCount(iterations=k, trips=finalized.get(k, 0))
            for k in range(1, top + 1)
        ],
        cost_per_finalized_trip_usd=(
            sum(c for c in costs if c is not None) / n_finalized
            if n_finalized and costs and None not in costs
            else None
        ),
    )


async def _compute(db: AsyncSession) -> PlatformStats:
    by_model = await _by_model(db)
    totals = await _totals(db, by_model)
    generation, lat_truncated, lat_by_version = await _generation(db)
    activity, act_truncated = await _activity(db)
    return PlatformStats(
        generated_at=datetime.now(UTC),
        totals=totals,
        funnel=await _funnel(db),
        generation=generation,
        by_model=by_model,
        by_prompt_version=await _by_prompt_version(db, lat_by_version),
        activity=activity,
        voting=await _voting(db, totals),
        sampling=StatsSampling(
            row_cap=ROW_CAP, truncated=lat_truncated or act_truncated
        ),
        pricing=PricingInfo(
            as_of=get_settings().AI_PRICES_AS_OF,
            unpriced_models=sorted({m.model for m in by_model if m.cost_usd is None}),
        ),
        prompt_quality=load_prompt_quality(),
    )
