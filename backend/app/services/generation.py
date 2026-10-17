"""AI itinerary generation orchestration.

Entry point: run_generation(trip_id, session_factory)

This module is called as a FastAPI BackgroundTask. It opens its own DB session
(the request-scoped session is already closed by the time the background task runs),
fetches trip data, renders the prompt, calls the AI service with retry/fallback,
persists Itinerary rows and one AICallLog row per provider attempt, then transitions
the trip to VOTING. It runs in three phases (read -> AI call -> write), each with its
own short-lived session, so no DB connection is held during the AI call.

On total failure the trip is set to GENERATION_FAILED (with a user-facing error
message) so the creator can retry.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Collection
from dataclasses import dataclass

import httpx
from openai import APIConnectionError, APIStatusError, RateLimitError
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.models.ai_call_log import AICallLog
from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.preference import Preference
from app.models.trip import Trip, TripStatus
from app.schemas._limits import max_trip_days
from app.schemas._sanitize import sanitize_text
from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.json_utils import AIInputError, AIOptionCountError, AIParseError
from app.services.ai.rate_limiter import LocalRateLimitError
from app.services.ai.service import AIService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template (code constant; version recorded on each Itinerary)
# ---------------------------------------------------------------------------

PROMPT_VERSION = "v3"

ITINERARY_PROMPT_V3 = """\
[SYSTEM]
You are an expert travel planner. Generate exactly {num_options} distinct travel itinerary options for a group trip. Respond with valid JSON ONLY — no markdown, no prose outside the JSON.

The JSON must conform exactly to this schema:
{{
  "options": [
    {{
      "option_title": "string — REQUIRED: non-empty creative theme name (see WRITING STYLE)",
      "destination_name": "string — REQUIRED",
      "destination_description": "string (2-3 sentences) — REQUIRED",
      "daily_itinerary": [
        {{
          "day_number": 1,
          "title": "string — REQUIRED",
          "activities": [
            {{
              "time": null,
              "title": "string — REQUIRED",
              "description": "string — REQUIRED",
              "estimated_cost": null
            }}
          ],
          "estimated_cost": null
        }}
      ],
      "total_estimated_budget": 1500.0,
      "currency": "USD",
      "match_reasoning": "string — why this option fits the group — REQUIRED",
      "highlights": ["string", "string", "string"]
    }}
  ]
}}

WRITING STYLE:
- Activity titles: 2-3 word noun-phrases. Must name a specific real place, dish, or activity. No verbs, no filler words. Examples: "Tsukiji tuna auction", "Raval vintage digging", "Fushimi Inari sunrise".
- Activity descriptions: 2-3 sentences. Open with a sensory or atmospheric detail, then give 1-2 practical specifics (location hint, timing tip, cost hint, insider knowledge). Write like a local friend texting a recommendation — casual, opinionated, useful. No guidebook voice.
- Day titles: Same 2-3 word compact style as activity titles.
- option_title: A creative 3-5 word thematic name capturing the trip's personality. Must NOT contain or repeat the destination name. Examples: "Coastal Culture Crawl", "Ramen, Rails & Rooftops", "Old Town Budget Blitz".
- NEVER use these words or patterns — they are dead giveaways of AI-generated text: em dashes (—), "nestled", "vibrant", "bustling", "hidden gem", "a testament to", "boasts", "delve", "tapestry", "unwind", "indulge", "immerse yourself", "whether you're", "from X to Y" sentence openers, "offers a unique". Use plain dashes (-) if needed.

