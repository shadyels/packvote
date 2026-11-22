from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event

from app.core.config import get_settings
from app.models.ai_call_log import AICallLog
from app.models.participant import Participant
from app.models.vote import Vote
from app.schemas.stats import (
    CheckRate,
    JudgeScore,
    PromptQuality,
    PromptQualityVersion,
)
from app.services import stats
from app.services.rate_limit import SlidingWindow
from tests.factories import make_itinerary, make_participant, make_trip, make_user

FORBIDDEN_KEYS = {
    "prompt",
    "raw_response",
    "error_message",
    "email",
    "name",
    "title",
    "destination",
    "notes",
    "candidate",
    "raw",
    "response",
    "api_key",
}


def _log(db, **kw) -> AICallLog:
    row = AICallLog(
        **{
            "model_used": "m1",
            "provider": "p1",
            "response_valid": False,
            "trip_id": None,
            **kw,
        }
    )
    db.add(row)
    return row


async def _get(client) -> dict:
    resp = await client.get("/stats")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _keys(node) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


async def test_empty_db(client) -> None:
    data = await _get(client)
    assert all(v == 0 for v in data["totals"].values())
    assert len(data["funnel"]) == 6
    assert all(f["trips"] == 0 for f in data["funnel"])
    gen = data["generation"]
    assert len(gen["latency"]["histogram"]) == 7
    assert all(b["attempts"] == 0 for b in gen["latency"]["histogram"])
    assert gen["latency"]["histogram"][-1]["max_ms"] is None
    assert len(data["activity"]) == 30
    assert all(
        d["trips"] == d["tokens_in"] == d["tokens_out"] == 0 for d in data["activity"]
    )
    for empty in (
        gen["attempts_per_run"],
        gen["finish_reasons"],
        data["by_model"],
        data["by_prompt_version"],
        data["voting"]["iterations_to_finalize"],
    ):
        assert empty == []
    assert gen["valid_rate"] is None
    assert gen["latency"]["p50_ms"] is None
    assert gen["latency"]["p95_ms"] is None
    assert data["voting"]["avg_participants_per_trip"] is None
    assert data["voting"]["avg_votes_per_trip"] is None
    assert data["sampling"] == {"row_cap": stats.ROW_CAP, "truncated": False}
    assert data["totals"]["cost_usd"] == 0
    assert data["voting"]["cost_per_finalized_trip_usd"] is None
    assert data["pricing"]["unpriced_models"] == []
    assert data["pricing"]["as_of"] == get_settings().AI_PRICES_AS_OF


async def test_aggregates(client, db) -> None:
    user = make_user(db)
    await db.flush()
    t1 = make_trip(db, user, status="FINALIZED", current_iteration=1)
    t2 = make_trip(db, user, status="FINALIZED", current_iteration=3)
    t3 = make_trip(db, user, status="VOTING", current_iteration=1)
    t4 = make_trip(db, user, status="CREATED", current_iteration=0)
    await db.flush()
    parts = [make_participant(db, t3) for _ in range(2)]
    await db.flush()
    db.add(
        Vote(
            participant_id=parts[0].id,
            trip_id=t3.id,
            iteration_number=1,
            rankings=[1, 2],
        )
    )
    # v4: two generations (t1 has two itineraries in one), v3: one, newest first.
    now = datetime.now(UTC)
    make_itinerary(db, t1, 1, prompt_version="v4", created_at=now)
    make_itinerary(db, t1, 1, prompt_version="v4", created_at=now)
    make_itinerary(db, t2, 1, prompt_version="v4", created_at=now)
    make_itinerary(db, t3, 1, prompt_version="v3", created_at=now - timedelta(days=1))
    # Runs of 1, 1, 2 and 3 attempts; the last attempt of each succeeds.
    for trip, n in [(t1, 1), (t2, 1), (t3, 2), (t4, 3)]:
        for a in range(1, n + 1):
            last = a == n
            _log(
                db,
                trip_id=trip.id,
                attempt=a,
                response_valid=last,
                finish_reason="stop" if last else "length",
                token_count_input=10,
                token_count_output=5,
            )
    # Orphan (trip deleted): no attempt number, request failed, other model.
    _log(db, trip_id=None, model_used="m2", finish_reason=None)
    await db.flush()

    data = await _get(client)
    gen = data["generation"]
    assert gen["attempts_per_run"] == [
        {"attempts": 1, "runs": 2},
        {"attempts": 2, "runs": 1},
        {"attempts": 3, "runs": 1},
    ]
    assert (gen["runs"], gen["runs_succeeded"]) == (4, 4)
    assert (gen["attempts"], gen["valid_attempts"], gen["valid_rate"]) == (8, 4, 0.5)
    assert gen["orphaned_attempts"] == 1
    assert gen["finish_reasons"][0] == {"finish_reason": "stop", "attempts": 4}
    assert {f["finish_reason"]: f["attempts"] for f in gen["finish_reasons"]} == {
        "stop": 4,
        "length": 3,
        None: 1,
    }
    assert [
        (m["model"], m["attempts"], m["valid_attempts"]) for m in data["by_model"]
    ] == [
        ("m1", 7, 4),
        ("m2", 1, 0),
    ]
    assert data["by_model"][0]["tokens_in"] == 70
    assert data["totals"]["tokens_in"] == 70
    assert data["totals"]["tokens_out"] == 35

    funnel = {f["status"]: f["trips"] for f in data["funnel"]}
    assert funnel == {
        "CREATED": 1,
        "COLLECTING_PREFERENCES": 0,
        "GENERATING": 0,
        "GENERATION_FAILED": 0,
        "VOTING": 1,
        "FINALIZED": 2,
    }
    assert [f["status"] for f in data["funnel"]][:1] == ["CREATED"]

    versions = {v["prompt_version"]: v for v in data["by_prompt_version"]}
    assert [v["prompt_version"] for v in data["by_prompt_version"]] == [
        "v4",
        "v3",
        None,
    ]
    assert (
        versions["v4"]["successful_generations"],
        versions["v4"]["itineraries"],
    ) == (2, 3)
    assert (
        versions["v3"]["successful_generations"],
        versions["v3"]["itineraries"],
    ) == (1, 1)
    # Logs here carry no prompt_version: all 8 attempts land on the None row.
    assert versions[None]["attempts"] == 8
    assert versions["v4"]["attempts"] == 0 and versions["v4"]["valid_rate"] is None

    voting = data["voting"]
    assert voting["finalized_trips"] == 2
    assert voting["iterations_to_finalize"] == [
        {"iterations": 1, "trips": 1},
        {"iterations": 2, "trips": 0},
        {"iterations": 3, "trips": 1},
    ]
    assert voting["trips_reached_voting"] == 3
    assert voting["avg_votes_per_trip"] == 1 / 3
    assert voting["avg_participants_per_trip"] == 2 / 4
    assert data["totals"]["ai_attempts"] == gen["attempts"]  # (g)


