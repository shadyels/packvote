# Testing — PackVote

## Backend

- Unit tests for all `services/` logic in `tests/unit/`
- Integration tests in `tests/integration/` — smoke E2E coverage for auth, trip creation, and participant access, using in-memory SQLite + `MockEmailService`. CI gates on these collecting + passing (exit 5 if empty).
- AI tests: mocked by default; `@pytest.mark.live` for real API calls (manual only — uses real API credits)

```bash
cd backend
uv run pytest                    # Run all tests
uv run pytest tests/unit         # Unit tests only
uv run pytest tests/integration  # Integration tests (in-memory SQLite, no real DB needed)
uv run pytest tests/ai -m live   # Live AI tests (manual only — burns API credits)
```

## Frontend

- Vitest + React Testing Library
- Component rendering, user flows, mocked API

```bash
cd frontend
pnpm test
```

## CI/CD

- Every push/PR: lint → type check → unit → integration tests (mocked AI)
- Live AI tests: manual trigger only
