# CLAUDE.md — PackVote

## Project Overview

PackVote is an AI-powered group travel planning app. Users create trips, invite participants via email, collect preferences, generate AI-powered itinerary recommendations, and vote using ranked-choice voting to finalize plans.

---

## Commands

**Backend** (from `backend/`):
- `uv run fastapi dev app/main.py` — dev server (port 8000)
- `uv run pytest` — all tests | `-m "not live"` skips AI live tests
- `uv run ruff check . && uv run ruff format .` — lint + format

**Frontend** (from `frontend/`):
- `pnpm dev` — dev server
- `pnpm test` — vitest watch
- `pnpm lint` — eslint zero-warnings
- `pnpm build` — tsc + vite build

---

## Tech Stack

### Backend
- **Language:** Python 3.12
- **Framework:** FastAPI (async ASGI)
- **ORM:** SQLAlchemy (async) + Alembic (migrations)
- **Package Manager:** uv
- **Database:** PostgreSQL
- **Email:** Brevo (free tier, 300 emails/day)
- **AI Inference:** Cerebras (`cerebras-cloud-sdk`, `AsyncCerebras`)
- **Default AI Model:** gpt-oss-120b (`gpt-oss-120b`, Apache 2.0). Reasoning suppressed via `reasoning_format="hidden"` + `reasoning_effort="low"` (escalate via `DEFAULT_REASONING_EFFORT` env var).
- **Auth:** Email + password (trip creators), token-based links + trip code/PIN (participants)
- **Password Hashing:** `bcrypt` directly — do NOT use `passlib` (incompatible with `bcrypt >= 4.0`)

### Frontend
- **Language:** TypeScript
- **Framework:** React 18+ with Vite
- **UI Library:** shadcn/ui (uses `@base-ui/react` primitives, NOT `@radix-ui`) + Tailwind CSS
- **Node Version:** 22 LTS
- **Package Manager:** pnpm — build script allowlist via `pnpm.allowBuilds` in `package.json` (v11 API). Do NOT use deprecated `onlyBuiltDependencies`.

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

- **Background:** Offwhite `#F8F8F6` (`--background`)
- **Card/Surface:** `#FDFCFA` (`--card`)
- **Text:** Near-black `#171717` (`--foreground`)
- **Brand accent:** Orange `#FF6B2C` — use `text-brand`, `bg-brand`, `hover:bg-brand-hover`
- **Borders:** `#E5E5E3` (`--border`)
- **Responsive:** Fully mobile-responsive
- **Images:** Unsplash API with gradient fallback
- **Style:** Modern, captivating, travel app aesthetic

---

## Architecture Quick Reference

Read the relevant `docs/` file before working in any of these areas:

| Area | Key constraint | Full details |
|------|---------------|-------------|
| **AI service** | Use `extract_json()`, never `json.loads()`. Pass `session_factory` (not `session`) to background tasks. `LocalRateLimitError` skips retry — do not add retry logic around it. | `docs/AI-ARCHITECTURE.md` |
| **Voting** | Pure algorithm in `ranked_choice.py`, DB ops in `service.py`. | `docs/VOTING-ARCHITECTURE.md` |
| **Frontend components** | `@base-ui/react` not `@radix-ui`. DatePicker trigger is `<button>`, not `<Button asChild>`. `Select.Value` needs explicit children to show a label (not raw value). Dashboard tabs use `?tab=` query param — not `useState`. | `docs/FRONTEND-ARCHITECTURE.md` |
| **Deployment** | `DATABASE_URL` needs `postgresql+asyncpg://` prefix. `VITE_API_URL` baked in at build time. | `docs/DEPLOYMENT.md` |
| **Testing** | Unit in `tests/unit/`, integration uses SQLite+MockEmail, AI tests need `@pytest.mark.live`. | `docs/TESTING.md` |
| **Email service** | Brevo free tier: 300 emails/day. Global in-process sliding-window rate limiter enforces the cap. When limit exhausted, `_send()` returns `False` with warning log; callers handle gracefully (no retry). All `try_consume()` calls async-safe via `asyncio.Lock`. | `docs/EMAIL-ARCHITECTURE.md` |
| **Unsplash proxy** | `GET /unsplash/photo` (no auth). Key lives in backend `UNSPLASH_ACCESS_KEY` only — never in frontend env. In-process 45 req/hr limiter + 1hr cache in `services/unsplash.py`. Over-limit returns `{images:[]}`, frontend renders gradient. | `backend/app/services/unsplash.py` |

### AI service split
`services/generation.py` — orchestration entry point (`run_generation(trip_id, session_factory)`). Edit here for pipeline changes.
`services/ai/` — provider layer (Cerebras client, JSON utils, base class, rate limiter). Edit here for provider changes.
`services/ai/rate_limiter.py` — in-process gate (RPM/TPM/context-length). Singleton `get_limiter()`. `LocalRateLimitError` fast-fails without retry.

### Admin API (`app/api/admin.py`)
Prefix `/admin`, requires `get_current_user`. Currently hosts email resend endpoints:
- `POST /admin/trips/{trip_id}/resend-emails` — resend status-appropriate email to all participants
- `POST /admin/trips/{trip_id}/participants/{participant_id}/resend-email` — resend to one participant

Email type is derived from `trip.status` + `trip.current_iteration` in `services/email_resend.py`. Both endpoints enforce creator-only ownership (403 if `trip.creator_id != current_user.id`). Returns `{sent: int, failed: int}`.

### Participant ↔ User linking
`Participant.user_id` is set in two places — keep both in sync if the logic ever changes:
1. **`create_trip` (`services/trips.py`)** — batch-looks up users by lowercased email at trip creation time and sets `user_id` immediately if the invitee already has an account.
2. **`register` (`api/auth.py`)** — after inserting the new user, bulk-updates all existing `Participant` rows whose email matches (case-insensitive) to backfill `user_id`.

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