async def test_latency_percentiles_and_histogram(client, db) -> None:
    for ms in range(1000, 11000, 1000):
        _log(db, latency_ms=ms)
    _log(db, latency_ms=None)  # no latency: excluded from percentiles
    await db.flush()
    lat = (await _get(client))["generation"]["latency"]
    assert (lat["p50_ms"], lat["p95_ms"], lat["sample_size"]) == (5000, 10000, 10)
    assert [(b["min_ms"], b["max_ms"], b["attempts"]) for b in lat["histogram"]] == [
        (0, 5000, 4),
        (5000, 10000, 5),
        (10000, 20000, 1),
        (20000, 30000, 0),
        (30000, 60000, 0),
        (60000, 120000, 0),
        (120000, None, 0),
    ]


async def test_latency_single_value(client, db) -> None:
    _log(db, latency_ms=7000)
    await db.flush()
    lat = (await _get(client))["generation"]["latency"]
    assert lat["p50_ms"] == lat["p95_ms"] == 7000


async def test_activity_window(client, db) -> None:
    user = make_user(db)
    await db.flush()
    today = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
    for days_ago in (31, 29, 0):
        make_trip(db, user, created_at=today - timedelta(days=days_ago))
    _log(db, created_at=today, token_count_input=7, token_count_output=3)
    _log(db, created_at=today - timedelta(days=31), token_count_input=99)
    await db.flush()

    days = (await _get(client))["activity"]
    assert len(days) == 30
    assert days[-1]["date"] == today.date().isoformat()
    assert days[0]["date"] == (today - timedelta(days=29)).date().isoformat()
    assert days[0]["trips"] == 1 and days[-1]["trips"] == 1
    assert (days[-1]["tokens_in"], days[-1]["tokens_out"]) == (7, 3)
    assert sum(d["trips"] for d in days) == 2
    assert sum(d["tokens_in"] for d in days) == 7
    assert all(d["trips"] == 0 for d in days[1:-1])


FLASH = "gemini-3.6-flash"


def _cost(tokens_in: int, billable_out: int) -> float:
    price_in, price_out = get_settings().AI_PRICES_USD_PER_1M[FLASH]
    return (tokens_in * price_in + billable_out * price_out) / 1_000_000


