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
`submit_admin_vote` looks up the `Participant` row where `trip_id` and `user_id` match the authenticated creator, then calls `_upsert_vote` with `participant_id = creator_participant.id`. This means all votes — participant and admin — are stored with `participant_id` set. The `votes` table has no `user_id` column.

**Pure algorithm separation:**
`services/voting/ranked_choice.py` exposes `tally(ballots, candidate_ids) -> (rounds, winner_id)`, a pure stateless function (no DB, no I/O) returning `VoteRoundResult` schema objects. `services/voting/service.py` handles all DB operations and calls the algorithm. This keeps the algorithm trivially unit-testable without DB setup.

**Tally rules:** a candidate with more than 50% of the live first-choice votes wins. Otherwise the candidate with the fewest votes is eliminated (lowest ID on a tie) and its ballots move to their next live preference. A lone remaining candidate wins. If all remaining counts are equal the result is a tie (`winner_id` None). Exhausted ballots are ignored; no ballots yields `([], None)`.

**Results are computed on every read:**
`compute_results(db, trip, iteration=None)` tallies the `votes` rows for the iteration on each call; nothing is stored, so results cannot go stale. `GET /votes/trips/{id}/results` returns `VotingResults` (`rounds`, `winner_id`, `is_complete`). For a FINALIZED trip viewed at its current iteration, `winner_id` is `trip.winner_itinerary_id` (the admin may have overridden the tally).

**Results auth (`get_results_trip` in `app/core/dependencies.py`):**
The caller presents a participant token in the `X-Participant-Token` header for this trip, or a bearer JWT of the trip creator or of a linked participant (`Participant.user_id`). Order of checks: no valid credentials → 401; trip missing → 404; valid credentials without access → 403. A valid participant token is not blocked by a stale JWT (the frontend may send both).

**Auto-tally and auto-finalize on last vote:**
When all `Participant` rows for the trip have submitted votes for the current iteration, `_maybe_auto_tally` runs automatically. If the tally produces a winner, the trip is finalised and finalized-itinerary emails are queued — no admin action required. Ties leave the trip in `VOTING` for the admin to resolve via `pick_winner`. `eligible = participant_count` — no `+1` fudge because the creator is already a participant.

**Finalise is a conditional UPDATE:**
`_finalize` runs `UPDATE trips SET status='FINALIZED', winner_itinerary_id=…` `WHERE id = … AND status = 'VOTING' AND current_iteration = <tallied iteration>`. Only the call that sees `rowcount == 1` queues the finalized emails (BackgroundTasks, plain values only). A losing concurrent call returns False: `pick_winner` answers 409, auto-tally does nothing. The `current_iteration` pin keeps a finalise from landing on a newer iteration than the one it tallied.

**Participant vote auth uses token-in-path:**
`POST /votes/trips/{trip_id}/vote/{token}` — same pattern as `POST /participants/{token}/preferences`.

**Re-voting allowed:**
Submitting a vote for the same trip+iteration overwrites the previous (upsert semantics, still 201). One `Vote` row per participant per trip per iteration (`uq_votes_trip_iteration_participant`). If two first votes race, the loser gets 409 ("Vote was submitted concurrently; please retry"). Rankings must be exactly the IDs of the current iteration's itineraries, otherwise 422.

**Deterministic tiebreaker:**
When candidates tie for fewest votes during elimination, the one with the lowest ID is eliminated. Ensures reproducible results.

**`pick_winner` bypasses voting:**
Admin can set `trip.winner_itinerary_id` and transition to `FINALIZED` from `VOTING`, overriding ranked-choice. The itinerary must belong to the trip (404 otherwise), and the transition uses the same conditional finalise as auto-tally (409 if the trip is no longer `VOTING`).

**`new-iteration` triggers generation directly:**
Status: `VOTING` → `GENERATING`. `POST /trips/{id}/new-iteration` requires `VOTING` (409 otherwise) and `current_iteration < max_iterations` (409 otherwise), and claims the run via `start_generation()`.
