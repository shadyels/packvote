# CLAUDE.md — PackVote

## Project Overview

PackVote is an AI-powered group travel planning app. Users create trips, invite participants via email, collect preferences, generate AI-powered destination/itinerary recommendations, and vote using ranked-choice voting to finalize plans.

---

## Tech Stack

### Backend
- **Language:** Python 3.12
- **Framework:** FastAPI (async ASGI)
- **ORM:** SQLAlchemy (async) + Alembic (migrations)
- **Package Manager:** uv
- **Database:** PostgreSQL
- **Email:** SendGrid (free tier, 100 emails/day)
- **AI Inference:** HuggingFace Inference Providers (provider-agnostic service layer)
- **Default AI Model:** Qwen2.5-72B-Instruct
- **API Style:** REST (not GraphQL — PackVote has a straightforward data model with one frontend client; GraphQL would add schema/resolver overhead without real benefit)
- **Auth:** Email + password (trip creators), token-based links + trip ID/PIN (participants)
- **Password Hashing:** `bcrypt` directly (do NOT use `passlib` — it is incompatible with `bcrypt >= 4.0` on Python 3.13; `bcrypt.hashpw`/`bcrypt.checkpw` are used in `app/core/security.py`)

### Frontend
- **Language:** TypeScript
- **Framework:** React 18+ with Vite
- **UI Library:** shadcn/ui + Tailwind CSS
- **Node Version:** 22 LTS
- **Package Manager:** pnpm

### Infrastructure
- **Deployment:** Railway (single platform for all services)
- **CI/CD:** GitHub Actions (on push/PR)
- **Monitoring (Phase 3, future):** Grafana dashboard for platform admin only (tech stack TBD)

---

## Monorepo Structure

```
packvote/
├── CLAUDE.md
├── REQUIREMENTS.md
├── .github/
│   └── workflows/          # CI/CD — DO NOT MODIFY
├── .claude/
│   └── settings.json
├── backend/
│   ├── pyproject.toml      # uv project config
│   ├── alembic/            # Database migrations
│   ├── app/
│   │   ├── main.py         # FastAPI entrypoint
│   │   ├── api/            # Route handlers (REST)
│   │   │   ├── trips.py
│   │   │   ├── participants.py
│   │   │   ├── votes.py
│   │   │   ├── auth.py
│   │   │   └── admin.py
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic layer
│   │   │   ├── ai/        # AI service layer (provider-agnostic)
│   │   │   ├── voting/    # Ranked-choice voting logic
│   │   │   ├── email/     # SendGrid integration
│   │   │   └── monitoring/ # Metrics collection
│   │   ├── prompts/        # Versioned prompt templates
│   │   ├── core/           # Config, security, dependencies
│   │   └── db/             # Database session, base model
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── ai/             # AI pipeline tests (mocked + live)
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── components/     # Reusable UI components (shadcn/ui)
│   │   ├── pages/          # Route pages
│   │   ├── hooks/          # Custom React hooks
│   │   ├── lib/            # Utilities, API client
│   │   ├── styles/         # Global styles, Tailwind theme
│   │   └── types/          # TypeScript type definitions
│   └── tests/
└── docs/                    # Additional documentation
```

---

## Commands

### Backend
```bash
cd backend
uv sync                          # Install dependencies
uv run alembic upgrade head      # Run database migrations
uv run uvicorn app.main:app --reload  # Start dev server
uv run pytest                    # Run all tests
uv run pytest tests/unit         # Run unit tests only
uv run pytest tests/ai -m live   # Run live AI integration tests (uses real API credits)
uv run ruff check .              # Lint
uv run ruff format .             # Format
```

### Frontend
```bash
cd frontend
pnpm install                     # Install dependencies
pnpm dev                         # Start dev server
pnpm build                       # Production build
pnpm test                        # Run tests (Vitest)
pnpm lint                        # ESLint
pnpm format                      # Prettier
```

---

## Code Conventions

### Python (Backend)
- **Linter/Formatter:** Ruff (configured in pyproject.toml)
- Use async/await for all database operations and HTTP handlers
- Type hints on all function signatures
- Pydantic models for all request/response schemas
- Business logic lives in `services/`, not in route handlers
- Route handlers are thin: validate input → call service → return response
- All database queries go through SQLAlchemy ORM, never raw SQL
- Environment variables accessed only via `app/core/config.py` using Pydantic Settings

