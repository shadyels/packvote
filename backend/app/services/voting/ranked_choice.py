from app.schemas.vote import VotingResults


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
        4. Redistribute eliminated candidate's votes to next preference.
        5. Repeat until a winner or unresolvable tie.
    """
    # TODO: implement in voting step
    raise NotImplementedError
