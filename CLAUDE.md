# CLAUDE.md — PackVote

## Project Overview

PackVote is an AI-powered group travel planning app. Users create trips, invite participants via email, collect preferences, generate AI-powered itinerary recommendations, and vote using ranked-choice voting to finalize plans.

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
- **Default AI Model:** Qwen-3-235B-A22B-Instruct (`qwen-3-235b-a22b-instruct-2507`)
- **Auth:** Email + password (trip creators), token-based links + trip code/PIN (participants)
- **Password Hashing:** `bcrypt` directly — do NOT use `passlib` (incompatible with `bcrypt >= 4.0`)

### Frontend
- **Language:** TypeScript
- **Framework:** React 18+ with Vite
- **UI Library:** shadcn/ui (uses `@base-ui/react` primitives, NOT `@radix-ui`) + Tailwind CSS
- **Node Version:** 22 LTS
- **Package Manager:** pnpm

### Infrastructure
- **Deployment:** Railway — builder is **Railpack** (do NOT use `builder = "nixpacks"`)
- **CI/CD:** GitHub Actions (do NOT modify `.github/workflows/`)

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

### Git
- **Branching:** `main` + feature branches (`feat/`, `fix/`, `refactor/`, etc.)
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `style:`)
- **PRs:** All changes go through PRs to `main`. Never push directly to `main`.

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
| **AI service** | Use `extract_json()`, never `json.loads()`. Pass `session_factory` (not `session`) to background tasks. | `docs/AI-ARCHITECTURE.md` |
| **Voting** | Pure algorithm in `ranked_choice.py`, DB ops in `service.py`. | `docs/VOTING-ARCHITECTURE.md` |
| **Frontend components** | `@base-ui/react` not `@radix-ui`. DatePicker trigger is `<button>`, not `<Button asChild>`. | `docs/FRONTEND-ARCHITECTURE.md` |
| **Deployment** | `DATABASE_URL` needs `postgresql+asyncpg://` prefix. `VITE_API_URL` baked in at build time. | `docs/DEPLOYMENT.md` |

### Authentication
- Trip creators: email + password
- Participants: token link OR trip code (8-char alphanumeric) + PIN (4 digits, per-participant)
- No account required for participants

### Phase 2 (DO NOT BUILD YET)
Price monitoring agent for finalized trips.

---

## Testing Strategy

### Backend
- Unit tests for all `services/` logic
- Integration tests for API endpoints
- AI tests: mocked by default; `@pytest.mark.live` for real API calls (manual only)

### Frontend
- Vitest + React Testing Library
- Component rendering, user flows, mocked API

### CI/CD
- Every push/PR: lint → type check → unit → integration tests (mocked AI)
- Live AI tests: manual trigger only

---

## Hard Constraints

1. **NEVER read `.env` files directly.** All env var access via `app/core/config.py`.
2. **NEVER push to `main`.** Always use feature branches.
3. **NEVER modify `.github/workflows/` files.**
4. **NEVER approve or merge PRs.** You may open PRs only.

---

## Workflow

- Use **Plan Mode** as default for all non-trivial changes.
- Read relevant code first, create a plan, get approval, then implement.
- For trivial fixes (typos, single-line changes), normal mode is fine.
- Always explain what you intend to do and wait for confirmation before making changes.
