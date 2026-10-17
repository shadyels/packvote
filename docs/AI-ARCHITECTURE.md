# AI Architecture — PackVote

## AI Service Layer

- Single provider class: `OpenAICompatProvider` (`services/ai/openai_compat.py`) using the `openai` SDK against **any** OpenAI-compatible chat-completions endpoint. There is no provider base class.
- Default: **Google Gemini free tier** — `gemini-3.6-flash` via `https://generativelanguage.googleapis.com/v1beta/openai/` (`gemini-2.5-flash` was retired for new API keys — 404 "no longer available to new users")
- All AI responses MUST return validated JSON (Pydantic validation).
- The prompt is a code constant (`ITINERARY_PROMPT_V3` in `services/generation.py`) with `PROMPT_VERSION = "v3"`, recorded on each `Itinerary.prompt_version`. There is no prompt table and no A/B split.

## Provider Implementation

**The provider is configuration, not code.**
Gemini, OpenRouter, Mistral, Groq and Cerebras all expose the same OpenAI chat-completions shape. Switching providers means changing these settings in `app/core/config.py` (all env-overridable) — never writing a new provider class:

| Setting | Purpose |
|---|---|
| `AI_API_KEY` | Provider API key |
| `AI_BASE_URL` | Endpoint root |
| `AI_PROVIDER_NAME` | Recorded in `AICallLog.provider` / `Itinerary.provider` |
| `DEFAULT_AI_MODEL` | Model id |
| `AI_EXTRA_BODY` | Vendor-specific knobs (see below) |

This replaced a history of provider-specific classes (HuggingFace → Groq → Cerebras), each of which required a full rewrite when a free tier disappeared.

**`AsyncOpenAI` from the `openai` SDK.** Do not use raw `httpx`, `huggingface_hub`, or a vendor SDK for AI inference. A client is built per call (`_make_client`, `timeout=180` seconds to accommodate slow cold-starts, `max_retries=0`) and closed with `async with client`, so no connection pool outlives the call.

**Thinking/reasoning suppression is mandatory — and it is a token-budget issue, not a formatting one.**
Gemini draws thinking tokens from the *same* `max_tokens` budget as the response. With `MAX_OUTPUT_TOKENS = 16_384` (`services/ai/openai_compat.py`) and `SAFE_OUTPUT_TOKENS = 15_000` of itinerary JSON, an enabled thinking pass risks silently truncating the JSON mid-array, surfacing as `finish_reason == "length"` rather than an error. `AI_EXTRA_BODY` defaults to:

```json
{"extra_body": {"google": {"thinking_config": {"thinking_level": "minimal"}}}}
```

Double-nested on purpose: the OpenAI SDK's `extra_body=` kwarg merges its keys into the *top level* of the outgoing request body, but Gemini's OpenAI-compat endpoint expects a literal `extra_body` field there. A single-level `{"google": ...}` produces `400 Unknown name "google"`.

