# REQUIREMENTS.md — PackVote

## Project Vision

PackVote is an AI-powered group travel planning application designed to eliminate the chaos of group trip coordination. It collects preferences from all participants, uses AI to generate personalized destination and itinerary recommendations, and lets the group decide democratically through ranked-choice voting.

**Portfolio context:** This project is part of a GitHub portfolio aimed at attracting investors, employers, and recruiters. Code quality, architecture decisions, testing, and documentation all matter.

---

## User Roles

### Trip Creator (Admin)
- Has an authenticated account (email + password)
- Creates and manages trips from a dashboard
- Sees all their trips, statuses, votes, and metrics
- Can trigger new voting iterations or manually pick a winner
- Has equal voting weight as participants during normal voting

### Participant
- Does NOT need an account
- Accesses trip pages via:
  - **Tokenized email link** (unique per participant per trip)
  - **Trip ID (8 digits) + PIN (4 digits)** entered on a retrieval form (like booking.com)
- There is no additional security beyond the ID+PIN combination — no login, no CAPTCHA, no account required
- Submits preferences (dates, budget, interests)
- Votes on AI-generated itineraries via ranked-choice

---

## Core Features (Phase 1)

### F1: Trip Creator Authentication
- Email + password registration and login
- Secure session/token management
- Architecture must support adding OAuth (Google, etc.) later without rewrite
- Authenticated dashboard showing all trips with status

### F2: Trip Creation
- Admin creates a trip with:
  - Destination (or "surprise me" — let AI decide)
  - Proposed travel dates
  - Number of itinerary options to generate (2–5, chosen by admin)
  - Participant list (email addresses)
- Each trip gets:
  - Unique 8-character alphanumeric code (uppercase A-Z + 0-9)
  - Unique 4-digit numeric PIN
- On creation, SendGrid emails are sent to all participants with:
  - Invitation text
  - Direct tokenized link to the trip preference page
  - Trip ID and PIN for manual access

### F3: Participant Preference Collection
- Participant lands on trip page (via link or ID+PIN)
- Submits:
  - Preferred travel dates (date range picker)
  - Budget range (min–max in their currency)
  - Interests / activity preferences (free text and/or category tags)
- Preferences are stored and associated with the participant

### F4: AI-Powered Recommendation Generation
- Generation has two triggers (both result in identical behaviour):
  - **Auto:** fires automatically when the last participant submits their preferences
  - **Manual:** admin hits `POST /trips/{id}/generate` at any time, even before all participants have submitted
- If both triggers race (e.g. last preference submitted at the same moment the admin clicks generate), the second trigger is silently ignored via the status guard — only one generation runs
- The endpoint returns **202 Accepted** immediately; generation runs as a background task. The client polls `GET /trips/{id}` until status changes from `GENERATING` to `VOTING`
- AI receives all participant preferences in a single prompt — no separate summarisation call (one AI credit per generation)
- AI receives:
  - All participant preferences (dates, budgets, interests, activity tags)
  - Trip constraints (destination if specified, or "open" if "surprise me"; number of options; proposed dates)
  - Current prompt template (from versioned prompt system)
- AI generates N itinerary options (N = 2–5, set at trip creation), each containing:
  - Destination name and description
  - Day-by-day itinerary with 3–5 activities per day
  - Total estimated budget and currency
  - Why this matches the group's preferences (`match_reasoning`)
  - Highlights list
- All AI output is structured JSON, validated by Pydantic schemas
- Failed/invalid AI responses are retried with exponential backoff (3 attempts on HuggingFace, then 1 attempt on Groq fallback)
- If all providers fail, trip status is reset to `COLLECTING_PREFERENCES` so the admin can retry
- Each generation is logged with: prompt version, model used, provider used, latency, response validity

### F5: Ranked-Choice Voting
- After AI generates options, participants receive an email notification with a link
- Each participant ranks all itinerary options from most to least preferred
- Voting uses full instant-runoff / ranked-choice:
  1. Count first-choice votes
  2. If one option has a majority (>50%), it wins
  3. If no majority, eliminate the option with fewest first-choice votes
  4. Redistribute eliminated option's votes to each voter's next preference
  5. Repeat until a winner emerges or a tie occurs
- Admin can also vote (equal weight)
- Admin can manually pick a winner at any time (overrides voting)
- All votes and rounds are stored for analytics

