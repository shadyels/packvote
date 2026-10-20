# CLAUDE.md — PackVote

## Project Overview

PackVote is an AI-powered group travel planning app. Users create trips, invite participants via email, collect preferences, generate AI-powered itinerary recommendations, and vote using ranked-choice voting to finalize plans.

---

## Commands

**Backend** (from `backend/`):
- `uv run uvicorn app.main:app --reload` — dev server (port 8000)
- `uv run pytest` — all tests | `-m "not live"` skips AI live tests
- `uv run ruff check . && uv run ruff format .` — lint + format

**Frontend** (from `frontend/`):
- `pnpm dev` — dev server
- `pnpm test --run` — vitest, single run (bare `pnpm test` is watch mode)
- `pnpm lint` — eslint zero-warnings
- `pnpm build` — tsc + vite build

---

## Tech Stack

### Backend
- **Language:** Python 3.12
- **Framework:** FastAPI (async ASGI)
- **ORM:** SQLAlchemy (async) + Alembic (migrations; single `0001_baseline` revision in `backend/alembic/versions/`)
- **Package Manager:** uv
- **Database:** PostgreSQL
- **Email:** Brevo (free tier, 300 emails/day)
- **AI Inference:** any OpenAI-compatible endpoint via `openai` SDK (`AsyncOpenAI`) — do NOT add vendor SDKs. Provider is config (`AI_API_KEY` / `AI_BASE_URL` / `AI_PROVIDER_NAME` / `AI_EXTRA_BODY`), not code.
- **Default AI Model:** `gemini-3.6-flash` on Google Gemini's free tier (`gemini-2.5-flash` was retired for new API keys — 404 "no longer available to new users"). Thinking suppressed via `AI_EXTRA_BODY` (`thinking_level: "minimal"` — Gemini 3.x replaced `thinking_budget` with this string enum; sending the old field 400s on 3.x models) because Gemini draws thinking tokens from the same `max_tokens` budget as the response — leaving it on risks truncating the itinerary JSON. Unlike `thinking_budget=0` on 2.5, `"minimal"` does not *guarantee* zero thinking tokens; watch for `finish_reason=length` warnings. `DEFAULT_REASONING_EFFORT="none"` omits `reasoning_effort` entirely (Gemini rejects it alongside `thinking_config`).
- **Auth:** Email + password (trip creators), token-based links + trip code/PIN (participants)
- **JWT:** `PyJWT` (HS256; decode requires `exp` + `sub`) — do NOT use `python-jose`. JWTs issued before the user's `password_changed_at` are rejected. `UserCreate`/`UserLogin`/`PasswordResetRequest` lowercase emails (`LowerEmail` in `schemas/user.py`). Passwords are capped at 72 UTF-8 bytes.
- **SECRET_KEY guard:** `app/core/config.py` — `ENVIRONMENT` defaults to `production`; outside `development`, `SECRET_KEY` must be non-default and ≥ 32 chars.
- **PIN throttle:** 10 failed PIN attempts per trip per 24h → 429 (`services/participants.py`, in-process).
- **Password Hashing:** `bcrypt` directly — do NOT use `passlib` (incompatible with `bcrypt >= 4.0`)

### Frontend
- **Language:** TypeScript
- **Framework:** React 18+ with Vite
- **UI Library:** Tailwind CSS v4 (`@tailwindcss/vite`, CSS-first `@theme` tokens in `frontend/src/styles.css`) + `@base-ui/react` for Dialog and Tabs only. No shadcn/ui, no `@radix-ui`. Native `<input type="date">` and `<select>` elsewhere.
- **Node Version:** 22 LTS
- **Package Manager:** pnpm — build script allowlist via `allowBuilds` in `frontend/pnpm-workspace.yaml` (v11 API). Do NOT use deprecated `onlyBuiltDependencies`.

### Infrastructure
- **Deployment:** Railway — builder is **Railpack** (do NOT use `builder = "nixpacks"`)
- **CI/CD:** GitHub Actions

---

## Code Conventions