async def test_cost_priced_unpriced_and_prefix(client, db) -> None:
    # Thinking tokens: total - input (500) beats token_count_output (200).
    _log(
        db,
        model_used=FLASH,
        token_count_input=1000,
        token_count_output=200,
        token_count_total=1500,
    )
    # No total: falls back to token_count_output.
    _log(db, model_used=FLASH, token_count_input=2000, token_count_output=100)
    # "models/" prefix is stripped before the price lookup; it stays its own row.
    _log(
        db,
        model_used=f"models/{FLASH}",
        token_count_input=1000,
        token_count_output=0,
        token_count_total=1000,
    )
    _log(db, model_used="mystery-1", token_count_input=50, token_count_output=50)
    _log(db, model_used="mystery-1", token_count_input=1, token_count_output=1)
    await db.flush()

    data = await _get(client)
    by_model = {m["model"]: m for m in data["by_model"]}
    assert by_model[FLASH]["cost_usd"] == pytest.approx(_cost(3000, 600))
    assert by_model[f"models/{FLASH}"]["cost_usd"] == pytest.approx(_cost(1000, 0))
    assert by_model["mystery-1"]["cost_usd"] is None
    assert data["totals"]["cost_usd"] == pytest.approx(
        _cost(3000, 600) + _cost(1000, 0)
    )
    assert data["pricing"]["unpriced_models"] == ["mystery-1"]
    assert data["pricing"]["as_of"] == get_settings().AI_PRICES_AS_OF
    assert stats._cost("mystery-1", 1, 1) is None
    assert stats._cost(f"models/{FLASH}", 1_000_000, 0) == pytest.approx(0.75)


async def test_prompt_version_stats(client, db) -> None:
    user = make_user(db)
    await db.flush()
    trip = make_trip(db, user, status="FINALIZED", current_iteration=1)
    await db.flush()
    make_itinerary(db, trip, 1, prompt_version="v4")
    make_itinerary(db, trip, 1, prompt_version="v4")
    make_itinerary(db, trip, 1, prompt_version="v3")
    for attempt, valid, ms, total in [(1, False, 1000, 160), (2, True, 3000, 200)]:
        _log(
            db,
            trip_id=trip.id,
            attempt=attempt,
            model_used=FLASH,
            prompt_version="v4",
            response_valid=valid,
            latency_ms=ms,
            token_count_input=100,
            token_count_output=10,
            token_count_total=total,
        )
    # v3 ran on a model with no price: cost is unknown, tokens still counted.
    _log(
        db,
        trip_id=trip.id,
        attempt=1,
        model_used="mystery-1",
        prompt_version="v3",
        response_valid=True,
        latency_ms=7000,
        token_count_input=10,
        token_count_output=5,
    )
    # Log-only version (every attempt failed, no itineraries).
    _log(db, prompt_version="v5", latency_ms=500, token_count_input=1)
    await db.flush()

    data = await _get(client)
    v = {x["prompt_version"]: x for x in data["by_prompt_version"]}
    assert set(v) == {"v3", "v4", "v5"}
    v4 = v["v4"]
    assert (v4["attempts"], v4["valid_rate"]) == (2, 0.5)
    assert (v4["latency_p50_ms"], v4["latency_p95_ms"]) == (1000, 3000)
    # tokens_in + (total - input) over both attempts, per itinerary.
    assert v4["tokens_per_itinerary"] == (200 + 160) / 2
    assert v4["cost_per_itinerary_usd"] == pytest.approx(_cost(200, 160) / 2)
    v3 = v["v3"]
    assert (v3["attempts"], v3["valid_rate"], v3["latency_p50_ms"]) == (1, 1.0, 7000)
    assert v3["tokens_per_itinerary"] == 15
    assert v3["cost_per_itinerary_usd"] is None
    v5 = v["v5"]
    assert (v5["itineraries"], v5["successful_generations"]) == (0, 0)
    assert (v5["attempts"], v5["valid_rate"], v5["latency_p95_ms"]) == (1, 0.0, 500)
    assert v5["tokens_per_itinerary"] is None
    assert v5["cost_per_itinerary_usd"] is None
    # Newest-first ordering is for versions with itineraries; log-only ones follow.
    assert [x["prompt_version"] for x in data["by_prompt_version"]][-1] == "v5"


async def test_cost_per_finalized_trip(client, db) -> None:
    user = make_user(db)
    await db.flush()
    done = make_trip(db, user, status="FINALIZED", current_iteration=1)
    voting = make_trip(db, user, status="VOTING", current_iteration=1)
    await db.flush()
    for trip, tin, total in [(done, 100, 160), (done, 100, 200), (voting, 9999, 99999)]:
        _log(
            db,
            trip_id=trip.id,
            model_used=FLASH,
            token_count_input=tin,
            token_count_total=total,
        )
    await db.flush()
    cost = (await _get(client))["voting"]["cost_per_finalized_trip_usd"]
    assert cost == pytest.approx(_cost(200, 160))  # voting trip excluded, one trip

    stats._cache = None
    _log(db, trip_id=done.id, model_used="mystery-1", token_count_input=1)
    await db.flush()
    assert (await _get(client))["voting"]["cost_per_finalized_trip_usd"] is None


