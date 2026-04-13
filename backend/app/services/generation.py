"""AI itinerary generation orchestration.

Entry point: run_generation(trip_id, session_factory)

This module is called as a FastAPI BackgroundTask. It opens its own DB session
(the request-scoped session is already closed by the time the background task runs),
fetches trip data, renders the prompt, calls the AI service with retry/fallback,
persists Itinerary rows and an AICallLog entry, then transitions the trip to VOTING.

On total failure the trip is reset to COLLECTING_PREFERENCES so the creator can retry.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.models.ai_call_log import AICallLog
from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.preference import Preference
from app.models.prompt_template import PromptTemplate
from app.models.trip import Trip
from app.services.ai.json_utils import AIInputError, AIParseError
from app.services.ai.service import AIService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template (seeded into DB on first generate call)
# ---------------------------------------------------------------------------

ITINERARY_PROMPT_V2 = """\
[SYSTEM]
You are an expert travel planner. Generate exactly {num_options} distinct travel itinerary options for a group trip. Respond with valid JSON ONLY — no markdown, no prose outside the JSON.

The JSON must conform exactly to this schema:
{{
  "options": [
    {{
      "destination_name": "string",
      "destination_description": "string (2-3 sentences)",
      "daily_itinerary": [
        {{
          "day_number": 1,
          "title": "string",
          "activities": [
            {{
              "time": null,
              "title": "string",
              "description": "string",
              "estimated_cost": null
            }}
          ],
          "estimated_cost": null
        }}
      ],
      "total_estimated_budget": 1500.0,
      "currency": "USD",
      "match_reasoning": "string — why this option fits the group",
      "highlights": ["string", "string", "string"]
    }}
  ]
}}

WRITING STYLE:
- Activity titles: 2-3 word noun-phrases. Must name a specific real place, dish, or activity. No verbs, no filler words. Examples: "Tsukiji tuna auction", "Raval vintage digging", "Fushimi Inari sunrise".
- Activity descriptions: 2-3 sentences. Open with a sensory or atmospheric detail, then give 1-2 practical specifics (location hint, timing tip, cost hint, insider knowledge). Write like a local friend texting a recommendation — casual, opinionated, useful. No guidebook voice.
- Day titles: Same 2-3 word compact style as activity titles.
- NEVER use these words or patterns — they are dead giveaways of AI-generated text: em dashes (—), "nestled", "vibrant", "bustling", "hidden gem", "a testament to", "boasts", "delve", "tapestry", "unwind", "indulge", "immerse yourself", "whether you're", "from X to Y" sentence openers, "offers a unique". Use plain dashes (-) if needed.

Rules:
- The "options" array must have exactly {num_options} items.
- Each option must cover all {trip_duration_days} days of the trip.
- Each day must have exactly 4 activities.
- Of each day's 4 activities, exactly 3 must reference a specific named venue, dish, or experience. Exactly 1 must be an unstructured neighborhood exploration (no fixed destination) — but still written with full descriptive depth: describe the area's vibe, what to look for, a landmark to orient around.
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

EXAMPLE (one day, Barcelona):
{{
  "day_number": 2,
  "title": "Sant Antoni to Bunkers",
  "activities": [
    {{
      "time": "09:00",
      "title": "Boqueria back-stall breakfast",
      "description": "Squeeze past the tourist clusters to the counter seats at Pinotxo Bar in the back. Chickpea stew and a cava for under €8. Best before 9:30 when the crowds hit.",
      "estimated_cost": null
    }},
    {{
      "time": "11:00",
      "title": "Raval morning wander",
      "description": "The blocks south of MACBA shift from skatepark chaos to quiet vintage shops within a few turns. Carrer dels Tallers is the vinyl-and-bookshop strip. Grab a cortado at Federal Café if you need an anchor, otherwise let the neighborhood happen.",
      "estimated_cost": null
    }},
    {{
      "time": "14:00",
      "title": "Vermouth at Morro Fi",
      "description": "Standing-room-only vermouth bar in Sant Antoni. House vermut on tap paired with conservas. The tinned mussels are the move. Cash only, closes at 2pm sharp so don't be late.",
      "estimated_cost": null
    }},
    {{
      "time": "18:30",
      "title": "Bunkers del Carmel sunset",
      "description": "Abandoned anti-aircraft batteries on a hilltop with the best 360° view of the city. Bring your own drinks from the Carmel market below. Arrive 45min before sunset or you'll be standing.",
      "estimated_cost": null
    }}
  ],
  "estimated_cost": null
}}
[USER]
Plan a group trip with the following details:

TRIP TITLE: {trip_title}
PROPOSED DATES: {proposed_dates}
TRIP DURATION: {trip_duration_days} days
NUMBER OF OPTIONS REQUIRED: {num_options}
{destination_constraint}

PARTICIPANT PREFERENCES ({participant_count} participants):
{preferences_block}

