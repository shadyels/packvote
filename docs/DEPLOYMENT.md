# Railway Deployment — PackVote

## Service Configuration

Two Railway services, both using **Railpack** builder:

| Service | Root Directory | Config file |
|---------|---------------|-------------|
| Backend | `backend/` | `backend/railway.toml` |
| Frontend | `frontend/` | `frontend/railway.toml` |

Database is a Railway-managed PostgreSQL add-on — `DATABASE_URL` is injected automatically.

## Start Commands

**Backend:** `uv run alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Alembic runs on every deploy (idempotent — only unapplied migrations run)
- Module path must be `app.main:app`, not `main:app` (Railpack auto-detection gets this wrong)

**Frontend:** `pnpm preview --port $PORT --host`
- Railpack auto-detects pnpm from `pnpm-lock.yaml` and runs `pnpm build`
- `.node-version` file in `frontend/` pins Node 22

## Environment Variables

**Backend service:**
- `SECRET_KEY` — JWT signing key
- `BREVO_API_KEY` — Brevo transactional email API key
- `BREVO_FROM_EMAIL` — verified sender address (must be verified in Brevo → Settings → Senders)
- `CEREBRAS_API_KEY` — Cerebras inference API key
- `FRONTEND_URL` — Frontend public domain, no port (e.g. `https://xxx.up.railway.app`). Used for CORS — must be the public URL, NOT `.railway.internal`
- `ENVIRONMENT` — `production`

**Frontend service:**
- `VITE_API_URL` — Backend public domain. **Must be set before first build** — Vite bakes it in at build time.
- `VITE_UNSPLASH_ACCESS_KEY` — Unsplash photos (optional; falls back to gradient)

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