### TypeScript (Frontend)
- **Linter:** ESLint | **Formatter:** Prettier
- Functional components only, no class components
- Custom hooks for all shared logic
- API calls centralized in `lib/api.ts`
- All API response types defined in `types/`
- Use shadcn/ui components as the base; customize via Tailwind theme
- No `any` types — strict TypeScript

### Git
- **Branching:** `main` + feature branches (e.g., `feat/trip-creation`, `fix/vote-tally`)
- **Commits:** Conventional commits enforced
  - `feat:` new features
  - `fix:` bug fixes
  - `docs:` documentation changes
  - `test:` adding/updating tests
  - `refactor:` code refactoring
  - `chore:` tooling, CI, dependencies
  - `style:` formatting only (no logic changes)
- **PRs:** All changes go through PRs to `main`. Never push directly to `main`.
- Write clear PR descriptions summarizing what changed and why.

---

## Design System

- **Primary background:** Offwhite (#F8F8F6) via `--background` CSS var
- **Card / Surface:** Warm near-white (#FDFCFA) via `--card` CSS var
- **Text:** Near-black (#171717) via `--foreground` CSS var
- **Accent (brand):** Orange (#FF6B2C) — use `brand` in Tailwind classes (`text-brand`, `bg-brand`, `hover:bg-brand-hover`)
- **Borders:** Warm-neutral (#E5E5E3) via `--border` CSS var
- **Responsive:** Fully mobile-responsive (participants will open email links on phones)
- **Images:** Unsplash API for high-quality travel photography (can be static/curated)
- **Style:** Modern, captivating, user-friendly — travel app aesthetic

---

## Architecture Constraints

### AI Service Layer
- The AI service layer MUST be provider-agnostic. It communicates via a unified interface that can swap between:
  - HuggingFace Inference Providers (default)
  - Groq free tier (fallback)
  - Any OpenAI-compatible API
- **Free tier constraint:** The project uses HuggingFace's free tier with limited monthly credits. Minimize AI calls, cache results, and use exponential backoff on failures. This constraint is why the fallback provider exists.
- Default model: `Qwen2.5-72B-Instruct` (chosen for: best-in-class structured JSON output among open-source models, superior instruction following, token-efficient with no thinking mode overhead, Apache 2.0 licensed, widely available across HF providers)
- Qwen 3.5 variants available as swappable alternatives for A/B testing
- All AI responses MUST return validated JSON (use Pydantic for validation)
- All prompts are versioned in the database with template storage
- Basic A/B testing: traffic split between prompt versions, metrics tracked per version (response quality, vote outcomes, latency)

### AI Generation Implementation Patterns

**`huggingface_hub.AsyncInferenceClient` for all providers:**
Both `HuggingFaceProvider` and `GroqProvider` use `AsyncInferenceClient` from `huggingface_hub`. Groq exposes an OpenAI-compatible API, so the same client works against both by changing `base_url` and `api_key`. Do not use raw `httpx` calls for AI inference.

**Provider return type includes provider name:**
`AIProvider.generate_itineraries()` returns `tuple[AIGenerationResponse, str]` where the string is the provider name (`"huggingface"` or `"groq"`). This is required so the generation service can accurately log which provider handled the request in `AICallLog.provider` and `Itinerary.provider`. Without it, the caller cannot tell whether HF or the Groq fallback actually answered.

**Retry strategy — primary then fallback:**
`AIService.generate_itineraries()` retries the primary provider (HuggingFace) up to 3 times with exponential backoff (1s, 2s, 4s). On exhaustion, it tries the fallback (Groq) once. If both fail, the last exception is re-raised. Never use immediate retries.

**Groq ignores the `model` parameter:**
The `model` argument passed to `GroqProvider.generate_itineraries()` is always a HuggingFace model ID and is meaningless to Groq. `GroqProvider` hardcodes `GROQ_MODEL = "llama-3.3-70b-versatile"` and ignores the argument. This is intentional — do not try to pass a Groq-specific model name through `AIService`.

**Prompt template format — `[SYSTEM]`/`[USER]` delimiter:**
Prompt templates are stored as a single text string in the `prompt_templates` table. The string uses `[SYSTEM]\n...\n[USER]\n...` as a delimiter that provider implementations split at call time to build the two-message array. This keeps a full prompt in one DB row (easy to version and A/B test) without requiring separate `system_text` / `user_text` columns.

**Prompt templates seeded at runtime, not via migration:**
`_upsert_prompt_template()` in `services/generation.py` does a SELECT then INSERT if missing, every time generation runs. This is idempotent. Do NOT create a separate Alembic data migration to seed prompt templates — runtime upsert is self-healing if the row is ever deleted and avoids migration fragility.

**JSON serialization of itinerary fields:**
`Itinerary.daily_itinerary_json` and `Itinerary.highlights` are `Text` columns storing JSON strings (not native JSON columns). This keeps the schema database-agnostic between SQLite (tests) and PostgreSQL (production). Always serialize with `json.dumps([day.model_dump() for day in ...])` and `json.dumps(list)`. Use Pydantic's `.model_dump()` (not `dict()`) to correctly handle nested models.

### Background Tasks and Session Isolation

**NEVER pass a request-scoped `AsyncSession` to a `BackgroundTask`.** FastAPI closes the session when the response is sent — before the background task runs. The task will receive a closed/invalid session.

**Pattern: pass `session_factory`, not `session`:**
```python
# Route handler
background_tasks.add_task(run_generation, trip_id, session_factory)

# Background task
async def run_generation(trip_id: int, session_factory: async_sessionmaker) -> None:
    async with session_factory() as db:   # opens its own fresh session
        ...
```

`get_session_factory()` in `app/core/dependencies.py` re-exports the module-level singleton from `app/db/session.py`. Inject it as a FastAPI dependency wherever a background task needs DB access.

**Failure recovery opens a second fresh session:**
If the generation task fails mid-way, the first session is rolled back automatically by the `async with` context manager. To reset trip status, open a second `async with session_factory() as db` — do not attempt to reuse the failed session.

**`AIService` is constructed inside the background task:**
Do not inject `AIService` as a FastAPI dependency. It has no I/O at construction time (just reads config), so constructing it fresh inside `run_generation` with `AIService.from_settings()` is cheap and avoids request lifecycle issues.

### Generation Status Transitions

**Commit `GENERATING` status before returning 202 and before scheduling the task:**
```python
trip.status = "GENERATING"
await db.commit()                              # committed first
background_tasks.add_task(run_generation, ...)
return {"status": "accepted"}
```
This ensures: (1) clients polling `GET /trips/{id}` immediately see `GENERATING`, and (2) the idempotency guard inside the background task sees the correct status.

**Idempotency guard at the top of every generation task:**
Re-read the trip from the DB at the start of `run_generation` and exit early if `trip.status != "GENERATING"`. This prevents a second task (from a race between manual and auto-trigger) from running twice.

**Auto-trigger guard in `submit_preferences`:**
After saving a preference, check if all participants have now submitted AND `trip.status == "COLLECTING_PREFERENCES"`. Only trigger if both conditions are true. The status check prevents double-triggering when the creator has already hit `POST /trips/{id}/generate` manually.

### Authentication
- Trip creators: email + password (architected so OAuth/social login can be added later)
- Participants: token-based email links OR trip code (8-char alphanumeric, uppercase A-Z + 0-9) + PIN (4 digits)
- No account creation required for participants
- No additional security beyond ID+PIN for participant access (no login, no CAPTCHA)
- Every email to participants includes both the direct link AND the trip ID + PIN

### Voting System
- Full ranked-choice / instant-runoff voting
- 2–5 itinerary options per round (trip creator chooses at trip creation)
- New iteration triggered by: no clear majority OR admin manual trigger
- Maximum 10 iterations
- Admin vote carries equal weight during voting
- Admin can manually pick a winner at any time to close voting

### Voting Implementation Patterns

**Admin voting via `user_id` on Vote model:** `Vote` has both `participant_id` (nullable) and `user_id` (nullable) — exactly one must be set. This allows the trip creator to vote without creating a fake Participant row. The ranked-choice algorithm is agnostic to voter identity — it only sees `list[list[int]]`.

**Pure algorithm separation:** `services/voting/ranked_choice.py` is a pure, stateless function (no DB, no I/O). `services/voting/service.py` handles all DB operations and calls the algorithm. This makes the algorithm trivially unit-testable without any DB setup.

**Auto-tally on last vote:** When all eligible voters (participants + 1 admin) have submitted votes for the current iteration, the tally runs automatically and persists `VoteRound` rows. Results are also available on-demand via `GET /votes/trips/{id}/results` (computes if not already stored, uses stored rows if present).

**Participant vote auth uses token-in-path:** `POST /votes/trips/{trip_id}/vote/{token}` — same pattern as `POST /participants/{token}/preferences`.

**Re-voting allowed:** Submitting a vote for the same trip+iteration overwrites the previous vote (upsert semantics). Only one `Vote` row per voter per trip per iteration is kept.

**Deterministic tiebreaker:** When multiple candidates tie for fewest votes during elimination, the candidate with the lowest ID is eliminated. This ensures reproducible results.

**`pick_winner` bypasses voting:** Admin can set `trip.winner_itinerary_id` and transition to `FINALIZED` at any time from `VOTING` or `ITERATING` status, overriding the ranked-choice result.

**`new-iteration` triggers generation directly:** Status goes `VOTING` → `GENERATING` (not `VOTING` → `ITERATING` → `GENERATING`). The `ITERATING` status is reserved for future follow-up survey flow (Phase 1 skips surveys).

### F7 Trip Page — Participant Architecture

**Composite endpoint `GET /participants/{token}/trip-view`:**
Returns a single `ParticipantTripView` payload containing the participant's own info, trip public info, all participant briefs (names + submitted status, no emails), current-iteration itineraries, voting results, and a `has_voted` flag. This avoids multiple sequential fetches from the participant page. Token is the auth — no bearer token required.

**`POST /participants/access-by-code` requires only `trip_code` and `pin`:**
The payload is `{ trip_code, pin }`. PIN is now per-participant (not shared per trip), so `trip_code + pin` uniquely identifies a participant — no email needed. Returns `ParticipantAccessResponse`: `{ token, participant }`. The frontend uses the token to redirect to `/trip/{token}`.

**`useTripView` hook:**
`frontend/src/hooks/useTripView.ts` calls `participants.getTripView(token)` and polls every 5s while `trip.status === "GENERATING"`, stopping automatically on status change or unmount. Same pattern as `useTripDetail` in the dashboard.

**Shared component and utility locations:**
- `ItineraryCard` — `frontend/src/components/shared/ItineraryCard.tsx` (used by both dashboard `ItinerariesSection` and participant `VotingForm`/`WinnerDisplay`)
- `STATUS_CONFIG` — `frontend/src/lib/trip-status.ts` (used by `TripCard`, `TripOverviewSection`, and participant `TripHeader`)
- `parseJson` — `frontend/src/lib/utils.ts` (safe JSON.parse with fallback; used wherever `daily_itinerary_json` or `highlights` are rendered)

**Participant trip component structure:**
`frontend/src/components/trip/` contains the status-dependent components: `TripHeader`, `ParticipantProgress`, `PreferenceForm`, `WaitingScreen`, `GeneratingScreen`, `VotingForm`, `WinnerDisplay`. `TripPage.tsx` is the state machine that renders the correct one based on `trip.status` and `participant.preferences_submitted`/`has_voted`.

**Route additions:**
- `/trip/:token/vote` → same `TripPage` (voting notification emails link here)
- `/join/:token` → `JoinRedirect` component that redirects to `/trip/:token` (invitation email links)
- `/join` → `JoinPage` (trip code + PIN form — no email required)

---

### F8 Dashboard — Frontend Architecture

**AuthContext pattern:**
`frontend/src/contexts/AuthContext.tsx` provides shared auth state (user, isLoading, isAuthenticated, login, register, logout) to the whole app. `AuthProvider` wraps the app in `main.tsx`. `useAuth` in `hooks/useAuth.ts` re-exports from the context. Never go back to the standalone-hook pattern — that caused multiple `auth.me()` calls.

**ProtectedRoute:**
`frontend/src/components/ProtectedRoute.tsx` guards authenticated routes. Shows skeletons while loading, redirects to `/login` if unauthenticated, renders `<Outlet />` otherwise. Used in `App.tsx` for `/dashboard` and `/dashboard/trip/:tripId`.

**Routing layout pattern:**
`LayoutWrapper` in `App.tsx` wraps non-login/non-landing routes with the Layout nav via `<Outlet />`. Login and LandingPage each render their own full-screen layouts outside `LayoutWrapper`.

**LoginPage** is built as part of F8 (it was a stub before).

**useTripDetail hook:**
`frontend/src/hooks/useTripDetail.ts` orchestrates parallel fetches (trip, participants, itineraries, voting results, AI logs) using `Promise.allSettled`. Starts a 5s polling interval when `trip.status === "GENERATING"` and clears it on status change or unmount.

**Dashboard sub-resource endpoints (F8 backend additions):**
- `GET /trips/{trip_id}/participants` — creator-only participant list (includes email field)
- `GET /trips/{trip_id}/itineraries` — creator-only itinerary list for all iterations
- `GET /trips/{trip_id}/ai-logs` — creator-only AI call log history per trip
Schema: `backend/app/schemas/ai_call_log.py` (AICallLogResponse)

**shadcn/ui is @base-ui/react:**
The shadcn components in this project use `@base-ui/react` primitives (not `@radix-ui`). Key API differences:
- `DialogTrigger` has no `asChild` — use `render` prop: `<DialogTrigger render={<Button />} />`
- `Select.Root` `onValueChange` callback is `(value: string | null, eventDetails) => void` — guard against null before calling setState
- `Tabs` uses `data-[state=active]` for active tab styling

**Async event handler lint rule:**
The project enforces `@typescript-eslint/no-misused-promises`. Wrap async handlers: `onClick={() => { void handleAsync(); }}` or `onSubmit={(e) => { void handleSubmit(e); }}`.

### F9 Frontend Polish — Architecture Notes

**Unsplash image utility:**
`frontend/src/lib/unsplash.ts` provides `useDestinationImage(destination: string)` — a React hook that fetches a landscape photo from the Unsplash API (`https://api.unsplash.com/search/photos`) and returns `{ imageUrl, gradient, photographer, photographerUrl, isLoading }`.
- API key is read from `VITE_UNSPLASH_ACCESS_KEY` (client-side env var, not backend)
- In-memory `Map<string, CachedResult>` cache with 1-hour TTL avoids redundant fetches per session
- **Fallback:** when no API key or fetch fails, a deterministic gradient is computed from the destination name hash — the app always looks polished with or without a key
- Proper Unsplash attribution (photographer name + link) is rendered as a small overlay on images (required by Unsplash API terms)
- `Array.prototype.at()` is unavailable under `lib: ["ES2020"]` — use index access or `results.length > 0 ? results[0] : undefined` instead
- The Unsplash response is typed via named interfaces (`UnsplashPhoto`, `UnsplashSearchResponse`) and validated with a type guard (`isSearchResponse`) rather than casting from `any`, to satisfy `@typescript-eslint/no-unsafe-assignment`

**Landing page standalone layout:**
`LandingPage.tsx` is rendered outside `LayoutWrapper` (same pattern as `LoginPage`) — it has its own transparent nav header and its own `<Footer />` at the bottom. The route is declared at the top level: `<Route path="/" element={<LandingPage />} />` before the `LayoutWrapper` wrapper.

**Footer component:**
`frontend/src/components/Footer.tsx` — minimal footer (PackVote link + copyright). Used in both `Layout.tsx` (all authenticated/participant pages) and `LandingPage.tsx` (landing page's own footer).

**CSS animations:**
`globals.css` defines `@keyframes fade-in-up`, `fade-in`, `shimmer`, and `progress` animations plus utility classes (`animate-fade-in-up`, `animate-fade-in`, `animate-shimmer`, `animation-delay-*`). The `GeneratingScreen` indeterminate progress bar uses a custom `progress` keyframe via Tailwind's arbitrary value: `animate-[progress_40s_linear_infinite]`.

**Emoji → Lucide icons:**
All emoji visual elements replaced with Lucide icons: `🏆` → `<Trophy />`, `✅` → `<CheckCircle2 />`, `🗺️` → `<MapPin />`. No emojis remain as visual elements in any component.

**Dead dependency removal:**
`@fontsource-variable/geist` and `next-themes` removed from `package.json`. `sonner.tsx` was updated to hardcode `theme="light"` instead of reading from `next-themes`. `globals.css` no longer imports the Geist font. The `.dark` CSS block and `.theme` CSS block were removed.

**ESLint config fixes (pre-existing issues resolved):**
`tsconfig.node.json` now includes `vite.config.ts` and `tailwind.config.ts` (they were previously missing, causing parse errors). `vitest.config.ts` is in the eslint `ignores` list because it uses a legitimate `// @ts-nocheck` to work around a vitest/vite version mismatch. The `react-refresh/only-export-components` rule is `"off"` — it was causing pre-existing warnings in shadcn/ui components that legitimately export both components and variant functions.

**Landing page hero overlay:**
The hero uses a radial vignette (`radial-gradient(ellipse at 50% 50%, ...)`) instead of a flat `bg-black/50` — denser at center where text sits, lighter at edges for a more natural photo framing. The bottom fade is `h-40` with a 3-stop gradient using the actual background HSL value (`hsl(80,14%,97%)`) for a smooth dissolve.

**Bottom CTA section:**
Solid `bg-[#192840]` background (matches the footer). A top fade div (`h-40`, absolute positioned) dissolves from offwhite (`hsl(80,14%,97%)`) → transparent, mirroring the hero's bottom fade. An orange glow overlay (`opacity-10`, `radial-gradient(ellipse at 60% 70%, rgba(255,107,44,0.5), ...)`) adds warmth. Content has `pt-36` to push it below the fade zone into the clearly dark area.

**Feature Highlights section layout:**
Replaced the hard `border-y border-border bg-card` section with a `rounded-3xl bg-card border border-border` card container that floats on the offwhite background. `FeatureBlock` accepts a `visual: React.ReactNode` prop instead of generating a generic progress-bar card.

**`AIRecommendationVisual` and `RankedVotingVisual`:**
`AIRecommendationVisual` is a mock itinerary card with a warm orange gradient header, match score (Star icon), per-person budget, activity Badge tags, and a Day 1 time-activity preview. `RankedVotingVisual` uses `Card`/`CardHeader`/`CardContent` with 3 ranked options, progress bars (brand-colored winner, muted losers), and a winner callout banner with Trophy + CheckCircle2. Both use Lucide icons: `Star`, `Utensils`, `Compass`, `Trophy`, `CheckCircle2`.

### Email
- SendGrid free tier (100 emails/day)
- Emails contain: invitation/notification text, direct tokenized link, trip ID + PIN
- Trip page is a persistent in-app page showing current status, votes, itineraries

### AI Call Logging (Phase 1)
- `ai_call_logs` table records each AI generation: prompt version, model, provider, latency, token counts, response validity
- This is part of the AI pipeline, not a monitoring dashboard
- The ops-level metrics *dashboard* is Phase 3 (Grafana, admin-only, separate from Trip Creator Dashboard)

### Phase 2 Feature: Price Monitoring Agent (DO NOT BUILD YET)
- Manual "Update Prices" button on finalized trips
- Uses free structured APIs (specific providers TBD)
- Budget logic: aim below lowest participant budget; if impossible, don't exceed average group budget by more than 30%
- Notify participants when trip exceeds their stated budget
- This is a separate phase — do not architect for it in Phase 1 beyond ensuring the itinerary data model can store price data

---

## Testing Strategy

### Backend (pytest + httpx)
- Unit tests for all business logic in `services/`
- Integration tests for API endpoints
- AI pipeline tests: mocked responses by default
- Small live AI integration test suite marked with `@pytest.mark.live` (run manually, not on every CI push)
- Target: all critical paths covered

### Frontend (Vitest + React Testing Library)
- Component rendering tests
- User interaction flows
- API integration tests with mocked backend

### CI/CD (GitHub Actions)
- Runs on every push and PR
- Steps: lint → type check → unit tests → integration tests (mocked AI)
- Live AI tests run on manual trigger or schedule only

---

## Hard Constraints (Enforced via Hooks)

1. **NEVER read `.env` files or environment variables directly.** All env var access goes through `app/core/config.py`.
2. **NEVER push to `main`.** Always work in feature branches.
3. **NEVER modify `.github/workflows/` files.** CI/CD config is off-limits.
4. **NEVER approve or merge PRs.** You may open PRs only.

---

## Workflow

- Use **Plan Mode** as the default for all non-trivial changes.
- Read the relevant code first, create a plan, get approval, then implement.
- For trivial fixes (typos, single-line changes), normal mode is fine.
- Always explain what you intend to do and wait for confirmation before making changes.