### Python (Backend)
- Ruff for lint/format (configured in `pyproject.toml`)
- async/await for all DB operations and HTTP handlers
- Type hints on all function signatures
- Pydantic models for all request/response schemas
- Business logic in `services/`, not in route handlers (thin handlers)
- All DB queries via SQLAlchemy ORM — never raw SQL
- Environment variables only via `app/core/config.py` (Pydantic Settings)

### TypeScript (Frontend)
- ESLint + Prettier
- Functional components only
- Custom hooks for all shared logic
- API calls centralized in `lib/api.ts`
- All API response types in `types/`
- No `any` types — strict TypeScript
- Async handlers: `onClick={() => { void handleAsync(); }}` (enforced by `no-misused-promises`)
- Auth state: `contexts/AuthContext.tsx` + `hooks/useAuth.ts` — do not replicate elsewhere

### Git
- **Branching:** `main` + feature branches (`feat/`, `fix/`, `refactor/`, etc.)
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `style:`)
- **PRs:** All changes go through PRs to `main`.

---

## Design System

- **Background:** `#e9ecef` light / `#0b0f17` dark (`--color-background`)
- **Card/Surface:** `#ffffff` light / `#141a24` dark (`--color-surface`)
- **Text:** `#0e1116` light / `#edeff2` dark (`--color-foreground`)
- **Accent:** `#ffc81e` yellow in both themes (`--color-accent`) — fill only: `bg-accent` with `text-accent-foreground`
- **Accent ink:** `#0e1116` light / `#ffc81e` dark (`--color-accent-ink`) — text, rings, underlines, focus: `text-accent-ink`, `ring-accent-ink`, `border-accent-ink`
- **Status:** success `--color-success` (boarding, winner), danger `--color-danger` (eliminated), warning `--color-warning` (orange, apart from the accent). Landing board flap tiles: `--color-flap`, `--color-flap-ink`, `--color-flap-edge`
- **Borders:** `#c9ced6` light / `#2a3343` dark (`--color-border`)
- **Theme:** Light and dark follow `prefers-color-scheme` only (no toggle). Geist + Geist Mono.
- **Responsive:** Fully mobile-responsive
- **Images:** None. No photos anywhere.
- **Style:** Modern, captivating, travel app aesthetic

---

## Architecture Quick Reference

Read the relevant `docs/` file before working in any of these areas:

| Area | Key constraint | Full details |
|------|---------------|-------------|
| **AI service** | Use `extract_json()`, never `json.loads()`. Keep `response_format` as `json_object` — `json_schema` would make the `{"error": {...}}` envelope unrepresentable. Pass `session_factory` (not `session`) to background tasks. Rate limiter enforces 6 limits (rpm/rph/rpd/tpm/tph/tpd) calibrated to Gemini's free tier; `LocalRateLimitError` skips retry. User-controlled fields injected into prompts must be wrapped in `<<<USER DATA>>>…<<<END USER DATA>>>` delimiters and passed through `sanitize_text()`. Trip duration is clamped to `max_trip_days(num_options)` in `_compute_trip_duration` — never let user-supplied dates exceed this cap. Generation runs in three phases (read session → AI call with no DB session open → write session guarded on `GENERATING`); every trigger claims the run via `start_generation()` (conditional UPDATE); `recover_stuck_generations` fails trips left in `GENERATING` at startup. | `docs/AI-ARCHITECTURE.md` |
| **Voting** | Pure algorithm `ranked_choice.tally()`, DB ops + `compute_results()` in `service.py`. Results are computed from votes on every read (nothing stored). `GET /votes/trips/{id}/results` requires a participant token (`X-Participant-Token`) for the trip, or the JWT of the creator or a linked participant. Finalise is a conditional UPDATE pinned to `current_iteration`. The frontend never sends `X-Participant-Token`; participant results come from the trip-view payload. | `docs/VOTING-ARCHITECTURE.md` |
| **Frontend components** | `@base-ui/react` for Dialog and Tabs only; native controls elsewhere. Tabs use the `?tab=` query param (Dashboard, TripDetail) — not `useState`. All server data goes through the single `useFetch` hook (`hooks/useFetch.ts`). `STATUS` and limits live in `lib/trip.ts`. A 401 on a JWT session call logs out globally via `lib/api.ts`. | `docs/FRONTEND-ARCHITECTURE.md` |
| **Deployment** | `DATABASE_URL` needs `postgresql+asyncpg://` prefix. `VITE_API_URL` baked in at build time. | `docs/DEPLOYMENT.md` |
| **Testing** | Unit in `tests/unit/`, integration uses SQLite+MockEmail, AI tests need `@pytest.mark.live`. | `docs/TESTING.md` |
| **Email service** | Brevo free tier: 300 emails/day. Shared synchronous `SlidingWindow` (`app/services/rate_limit.py`: `allowed`/`hit`/`acquire`) enforces the cap; when exhausted `_send()` returns `False` with a warning and callers do not retry. Single `send_trip_email(kind)` in `services/email/brevo.py`, kinds from `TRIP_EMAILS`. Invitation, finalized, generation and password-reset emails go out via FastAPI BackgroundTasks; admin resend sends inline. Never log recipient addresses or Brevo bodies. | `docs/EMAIL-ARCHITECTURE.md` |

