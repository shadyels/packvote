# Railway Deployment — PackVote

## Service Configuration

Two Railway services, both using **Railpack** builder:

| Service | Root Directory | Config file |
|---------|---------------|-------------|
| Backend | `backend/` | `backend/railway.toml` |
| Frontend | `frontend/` | `frontend/railway.toml` |

Database is a Railway-managed PostgreSQL add-on — `DATABASE_URL` is injected automatically.

**Live domain:** `packvote.shadyels.com` (custom domain configured in Railway dashboard on the frontend service).

## Start Commands

**Backend:** `uv run alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Alembic runs on every deploy (idempotent — only unapplied migrations run)
- Module path must be `app.main:app`, not `main:app` (Railpack auto-detection gets this wrong)

**Frontend:** `pnpm preview --port $PORT --host`
- Railpack auto-detects pnpm from `pnpm-lock.yaml` and runs `pnpm build`
- `.node-version` file in `frontend/` pins Node 22

## Environment Variables

**Backend service:**
- `SECRET_KEY` — JWT signing key. Must be non-default and at least 32 characters unless `ENVIRONMENT=development`; the app refuses to start otherwise
- `BREVO_API_KEY` — Brevo transactional email API key
- `BREVO_FROM_EMAIL` — verified sender address (must be verified in Brevo → Settings → Senders)
- `AI_API_KEY` — inference API key (Google Gemini by default: https://aistudio.google.com/apikey)
- `AI_BASE_URL` — *optional*, defaults to Gemini's OpenAI-compatible endpoint
- `DEFAULT_AI_MODEL` — *optional*, defaults to `gemini-3.6-flash` (`gemini-2.5-flash` was retired for new API keys)
- `FRONTEND_URL` — Frontend public domain, no port (e.g. `https://xxx.up.railway.app`). Used for CORS — must be the public URL, NOT `.railway.internal`
- `ENVIRONMENT` — defaults to `production` (fail-closed); leave it unset or set `production` on Railway. Set `development` only for local runs, which is the only setting that accepts the default `SECRET_KEY`

**Frontend service:**
- `VITE_API_URL` — Backend public domain. **Must be set before first build** — Vite bakes it in at build time. This is the only frontend env var.

## Known Gotchas

**1. DATABASE_URL must use the asyncpg driver prefix**
Railway injects `DATABASE_URL` as `postgresql://...`. Manually edit to `postgresql+asyncpg://...` in the Railway dashboard. Without this, Alembic fails and uvicorn never starts ("1/1 replicas never became healthy").

**2. Public domain target port for backend is 8000**
Railway maps public HTTPS (443) → internal port 8000. Set this when generating the public domain.

**3. FRONTEND_URL is the public URL, not `.railway.internal`**
CORS validation happens in the browser — outside Railway's private network. Use `https://xxx.up.railway.app`.

**4. Set VITE_API_URL before first frontend deploy**
If deployed before the var is set, the build bakes in an empty value. Redeploy after setting.

**5. `vite preview` allowedHosts must be boolean `true`**
`vite.config.ts` has `preview: { allowedHosts: true }`. Do not change to a string `"true"` — must be boolean.

**6. One-time database wipe before the baseline migration**
Migrations were squashed into a single `0001_baseline` revision (`backend/alembic/versions/0001_baseline.py`). An existing database must be wiped before the first deploy of this revision: drop all tables and the `alembic_version` table, then let `alembic upgrade head` (in the start command) create the schema.

**7. Startup recovery assumes a single process**
On startup, `recover_stuck_generations` marks every trip left in `GENERATING` as `GENERATION_FAILED`. This is correct for one uvicorn process. During a zero-downtime deploy, the new instance fails generations still running on the old one; the old run's write-phase CAS then discards its result, so the user must retry. Upgrade path (undecided): a heartbeat/lease column on the trip.

**8. Trip dates can shift by a day on a non-UTC backend host (known issue, fix undecided)**
Trip dates are stored as `timestamptz` and are set from date-only input. On a backend host whose timezone is not UTC, they can shift by a day. Observed with `Europe/Zurich`: 1 Mar was stored as 28 Feb 23:00Z, and re-saving the edit form shifted it again. A host running in UTC is unaffected; the production host's timezone has not been verified. The fix is undecided.