### F6: Iteration Flow
- If no clear majority after ranked-choice resolution → system flags for new iteration
- Admin can also manually trigger a new iteration at any point
- On new iteration:
  - AI generates follow-up survey questions (decided by AI based on previous round results and feedback) — **NOT YET BUILT** (see note below)
  - Participants receive email with link to follow-up survey — **NOT YET BUILT**
  - AI generates new itinerary options incorporating new feedback ✅
  - New ranked-choice vote begins ✅
- Maximum 10 iterations per trip ✅
- Admin can close voting at any time by:
  - Manually picking a winner ✅
  - Accepting the current ranked-choice winner ✅
- Trip status flow: `CREATED` → `COLLECTING_PREFERENCES` → `GENERATING` → `VOTING` → `ITERATING` → `FINALIZED`

**F6 implementation status:** The iteration *mechanics* are built — `POST /trips/{id}/new-iteration` triggers a new AI generation round and resets voting. What is **not yet built** is the *survey phase*: after a no-majority result, the AI should analyse the previous round and generate targeted follow-up questions before re-generation. This requires a new AI prompt, a survey response data model, a participant survey UI, and the `ITERATING` status (currently unused — new iteration goes `VOTING → GENERATING` directly, skipping `ITERATING`). The `send_new_iteration_notification` email exists but the `survey_questions` param was removed until this is built.

### F7: Trip Page (Participant View)
- Persistent page accessible via link or ID+PIN
- Shows:
  - Trip status
  - Who has responded (names/initials, not emails)
  - Current itinerary options (when generated)
  - Voting interface (when in voting phase)
  - Final result (when finalized)
- Fully responsive — must work well on mobile (participants will open email links on phones)

### F8: Trip Creator Dashboard
- Authenticated, creator-only view
- Shows:
  - All trips with status badges
  - Participant response progress per trip
  - Voting results and round details
  - AI generation history (prompt version, model, latency)
  - Controls: trigger generation, trigger new iteration, pick winner, close voting

### F9: Email Notifications (SendGrid)
- Triggered at each stage:
  - Trip created → invitation to submit preferences
  - AI generated options → invitation to vote
  - New iteration → follow-up survey notification
  - Trip finalized → final itinerary notification
- Every email includes:
  - Direct tokenized link
  - Trip ID and PIN
  - Relevant context (what action is needed)
- SendGrid free tier: 100 emails/day

---

## AI Pipeline Architecture

### Provider-Agnostic Service Layer
```
AIServiceLayer (abstract interface)
├── HuggingFaceProvider (default)
│   └── Routes via HF Inference Providers API
│   └── Supports: Sambanova, Together AI, Cerebras, Groq, etc.
├── GroqProvider (fallback)
│   └── Direct Groq API (free tier)
└── Any future OpenAI-compatible provider
```

- All providers implement the same interface: `generate_itineraries()`, `generate_followup_survey()`, `organize_preferences()`
- Provider selection is configurable per request (for A/B testing)
- Automatic fallback: if primary provider fails or credits exhausted, try fallback

### Default Model: Qwen2.5-72B-Instruct
Chosen for:
- Best-in-class structured JSON output among open-source models
- Superior instruction following reliability for structured data generation
- Token-efficient (no thinking mode overhead), critical for limited free-tier credits
- Apache 2.0 licensed, commercially usable
- Widely available across multiple HuggingFace Inference Providers (Sambanova, Together, etc.)
- Qwen 3.5 variants available as swappable alternatives for A/B testing

### Prompt Management
- Prompts stored in database table: `prompt_templates`
  - Fields: id, name, version, template_text, model_target, is_active, created_at
- Each AI call logs: prompt_version_id, model_used, provider, latency_ms, token_count, response_valid (bool)
- Basic A/B testing:
  - Traffic split configurable (e.g., 50/50 between prompt v1 and v2)
  - Metrics per version: average response quality, vote outcome correlation, latency
  - Admin can view results and promote winning version

### AI Output Schema (validated by Pydantic)
Each itinerary option must include:
- `destination_name`: string
- `destination_description`: string
- `daily_itinerary`: list of day objects (day_number, title, activities, estimated_cost)
- `total_estimated_budget`: number
- `currency`: string
- `match_reasoning`: string (why this fits the group)
- `highlights`: list of strings

---

## Phase 2 Feature: Price Monitoring Agent

**Do not build in Phase 1. Document only.**

### Overview
An agent that fetches live prices for finalized trip itineraries so the group can see real costs before booking.

### Trigger
- Manual "Update Prices" button on finalized trip page (admin only)
- No background worker — on-demand only

