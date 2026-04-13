# AI Generation Error Handling & Destination Input Improvement

**Date:** 2026-04-13
**Branch:** fix/ai-error-handling
**Status:** Approved

## Context

AI itinerary generation occasionally fails with silent or generic errors. When users type a free-text destination that the AI can't interpret — misspellings, vague phrases like "somewhere beachy", fictional places — the model either returns unparseable JSON, produces nonsensical output, or errors out with a generic "invalid response" message. This creates trial-and-error retries with no guidance on what to fix.

The goal is to surface actionable, AI-generated error messages when generation fails due to bad input, and add light frontend hints to nudge users toward valid destination input.

## Approach

Prompt-level error envelope + `AIInputError` fast-fail path.

The AI prompt is updated to include an alternative response path: when the model detects problematic input (unrecognizable destination, contradictory constraints), it returns a structured error JSON instead of itineraries. The backend detects this error envelope, raises a specialized exception that skips retries, and surfaces the AI's user-friendly message via `trip.generation_error`.

## Design

### 1. New Exception: `AIInputError`

**File:** `backend/app/services/ai/json_utils.py`

Add a subclass of `AIParseError` to represent AI-reported input validation failures:

```python
class AIInputError(AIParseError):
    """Raised when the AI reports the input is invalid (bad destination, etc.)."""
    def __init__(self, message: str, suggestion: str, field: str) -> None:
        super().__init__(message)
        self.ai_message = message
        self.suggestion = suggestion
        self.field = field  # "destination" | "dates" | "budget" | "general"
```

### 2. Prompt v2 with Error Envelope

**File:** `backend/app/services/generation.py`

Add `ITINERARY_PROMPT_V2` — identical to v1 except the `[SYSTEM]` block gains a new section before the closing Rules:

```
ERROR REPORTING:
If you cannot fulfill the request because:
- The destination is not a real, recognizable place
- The constraints are contradictory or impossible (e.g. end date before start date)
- The input is too vague to generate meaningful itineraries

Do NOT return the options array. Instead return ONLY this JSON:
{
  "error": {
    "message": "<user-friendly sentence explaining what's wrong>",
    "suggestion": "<specific actionable fix, e.g. try 'Cancun, Mexico' or 'Kyoto, Japan'>",
    "field": "<one of: destination | dates | budget | general>"
  }
}
```

`_upsert_prompt_template()` is updated to seed v2 as active and deactivate v1.

### 3. Error Envelope Detection in Providers

**Files:** `backend/app/services/ai/huggingface.py`, `backend/app/services/ai/groq.py`

After `extract_json()` returns a dict, check for the error envelope **before** attempting `AIGenerationResponse.model_validate()`:

```python
data = extract_json(raw_text)

# Check for AI-reported input error before schema validation
if "error" in data and isinstance(data["error"], dict):
    err = data["error"]
    raise AIInputError(
        message=err.get("message", "The AI could not process this request."),
        suggestion=err.get("suggestion", ""),
        field=err.get("field", "general"),
    )
```

### 4. Fast-Fail on `AIInputError` in `AIService`

**File:** `backend/app/services/ai/service.py`

`AIInputError` should **not** be retried — retrying with the same bad input won't help. In `generate_itineraries()`, re-raise `AIInputError` immediately instead of entering the retry loop:

```python
try:
    return await self.primary.generate_itineraries(...)
except AIInputError:
    raise  # don't retry — bad input won't improve with retries
except Exception as exc:
    last_exc = exc
    # ... existing retry logic
```

Same guard applies before the Groq fallback call.

### 5. `_humanize_error()` Update

**File:** `backend/app/services/generation.py`

Add a case for `AIInputError` at the top of the function (before other cases):

```python
if isinstance(exc, AIInputError):
    msg = exc.ai_message
    if exc.suggestion:
        msg = f"{msg} Tip: {exc.suggestion}"
    return msg
```

This surfaces the AI's own message verbatim (e.g. "I couldn't find a real destination matching 'warm beach vibes'. Tip: Try a specific city or region, e.g. 'Cancun, Mexico' or 'Algarve, Portugal'.").

### 6. Frontend: Destination Field Hints

**File:** `frontend/src/components/CreateTripDialog.tsx`

Two minimal changes to the destination `<Input>`:
- Add `maxLength={100}`
- Add helper text below the input: `<p className="text-xs text-black/40">City, region, or country name</p>`

No other frontend changes needed — the existing `GENERATION_FAILED` error banner in `TripOverviewSection.tsx` already renders `trip.generation_error` and includes the "Edit Trip" button.

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/ai/json_utils.py` | Add `AIInputError` subclass |
| `backend/app/services/generation.py` | Add `ITINERARY_PROMPT_V2`, update `_upsert_prompt_template()`, update `_humanize_error()` |
| `backend/app/services/ai/huggingface.py` | Add error envelope detection before schema validation |
| `backend/app/services/ai/groq.py` | Same error envelope detection |
| `backend/app/services/ai/service.py` | Skip retries on `AIInputError` |
| `frontend/src/components/CreateTripDialog.tsx` | `maxLength` + helper text on destination field |

## Verification

1. **Unit tests** (`backend/tests/unit/`):
   - `_humanize_error(AIInputError("msg", "suggestion", "destination"))` returns the formatted message
   - Provider `generate_itineraries()` raises `AIInputError` when `extract_json()` returns a dict with `"error"` key
   - `AIService.generate_itineraries()` does not retry on `AIInputError`

2. **Integration test** (mocked AI response):
   - Mock the HF provider to return `{"error": {"message": "...", "suggestion": "...", "field": "destination"}}`
   - Trigger generation, verify trip transitions to `GENERATION_FAILED` with the expected `generation_error` text

3. **Live AI test** (`@pytest.mark.live`):
   - Create a trip with `destination = "xxxxnotaplace"`, trigger generation
   - Verify `generation_error` contains actionable guidance

4. **Frontend smoke test**:
   - Create a trip with a nonsensical destination, trigger generation
   - Confirm the red error banner shows the AI's suggestion, not the generic "invalid response" message