Rules:
- EVERY option MUST include a non-empty "option_title" field. An option missing option_title is invalid and will be rejected.
- The "options" array must have exactly {num_options} items.
- Each option must cover all {trip_duration_days} days of the trip.
- Each day must have exactly 4 activities.
- Of each day's 4 activities, exactly 3 must reference a specific named venue, dish, or experience. Exactly 1 must be an unstructured neighborhood exploration (no fixed destination) — but still written with full descriptive depth: describe the area's vibe, what to look for, a landmark to orient around.
- NEVER use logistics as activities: no check-in, check-out, arrival, departure, hotel settling, packing, transfers, or airport activities. Every activity slot must be a real experience the group will remember.
- Meals are NOT activities unless they reference a specific, well-known restaurant or food experience by name (e.g. "Dinner at Noma", "Tsukiji tuna auction breakfast", "Michelin-starred lunch at Osteria Francescana"). Generic meals — "lunch at a local restaurant", "dinner in the old town", "grab street food" — are banned.
- All activity time fields must be null. Activities are ordered sequentially within each day; do not assign clock times.
- All estimated_cost fields must be null (price data is not available yet).
- total_estimated_budget must be a realistic float in the stated currency.
- currency must be a valid 3-letter ISO 4217 code.
- Return ONLY the JSON object — no preamble, no explanation.

ERROR REPORTING:
If you cannot fulfill the request because the destination is not a real, recognizable place, the constraints are contradictory or impossible, or the input is too vague to generate meaningful itineraries — do NOT attempt to generate options. Instead return ONLY this JSON:
{{
  "error": {{
    "message": "<one sentence explaining what is wrong, addressed to the user>",
    "suggestion": "<specific actionable fix — name 2-3 real alternatives if destination is the problem>",
    "field": "<one of: destination | dates | budget | general>"
  }}
}}

EXAMPLE (one option, one day shown, Barcelona):
{{
  "option_title": "Barcelona Back-Alley Binge",
  "destination_name": "Barcelona, Spain",
  "destination_description": "Barcelona trades on contrasts - Gothic stone alleys spill into Modernista show-offs, and every neighbourhood has its own pace. The food scene runs from standing-room-only tapas bars to decade-long reservation lists. Salt air off the Mediterranean shows up in unexpected places.",
  "daily_itinerary": [
    {{
      "day_number": 2,
      "title": "Sant Antoni to Bunkers",
      "activities": [
        {{
          "time": null,
          "title": "Boqueria back-stall breakfast",
          "description": "Squeeze past the tourist clusters to the counter seats at Pinotxo Bar in the back. Chickpea stew and a cava for under €8. Best before 9:30 when the crowds hit.",
          "estimated_cost": null
        }},
        {{
          "time": null,
          "title": "Raval morning wander",
          "description": "The blocks south of MACBA shift from skatepark chaos to quiet vintage shops within a few turns. Carrer dels Tallers is the vinyl-and-bookshop strip. Grab a cortado at Federal Café if you need an anchor, otherwise let the neighbourhood happen.",
          "estimated_cost": null
        }},
        {{
          "time": null,
          "title": "Vermouth at Morro Fi",
          "description": "Standing-room-only vermouth bar in Sant Antoni. House vermut on tap paired with conservas. The tinned mussels are the move. Cash only, closes at 2pm sharp so don't be late.",
          "estimated_cost": null
        }},
        {{
          "time": null,
          "title": "Bunkers del Carmel sunset",
          "description": "Abandoned anti-aircraft batteries on a hilltop with the best 360° view of the city. Bring your own drinks from the Carmel market below. Arrive 45min before sunset or you'll be standing.",
          "estimated_cost": null
        }}
      ],
      "estimated_cost": null
    }}
  ],
  "total_estimated_budget": 1800.0,
  "currency": "EUR",
  "match_reasoning": "Barcelona suits this group because the budget range comfortably covers mid-range accommodation plus daily dining. The food-first interests align with the city's eating culture, and the mix of architecture and nightlife covers the activity variety the group asked for.",
  "highlights": ["Vermouth culture in Sant Antoni", "Gothic Quarter night maze", "Beachfront morning runs"]
}}
[USER]
Plan a group trip with the following details:

