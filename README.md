# PackVote

**AI-powered collaborative trip planning — from idea to voted-on itinerary.**

Live demo: [https://packvote.shadyels.com](https://packvote.shadyels.com)

---

## What it does

Planning a group trip means juggling mismatched schedules, budgets, and interests across dozens of messages. PackVote replaces that chaos with a structured workflow: a trip creator invites participants, everyone submits their preferences, an AI generates personalised itinerary options, and the group votes using ranked-choice to reach a fair consensus — all without participants needing to create an account.

---

## Key Features

- **AI itinerary generation** — Qwen-3-235B (Cerebras) generates complete day-by-day itineraries tailored to group preferences
- **Ranked-choice voting** — full instant-runoff algorithm; re-voting supported; auto-tally when all votes are in; creator can manually finalise at any time
- **Zero-friction participant flow** — no account required; join via a tokenized email link or trip code + 4-digit PIN
- **Real-time status tracking** — 7 trip statuses (CREATED → COLLECTING\_PREFERENCES → GENERATING → GENERATION\_FAILED → VOTING → ITERATING → FINALIZED) with polling and live UI updates
- **Destination photography** — Unsplash API integration with in-memory caching, graceful gradient fallback, and proper attribution
- **Transactional email** — Brevo-powered invitations containing the direct link and trip code + PIN
- **Multi-iteration support** — if no winner emerges, the creator triggers a new AI generation round (up to 10 iterations)
- **AI observability** — every generation is logged with provider, model, latency, token counts, and raw response on failure

---

## How It Works

1. **Create a trip** — set a destination (or let the AI surprise the group), travel dates, number of itinerary options, and invite participants by email
2. **Participants submit preferences** — dates, budget range (8 currencies), interests, and activity tags; no account needed
3. **AI generates options** — once all preferences are in (auto-triggered) or manually by the creator, the AI produces 2–5 full itineraries with daily plans and budget breakdowns
4. **Everyone votes** — participants rank the options; ranked-choice tallies the result automatically
5. **Trip finalised** — the winning itinerary is displayed to all participants with Unsplash destination imagery

---

## Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| Python 3.12 + FastAPI | Async REST API (ASGI) |
| SQLAlchemy (async) + asyncpg | ORM + PostgreSQL async driver |
| Alembic | Database migrations |
| Pydantic v2 + pydantic-settings | Schema validation + config |
| python-jose + bcrypt | JWT auth + password hashing |
| cerebras-cloud-sdk `AsyncCerebras` | AI inference (Cerebras) |
| Brevo API | Transactional email |
| Ruff | Linting + formatting |
| pytest + pytest-asyncio | Testing |

### Frontend

| Technology | Purpose |
|---|---|
| React 18 + TypeScript | UI framework |
| Vite | Build tool |
| Tailwind CSS + shadcn/ui + @base-ui/react | Styling + component library (base-ui primitives, not Radix) |
| React Router v6 | Client-side routing |
| Lucide React | Icons |
| date-fns + react-day-picker v9 | Date utilities + custom drill-down calendar |
| Sonner | Toast notifications |
| Vitest + React Testing Library | Testing |

### Infrastructure

| Technology | Purpose |
|---|---|
| Railway (Railpack) | Deployment — 2 services (backend + frontend) |
| PostgreSQL | Production database (Railway add-on) |
| GitHub Actions | CI/CD — lint → type-check → unit tests → integration tests |
| Cerebras | AI inference provider |
| Unsplash API | Destination photography |

---

## Architecture Highlights

- **Provider-agnostic AI service** — `CerebrasProvider` implements the `AIProvider` interface; the service retries up to 3× with exponential backoff on transient failures
- **Background task session isolation** — FastAPI closes request-scoped DB sessions before background tasks run; generation tasks open their own `async with session_factory()` session to avoid stale-connection errors
- **Pure ranked-choice algorithm** — `services/voting/ranked_choice.py` is a stateless function with zero DB dependencies, making it trivially unit-testable and reusable
- **Robust AI JSON extraction** — open-source models sometimes wrap responses in markdown fences; `extract_json()` tries direct parse → strip fences → brace-extraction before raising `AIParseError` with the raw text attached for logging
- **Versioned prompt templates** — stored in the DB, seeded at runtime (idempotent); designed to support A/B testing across prompt versions with per-version metrics
- **Dual auth model** — JWT for trip creators; tokenized links + trip code/PIN for participants (no account creation)

---

## Project Structure

```
packvote/
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers (trips, participants, votes, auth, admin)
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── ai/         # Provider-agnostic AI service layer
│   │   │   ├── voting/     # Ranked-choice algorithm + DB service
│   │   │   └── email/      # Brevo integration
│   │   ├── prompts/        # Versioned prompt templates
│   │   └── core/           # Config, security, dependencies
│   └── tests/              # Unit + integration tests (SQLite in-memory)
└── frontend/
    └── src/
        ├── components/     # Reusable UI (shadcn/ui + custom)
        ├── pages/          # Route pages
        ├── hooks/          # Custom React hooks (useTripDetail, useTripView, useAuth)
        ├── lib/            # API client, utilities, Unsplash integration
        └── types/          # TypeScript type definitions
```

---

## Getting Started

### Prerequisites
- Python 3.12+, `uv`
- Node 22, `pnpm`
- PostgreSQL (or Docker)

### Backend
```bash
# Start a local PostgreSQL instance (Docker)
docker run -d --name packvote-db \
  -e POSTGRES_USER=packvote \
  -e POSTGRES_PASSWORD=packvote \
  -e POSTGRES_DB=packvote \
  -p 5432:5432 postgres:16

cd backend
cp .env.example .env          # fill in DATABASE_URL, SECRET_KEY, CEREBRAS_API_KEY, etc.
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
cp .env.example .env          # set VITE_API_URL=http://localhost:8000
pnpm install
pnpm dev
```

### Running Tests
```bash
# Backend (uses in-memory SQLite — no DB setup needed)
cd backend && uv run pytest

# Frontend
cd frontend && pnpm test
```

---

## Deployment

Both services are deployed on [Railway](https://railway.app) using the Railpack builder.

- **Backend**: FastAPI served by Uvicorn; Alembic migrations run on every deploy
- **Frontend**: Vite production build served by `vite preview`
- **Database**: Railway-managed PostgreSQL add-on
- **CI/CD**: GitHub Actions runs the full test suite on every push and PR

---

## License

MIT