### Data Sources
- Free structured APIs (specific providers TBD in Phase 2)
- Prioritize free API availability over completeness of data
- Categories: flights, hotels, activities

### Budget Logic
- Soft constraint, not hard: the system tries to respect budgets but does not exclude options that exceed them
- Rule of thumb:
  - Aim to stay below the **lowest** participant budget
  - If not possible, do not exceed the **average group budget by more than 30%**
- Participants are **notified** when a trip's estimated cost exceeds their stated budget
- Budget alerts are informational, not blocking

### Data Model Consideration
- In Phase 1, ensure the itinerary data model includes nullable price fields so Phase 2 can populate them without schema migration:
  - `estimated_cost` on daily itinerary items
  - `price_last_updated` timestamp
  - `price_source` string

---

## Phase 3 Feature: System Monitoring Dashboard

**Do not build in Phase 1 or Phase 2. Document only.**

### Overview
An ops-level monitoring dashboard for the platform administrator only. Not accessible to registered trip creators.

### Metrics to Track
- API request counts and latency
- Active trips and users
- AI pipeline response times
- Vote completion rates
- Error rates
- Email delivery success rates

### Tech Stack (TBD)
- Option A: PostgreSQL (existing) + Grafana — simpler, no new infra
- Option B: Prometheus + Grafana — industry standard, more powerful for time-series
- Decision deferred to Phase 3

### Access Control
- Accessible only to the platform admin, NOT to regular registered users
- Separate from the Trip Creator Dashboard (F8)

---

## Architecture Decisions

### Email Notifications over SMS
SMS (Twilio) was considered and rejected in favor of email (SendGrid) because:
- SMS feels dated for this use case — participants are more accustomed to email-based collaboration
- Email is cheaper (SendGrid free tier: 100/day) vs Twilio ($1.15/month for a number + per-message costs)
- Email allows richer content (HTML formatting, direct links, trip details)
- Easier to test during development (multiple email addresses vs single phone number)
- Email links bring participants into the in-app experience where they can see full trip status

### REST API (not GraphQL)
PackVote uses a REST API. GraphQL was considered and rejected because:
- The data model is straightforward (trips, participants, votes, itineraries) with no deeply nested queries
- There is a single frontend client — no need for flexible query shapes across different clients
- REST endpoints map naturally to the app's operations (`GET /trips/{id}`, `POST /trips/{id}/vote`, etc.)
- GraphQL would add schema definition and resolver boilerplate without meaningful benefit

### HuggingFace Inference Providers Free Tier
The project uses HuggingFace's free tier, which has significant constraints:
- Limited monthly inference credits (exact amount not publicly documented, but users report hitting limits with moderate usage)
- Rate limits on requests per minute/day
- This is why Qwen2.5-72B-Instruct was chosen over Qwen 3.5 (no thinking mode token overhead)
- This is why the provider-agnostic service layer includes a Groq free tier fallback
- AI calls should be minimized: generate only when needed, cache results, avoid redundant calls
- Failed requests should use exponential backoff, not immediate retries

### Async Generation (202 + polling) over Synchronous Response
AI generation can take 10–30 seconds. Returning a synchronous response would risk HTTP timeouts and a poor user experience. Instead:
- `POST /trips/{id}/generate` returns 202 immediately and schedules a background task
- Trip status transitions from `GENERATING` → `VOTING` when complete
- Clients poll `GET /trips/{id}` to detect the transition
- This was chosen over WebSockets (overkill for a low-frequency status change) and server-sent events (added complexity with no benefit at this scale)

### Single Prompt per Generation (No Pre-Summarisation)
Raw participant preferences are fed directly into one generation prompt rather than using a separate AI call to summarise/organise them first. Reasons:
- Saves AI credits (one call vs two per generation)
- Participant data is already structured (dates, budget range, tags) — it doesn't need narrative summarisation to be useful to the model
- A separate summarisation call would add latency to an already-slow pipeline
- If group size grows very large (10+ participants), this decision can be revisited

### BackgroundTasks over a Task Queue
FastAPI's built-in `BackgroundTasks` is used rather than an external task queue (Celery, Redis Queue, etc.) because:
- Generation is a single async function, not a distributed workload
- No retry persistence is needed at this scale — if the server restarts mid-generation, the trip stays in `GENERATING` and the admin can manually re-trigger
- Avoids adding Redis or a broker as an infrastructure dependency on the free Railway tier
- If the app scales to high concurrency or needs durable retries in the future, migrating to a task queue is straightforward