TRIP TITLE: {trip_title}
PROPOSED DATES: {proposed_dates}
TRIP DURATION: {trip_duration_days} days
NUMBER OF OPTIONS REQUIRED: {num_options}
{destination_constraint}

GROUP SIZE: {group_size} participants total ({participant_count} submitted preferences)

PARTICIPANT PREFERENCES:
{preferences_block}

Generate {num_options} travel itinerary options that best satisfy the group's collective preferences. Prioritize destinations and activities that maximize overlap between participants' interests and budgets.\
"""


# ---------------------------------------------------------------------------
# Public entry point (called by BackgroundTasks)
# ---------------------------------------------------------------------------


def _humanize_wait(seconds: float) -> str:
    """Seconds under two minutes, then minutes, then hours (rounded up)."""
    secs = int(seconds) + 1
    if secs < 120:
        return f"{secs} seconds"
    if secs < 7200:
        return f"{-(-secs // 60)} minutes"
    return f"about {round(secs / 3600)} hours"


def _humanize_error(exc: Exception) -> str:
    """Convert a technical exception into a user-friendly error message."""
    if isinstance(exc, AIInputError):
        msg = exc.ai_message
        if exc.suggestion:
            msg = f"{msg} Tip: {exc.suggestion}"
        return msg
    if isinstance(exc, AIOptionCountError):
        return (
            "The AI generated the wrong number of itinerary options. "
            "Try again or reduce the number of options in the trip settings."
        )
    if isinstance(exc, AIParseError):
        return (
            "The AI returned an invalid response. "
            "This is usually temporary — try again."
        )
    if isinstance(exc, LocalRateLimitError):
        if exc.kind == "context_length":
            return (
                "The trip preferences are too long to process. "
                "Try reducing the number of participants or shortening preference details."
            )
        return (
            "The AI service is busy. Please try again in "
            f"{_humanize_wait(exc.retry_after_seconds)}."
        )
    if isinstance(exc, RateLimitError):
        return (
            "The AI service is currently busy (rate limit reached). "
            "Please wait a few minutes and try again."
        )
    if isinstance(exc, APIStatusError) and exc.status_code >= 500:
        return (
            "The AI service is temporarily unavailable. "
            "Please try again in a few minutes."
        )
    if isinstance(exc, APIConnectionError | TimeoutError | httpx.TimeoutException):
        return (
            "Could not connect to the AI service. "
            "Please check your internet connection and try again."
        )
    return "Something went wrong while generating itineraries. Please try again."


async def run_generation(
    trip_id: int,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Background task entry point.

    Three phases, each with its own short-lived session, so no DB connection is
    held while the (minutes-long) AI call runs: read -> AI call -> write.
    """
    try:
        job = await _read_phase(trip_id, session_factory)
        if job is None:
            return
        calls: list[AICallLog] = []
        try:
            ai_response = await AIService.from_settings().generate_itineraries(
                prompt=job.prompt, num_options=job.num_options, calls=calls
            )
        except Exception:
            await _write_call_logs(
                trip_id, job.iteration_number, calls, session_factory
            )
            raise
        if not await _write_phase(trip_id, job, ai_response, calls, session_factory):
            return
    except Exception as exc:
        logger.error("Generation failed for trip %d: %s", trip_id, exc, exc_info=True)
        await _reset_trip_status(
            trip_id, session_factory, error_message=_humanize_error(exc)
        )
        return
    await _send_voting_emails(trip_id, job.iteration_number, session_factory)


# ---------------------------------------------------------------------------
# Generation start / crash recovery
# ---------------------------------------------------------------------------


async def start_generation(
    db: AsyncSession, trip_id: int, allowed: Collection[TripStatus]
) -> bool:
    """Atomically flip a trip to GENERATING if its status is in ``allowed``.

    Returns True when this call won the transition (rowcount == 1); a concurrent
    caller that lost the race gets False and must not schedule a generation.
    """
    result = await db.execute(
        update(Trip)
        .where(Trip.id == trip_id, Trip.status.in_(allowed))
        .values(status=TripStatus.GENERATING, generation_error=None)
    )
    await db.commit()
    return result.rowcount == 1


