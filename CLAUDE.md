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
- **Monitoring Phase 1:** Metrics logged to PostgreSQL + admin dashboard page
- **Monitoring Phase 2 (future):** Prometheus + Grafana

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

- **Primary background:** Black (#000000)
- **Secondary background / text:** Cream (#FFF8E7)
- **Accent:** Orange (#FF6B2C)
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

### Email
- SendGrid free tier (100 emails/day)
- Emails contain: invitation/notification text, direct tokenized link, trip ID + PIN
- Trip page is a persistent in-app page showing current status, votes, itineraries

### Monitoring (Phase 1)
- All metrics logged to PostgreSQL
- Admin-only dashboard page (not exposed to users)
- Metrics: API request counts/latency, active trips/users, AI pipeline response times, vote completion rates, error rates, email delivery success rates

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
