# AI Architecture — PackVote

## AI Service Layer

- Single provider: `CerebrasProvider` using `cerebras-cloud-sdk`. Interface is `AIProvider` (abstract); provider is swappable.
- Default model: `qwen-3-235b-a22b-instruct-2507` (Qwen-3 Instruct — non-thinking checkpoint)
- All AI responses MUST return validated JSON (Pydantic validation).
- Prompts are versioned in the database (`prompt_templates` table) with basic A/B testing (traffic split, metrics per version).

## Provider Implementation

**`AsyncCerebras` from `cerebras-cloud-sdk`:**
`CerebrasProvider` uses `AsyncCerebras` from `cerebras-cloud-sdk`. Do not use raw `httpx` or `huggingface_hub` for AI inference.
- Client is initialized with `timeout=180` seconds to accommodate slow model cold-starts.
- Qwen-3 Instruct is a non-thinking checkpoint. `disable_reasoning` is GLM-family-specific and must not be passed.

**Provider return type includes provider name:**
`AIProvider.generate_itineraries()` returns `tuple[AIGenerationResponse, str]` where the string is `"cerebras"`. Required so the generation service can log which provider answered in `AICallLog.provider` and `Itinerary.provider`.

**Retry strategy:**
`AIService.generate_itineraries()` retries the Cerebras provider up to 3 times. On exhaustion, re-raises the last exception. No fallback provider. Never use immediate retries.

Two delay schedules in `services/ai/service.py`:
- `RETRY_DELAYS = [1.0, 2.0, 4.0]` — transient errors (parse failures, timeouts, 5xx)
- `RATE_LIMIT_DELAYS = [30.0, 60.0, 90.0]` — `CerebrasRateLimitError` (HTTP 429 / `queue_exceeded`)

The long backoff for 429s is intentional: short delays (1/2/4s) were exhausted before Cerebras traffic spikes resolved, causing live generation to fail after retrying too quickly.

**`AIInputError` fast-fail (no retry):**
When the AI returns a structured error envelope instead of itineraries (bad destination, contradictory constraints), providers raise `AIInputError` (a subclass of `AIParseError`). `AIService` re-raises it immediately — retrying bad input won't help. `AIInputError` carries `ai_message`, `suggestion`, and `field` attributes so `_humanize_error()` can surface them verbatim.

## JSON Extraction

**Always use `extract_json()` from `services/ai/json_utils.py` — never bare `json.loads()`.**

Open-source models wrap JSON in markdown fences or add preamble even with `response_format={"type": "json_object"}`. `extract_json(raw)` tries three strategies:
1. Direct parse
2. Strip markdown fences
3. Brace-extraction: `raw[raw.find("{"):raw.rfind("}")+1]`

On total failure raises `AIParseError` with the raw text attached. A `pydantic.ValidationError` is wrapped in `AIParseError` so raw text always propagates to the caller.

**Error envelope detection (check before schema validation):**
After `extract_json()` returns a dict, both providers check for `"error"` key before attempting `AIGenerationResponse.model_validate()`. If present, they raise `AIInputError` immediately:
```python
if "error" in data and isinstance(data["error"], dict):
    err = data["error"]
    raise AIInputError(message=err.get("message", "..."), suggestion=err.get("suggestion", ""), field=err.get("field", "general"))
```

**Raw response logging:**
`ai_call_logs.raw_response` (Text column, nullable) stores the raw AI response only when parsing/validation fails. Always `None` on success to avoid table bloat.

## Prompt Style Contract

When writing or updating a prompt version, maintain these constraints — they exist to prevent bland, AI-sounding output:

- **Activity titles:** 2-3 word noun-phrases naming a specific real place, dish, or activity. No verbs, no filler. e.g. `"Tsukiji tuna auction"`, `"Fushimi Inari sunrise"`.
- **Activity descriptions:** 2-3 sentences. Sensory/atmospheric opener, then 1-2 practical specifics (location, timing, cost hint, insider tip). Voice: local friend texting a recommendation — casual, opinionated, useful. No guidebook tone.
- **Day titles:** Same compact noun-phrase style as activity titles.
- **`option_title`:** A creative 3-5 word thematic name capturing the trip's personality. Must NOT contain or repeat the destination name. e.g. `"Coastal Culture Crawl"`, `"Ramen, Rails & Rooftops"`, `"Old Town Budget Blitz"`. This is the primary heading shown to users; `destination_name` is demoted to a subtitle.
- **Specificity ratio:** Exactly 4 activities per day. 3 must name a specific venue/dish/experience. 1 must be an unstructured neighborhood exploration — no fixed destination, but still written with full descriptive depth (area vibe, what to look for, an orienting landmark).
- **Banned patterns:** em dashes (—), "nestled", "vibrant", "bustling", "hidden gem", "a testament to", "boasts", "delve", "tapestry", "unwind", "indulge", "immerse yourself", "whether you're", "from X to Y" openers, "offers a unique".