---

## Non-Functional Requirements

### Performance
- API response time: < 500ms for standard endpoints
- AI generation: < 60s timeout (with loading UI)
- Frontend: Lighthouse performance score > 80

### Security
- Password hashing (bcrypt or argon2)
- JWT or session tokens for admin auth
- Tokenized participant links with expiry
- Rate limiting on auth endpoints and AI generation
- Input sanitization on all user inputs
- CORS configured for frontend domain only

### Accessibility
- Semantic HTML
- Keyboard navigation support
- Sufficient color contrast (especially with black/cream/orange palette)
- Screen reader friendly

### Testing
- Backend: pytest + httpx (unit + integration)
- Frontend: Vitest + React Testing Library
- AI pipeline: mocked responses by default, small live suite (`@pytest.mark.live`)
- CI/CD: GitHub Actions runs lint → typecheck → tests on every push/PR
- Live AI tests: manual trigger or scheduled, not on every CI run

---

## Database Schema (High-Level)

### Core Tables
- `users` — trip creators (email, hashed_password, created_at)
- `trips` — (id, trip_code_8char_alphanum, pin_4digit, creator_id, destination, proposed_dates, num_options, status, max_iterations, current_iteration, created_at)
- `participants` — (id, trip_id, email, name, token, preferences_submitted, created_at)
- `preferences` — (id, participant_id, trip_id, preferred_dates, budget_min, budget_max, currency, interests, submitted_at)
- `itineraries` — (id, trip_id, iteration_number, destination_name, description, daily_itinerary_json, total_estimated_budget, currency, match_reasoning, highlights, estimated_cost, price_last_updated, price_source, prompt_version_id, model_used, provider, generation_latency_ms, created_at)
- `votes` — (id, participant_id nullable, user_id nullable, trip_id, iteration_number, rankings_json, submitted_at) — exactly one of participant_id or user_id must be set (participant_id for participant votes, user_id for admin/creator votes)
- `vote_rounds` — (id, trip_id, iteration_number, round_number, eliminated_option_id, results_json, winner_id, created_at)

### AI & Monitoring Tables
- `prompt_templates` — (id, name, version, template_text, model_target, is_active, ab_test_group, traffic_weight, created_at)
- `ai_call_logs` — (id, trip_id, prompt_version_id, model_used, provider, latency_ms, token_count_input, token_count_output, response_valid, error_message, created_at)
- `metrics` — (id, metric_name, metric_value, tags_json, recorded_at)

---

## Deployment

### Railway Configuration
- **Frontend service:** Static build from `frontend/` (Vite build output)
- **Backend service:** Python FastAPI app from `backend/`
- **Database:** Railway managed PostgreSQL add-on
- **Environment variables:** Managed via Railway dashboard (never committed to repo)
- **Domain:** Default Railway subdomain initially; custom domain can be added later

### Environment Variables Needed
- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — JWT/session signing key
- `SENDGRID_API_KEY` — SendGrid email service
- `HF_API_TOKEN` — HuggingFace Inference Providers token
- `GROQ_API_KEY` — Groq fallback provider token (optional)
- `UNSPLASH_ACCESS_KEY` — Unsplash API for travel images
- `FRONTEND_URL` — Frontend base URL (for CORS and email links)
- `ENVIRONMENT` — development / staging / production

---

## Implementation Priority

Build in this order:

1. **Project scaffolding** — Monorepo setup, linting, CI/CD pipeline, database connection
2. **Auth system** — Creator registration/login, JWT, protected routes
3. **Trip CRUD** — Create trip, generate ID+PIN, store participants
4. **Participant flow** — Token links, ID+PIN retrieval, preference form
5. **Email integration** — SendGrid setup, invitation emails
6. **AI pipeline** — Service layer, HuggingFace integration, prompt versioning, itinerary generation
7. **Voting system** — Ranked-choice voting logic, voting UI, iteration flow ✅ *(mechanics done; F6 follow-up survey phase deferred)*
8. **Trip Creator Dashboard** — Trip management, voting results, AI logs, controls
9. **Frontend polish** — Design system (black/cream/orange), Unsplash images, responsive refinement
10. **Testing** — Full test suite, CI integration
11. **Deployment** — Railway setup, environment config, live demo

**Phase 2 (later):** Price monitoring agent

**Phase 3 (later):** System monitoring dashboard (Grafana, admin-only)
