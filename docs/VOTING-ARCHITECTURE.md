# Voting Architecture — PackVote

## System Design

- Full ranked-choice / instant-runoff voting
- 2–5 itinerary options per round (trip creator chooses at creation)
- New iteration triggered by: no clear majority OR admin manual trigger
- Maximum 10 iterations
- Admin vote carries equal weight

## Implementation Patterns

**Creator is a first-class Participant:**
`create_trip` inserts a `Participant` row for the trip creator with `user_id = creator.id` and `preferences_submitted = True`. The creator's intent is expressed at trip creation; no separate preference submission is required or expected. The `Participant.user_id` FK (nullable) links the creator row to the `users` table. Invited participants have `user_id = NULL`. A partial-unique index on `(trip_id, user_id) WHERE user_id IS NOT NULL` enforces at most one creator row per trip.

**Admin voting routes through the creator's Participant row:**
`submit_admin_vote` looks up the `Participant` row where `trip_id` and `user_id` match the authenticated creator, then calls `_upsert_vote` with `participant_id = creator_participant.id, user_id = None`. This means all votes — participant and admin — are uniformly stored with `participant_id` set. `Vote.user_id` is write-dead (kept for schema compatibility; never written by new code).

**Pure algorithm separation:**
`services/voting/ranked_choice.py` is a pure stateless function (no DB, no I/O). `services/voting/service.py` handles all DB operations and calls the algorithm. This keeps the algorithm trivially unit-testable without DB setup.

**Auto-tally and auto-finalize on last vote:**
When all `Participant` rows for the trip have submitted votes for the current iteration, `_maybe_auto_tally` runs automatically. It persists `VoteRound` rows and, if the IRV algorithm produces a clear winner, commits `trip.status = "FINALIZED"` + `trip.winner_itinerary_id` atomically and fires finalized-itinerary emails — no admin action required. Ties leave the trip in `VOTING` for the admin to resolve via `pick_winner`. `eligible = participant_count` — no `+1` fudge because the creator is already a participant. Results also available on-demand via `GET /votes/trips/{id}/results` (computes if not stored, uses stored rows if present).

**Participant vote auth uses token-in-path:**
`POST /votes/trips/{trip_id}/vote/{token}` — same pattern as `POST /participants/{token}/preferences`.

**Re-voting allowed:**
Submitting a vote for the same trip+iteration overwrites the previous (upsert semantics). One `Vote` row per voter per trip per iteration.

**Deterministic tiebreaker:**
When candidates tie for fewest votes during elimination, the one with the lowest ID is eliminated. Ensures reproducible results.

**`pick_winner` bypasses voting:**
Admin can set `trip.winner_itinerary_id` and transition to `FINALIZED` at any time from `VOTING` or `ITERATING`, overriding ranked-choice.

**`new-iteration` triggers generation directly:**
Status: `VOTING` → `GENERATING` (not `VOTING` → `ITERATING` → `GENERATING`). `ITERATING` is reserved for a future follow-up survey flow.
