import json
import shutil
from pathlib import Path

import pytest

from evals import run

CASES = Path(run.__file__).parent / "cases.json"


@pytest.fixture
def evals_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    shutil.copy(CASES, tmp_path / "cases.json")
    monkeypatch.setattr(run, "HERE", tmp_path)
    return tmp_path


async def test_failed_run_exits_nonzero_without_writing(
    evals_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_response(*_: object) -> None:
        return None

    monkeypatch.setattr(run, "_generate", no_response)
    with pytest.raises(SystemExit) as exc:
        await run.main()
    assert exc.value.code != 0
    assert not (evals_dir / "results.json").exists()


async def test_half_answered_run_still_writes(
    evals_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    async def every_other_case(*_: object) -> str | None:
        nonlocal calls
        calls += 1
        # Calls alternate v3/v4 per case; drop every second case for both.
        return None if (calls - 1) // 2 % 2 else "{}"

    monkeypatch.setattr(run, "_generate", every_other_case)
    await run.main()
    assert (evals_dir / "results.json").exists()


async def test_case_dropped_for_all_versions_when_one_has_no_response(
    evals_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    async def v4_fails_on_case_three(*_: object) -> str | None:
        nonlocal calls
        calls += 1
        return None if calls == 6 else "{}"  # 6th call = v4 of case 3

    monkeypatch.setattr(run, "_generate", v4_fails_on_case_three)
    await run.main()
    versions = json.loads((evals_dir / "results.json").read_text())["versions"]
    n = len(json.loads(CASES.read_text())) - 1
    assert [v["cases"] for v in versions] == [n, n]


def test_judge_scores_must_be_true_ints() -> None:
    assert run._valid_scores({c: 3 for c in run.CRITERIA}) is not None
    for bad in (4.5, True, 0, 6, "4", None):
        scores = {c: 3 for c in run.CRITERIA} | {"specificity": bad}
        assert run._valid_scores(scores) is None, bad


def test_aggregate_excludes_informational_checks_from_overall() -> None:
    passing = {"json_valid": True, "time_field": True, "time_slots": False}
    agg = run._aggregate(
        "v3", [(passing, None), (passing, {c: 4 for c in run.CRITERIA})]
    )
    assert agg.all_checks_pass_rate == 1.0
    assert (agg.cases, agg.judged_cases) == (2, 1)
    gating = {c.check: c.gating for c in agg.checks}
    assert gating == {"json_valid": True, "time_field": True, "time_slots": False}