### AI service split
`services/generation.py` — orchestration entry point (`run_generation(trip_id, session_factory)`). Edit here for pipeline changes.
`services/ai/` — provider layer (`openai_compat.py`, JSON utils, rate limiter). Edit here for provider changes. Switching providers should mean editing config, not this directory.
`services/ai/rate_limiter.py` — in-process gate enforcing 6 limits (rpm/rph/rpd/tpm/tph/tpd) via single deque with 24h eviction. Singleton `get_limiter()`. `LocalRateLimitError` fast-fails without retry. Window constants: `WINDOW_1M` (60s), `WINDOW_1H` (3600s), `WINDOW_24H` (86400s).

### Admin API (`app/api/admin.py`)
Prefix `/admin`, requires `get_current_user`. Currently hosts email resend endpoints:
- `POST /admin/trips/{trip_id}/resend-emails` — resend status-appropriate email to all participants
- `POST /admin/trips/{trip_id}/participants/{participant_id}/resend-email` — resend to one participant

Email type is derived from `trip.status` + `trip.current_iteration` in `services/email_resend.py`. Both endpoints enforce creator-only ownership via `get_owned_trip` in `services/trips.py` (404 if missing, 403 `Not the trip creator` otherwise). Returns `{sent: int, failed: int}`.

### Participant ↔ User linking
`Participant.user_id` is set in two places — keep both in sync if the logic ever changes:
1. **`create_trip` (`services/trips.py`)** — batch-looks up users by lowercased email at trip creation time and sets `user_id` immediately if the invitee already has an account.
2. **`register_user` (`services/auth.py`)** — after inserting the new user, bulk-updates all existing `Participant` rows whose email matches (case-insensitive) to backfill `user_id`.

### Trips router — static routes before dynamic
`GET /trips/invited` **must** be declared before `GET /trips/{trip_id}` in `app/api/trips.py`. FastAPI matches routes top-to-bottom; placing a static segment after a dynamic one causes `/invited` to be swallowed by the `{trip_id}` pattern.

### Phase 2 (DO NOT BUILD YET)
Price monitoring agent for finalized trips.

---

## Hard Constraints

1. **NEVER read `.env` files directly.** All env var access via `app/core/config.py`.
2. **NEVER push to `main`.** Always use feature branches.
3. **NEVER modify `.github/workflows/` files.**
4. **NEVER approve or merge PRs.** You may open PRs only.
5. **NEVER create git branches directly** — a git hook blocks it. Propose the branch name and wait for the user to create it.
6. **NEVER create PRs directly** — prepare the PR title and description for the user to submit manually.
7. **One phase per branch.** Complete the current phase → open PR → wait for merge → pull `main` → new branch → only then start next phase.
8. **Before opening a PR:** remove all dead/unused code.