Gemini 3.x models (including the default `gemini-3.6-flash`) replaced the old `thinking_budget` integer with the string enum `thinking_level` — `minimal`/`low`/`medium`/`high`, default `medium` on 3.6 Flash. Sending `thinking_budget` on a 3.x model 400s (they can't be combined, and 3.6 rejects `thinking_budget` outright). `minimal` is the lowest level Flash models support, but per Google's own docs it is **not a guarantee** thinking is off — unlike `thinking_budget=0` on Gemini 2.5, which was absolute. Watch `finish_reason=length` warnings (logged in `openai_compat.py`) as the signal that this non-guarantee is manifesting; if it starts happening regularly, the mitigation is a real token-budget increase in `MAX_OUTPUT_TOKENS`/`_limits.py`, not a smaller `thinking_level`. Set `AI_EXTRA_BODY={}` for providers that reject unknown request fields.

`DEFAULT_REASONING_EFFORT` defaults to `"none"`, which **omits the `reasoning_effort` param entirely** — Gemini rejects `reasoning_effort` and `thinking_config` supplied together. Any other value is forwarded as the standard OpenAI `reasoning_effort`.

**Provider name comes from config:**
`OpenAICompatProvider.generate_itineraries()` returns `AIGenerationResponse`. The provider name is `AI_PROVIDER_NAME` (default `"gemini"`), written to `AICallLog.provider`; the winning attempt's value is copied to `Itinerary.provider`.

**Retry strategy:**
`AIService.generate_itineraries()` retries up to 3 times. On exhaustion, re-raises the last exception. No fallback provider. Never use immediate retries. The openai SDK's own retries are disabled (`max_retries=0` in `_make_client`), so each `AIService` attempt is exactly one HTTP request — and one `ai_call_logs` row.

Two delay schedules in `services/ai/service.py`:
- `RETRY_DELAYS = [1.0, 2.0, 4.0]` — transient errors (parse failures, timeouts, 5xx)
- `RATE_LIMIT_DELAYS = [30.0, 60.0, 90.0]` — `openai.RateLimitError` (HTTP 429)

The long backoff for 429s is intentional: short delays (1/2/4s) were exhausted before upstream traffic spikes resolved, causing live generation to fail after retrying too quickly.

**`AIInputError` and `LocalRateLimitError` fast-fail (no retry):**
When the AI returns a structured error envelope instead of itineraries (bad destination, contradictory constraints), the provider raises `AIInputError` (a subclass of `AIParseError`). `AIService` re-raises it immediately — retrying bad input won't help. `AIInputError` carries `ai_message`, `suggestion`, and `field` attributes so `_humanize_error()` can surface them verbatim.

A wrong option count raises `AIOptionCountError` (also an `AIParseError` subclass, so it *is* retried). It replaces the old string matching on the error message.

`LocalRateLimitError` (from `services/ai/rate_limiter.py`) is also re-raised without retry — the in-process gate rejected the request, so retrying within the same 60s window would hit the same gate.

## In-Process Rate Limiter

`services/ai/rate_limiter.py` provides a process-level guard that rejects requests **before** the network call. Single shared API key means all users share free-tier ceilings; this prevents wasting time on requests that would 429.

**`GlobalRateLimiter` (singleton via `get_limiter()`):**
Enforces limits across three time windows via a single deque (entries evicted at 24h+). Constants are calibrated against **Gemini's free tier** (~10 RPM / 250K TPM / ~1.5K RPD) and set deliberately *under* the published ceilings so this gate trips before Google's:
- **Request limits:** 8/min (rpm), 400/hour (rph), 1,200/day (rpd)
- **Token limits:** 200,000/min (tpm), 2,000,000/hour (tph), 4,000,000/day (tpd)
- **Context length gate:** immediate reject if `estimated_tokens > 128_000`

Gemini publishes no hourly/daily *token* cap, so `MAX_TPH`/`MAX_TPD` are derived from RPD × a generous per-call budget. `MAX_CONTEXT_TOKENS` is **not** the model's context window (Gemini accepts 1M) — it is a runaway-input guard.

**Re-tune these whenever `AI_BASE_URL` changes**, and confirm real numbers in the provider's console — Gemini's public docs defer to AI Studio. `tests/unit/test_rate_limiter.py` derives its fixtures arithmetically from these constants, so re-tuning does not require editing tests.

All six limits checked on every `reserve()` call. Single deque design: `commit()` patches one `(timestamp, tokens)` entry; all window sums computed by filtering that deque at query time. No separate per-window deques.

**Estimate → commit pattern:**
Token cost is unknown before the call, so `reserve(estimated_tokens)` places an optimistic entry in the deque. After the call, `commit(reservation, actual_tokens)` replaces the estimate with actual `completion.usage.total_tokens`. On exception, `commit` is called with the estimate to avoid a leaked slot.

```python
reservation = await limiter.reserve(estimated_tokens)  # async; raises LocalRateLimitError
try:
    completion = await client.chat.completions.create(...)
except Exception:
    limiter.commit(reservation, estimated_tokens)  # sync
    raise
limiter.commit(reservation, completion.usage.total_tokens)
```

**`LocalRateLimitError`** carries `kind` (`"rpm"` | `"rph"` | `"rpd"` | `"tpm"` | `"tph"` | `"tpd"` | `"context_length"`) and `retry_after_seconds`. `_humanize_error()` surfaces it as:
- `context_length` → "The trip preferences are too long to process. Try reducing the number of participants or shortening preference details."
- `rpm` / `rph` / `rpd` / `tpm` / `tph` / `tpd` → "The AI service is busy. Please try again in N seconds." (`_humanize_wait` reports minutes or hours for longer waits; all windows map to the same user message)

## JSON Extraction

**Always use `extract_json()` from `services/ai/json_utils.py` — never bare `json.loads()`.**

**Keep `response_format={"type": "json_object"}` — do NOT upgrade to `json_schema`.**
Gemini supports strict schema-enforced output, and it is tempting to enforce `AIGenerationResponse` and delete the extraction fallbacks. Don't: a strict schema makes the `{"error": {...}}` envelope below unrepresentable, and `AIInputError` / `_humanize_error` are built on it.

Models wrap JSON in markdown fences or add preamble even with `response_format={"type": "json_object"}`. `extract_json(raw)` tries three strategies:
1. Direct parse
2. Strip markdown fences
3. Brace-extraction: `raw[raw.find("{"):raw.rfind("}")+1]`

On total failure raises `AIParseError` with the raw text attached. A `pydantic.ValidationError` is wrapped in `AIParseError` so raw text always propagates to the caller.

**Error envelope detection (check before schema validation):**
After `extract_json()` returns a dict, the provider checks for an `"error"` key before attempting `AIGenerationResponse.model_validate()`. If present, it raises `AIInputError` immediately:
```python
if "error" in data and isinstance(data["error"], dict):
    err = data["error"]
    raise AIInputError(message=err.get("message", "..."), suggestion=err.get("suggestion", ""), field=err.get("field", "general"))
```

**Raw response logging:**
`ai_call_logs.raw_response` stores the raw AI output for every attempt that got a response (success or parse failure); `None` only when the request itself failed. See [AI Call Logging](#ai-call-logging).

## Input Sanitization and Prompt Isolation

### Sanitization before injection
All user-controlled text fields injected into AI prompts **must** be passed through `sanitize_text()` from `app.schemas._sanitize` before use. This strips control characters, zero-width Unicode, and normalises whitespace — preventing structural manipulation via invisible characters.

```python
from app.schemas._sanitize import sanitize_text
clean = sanitize_text(user_value)
```

### Delimiter isolation
Every user-controlled value injected into `ITINERARY_PROMPT_V3` must be wrapped in structural delimiters so the model treats it as data, not instructions:

```
<<<USER DATA>>>{value}<<<END USER DATA>>>
```

Applied in `_render_prompt` (trip title, destination) and `_build_preferences_block` (interests, activity_tags). `sanitize_text()` also strips runs of three or more `<` or `>`, so user text cannot close the block. This is not a security absolute — it reduces the attack surface without adding latency or cost.

Do NOT add phrase-blacklisting (e.g. filtering "ignore previous instructions"). Structural isolation is the correct approach.

### Duration backstop
`_compute_trip_duration` (the single chokepoint for all three duration paths) clamps its result to `max_trip_days(trip.num_options)` from `app.schemas._limits`. This prevents AI output truncation caused by the fixed `MAX_OUTPUT_TOKENS = 16_384` budget in `services/ai/openai_compat.py`.

Formula: `floor((15000 - num_options×250) / (num_options×360))` — n=2→20d, n=3→13d, n=4→9d, n=5→7d. Constants in `_limits.py` are calibration estimates; lock them from real measured completion tokens.

If a real generation is measured and constants change, update **both** `backend/app/schemas/_limits.py` and `frontend/src/lib/validation.ts` (the JS mirror used for frontend date-range validation).

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
The prompt is one string using `[SYSTEM]\n...\n[USER]\n...`. `_split_prompt()` in `openai_compat.py` splits it at call time into the two-message array.

**Versioning:**
`PROMPT_VERSION` (`services/generation.py`) is written to `Itinerary.prompt_version` for every option. Bump it when `ITINERARY_PROMPT_V3` changes. There is no database table and no seeding migration.

## JSON Columns for Structured Fields

`Itinerary.daily_itinerary` (`list`), `Itinerary.highlights` (`list[str]`), `Preference.activity_tags` (`list[str] | None`), and `Vote.rankings` (`list[int]`) are stored with the shared `JSONType` (`app/db/base.py`). SQLAlchemy serializes/deserializes automatically — no `json.dumps`/`json.loads` at call sites.

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

**Claim the run with `start_generation()` before scheduling the task:**
```python
if not await start_generation(db, trip_id, allowed):  # conditional UPDATE + commit
    raise HTTPException(status_code=409, ...)
background_tasks.add_task(generation.run_generation, trip_id, session_factory)
```
`start_generation()` runs `UPDATE trips SET status='GENERATING', generation_error=NULL WHERE id=? AND status IN (allowed)` and commits. Only the caller that sees `rowcount == 1` schedules the run; a losing concurrent caller gets False and does nothing. Allowed sources:
- `POST /trips/{id}/generate`: `CREATED`, `COLLECTING_PREFERENCES`, `GENERATION_FAILED`
- auto-trigger when the last participant submits preferences: `CREATED`, `COLLECTING_PREFERENCES`
- `POST /trips/{id}/new-iteration`: `VOTING`

The commit happens before the task is scheduled, so clients polling `GET /trips/{id}` immediately see `GENERATING`.

**Three phases, no DB connection during the AI call** (`run_generation`):
1. `_read_phase` — session 1 snapshots trip, preferences and participant count into a plain `_GenerationJob`. Returns nothing unless the trip is `GENERATING`.
2. `AIService.generate_itineraries()` — no session is open.
3. `_write_phase` — session 2 runs a CAS `UPDATE trips SET current_iteration=…, status='VOTING' WHERE id=? AND status='GENERATING'`. If the CAS loses (e.g. startup recovery already failed the trip), the options are discarded and only the call logs are written. Otherwise `Itinerary` rows are added. `model_used`, `provider` and `generation_latency_ms` come from the winning (last `response_valid`) `AICallLog`, falling back to config if there is none.

**On failure → `GENERATION_FAILED`** (not `COLLECTING_PREFERENCES`):
`_reset_trip_status()` sets `trip.status = "GENERATION_FAILED"` and stores a user-friendly message in `trip.generation_error`, but only while the trip is still `GENERATING`. Call logs are written first (`_write_call_logs`). Raw exceptions go to server logs and `ai_call_logs.error_message` only — never shown to users.

**Startup recovery:** `recover_stuck_generations()` runs from the FastAPI lifespan (`app/main.py`) and marks every trip left in `GENERATING` as `GENERATION_FAILED` with "Generation was interrupted by a server restart. Please try again." It assumes a single process; see `docs/DEPLOYMENT.md`.

User-facing messages from `_humanize_error(exc)` in `services/generation.py`:
- `AIInputError` → AI's own `ai_message` verbatim, with `suggestion` appended as "Tip: …" if present. Always checked first (before the `AIParseError` branch, since `AIInputError` is a subclass).
- `AIParseError` → "The AI returned an invalid response. This is usually temporary — try again."
- `AIOptionCountError` → "The AI generated the wrong number of itinerary options..."
- `LocalRateLimitError` (`context_length`) → preferences too long message
- `LocalRateLimitError` (`rpm`/`tpm`) → "The AI service is busy. Please try again in N seconds."
- `openai.RateLimitError` → rate limit message
- `openai.APIStatusError` (5xx) → service unavailable message
- `openai.APIConnectionError` / `TimeoutError` → connection error message

`openai.RateLimitError` subclasses `APIStatusError`, so the 429 branch must stay **above** the 5xx branch.
- Anything else → generic "Something went wrong" message

`start_generation()` clears `generation_error` when it sets `GENERATING`. `GENERATION_FAILED` is an allowed source status for `POST /trips/{id}/generate` (alongside `CREATED` and `COLLECTING_PREFERENCES`).

**Idempotency guard:**
`_read_phase` re-reads the trip and exits early if `trip.status != GENERATING`. Together with the `start_generation()` claim, this prevents a double run from a race between manual and auto-trigger.

**Auto-trigger in `submit_preferences`:**
When all participants have submitted, `_maybe_trigger_generation` calls `start_generation()` with `CREATED` / `COLLECTING_PREFERENCES`. A creator who already hit `POST /trips/{id}/generate` leaves the trip in `GENERATING`, so the auto-trigger loses the claim and does nothing.

## AI Call Logging

**One row per network attempt**, not per generation. A generation that succeeds on its second try writes two rows; one that exhausts retries writes three.

- **Provider (`openai_compat.py`)** appends a transient `AICallLog` to the `calls` list threaded `generation.py → AIService → provider`, *after* `limiter.reserve()` succeeds. Local-limiter rejections made no network call, so they are **not recorded**. It fills: `provider`, `model_used` (as reported by the API in `completion.model`, not the configured name), `prompt` (rendered), `raw_response`, `latency_ms` (the `create()` call only — excludes retry backoff), `token_count_input`/`_output`/`_total` from `completion.usage`, `finish_reason`, `response_valid`, `error_message`, `created_at` (per attempt).
- **Orchestrator (`generation.py` `_add_call_logs`)** stamps the context only it knows — `trip_id`, `iteration_number`, `attempt` (1-based) — adds the rows to the session, and emits one INFO line per attempt:
  `ai_call trip=… iteration=… attempt=… provider=… model=… latency_ms=… tokens_in=… tokens_out=… tokens_total=… finish=… valid=… error=…`
  Rows are committed on both the success and the failure path.
- **Retention:** rows outlive their trip. `ai_call_logs.trip_id` is `ON DELETE SET NULL`, so `delete_trip` keeps them. The stored `prompt` contains participants' free-text preferences, so that text is retained after the trip is gone.
- **Stdout:** `app/main.py` attaches a stdout handler to the `app` logger at INFO (not `basicConfig` — a root handler would double SQLAlchemy echo output and surface httpx's per-request INFO lines).

The ops-level dashboard is Phase 3 (Grafana, admin-only).

## Evaluation Dataset

`ai_call_logs` is the system of record for comparing models, prompts and configs over time: append-only, one row per attempt. It has no prompt-version column; the prompt version lives on `itineraries.prompt_version`. Join to `itineraries` / `votes` / `trips` via `(trip_id, iteration_number)` while the trip exists.

**Grouping attempts into runs:** order by `id`; `attempt` resets to `1` at the start of each generation. **Thinking tokens** are derived: `token_count_total − token_count_input − token_count_output` (non-zero means `thinking_level: minimal` still spent some).

**Usage ideas — *not built*, later phases:**
1. **Live scorecards (SQL only).** Per `model_used` × `itineraries.prompt_version`: p50/p95 `latency_ms` on valid attempts; avg tokens in/out/total/thinking; validity rate; `finish_reason='length'` rate; attempts per generation.
2. **Outcome labels from voting.** Label each `(trip_id, iteration_number)` *accepted* (trip FINALIZED with a winner from that iteration) or *rejected* (`trigger_new_iteration` moved past it). Ranked-choice results rank options within one call (option-level quality, position bias) but don't compare models head-to-head. Labels must be snapshotted before trip deletion nulls `trip_id`.
3. **Golden set + replay harness.** Export ~30 diverse valid prompts as JSONL `{prompt, reference_output, model, metrics, label}`; replay through `OpenAICompatProvider` with a `calls` list (capture works unchanged); score validity, option count, latency, tokens, and pairwise LLM-as-judge vs. the reference. Small batches — the free-tier limiter applies.
4. **Regression gate.** Replay the golden set before changing `DEFAULT_AI_MODEL` or `AI_EXTRA_BODY`; compare scorecards.
5. **Prompt A/B.** Not built: there is no traffic split. `Itinerary.prompt_version` records which prompt produced each option, so per-version comparisons are possible later.