async def test_cost_per_finalized_trip_none_without_logs(client, db) -> None:
    user = make_user(db)
    await db.flush()
    make_trip(db, user, status="FINALIZED", current_iteration=1)
    await db.flush()
    voting = (await _get(client))["voting"]
    assert voting["finalized_trips"] == 1
    assert voting["cost_per_finalized_trip_usd"] is None


@pytest.fixture
def quality_file(tmp_path, monkeypatch):
    quality = PromptQuality(
        run_date="2026-11-19",
        model="m",
        judge_model="j",
        cases=12,
        versions=[
            PromptQualityVersion(
                prompt_version="v3",
                cases=12,
                judged_cases=11,
                all_checks_pass_rate=0.25,
                checks=[
                    CheckRate(check="time_slots", pass_rate=0.0, cases=12, gating=False)
                ],
                judge=[JudgeScore(criterion="preference_fit", mean=4.0)],
                judge_overall=4.0,
            )
        ],
    )
    path = tmp_path / "results.json"
    path.write_text(quality.model_dump_json())
    monkeypatch.setattr(stats, "PROMPT_QUALITY_PATH", path)
    return path


async def test_prompt_quality_present(client, quality_file) -> None:
    pq = (await _get(client))["prompt_quality"]
    assert pq["cases"] == 12 and pq["versions"][0]["prompt_version"] == "v3"
    assert pq["versions"][0]["checks"][0] == {
        "check": "time_slots",
        "pass_rate": 0.0,
        "cases": 12,
        "gating": False,
    }
    assert pq["versions"][0]["judged_cases"] == 11


async def test_prompt_quality_absent_or_corrupt(client, quality_file) -> None:
    quality_file.unlink()
    assert (await _get(client))["prompt_quality"] is None
    quality_file.write_text("{not json")
    stats.load_prompt_quality.cache_clear()
    stats._cache = None
    assert (await _get(client))["prompt_quality"] is None


async def test_privacy(client, db, quality_file) -> None:
    secrets_ = [
        "S3NT-prompt",
        "S3NT-raw",
        "S3NT-err",
        "S3NT-title",
        "S3NT-dest",
        "S3NT-notes",
        "S3NT-user",
        "S3NT-part",
        "S3NT-iname",
        "S3NT-otitle",
        "S3NT-reason",
        "S3NT-hl",
        "S3NT-day",
        "S3NT-generr",
        "S3NTCODE",
        "S3NT-tok",
        "S3N7",
    ]
    prompt, raw, err, title, dest, notes, uname, pname = secrets_[:8]
    iname, otitle, reason, hl, day, generr, code, tok, pin = secrets_[8:]
    user = make_user(db, full_name=uname)
    await db.flush()
    trip = make_trip(
        db,
        user,
        title=title,
        destination=dest,
        notes=notes,
        generation_error=generr,
        trip_code=code,
    )
    await db.flush()
    db.add(
        Participant(trip_id=trip.id, email="p@x.com", name=pname, pin=pin, token=tok)
    )
    _log(
        db,
        trip_id=trip.id,
        prompt=prompt,
        raw_response=raw,
        error_message=err,
        attempt=1,
        latency_ms=100,
    )
    make_itinerary(
        db,
        trip,
        1,
        prompt_version="v4",
        destination_name=iname,
        option_title=otitle,
        match_reasoning=reason,
        highlights=[hl],
        daily_itinerary=[{"day": 1, "title": day}],
    )
    await db.flush()

    resp = await client.get("/stats")
    assert resp.status_code == 200
    assert resp.json()["prompt_quality"] is not None
    for sentinel in secrets_:
        assert sentinel not in resp.text
    assert "@" not in resp.text
    assert not FORBIDDEN_KEYS & _keys(resp.json())


async def test_ttl_cache_skips_db(client, db, engine) -> None:
    await _get(client)
    seen: list[str] = []

    def _count(_conn, _cur, statement, *_a):
        seen.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", _count)
    try:
        await _get(client)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _count)
    assert seen == []


async def test_request_cap(client, monkeypatch) -> None:
    monkeypatch.setattr(stats, "_limiter", SlidingWindow(1, 60))
    assert (await client.get("/stats")).status_code == 200
    assert (await client.get("/stats")).status_code == 429


async def test_failure_backoff(client, monkeypatch) -> None:
    real = stats._compute
    calls = 0

    async def flaky(db):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("S3NT-boom")
        return await real(db)

    monkeypatch.setattr(stats, "_compute", flaky)
    first = await client.get("/stats")
    assert first.status_code == 503
    assert "S3NT-boom" not in first.text
    assert (await client.get("/stats")).status_code == 503
    assert calls == 1  # backoff window: no recompute

    monkeypatch.setattr(stats, "_failed_until", 0.0)
    assert (await client.get("/stats")).status_code == 200
    assert calls == 2
