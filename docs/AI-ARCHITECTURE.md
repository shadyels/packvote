# AI Architecture — PackVote

## AI Service Layer

- Provider-agnostic: `HuggingFaceProvider` (default) → `GroqProvider` (fallback). Any OpenAI-compatible API can be swapped in.
- Default model: `Qwen2.5-72B-Instruct`
- Free tier constraint (HuggingFace): minimize AI calls, cache results, use exponential backoff.
- All AI responses MUST return validated JSON (Pydantic validation).
- Prompts are versioned in the database (`prompt_templates` table) with basic A/B testing (traffic split, metrics per version).

## Provider Implementation

**`AsyncInferenceClient` for all providers:**
Both `HuggingFaceProvider` and `GroqProvider` use `AsyncInferenceClient` from `huggingface_hub`. Groq exposes an OpenAI-compatible API — same client, different `base_url` and `api_key`. Do not use raw `httpx` for AI inference.

**Provider return type includes provider name:**
`AIProvider.generate_itineraries()` returns `tuple[AIGenerationResponse, str]` where the string is `"huggingface"` or `"groq"`. Required so the generation service can log which provider answered in `AICallLog.provider` and `Itinerary.provider`.

**Retry strategy:**
`AIService.generate_itineraries()` retries HuggingFace up to 3 times with exponential backoff (1s, 2s, 4s). On exhaustion, tries Groq once. If both fail, re-raises the last exception. Never use immediate retries.

**Groq ignores the `model` parameter:**
`GroqProvider` hardcodes `GROQ_MODEL = "llama-3.3-70b-versatile"` and ignores the `model` argument (which is always a HF model ID). This is intentional.

## JSON Extraction

**Always use `extract_json()` from `services/ai/json_utils.py` — never bare `json.loads()`.**

Open-source models wrap JSON in markdown fences or add preamble even with `response_format={"type": "json_object"}`. `extract_json(raw)` tries three strategies:
1. Direct parse
2. Strip markdown fences
3. Brace-extraction: `raw[raw.find("{"):raw.rfind("}")+1]`

On total failure raises `AIParseError` with the raw text attached. A `pydantic.ValidationError` is wrapped in `AIParseError` so raw text always propagates to the caller.

**Raw response logging:**
`ai_call_logs.raw_response` (Text column, nullable) stores the raw AI response only when parsing/validation fails. Always `None` on success to avoid table bloat.

## Prompt Templates

**Format — `[SYSTEM]`/`[USER]` delimiter:**
Templates are stored as a single string in `prompt_templates` using `[SYSTEM]\n...\n[USER]\n...`. Providers split this at call time into the two-message array. Keeps a full prompt in one DB row for versioning/A/B testing.

**Seeded at runtime, not via migration:**
`_upsert_prompt_template()` in `services/generation.py` does SELECT then INSERT if missing on every generation run. Idempotent. Do NOT create an Alembic data migration for this.

## JSON Serialization of Itinerary Fields

`Itinerary.daily_itinerary_json` and `Itinerary.highlights` are `Text` columns storing JSON strings (not native JSON columns) for SQLite/PostgreSQL portability. Always serialize with:
- `json.dumps([day.model_dump() for day in ...])`
- Use `.model_dump()` not `dict()` for nested Pydantic models.

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
- `AIParseError` → "The AI returned an invalid response. This is usually temporary — try again."
- `ValueError` (wrong option count) → "The AI generated the wrong number of itinerary options..."
- `httpx.HTTPStatusError` 429 → rate limit message
- `httpx.HTTPStatusError` 5xx → service unavailable message
- `httpx.ConnectError` / `TimeoutError` → connection error message
- Anything else → generic "Something went wrong" message

On next successful `POST /trips/{id}/generate`, both `status` and `generation_error` are cleared before setting `GENERATING`. `GENERATION_FAILED` is an allowed source status for `trigger_generation` (alongside `CREATED` and `COLLECTING_PREFERENCES`).

**Idempotency guard:**
At the top of `run_generation`, re-read the trip and exit early if `trip.status != "GENERATING"`. Prevents double-run from race between manual and auto-trigger.

**Auto-trigger guard in `submit_preferences`:**
Only auto-trigger if all participants submitted AND `trip.status == "COLLECTING_PREFERENCES"`. Prevents double-trigger when creator already hit `POST /trips/{id}/generate`.

## AI Call Logging

`ai_call_logs` table records each generation: prompt version, model, provider, latency, token counts, response validity. This is part of the AI pipeline — the ops-level dashboard is Phase 3 (Grafana, admin-only).
