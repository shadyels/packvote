from app.schemas.vote import VoteRoundResult, VotingResults


def run_instant_runoff(
    trip_id: int,
    iteration_number: int,
    votes: list[list[int]],
    candidates: list[int],
) -> VotingResults:
    """Run instant-runoff / ranked-choice voting.

    Args:
        trip_id: ID of the trip.
        iteration_number: Current iteration number.
        votes: List of ranked ballots. Each ballot is an ordered list
               of itinerary IDs (most preferred first).
        candidates: All itinerary IDs in this round.

    Returns:
        VotingResults with all rounds and the winner (or None if tie).

    Algorithm:
        1. Count first-choice votes for each remaining candidate.
        2. If one candidate has >50% of votes, it wins.
        3. Eliminate the candidate with the fewest first-choice votes.
           On a tie for last place, eliminate the candidate with the lowest ID
           (deterministic tiebreaker).
        4. Redistribute eliminated candidate's votes to next preference.
        5. Repeat until a winner or unresolvable tie (all remaining candidates
           have identical vote counts).
    """
    if not votes:
        return VotingResults(
            trip_id=trip_id,
            iteration_number=iteration_number,
            rounds=[],
            winner_id=None,
            is_complete=False,
        )

    remaining = set(candidates)
    rounds: list[VoteRoundResult] = []
    round_number = 1

    while remaining:
        # Count first-choice votes for remaining candidates
        tally: dict[int, int] = {c: 0 for c in remaining}
        for ballot in votes:
            for choice in ballot:
                if choice in remaining:
                    tally[choice] += 1
                    break
            # If no choice in remaining, ballot is exhausted — skip

        total = sum(tally.values())

        # Check for a majority winner
        winner_id: int | None = None
        for candidate_id, count in tally.items():
            if total > 0 and count > total / 2:
                winner_id = candidate_id
                break

        if winner_id is not None:
            rounds.append(
                VoteRoundResult(
                    round_number=round_number,
                    results=dict(tally),
                    eliminated_option_id=None,
                    winner_id=winner_id,
                )
            )
            return VotingResults(
                trip_id=trip_id,
                iteration_number=iteration_number,
                rounds=rounds,
                winner_id=winner_id,
                is_complete=True,
            )

        # If only one candidate remains, they win
        if len(remaining) == 1:
            sole = next(iter(remaining))
            rounds.append(
                VoteRoundResult(
                    round_number=round_number,
                    results=dict(tally),
                    eliminated_option_id=None,
                    winner_id=sole,
                )
            )
            return VotingResults(
                trip_id=trip_id,
                iteration_number=iteration_number,
                rounds=rounds,
                winner_id=sole,
                is_complete=True,
            )

        # Check for an unresolvable tie (all counts equal)
        counts = list(tally.values())
        if len(set(counts)) == 1:
            rounds.append(
                VoteRoundResult(
                    round_number=round_number,
                    results=dict(tally),
                    eliminated_option_id=None,
                    winner_id=None,
                )
            )
            return VotingResults(
                trip_id=trip_id,
                iteration_number=iteration_number,
                rounds=rounds,
                winner_id=None,
                is_complete=True,
            )

        # Eliminate the candidate with fewest votes; break ties by lowest ID
        min_votes = min(tally.values())
        last_place = [c for c, v in tally.items() if v == min_votes]
        eliminated = min(last_place)  # deterministic: lowest ID

        rounds.append(
            VoteRoundResult(
                round_number=round_number,
                results=dict(tally),
                eliminated_option_id=eliminated,
                winner_id=None,
            )
        )
        remaining.remove(eliminated)
        round_number += 1

    # Should not reach here; return tie if candidates list was empty
    return VotingResults(
        trip_id=trip_id,
        iteration_number=iteration_number,
        rounds=rounds,
        winner_id=None,
        is_complete=True,
    )