The current prompt (`ITINERARY_PROMPT_V3`) embeds a full-option Barcelona example (not just a single day) so the model pattern-matches the complete schema including `option_title`, adds inline `REQUIRED` annotations on schema fields, and promotes `option_title` to Rule #1 to prevent the field being silently omitted. It also includes an ERROR REPORTING section so the AI can self-report invalid input. `ITINERARY_PROMPT_V1` and `ITINERARY_PROMPT_V2` have been retired. Any future version should preserve the full-option example, the REQUIRED markers, and the error envelope instructions.

## Prompt Templates

**Format — `[SYSTEM]`/`[USER]` delimiter:**
Templates are stored as a single string in `prompt_templates` using `[SYSTEM]\n...\n[USER]\n...`. Providers split this at call time into the two-message array. Keeps a full prompt in one DB row for versioning/A/B testing.

**Seeded at runtime, not via migration:**
`_upsert_prompt_template()` in `services/generation.py` does SELECT then INSERT if missing on every generation run. Idempotent. Do NOT create an Alembic data migration for this.

## JSON Columns for Structured Fields

`Itinerary.daily_itinerary` (`list`), `Itinerary.highlights` (`list[str]`), `Preference.activity_tags` (`list[str] | None`), `Vote.rankings` (`list[int]`), and `VoteRound.results` (`dict`) are native `JSON` columns. SQLAlchemy serializes/deserializes automatically — no `json.dumps`/`json.loads` at call sites.

When assigning from Pydantic models, use `.model_dump()` to produce plain dicts/lists before storing:
- `[day.model_dump() for day in daily_itinerary]`

## Background Tasks and Session Isolation

**NEVER pass a request-scoped `AsyncSession` to a `BackgroundTask`.** FastAPI closes the session when the response is sent.

**Pattern: pass `session_factory`, not `session`:**
```python
# Route handler
background_tasks.add_task(run_generation, trip_id, session_factory)

# Background task
async def run_generation(trip_id: int, session_factory: async_sessionmaker) -> None:
    async with session_factory() as db:   # fresh session
        ...
```

`get_session_factory()` in `app/core/dependencies.py` re-exports the singleton from `app/db/session.py`.

**Failure recovery:** On failure, the first session rolls back automatically. Open a second `async with session_factory() as db` to reset trip status — never reuse the failed session.

**`AIService` is constructed inside the background task** with `AIService.from_settings()`. Do not inject it as a FastAPI dependency.

## Generation Status Transitions

**Commit `GENERATING` before scheduling the task:**
```python
trip.status = "GENERATING"
await db.commit()
background_tasks.add_task(run_generation, ...)
return {"status": "accepted"}
```
Ensures clients polling `GET /trips/{id}` immediately see `GENERATING`.

**On failure → `GENERATION_FAILED`** (not `COLLECTING_PREFERENCES`):
`_reset_trip_status()` sets `trip.status = "GENERATION_FAILED"` and stores a user-friendly message in `trip.generation_error`. Raw exceptions go to server logs and `ai_call_logs.error_message` only — never shown to users.

User-facing messages from `_humanize_error(exc)` in `services/generation.py`:
- `AIInputError` → AI's own `ai_message` verbatim, with `suggestion` appended as "Tip: …" if present. Always checked first (before the `AIParseError` branch, since `AIInputError` is a subclass).
- `AIParseError` → "The AI returned an invalid response. This is usually temporary — try again."
- `ValueError` (wrong option count) → "The AI generated the wrong number of itinerary options..."
- `CerebrasRateLimitError` → rate limit message
- `CerebrasAPIStatusError` (5xx) → service unavailable message
- `CerebrasConnectionError` / `TimeoutError` → connection error message
- Anything else → generic "Something went wrong" message

On next successful `POST /trips/{id}/generate`, both `status` and `generation_error` are cleared before setting `GENERATING`. `GENERATION_FAILED` is an allowed source status for `trigger_generation` (alongside `CREATED` and `COLLECTING_PREFERENCES`).

**Idempotency guard:**
At the top of `run_generation`, re-read the trip and exit early if `trip.status != "GENERATING"`. Prevents double-run from race between manual and auto-trigger.

**Auto-trigger guard in `submit_preferences`:**
Only auto-trigger if all participants submitted AND `trip.status == "COLLECTING_PREFERENCES"`. Prevents double-trigger when creator already hit `POST /trips/{id}/generate`.

## AI Call Logging

`ai_call_logs` table records each generation: prompt version, model, provider, latency, token counts, response validity. This is part of the AI pipeline — the ops-level dashboard is Phase 3 (Grafana, admin-only).
