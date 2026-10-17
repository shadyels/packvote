from collections import Counter

from app.schemas.vote import VoteRoundResult


def tally(
    ballots: list[list[int]], candidate_ids: list[int]
) -> tuple[list[VoteRoundResult], int | None]:
    """Instant-runoff / ranked-choice tally. Pure; returns (rounds, winner_id).

    Each ballot is an ordered list of itinerary IDs (most preferred first).
    A candidate with >50% of the live first-choice votes wins. Otherwise the
    candidate with the fewest votes is eliminated (lowest ID on a tie for last)
    and its ballots move to their next preference. A lone remaining candidate
    wins; if all remaining counts are equal the result is a tie (winner None).
    Exhausted ballots are ignored. No ballots yields ([], None).
    """
    if not ballots:
        return [], None

    remaining = set(candidate_ids)
    rounds: list[VoteRoundResult] = []

    while remaining:
        counts = Counter(dict.fromkeys(sorted(remaining), 0))
        counts.update(
            next((c for c in ballot if c in remaining), None) for ballot in ballots
        )
        counts.pop(None, None)
        total = sum(counts.values())

        winner = next((c for c, n in counts.items() if n > total / 2 and total), None)
        if winner is None and len(remaining) == 1:
            winner = next(iter(remaining))
        tied = len(set(counts.values())) == 1
        eliminated = (
            None
            if winner is not None or tied
            else min(counts, key=lambda c: (counts[c], c))
        )

        rounds.append(
            VoteRoundResult(
                round_number=len(rounds) + 1,
                results=dict(counts),
                eliminated_option_id=eliminated,
                winner_id=winner,
            )
        )
        if eliminated is None:
            return rounds, winner
        remaining.discard(eliminated)

    return rounds, None
