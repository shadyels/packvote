"""Unit tests for the pure ranked-choice / instant-runoff algorithm."""

from app.services.voting.ranked_choice import run_instant_runoff

TRIP_ID = 1
ITERATION = 1


class TestMajorityInRoundOne:
    def test_clear_majority_wins(self) -> None:
        # 3 votes for candidate 10, 1 for 20 → 10 wins in round 1
        votes = [[10, 20], [10, 20], [10, 20], [20, 10]]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [10, 20])
        assert result.winner_id == 10
        assert result.is_complete is True
        assert len(result.rounds) == 1
        assert result.rounds[0].winner_id == 10
        assert result.rounds[0].eliminated_option_id is None

    def test_exactly_majority_wins(self) -> None:
        # 3 out of 5 = 60% → majority
        votes = [[10], [10], [10], [20], [30]]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [10, 20, 30])
        assert result.winner_id == 10

    def test_no_majority_does_not_win_in_round_one(self) -> None:
        # 2 out of 4 = 50%, not >50% → no winner in round 1
        votes = [[10, 20], [10, 20], [20, 10], [20, 10]]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [10, 20])
        # With 2 candidates and a tie, all counts are equal → tie result
        assert result.is_complete is True
        assert result.winner_id is None


class TestElimination:
    def test_elimination_leads_to_winner(self) -> None:
        # Round 1: 10→2, 20→2, 30→1 → 30 eliminated
        # Round 2: 10→3, 20→2 → 10 wins (>50% of 5)
        votes = [
            [10, 20, 30],
            [10, 30, 20],
            [20, 10, 30],
            [20, 30, 10],
            [30, 10, 20],
        ]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [10, 20, 30])
        assert result.winner_id == 10
        assert result.is_complete is True
        assert len(result.rounds) == 2
        assert result.rounds[0].eliminated_option_id == 30
        assert result.rounds[1].winner_id == 10

    def test_multi_round_five_candidates(self) -> None:
        # 5 candidates, sequential elimination until one wins
        votes = [
            [1, 2, 3, 4, 5],
            [1, 2, 3, 4, 5],
            [1, 2, 3, 4, 5],
            [2, 1, 3, 4, 5],
            [3, 2, 1, 4, 5],
            [4, 2, 3, 1, 5],
            [5, 2, 3, 4, 1],
        ]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [1, 2, 3, 4, 5])
        assert result.winner_id is not None
        assert result.is_complete is True


class TestTie:
    def test_full_tie_all_equal(self) -> None:
        # 2 votes each for 3 candidates — all equal, unresolvable
        votes = [
            [10, 20, 30],
            [10, 20, 30],
            [20, 30, 10],
            [20, 30, 10],
            [30, 10, 20],
            [30, 10, 20],
        ]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [10, 20, 30])
        assert result.winner_id is None
        assert result.is_complete is True

    def test_two_candidate_tie(self) -> None:
        votes = [[10, 20], [20, 10]]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [10, 20])
        assert result.winner_id is None
        assert result.is_complete is True


class TestEdgeCases:
    def test_no_votes(self) -> None:
        result = run_instant_runoff(TRIP_ID, ITERATION, [], [10, 20])
        assert result.winner_id is None
        assert result.is_complete is False
        assert result.rounds == []

    def test_single_candidate(self) -> None:
        votes = [[42], [42]]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [42])
        assert result.winner_id == 42
        assert result.is_complete is True
        assert len(result.rounds) == 1

    def test_exhausted_ballots(self) -> None:
        # Voter 3 only ranked candidate 30, which gets eliminated first
        # Their ballot is exhausted after 30 is eliminated
        votes = [
            [10, 20, 30],
            [10, 20, 30],
            [20, 10, 30],
            [30],  # exhausted after round 1
        ]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [10, 20, 30])
        # 30 has 1 vote, gets eliminated. Remaining: 10(2), 20(1) → 10 wins (2/3 > 50%)
        assert result.winner_id == 10
        assert result.is_complete is True

    def test_deterministic_tiebreaker_lowest_id_eliminated(self) -> None:
        # Round 1: 30→2, 10→1, 20→1 (no majority — 2/4 = 50%, not >50%)
        # 10 and 20 tied for last; lowest ID (10) must be eliminated
        votes = [
            [30, 10, 20],
            [30, 20, 10],
            [10, 20, 30],
            [20, 10, 30],
        ]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [10, 20, 30])
        assert result.rounds[0].eliminated_option_id == 10

    def test_results_have_correct_trip_and_iteration(self) -> None:
        votes = [[7, 8], [7, 8], [8, 7]]
        result = run_instant_runoff(99, 3, votes, [7, 8])
        assert result.trip_id == 99
        assert result.iteration_number == 3

    def test_round_results_contain_all_remaining_candidates(self) -> None:
        votes = [[10, 20, 30], [20, 10, 30], [30, 10, 20]]
        result = run_instant_runoff(TRIP_ID, ITERATION, votes, [10, 20, 30])
        # First round must have tallies for all 3 candidates
        assert set(result.rounds[0].results.keys()) == {10, 20, 30}