async def recover_stuck_generations(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Mark trips left in GENERATING (server restarted mid-run) as failed."""
    # ponytail: Railway runs one uvicorn process, but during a zero-downtime
    # deploy the new instance fails every in-flight generation on the old one,
    # and the write-phase CAS then discards the old run's result, so the user
    # must retry. Upgrade path: heartbeat/lease column.
    async with session_factory() as db:
        result = await db.execute(
            update(Trip)
            .where(Trip.status == TripStatus.GENERATING)
            .values(
                status=TripStatus.GENERATION_FAILED,
                generation_error=(
                    "Generation was interrupted by a server restart. Please try again."
                ),
            )
        )
        await db.commit()
        return result.rowcount


# ---------------------------------------------------------------------------
# Core generation pipeline
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _GenerationJob:
    """Plain values snapshotted in the read phase (no ORM objects survive)."""

    prompt: str
    num_options: int
    iteration_number: int


async def _read_phase(
    trip_id: int, session_factory: async_sessionmaker[AsyncSession]
) -> _GenerationJob | None:
    async with session_factory() as db:
        # Re-fetch trip — idempotency guard in case of double-trigger
        trip = (
            await db.execute(select(Trip).where(Trip.id == trip_id))
        ).scalar_one_or_none()
        if trip is None or trip.status != TripStatus.GENERATING:
            logger.warning(
                "run_generation called for trip %d but status is %s — skipping",
                trip_id,
                getattr(trip, "status", "NOT_FOUND"),
            )
            return None

        preferences = list(
            (await db.execute(select(Preference).where(Preference.trip_id == trip_id)))
            .scalars()
            .all()
        )
        # Count all participants (including creator who never submits a Preference row)
        group_size = (
            await db.execute(
                select(func.count(Participant.id)).where(Participant.trip_id == trip_id)
            )
        ).scalar_one()
        return _GenerationJob(
            prompt=_render_prompt(trip, preferences, group_size=group_size),
            num_options=trip.num_options,
            iteration_number=trip.current_iteration + 1,
        )


async def _write_call_logs(
    trip_id: int,
    iteration_number: int,
    calls: list[AICallLog],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as db:
        _add_call_logs(db, calls, trip_id=trip_id, iteration_number=iteration_number)
        await db.commit()


async def _write_phase(
    trip_id: int,
    job: _GenerationJob,
    ai_response: AIGenerationResponse,
    calls: list[AICallLog],
    session_factory: async_sessionmaker[AsyncSession],
) -> bool:
    """Persist results; False (call logs only) if the trip is no longer GENERATING."""
    # Model/provider/latency come from the winning (valid) attempt's AICallLog.
    winner = next((c for c in reversed(calls) if c.response_valid), None)
    settings = get_settings()
    model_used = winner.model_used if winner else settings.DEFAULT_AI_MODEL
    provider = winner.provider if winner else settings.AI_PROVIDER_NAME
    latency_ms = winner.latency_ms if winner else None

    async with session_factory() as db:
        # CAS: startup recovery on a newer instance may have failed this trip while
        # the AI call ran. ponytail: a retry started after recovery can still race
        # this stale run (both see GENERATING); upgrade path is a per-attempt
        # generation id on the trip.
        result = await db.execute(
            update(Trip)
            .where(Trip.id == trip_id, Trip.status == TripStatus.GENERATING)
            .values(current_iteration=job.iteration_number, status=TripStatus.VOTING)
        )
        if result.rowcount != 1:
            logger.warning(
                "Trip %d no longer GENERATING after AI call — discarding results",
                trip_id,
            )
            _add_call_logs(
                db, calls, trip_id=trip_id, iteration_number=job.iteration_number
            )
            await db.commit()
            return False
        for option in ai_response.options:
            db.add(
                Itinerary(
                    trip_id=trip_id,
                    iteration_number=job.iteration_number,
                    option_title=option.option_title,
                    destination_name=option.destination_name,
                    destination_description=option.destination_description,
                    daily_itinerary=[d.model_dump() for d in option.daily_itinerary],
                    total_estimated_budget=option.total_estimated_budget,
                    currency=option.currency,
                    match_reasoning=option.match_reasoning,
                    highlights=option.highlights,
                    prompt_version=PROMPT_VERSION,
                    model_used=model_used,
                    provider=provider,
                    generation_latency_ms=latency_ms,
                )
            )
        _add_call_logs(
            db, calls, trip_id=trip_id, iteration_number=job.iteration_number
        )
        await db.commit()
    logger.info(
        "Generation complete for trip %d: %d options, provider=%s, latency=%sms",
        trip_id,
        len(ai_response.options),
        provider,
        latency_ms,
    )
    return True


async def _reset_trip_status(
    trip_id: int,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    error_message: str,
) -> None:
    """Open a fresh session to set trip status to GENERATION_FAILED after a failure."""
    async with session_factory() as db:
        result = await db.execute(
            update(Trip)
            .where(Trip.id == trip_id, Trip.status == TripStatus.GENERATING)
            .values(status=TripStatus.GENERATION_FAILED, generation_error=error_message)
        )
        await db.commit()
        if result.rowcount == 1:
            logger.info("Trip %d set to GENERATION_FAILED: %s", trip_id, error_message)


# ---------------------------------------------------------------------------
# Prompt rendering helpers
# ---------------------------------------------------------------------------


def _render_prompt(
    trip: Trip,
    preferences: list[Preference],
    *,
    group_size: int,
) -> str:
    trip_duration_days = _compute_trip_duration(trip, preferences)

    if trip.proposed_start_date and trip.proposed_end_date:
        proposed_dates = (
            f"{trip.proposed_start_date.date()} to {trip.proposed_end_date.date()}"
        )
    else:
        proposed_dates = "flexible"

    if trip.destination:
        clean_dest = sanitize_text(trip.destination)
        destination_constraint = (
            f"DESTINATION: <<<USER DATA>>>{clean_dest}<<<END USER DATA>>>"
        )
    else:
        destination_constraint = (
            "DESTINATION: Open — suggest the best fit for this group"
        )

    preferences_block = _build_preferences_block(preferences)

    return ITINERARY_PROMPT_V3.format(
        num_options=trip.num_options,
        trip_duration_days=trip_duration_days,
        trip_title=f"<<<USER DATA>>>{sanitize_text(trip.title)}<<<END USER DATA>>>",
        proposed_dates=proposed_dates,
        destination_constraint=destination_constraint,
        group_size=group_size,
        participant_count=len(preferences),
        preferences_block=preferences_block,
    )


def _build_preferences_block(preferences: list[Preference]) -> str:
    if not preferences:
        return "No preferences submitted yet."

    lines: list[str] = []
    for i, pref in enumerate(preferences, start=1):
        lines.append(f"Participant {i}:")

        if pref.preferred_start_date and pref.preferred_end_date:
            lines.append(
                f"  - Dates: {pref.preferred_start_date.date()} to {pref.preferred_end_date.date()}"
            )
        else:
            lines.append("  - Dates: flexible")

        if pref.budget_min is not None and pref.budget_max is not None:
            currency = pref.currency or "USD"
            lines.append(
                f"  - Budget: {pref.budget_min} - {pref.budget_max} {currency}"
            )
        elif pref.budget_max is not None:
            currency = pref.currency or "USD"
            lines.append(f"  - Budget: up to {pref.budget_max} {currency}")

        if pref.interests:
            clean_interests = sanitize_text(pref.interests)
            lines.append(
                f"  - Interests: <<<USER DATA>>>{clean_interests}<<<END USER DATA>>>"
            )

        if pref.activity_tags:
            clean_tags = ", ".join(sanitize_text(t) for t in pref.activity_tags)
            lines.append(
                f"  - Activity tags: <<<USER DATA>>>{clean_tags}<<<END USER DATA>>>"
            )

        lines.append("")  # blank line between participants

    return "\n".join(lines).rstrip()


def _compute_trip_duration(trip: Trip, preferences: list[Preference]) -> int:
    """Compute trip duration in days.

    Priority:
    1. Trip-level proposed dates (most authoritative)
    2. Most common participant date range (naive: use median length)
    3. Fallback: 7 days

    Final result is clamped to max_trip_days(num_options) to prevent
    AI output truncation when the fixed max_tokens budget is exceeded.
    """
    if trip.proposed_start_date and trip.proposed_end_date:
        delta = trip.proposed_end_date - trip.proposed_start_date
        days = max(1, delta.days)
    else:
        durations: list[int] = []
        for pref in preferences:
            if pref.preferred_start_date and pref.preferred_end_date:
                delta = pref.preferred_end_date - pref.preferred_start_date
                if delta.days > 0:
                    durations.append(delta.days)

        if durations:
            durations.sort()
            days = durations[len(durations) // 2]  # median
        else:
            days = 7  # default

    cap = max_trip_days(trip.num_options)
    if days > cap:
        logger.warning(
            "Trip %s duration %d days exceeds cap %d for num_options=%d; clamping",
            trip.id,
            days,
            cap,
            trip.num_options,
        )
        days = cap

    return days


# ---------------------------------------------------------------------------
# Email notifications after generation
# ---------------------------------------------------------------------------


async def _send_voting_emails(
    trip_id: int,
    iteration_number: int,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Send voting or new-iteration notifications to all participants (best-effort)."""
    from app.services.email.brevo import EmailKind, EmailService

    async with session_factory() as db:
        trip = (await db.execute(select(Trip).where(Trip.id == trip_id))).scalar_one()
        title, trip_code = trip.title, trip.trip_code
        participants = list(
            (
                await db.execute(
                    select(Participant).where(Participant.trip_id == trip_id)
                )
            )
            .scalars()
            .all()
        )

    email_service = EmailService.from_settings()
    kind: EmailKind = "voting" if iteration_number == 1 else "new_iteration"
    results = await asyncio.gather(
        *[
            email_service.send_trip_email(
                kind,
                to_email=p.email,
                participant_name=p.name,
                trip_title=title,
                trip_code=trip_code,
                pin=p.pin,
                token=p.token,
            )
            for p in participants
        ],
        return_exceptions=True,
    )
    for p, r in zip(participants, results, strict=True):
        if isinstance(r, Exception):
            logger.warning(
                "Failed to send voting email to participant %d for trip %d",
                p.id,
                trip_id,
            )


# ---------------------------------------------------------------------------
# AI call logging
# ---------------------------------------------------------------------------


def _add_call_logs(
    db: AsyncSession,
    calls: list[AICallLog],
    *,
    trip_id: int,
    iteration_number: int,
) -> None:
    """Stamp per-attempt rows with generation context, stage them, log each."""
    for attempt, log in enumerate(calls, start=1):
        log.trip_id = trip_id
        log.iteration_number = iteration_number
        log.attempt = attempt
        db.add(log)
        logger.info(
            "ai_call trip=%s iteration=%s attempt=%s provider=%s model=%s "
            "latency_ms=%s tokens_in=%s tokens_out=%s tokens_total=%s "
            "finish=%s valid=%s error=%.200r",
            trip_id,
            iteration_number,
            attempt,
            log.provider,
            log.model_used,
            log.latency_ms,
            log.token_count_input,
            log.token_count_output,
            log.token_count_total,
            log.finish_reason,
            log.response_valid,
            log.error_message,
        )
