# Voting Architecture — PackVote

## System Design

- Full ranked-choice / instant-runoff voting
- 2–5 itinerary options per round (trip creator chooses at creation)
- New iteration triggered by: no clear majority OR admin manual trigger
- Maximum 10 iterations
- Admin vote carries equal weight

## Implementation Patterns

**Admin voting via `user_id` on Vote model:**
`Vote` has both `participant_id` (nullable) and `user_id` (nullable) — exactly one must be set. Allows the trip creator to vote without creating a fake `Participant` row. The ranked-choice algorithm only sees `list[list[int]]` — agnostic to voter identity.

**Pure algorithm separation:**
`services/voting/ranked_choice.py` is a pure stateless function (no DB, no I/O). `services/voting/service.py` handles all DB operations and calls the algorithm. This keeps the algorithm trivially unit-testable without DB setup.

**Auto-tally on last vote:**
When all eligible voters (participants + 1 admin) submit votes for the current iteration, the tally runs automatically and persists `VoteRound` rows. Results also available on-demand via `GET /votes/trips/{id}/results` (computes if not stored, uses stored rows if present).

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
