"""Offline prompt eval: `cd backend && uv run python -m evals.run`.

Runs every case in cases.json against prompt v3 and v4 (one real model call per
case x version, plus one judge call per schema-valid response), then writes the
aggregates to evals/results.json for /stats to serve. Spends real quota. A case
counts only when BOTH versions answered, so the columns are like-for-like.

budget_realism inherits the same per-person-vs-group budget ambiguity that led
to dropping the budget_in_range check.

It calls the provider directly and never opens a DB session, so nothing it does
reaches ai_call_logs. Per-case detail is printed only; results.json holds
aggregates and no prompt or response text.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
from pathlib import Path

from openai import RateLimitError

from app.core.config import get_settings
from app.models.ai_call_log import AICallLog
from app.models.preference import Preference
from app.models.trip import Trip
from app.schemas._sanitize import sanitize_text
from app.schemas.itinerary import AIGenerationResponse
from app.schemas.stats import (
    CheckRate,
    JudgeScore,
    PromptQuality,
    PromptQualityVersion,
)
from app.services.ai.json_utils import AIParseError, extract_json
from app.services.ai.openai_compat import OpenAICompatProvider
from app.services.ai.rate_limiter import LocalRateLimitError, get_limiter
from app.services.generation import (
    ITINERARY_PROMPT_V4,
    _build_preferences_block,
    _compute_trip_duration,
    _render_prompt,
)
from evals.checks import CHECKS, INFORMATIONAL, check
from evals.prompts import ITINERARY_PROMPT_V3, JUDGE_PROMPT

HERE = Path(__file__).parent
# version -> (template, whether it instructs a time-of-day slot on every activity)
TEMPLATES = {"v3": (ITINERARY_PROMPT_V3, False), "v4": (ITINERARY_PROMPT_V4, True)}
CRITERIA = ("preference_fit", "conflict_handling", "specificity", "budget_realism")
CHECK_ORDER = (*CHECKS, "destination_respected")
JUDGE_MAX_TOKENS = 1024
PROVIDER_429_WAIT_S = 60


def _err(exc: Exception) -> str:
    """Type and HTTP status only: exception text can carry response bodies."""
    return f"{type(exc).__name__} {getattr(exc, 'status_code', '')}".strip()


async def _retrying[T](call: Callable[[], Awaitable[T]]) -> T:
    """Sleep out our own rate gate; one 60s wait on a provider 429."""
    rate_limited = False
    while True:
        try:
            return await call()
        except LocalRateLimitError as exc:
            if exc.kind == "context_length":
                raise
            await asyncio.sleep(exc.retry_after_seconds + 1)
        except RateLimitError:
            if rate_limited:
                raise
            rate_limited = True
            await asyncio.sleep(PROVIDER_429_WAIT_S)


def _build(case: dict) -> tuple[Trip, list[Preference]]:
    """Transient ORM objects: never added to a session."""
    t = case["trip"]
    start = datetime.fromisoformat(t["proposed_start_date"])
    trip = Trip(
        title=t["title"],
        destination=t["destination"],
        proposed_start_date=start,
        proposed_end_date=start + timedelta(days=t["days"]),
        num_options=t["num_options"],
    )
    return trip, [Preference(**p) for p in case["preferences"]]


async def _generate(
    provider: OpenAICompatProvider, prompt: str, num_options: int
) -> str | None:
    """Raw response text, or None when no response came back at all."""
    settings = get_settings()
    calls: list[AICallLog] = []

    async def go() -> AIGenerationResponse:
        calls.clear()
        return await provider.generate_itineraries(
            prompt,
            num_options,
            settings.DEFAULT_AI_MODEL,
            settings.DEFAULT_REASONING_EFFORT,
            calls=calls,
        )

    try:
        await _retrying(go)
    except AIParseError:
        pass  # bad output is a result, not an error; the raw text is on the log
    except Exception as exc:
        print(f"    provider error: {_err(exc)}")
        return None
    return (calls[-1].raw_response or "") if calls else None


def _judge_prompt(trip: Trip, prefs: list[Preference], duration: int, raw: str) -> str:
    dest = (
        f"<<<USER DATA>>>{sanitize_text(trip.destination)}<<<END USER DATA>>>"
        if trip.destination
        else "Open (the group asked for suggestions)"
    )
    trip_block = (
        f"Title: <<<USER DATA>>>{sanitize_text(trip.title)}<<<END USER DATA>>>\n"
        f"Destination: {dest}\nDuration: {duration} days\n"
        f"Options requested: {trip.num_options}"
    )
    return JUDGE_PROMPT.format(
        trip_block=trip_block,
        preferences_block=_build_preferences_block(prefs),
        candidate=sanitize_text(raw),
    )


def _valid_scores(scores: dict) -> dict[str, int] | None:
    # type() is int: rejects bool (an int subclass) and floats int() would truncate.
    ok = all(type(v) is int and 1 <= v <= 5 for v in scores.values())
    return scores if ok else None


async def _judge(provider: OpenAICompatProvider, prompt: str) -> dict[str, int] | None:
    settings = get_settings()
    model = settings.EVAL_JUDGE_MODEL or settings.DEFAULT_AI_MODEL
    estimated = len(prompt) // 4 + JUDGE_MAX_TOKENS

    async def go() -> str | None:
        reservation = await get_limiter().reserve(estimated)
        # ponytail: reuses the provider's private client factory so the judge hits
        # the same endpoint/key; make it public if a second caller appears.
        client = provider._make_client()
        extra = {"extra_body": settings.AI_EXTRA_BODY} if settings.AI_EXTRA_BODY else {}
        try:
            async with client:
                completion = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=JUDGE_MAX_TOKENS,
                    **extra,
                )
        except Exception:
            get_limiter().commit(reservation, estimated)
            raise
        usage = completion.usage
        get_limiter().commit(
            reservation, usage.total_tokens if usage is not None else estimated
        )
        return completion.choices[0].message.content

    try:
        data = extract_json(await _retrying(go))
        scores = {c: data[c] for c in CRITERIA}
    except Exception as exc:
        print(f"    judge failed: {_err(exc)}")
        return None
    valid = _valid_scores(scores)
    if valid is None:
        print("    judge failed: score not an integer in 1..5")
    return valid


def _mean(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _aggregate(
    version: str, records: list[tuple[dict, dict | None]]
) -> PromptQualityVersion:
    checks = []
    for name in CHECK_ORDER:
        hits = [r[name] for r, _ in records if name in r]
        if hits:
            checks.append(
                CheckRate(
                    check=name,
                    pass_rate=sum(hits) / len(hits),
                    cases=len(hits),
                    gating=name not in INFORMATIONAL,
                )
            )
    judged = [j for _, j in records if j]
    judge = [
        JudgeScore(criterion=c, mean=_mean([j[c] for j in judged])) for c in CRITERIA
    ]
    return PromptQualityVersion(
        prompt_version=version,
        cases=len(records),
        judged_cases=len(judged),
        all_checks_pass_rate=_mean(
            [all(v for k, v in r.items() if k not in INFORMATIONAL) for r, _ in records]
        )
        or 0.0,
        checks=checks,
        judge=judge,
        judge_overall=_mean([s.mean for s in judge if s.mean is not None]),
    )


async def main() -> None:
    settings = get_settings()
    cases = json.loads((HERE / "cases.json").read_text())
    provider = OpenAICompatProvider(
        api_key=settings.AI_API_KEY,
        base_url=settings.AI_BASE_URL,
        provider_name=settings.AI_PROVIDER_NAME,
        extra_body=settings.AI_EXTRA_BODY,
    )
    records: dict[str, list[tuple[dict, dict | None]]] = {v: [] for v in TEMPLATES}
    for case in cases:
        trip, prefs = _build(case)
        duration = _compute_trip_duration(trip, prefs)
        # Generate every version first: a case missing any answer is dropped for
        # all versions so the columns stay paired.
        raws = {}
        for version, (template, _) in TEMPLATES.items():
            prompt = _render_prompt(
                trip, prefs, group_size=case["group_size"], template=template
            )
            raws[version] = await _generate(provider, prompt, trip.num_options)
        if any(raw is None for raw in raws.values()):
            print(f"{case['case_id']}: a version had no response, excluded from all")
            continue
        for version, raw in raws.items():
            slots_required = TEMPLATES[version][1]
            results = check(raw, case, duration, trip.num_options, slots_required)
            scores = None
            if results["schema_valid"]:
                scores = await _judge(
                    provider, _judge_prompt(trip, prefs, duration, raw)
                )
            records[version].append((results, scores))
            failed = [k for k, ok in results.items() if not ok]
            print(f"{case['case_id']} {version}: failed={failed or '-'} judge={scores}")

    out = HERE / "results.json"
    # Under half the cases answered means a provider/config failure, not a
    # prompt result: publishing it would show /stats a bogus scorecard.
    usable = len(next(iter(records.values())))
    if not usable or usable * 2 < len(cases):
        raise SystemExit(
            f"aborting, {out} not written: too few usable cases "
            f"({usable}/{len(cases)}); need at least half answered by both "
            "versions, see provider errors above"
        )
    quality = PromptQuality(
        run_date=date.today().isoformat(),
        model=settings.DEFAULT_AI_MODEL,
        judge_model=settings.EVAL_JUDGE_MODEL or settings.DEFAULT_AI_MODEL,
        cases=len(cases),
        versions=[_aggregate(v, r) for v, r in records.items()],
    )
    out.write_text(quality.model_dump_json(indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