Generate {num_options} travel itinerary options that best satisfy the group's collective preferences. Prioritize destinations and activities that maximize overlap between participants' interests and budgets.\
"""


# ---------------------------------------------------------------------------
# Public entry point (called by BackgroundTasks)
# ---------------------------------------------------------------------------


def _humanize_error(exc: Exception) -> str:
    """Convert a technical exception into a user-friendly error message."""
    if isinstance(exc, AIInputError):
        msg = exc.ai_message
        if exc.suggestion:
            msg = f"{msg} Tip: {exc.suggestion}"
        return msg
    if isinstance(exc, AIParseError):
        return (
            "The AI returned an invalid response. "
            "This is usually temporary — try again."
        )
    if isinstance(exc, ValueError) and "options" in str(exc):
        return (
            "The AI generated the wrong number of itinerary options. "
            "Try again or reduce the number of options in the trip settings."
        )
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 429:
            return (
                "The AI service is currently busy (rate limit reached). "
                "Please wait a few minutes and try again."
            )
        if exc.response.status_code >= 500:
            return (
                "The AI service is temporarily unavailable. "
                "Please try again in a few minutes."
            )
    if isinstance(exc, httpx.ConnectError | TimeoutError | httpx.TimeoutException):
        return (
            "Could not connect to the AI service. "
            "Please check your internet connection and try again."
        )
    return "Something went wrong while generating itineraries. Please try again."


async def run_generation(
    trip_id: int,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Background task entry point. Opens its own DB session."""
    async with session_factory() as db:
        try:
            await _do_generation(trip_id, db)
        except Exception as exc:
            logger.error(
                "Generation failed for trip %d: %s", trip_id, exc, exc_info=True
            )
            await _reset_trip_status(
                trip_id, session_factory, error_message=_humanize_error(exc)
            )


# ---------------------------------------------------------------------------
# Core generation pipeline
# ---------------------------------------------------------------------------


async def _do_generation(trip_id: int, db: AsyncSession) -> None:
    # Re-fetch trip — idempotency guard in case of double-trigger
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if trip is None or trip.status != "GENERATING":
        logger.warning(
            "run_generation called for trip %d but status is %s — skipping",
            trip_id,
            getattr(trip, "status", "NOT_FOUND"),
        )
        return

    # Clear any previous generation error
    trip.generation_error = None

    # Seed / fetch the active prompt template
    template = await _upsert_prompt_template(db)

    # Fetch all preferences for this trip
    prefs_result = await db.execute(
        select(Preference).where(Preference.trip_id == trip_id)
    )
    preferences = list(prefs_result.scalars().all())

    # Render prompt
    prompt = _render_prompt(template, trip, preferences)

    # Call AI with retry + fallback
    ai_service = AIService.from_settings()
    t_start = time.monotonic()
    try:
        ai_response, provider_name = await ai_service.generate_itineraries(
            prompt=prompt,
            num_options=trip.num_options,
        )
    except Exception as exc:
        latency_ms = int((time.monotonic() - t_start) * 1000)
        await _log_ai_call(
            db=db,
            trip_id=trip_id,
            prompt_version_id=template.id,
            model_used=get_settings().DEFAULT_AI_MODEL,
            provider_name="unknown",
            latency_ms=latency_ms,
            response_valid=False,
            error_message=str(exc),
            raw_response=getattr(exc, "raw_text", None),
        )
        await db.commit()
        raise

    latency_ms = int((time.monotonic() - t_start) * 1000)

    # Increment iteration counter
    trip.current_iteration += 1
    iteration_number = trip.current_iteration

    # Persist itinerary rows
    for option in ai_response.options:
        itinerary = Itinerary(
            trip_id=trip_id,
            iteration_number=iteration_number,
            destination_name=option.destination_name,
            destination_description=option.destination_description,
            daily_itinerary_json=json.dumps(
                [day.model_dump() for day in option.daily_itinerary]
            ),
            total_estimated_budget=option.total_estimated_budget,
            currency=option.currency,
            match_reasoning=option.match_reasoning,
            highlights=json.dumps(option.highlights),
            prompt_version_id=template.id,
            model_used=get_settings().DEFAULT_AI_MODEL,
            provider=provider_name,
            generation_latency_ms=latency_ms,
        )
        db.add(itinerary)

    await _log_ai_call(
        db=db,
        trip_id=trip_id,
        prompt_version_id=template.id,
        model_used=get_settings().DEFAULT_AI_MODEL,
        provider_name=provider_name,
        latency_ms=latency_ms,
        response_valid=True,
        error_message=None,
    )

    trip.status = "VOTING"
    await db.commit()
    logger.info(
        "Generation complete for trip %d: %d options, provider=%s, latency=%dms",
        trip_id,
        len(ai_response.options),
        provider_name,
        latency_ms,
    )

    await _send_voting_emails(trip, iteration_number, db)


async def _reset_trip_status(
    trip_id: int,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    error_message: str,
) -> None:
    """Open a fresh session to set trip status to GENERATION_FAILED after a failure."""
    async with session_factory() as db:
        result = await db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one_or_none()
        if trip is not None and trip.status == "GENERATING":
            trip.status = "GENERATION_FAILED"
            trip.generation_error = error_message
            await db.commit()
            logger.info(
                "Trip %d set to GENERATION_FAILED: %s",
                trip_id,
                error_message,
            )


