# Testing — PackVote

## Backend

- Unit tests for all `services/` logic in `tests/unit/`. Edge cases and parametrised validation live here.
- Integration tests in `tests/integration/` — broad smoke coverage only: register/login/me round-trip, the voting lifecycle (auto-finalise, tie), admin email resend. Uses in-memory SQLite + `MockEmailService`. CI gates on these collecting + passing (exit 5 if empty).
- AI tests: mocked by default; `@pytest.mark.live` for real API calls (manual only — uses real API credits)

### Shared fixtures and helpers

`backend/tests/conftest.py` (root) serves unit and integration tests:
- `engine` — fresh in-memory `sqlite+aiosqlite` database per test, `StaticPool`, `PRAGMA foreign_keys=ON`. Tests cannot leak state into each other.
- `db` (`AsyncSession`) and `client` (httpx `AsyncClient` over the ASGI app, `get_db` overridden).
- `MockEmailService` / `mock_email` — overrides the email dependency; every `send_trip_email` call is recorded in `.sent`.
- `mock_session_factory` — injects the test engine's session factory for background tasks.
- Autouse: `_fast_bcrypt` (bcrypt cost factor 4) and `_reset_module_state` (clears the Brevo limiter, AI limiter and PIN throttle windows before and after each test).

Other shared code:
- `tests/factories.py` — ORM seed builders `make_user`, `make_trip`, `make_participant`, `make_itinerary`, and `seed_voting_trip` (a VOTING trip with creator, invitee and two itineraries). Each `make_*` adds the row to the session.
- `tests/helpers.py` — URL constants, `register`, `login`, `register_and_login`, `auth_headers`, and `create_trip` (asserts 201).
- `tests/unit/conftest.py` — `auth_headers` fixture (registers and logs in a fresh user).

```bash
cd backend
uv run pytest                    # Run all tests
uv run pytest tests/unit         # Unit tests only
uv run pytest tests/integration  # Integration tests (in-memory SQLite, no real DB needed)
uv run pytest tests/ai -m live   # Live AI tests (manual only — burns API credits)
```

## Frontend

- Vitest + React Testing Library (jsdom). Config in `frontend/vitest.config.ts`; setup file `frontend/tests/setup.ts`
- Component rendering, user flows, mocked API
- Test files live in `__tests__/` folders next to the code:
  - `src/__tests__/routes.test.tsx`
  - `src/pages/__tests__/`: `Dashboard`, `Join`, `Landing`, `Login`, `Trip`, `TripDetail`
  - `src/components/__tests__/`: `Ballot`, `OptionCard`, `PreferenceForm`, `ProtectedRoute`, `Results`, `TripForm`
  - `src/hooks/__tests__/useFetch.test.ts`
  - `src/lib/__tests__/`: `api.test.ts`, `trip.test.ts`
  - `src/contexts/__tests__/AuthContext.test.tsx`

```bash
cd frontend
pnpm test --run                  # Single run (bare `pnpm test` is watch mode)
```

## CI/CD

- Every push/PR: lint → type check → unit → integration tests (mocked AI)
- Live AI tests: manual trigger only