# ---------------------------------------------------------------------------
# Prompt template upsert (seeds DB on first call, idempotent)
# ---------------------------------------------------------------------------


async def _upsert_prompt_template(db: AsyncSession) -> PromptTemplate:
    # Try to find the active v2 template first
    result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.name == "itinerary_generation",
            PromptTemplate.version == "v2",
            PromptTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if template is not None:
        return template

    # Deactivate any existing v1 templates
    v1_result = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.name == "itinerary_generation",
            PromptTemplate.version == "v1",
        )
    )
    for old in v1_result.scalars().all():
        old.is_active = False

    # Seed v2
    template = PromptTemplate(
        name="itinerary_generation",
        version="v2",
        template_text=ITINERARY_PROMPT_V2,
        model_target="Qwen/Qwen2.5-72B-Instruct",
        is_active=True,
        traffic_weight=1.0,
    )
    db.add(template)
    await db.flush()  # assigns template.id before we use it
    return template


# ---------------------------------------------------------------------------
# Prompt rendering helpers
# ---------------------------------------------------------------------------


def _render_prompt(
    template: PromptTemplate,
    trip: Trip,
    preferences: list[Preference],
) -> str:
    trip_duration_days = _compute_trip_duration(trip, preferences)

    if trip.proposed_start_date and trip.proposed_end_date:
        proposed_dates = (
            f"{trip.proposed_start_date.date()} to {trip.proposed_end_date.date()}"
        )
    else:
        proposed_dates = "flexible"

    if trip.destination:
        destination_constraint = f"DESTINATION: {trip.destination}"
    else:
        destination_constraint = (
            "DESTINATION: Open — suggest the best fit for this group"
        )

    preferences_block = _build_preferences_block(preferences)

    return template.template_text.format(
        num_options=trip.num_options,
        trip_duration_days=trip_duration_days,
        trip_title=trip.title,
        proposed_dates=proposed_dates,
        destination_constraint=destination_constraint,
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
            lines.append(f"  - Interests: {pref.interests}")

        if pref.activity_tags:
            try:
                tags = json.loads(pref.activity_tags)
                if tags:
                    lines.append(f"  - Activity tags: {', '.join(tags)}")
            except (json.JSONDecodeError, TypeError):
                pass

        lines.append("")  # blank line between participants

    return "\n".join(lines).rstrip()


def _compute_trip_duration(trip: Trip, preferences: list[Preference]) -> int:
    """Compute trip duration in days.

    Priority:
    1. Trip-level proposed dates (most authoritative)
    2. Most common participant date range (naive: use median length)
    3. Fallback: 7 days
    """
    if trip.proposed_start_date and trip.proposed_end_date:
        delta = trip.proposed_end_date - trip.proposed_start_date
        return max(1, delta.days)

    durations: list[int] = []
    for pref in preferences:
        if pref.preferred_start_date and pref.preferred_end_date:
            delta = pref.preferred_end_date - pref.preferred_start_date
            if delta.days > 0:
                durations.append(delta.days)

    if durations:
        durations.sort()
        return durations[len(durations) // 2]  # median

    return 7  # default


# ---------------------------------------------------------------------------
# Email notifications after generation
# ---------------------------------------------------------------------------


async def _send_voting_emails(
    trip: Trip, iteration_number: int, db: AsyncSession
) -> None:
    """Send voting or new-iteration notifications to all participants (best-effort)."""
    from app.services.email.brevo import EmailService

    participants_result = await db.execute(
        select(Participant).where(Participant.trip_id == trip.id)
    )
    participants = participants_result.scalars().all()

    email_service = EmailService.from_settings()
    for p in participants:
        try:
            if iteration_number == 1:
                await email_service.send_voting_notification(
                    to_email=p.email,
                    participant_name=p.name,
                    trip_title=trip.title,
                    trip_code=trip.trip_code,
                    pin=p.pin,
                    token=p.token,
                )
            else:
                await email_service.send_new_iteration_notification(
                    to_email=p.email,
                    participant_name=p.name,
                    trip_title=trip.title,
                    trip_code=trip.trip_code,
                    pin=p.pin,
                    token=p.token,
                )
        except Exception:
            logger.warning(
                "Failed to send voting email to %s for trip %d", p.email, trip.id
            )


# ---------------------------------------------------------------------------
# AI call logging
# ---------------------------------------------------------------------------


async def _log_ai_call(
    db: AsyncSession,
    trip_id: int,
    prompt_version_id: int | None,
    model_used: str,
    provider_name: str,
    latency_ms: int,
    response_valid: bool,
    error_message: str | None,
    raw_response: str | None = None,
) -> None:
    log_entry = AICallLog(
        trip_id=trip_id,
        prompt_version_id=prompt_version_id,
        model_used=model_used,
        provider=provider_name,
        latency_ms=latency_ms,
        response_valid=response_valid,
        error_message=error_message,
        raw_response=raw_response,
        created_at=datetime.now(UTC),
    )
    db.add(log_entry)
